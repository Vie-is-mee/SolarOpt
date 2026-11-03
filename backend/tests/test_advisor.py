import json

import pytest

from app.schemas import DesignRequest, PanelSpec, ProjectConfig, RectObstacle
from app.services.advisor.agent import propose
from app.services.advisor.llm import LLMError
from app.services.advisor.models import AdvisorRequest, Customer
from app.services.advisor.tariff import monthly_saving, residential_bill, residential_kwh
from app.services.optimizer import generate_design


@pytest.fixture(autouse=True)
def no_real_model(monkeypatch):
    """backend/.env may hold a real key (loaded when app.main is imported): tests never call a live model."""
    monkeypatch.setenv('AI_PROVIDER', 'none')
    monkeypatch.delenv('ADVISOR_BASE_URL', raising=False)


def request(need='min_cost', **customer):
    cfg = ProjectConfig(roof_width_m=12, roof_height_m=9, geometry_confirmed=True)
    obstacles = [RectObstacle(id='tank', label='Bồn nước', x=7, y=5.6, width_m=1.6, depth_m=1.4, height_m=1.2),
                 RectObstacle(id='stair', label='Tum thang', x=1, y=6, width_m=2.5, depth_m=2, height_m=2.7)]
    return AdvisorRequest(config=cfg, panel=PanelSpec(), obstacles=obstacles, need=need,
                          customer=Customer(**({'monthly_kwh': 600, 'daytime_share_pct': 50} | customer)))


class Scripted:
    """Plays back assistant messages; records what it was sent."""
    model = 'fake-model'

    def __init__(self, replies):
        self.replies, self.sent = list(replies), []

    def chat(self, messages, tools=None, json_mode=False):
        self.sent.append(messages[-1])
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def call(i, **args):
    return {'id': f'c{i}', 'type': 'function', 'function': {'name': 'evaluate_scenario', 'arguments': json.dumps(args)}}


def test_stepped_tariff_round_trips_and_removes_the_top_tiers_first():
    assert residential_bill(100, 0) == 50 * 1984 + 50 * 2050
    for kwh in (30, 120, 260, 450, 1200):
        assert residential_kwh(residential_bill(kwh, 8), 8) == pytest.approx(kwh)
    # Saving 100 kWh from a 400 kWh month removes tier 5 (301–400 kWh), not an average price.
    assert monthly_saving(400, 100, 'residential', None, 0) == pytest.approx(100 * 3350)


def test_rule_planner_proposes_grounded_scenarios_and_apply_reproduces_the_choice():
    req = request()
    proposal = propose(req, client=None)
    assert proposal.mode == 'rules' and len(proposal.scenarios) >= 2
    assert proposal.consumption.annual_kwh == 7200 and proposal.consumption.daytime_kwh_year == 3600
    chosen = next(s for s in proposal.scenarios if s.id == proposal.recommended_id)
    assert all(r.refs and all(proposal.facts[k] is not None for k in r.refs) for r in proposal.reasons)
    assert proposal.recommended_budget_vnd >= chosen.investment_vnd
    plan = proposal.apply
    cfg = req.config.model_copy(update={'budget_vnd': plan.budget_vnd, 'target_energy_kwh_year': plan.target_energy_kwh_year, 'layout_edge_reserve_m': plan.layout_edge_reserve_m})
    assert generate_design(DesignRequest(config=cfg, panel=req.panel, obstacles=req.obstacles, objective=plan.objective)).metrics.panel_count == chosen.panel_count


def test_model_picks_scenarios_but_uncited_figures_are_dropped():
    final = {'recommended_id': 'S1', 'summary': 'Chọn S1 vì vừa điện ban ngày.',
             'reasons': [{'text': 'Hoàn vốn nhanh hơn S2.', 'refs': ['S1.payback_years', 'S2.payback_years']},
                         {'text': 'Tiết kiệm 99 triệu mỗi năm.', 'refs': ['made.up']},
                         {'text': 'Khách ưu tiên vốn thấp.', 'refs': []}],
             'risks': ['Giả định 50% điện ban ngày'], 'questions': ['Khách có định lắp điều hòa?']}
    client = Scripted([
        {'content': None, 'tool_calls': [call(1, label='Vừa điện ban ngày', objective='min_cost', target_energy_kwh_year=3600)]},
        {'content': None, 'tool_calls': [call(2, label='Tối đa mái', objective='max_energy')]},
        {'content': json.dumps(final, ensure_ascii=False)},
    ])
    proposal = propose(request(), client=client)
    assert proposal.mode == 'llm' and proposal.model == 'fake-model' and proposal.recommended_id == 'S1'
    assert [s.label for s in proposal.scenarios] == ['Vừa điện ban ngày', 'Tối đa mái']
    texts = [r.text for r in proposal.reasons]
    assert 'Tiết kiệm 99 triệu mỗi năm.' not in texts and 'Khách ưu tiên vốn thấp.' in texts
    assert json.loads(client.sent[1]['content'])['panel_count'] == proposal.scenarios[0].panel_count   # tool result went back to the model


def test_provider_failure_falls_back_to_rules_with_a_notice():
    proposal = propose(request(), client=Scripted([LLMError('groq đang giới hạn số lượt gọi (429).')]))
    assert proposal.mode == 'rules' and '429' in proposal.notice and proposal.scenarios


def test_engineer_budget_note_caps_the_rule_scenarios():
    req = request('max_energy')
    req.feedback = ['Khách chốt ngân sách tối đa 60 triệu, chừa lối đi phía Bắc']
    proposal = propose(req, client=None)
    assert all(s.investment_vnd <= 60e6 for s in proposal.scenarios)
    assert all(s.params.edge_reserve_m == .15 for s in proposal.scenarios)


def test_without_a_bill_the_advisor_asks_instead_of_guessing_demand():
    proposal = propose(request('min_cost', monthly_kwh=None, daytime_share_pct=None), client=None)
    assert proposal.consumption.annual_kwh is None
    assert any('Tiền điện' in q for q in proposal.questions)
    assert all(s.params.objective == 'max_energy' for s in proposal.scenarios)


def test_a_revision_explains_what_changed_and_drops_duplicate_layouts():
    first = propose(request(), client=None)
    req = request()
    req.feedback, req.previous = ['Ngân sách tối đa 40 triệu'], first
    revised = propose(req, client=None)
    assert revised.reasons[0].text.startswith('Theo góp ý (trần vốn 40 triệu đ)')
    assert revised.facts['previous.panel_count'] == next(s for s in first.scenarios if s.id == first.recommended_id).panel_count
    assert len({s.panel_count for s in revised.scenarios}) == len(revised.scenarios)   # same-size layouts are one option
    assert set(revised.plans) == {s.id for s in revised.scenarios}


def test_openai_gateway_config_and_model_fallback(monkeypatch):
    from app.services.advisor import llm
    for name in ('ADVISOR_BASE_URL', 'ADVISOR_API_KEY'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    monkeypatch.setenv('AI_BASE_URL', 'https://gateway.example/v1/')
    monkeypatch.setenv('AI_API_KEY', 'test-key')
    monkeypatch.setenv('AI_MODEL', 'vision-model')
    monkeypatch.setenv('ADVISOR_MODEL', 'big-model, fast-model')
    client = llm.default_client()
    assert client.url == 'https://gateway.example/v1/chat/completions' and client.models == ['big-model', 'fast-model']
    tried = []

    def fake(model, messages, tools, json_mode):
        tried.append(model)
        if model == 'big-model':
            raise llm.LLMError('đang giới hạn số lượt gọi (429)')
        return {'content': 'ok'}
    monkeypatch.setattr(client, '_call', fake)
    assert client.chat([{'role': 'user', 'content': 'x'}]) == {'content': 'ok'}
    client.chat([{'role': 'user', 'content': 'y'}])
    assert tried == ['big-model', 'fast-model', 'fast-model'] and client.model == 'fast-model'
    monkeypatch.setenv('AI_BASE_URL', '')
    assert llm.default_client() is None   # incomplete gateway settings: rule planner, never a broken call


def test_extra_daytime_demand_from_a_note_changes_the_economics():
    base = propose(request(), client=None)
    req = request()
    req.feedback = ['Khách sắp mua xe điện, sạc ban ngày, thêm khoảng 250 kWh/tháng']
    ev = propose(req, client=None)
    assert all(s.params.extra_daytime_kwh_year == 3000 for s in ev.scenarios)
    pick = lambda p: next(s for s in p.scenarios if s.id == p.recommended_id)
    assert pick(ev).panel_count > pick(base).panel_count   # sized for the new daytime load
