import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import DesignRequest, PanelSpec, ProjectConfig, RectObstacle
from app.services.assistant import AssistantRequest, answer, unverified_numbers
from app.services.optimizer import generate_design


@pytest.fixture(autouse=True)
def no_real_model(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "none")


CONFIG = ProjectConfig(project_name="Chat", roof_width_m=12, roof_height_m=9, geometry_confirmed=True, budget_vnd=2e9)
OBSTACLES = [RectObstacle(id="tank", label="Bồn nước", x=7, y=5.6, width_m=1.6, depth_m=1.4, height_m=1.2, confirmed=True),
             RectObstacle(id="ac", label="Dàn nóng", x=1, y=1, width_m=1, depth_m=0.8, height_m=0.9, confirmed=True)]
DESIGN = generate_design(DesignRequest(config=CONFIG, panel=PanelSpec(), obstacles=OBSTACLES, objective="max_energy"))


def ask(text, design=DESIGN, history=(), **extra):
    msgs = [*history, {"role": "user", "content": text}]
    return answer(AssistantRequest(messages=msgs, config=CONFIG, panel=PanelSpec(), obstacles=OBSTACLES, design=design, **extra))


def test_rules_explain_the_panel_count_from_computed_facts():
    r = ask("Vì sao chỉ có bấy nhiêu tấm?")
    assert r.mode == "rules" and str(DESIGN.metrics.panel_count) in r.reply
    assert "design.panel_count" in r.facts_used and r.facts["design.panel_count"] == DESIGN.metrics.panel_count


def test_move_request_becomes_a_validated_proposal_not_a_change():
    r = ask("Dời bồn nước sang phải 1 m")
    move = next(a for a in r.actions if a.kind == "set_obstacle")
    assert move.params["id"] == "tank" and move.params["x"] == 8.0 and move.params["y"] == 5.6
    assert any(a.kind == "run_design" for a in r.actions)
    # Pushing past the roof edge is clamped inside the roof.
    far = next(a for a in ask("dời bồn nước sang phải 9 m").actions if a.kind == "set_obstacle")
    assert far.params["x"] == pytest.approx(12 - 1.6)


def test_height_budget_target_and_reserve_requests():
    assert next(a for a in ask("Bồn nước cao 1,5 m").actions).params == {"id": "tank", "height_m": 1.5}
    assert next(a for a in ask("đặt ngân sách 80 triệu").actions).params == {"value": 80e6}
    target = next(a for a in ask("khách dùng 400 kWh/tháng").actions)
    assert target.kind == "set_target_energy" and target.params["value"] == 4800
    assert next(a for a in ask("lùi mép 30 cm").actions).params == {"value": 0.3}


def test_what_if_without_an_obstacle_runs_on_a_copy():
    r = ask("Nếu bỏ bồn nước thì sao?")
    assert r.facts["whatif.panel_count"] >= DESIGN.metrics.panel_count and "bản sao" in r.reply
    assert r.actions == []


def test_without_a_layout_the_assistant_says_so_and_points_to_the_step():
    r = ask("sản lượng bao nhiêu?", design=None)
    assert "chưa có phương án" in r.reply and r.actions[0].params == {"step": 3}


def test_numbers_not_in_the_sources_are_flagged():
    assert unverified_numbers("Hệ có 12 tấm, 6,96 kWp, hoàn vốn 4,2 năm", ['{"kwp": 6.96}', '{"years": 4.2}']) == []
    assert unverified_numbers("Sản lượng 9.876 kWh/năm", ['{"annual_energy_kwh": 8123}']) == ["9.876"]


class Fake:
    model = "fake"

    def __init__(self, replies):
        self.replies, self.seen = list(replies), []

    def chat(self, messages, tools=None, json_mode=False):
        self.first_prompt = getattr(self, "first_prompt", None) or messages[1]["content"]
        self.seen.append(messages[-1])
        return self.replies.pop(0)


def call(name, **args):
    return {"content": "", "tool_calls": [{"id": "c", "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_model_gets_facts_in_the_prompt_proposes_and_unfounded_numbers_are_flagged():
    n, kwp = DESIGN.metrics.panel_count, DESIGN.metrics.peak_power_kwp
    client = Fake([call("propose_action", kind="set_obstacle", obstacle="Dàn nóng", dx=-0.5),
                   {"content": f"Phương án có {n} tấm, {str(kwp).replace('.', ',')} kWp; dời dàn nóng sẽ thêm khoảng 777 kWh."}])
    req = AssistantRequest(messages=[{"role": "user", "content": "Có cách nào thêm tấm?"}], config=CONFIG, panel=PanelSpec(), obstacles=OBSTACLES, design=DESIGN)
    r = answer(req, client=client)
    assert r.mode == "llm" and "design.peak_power_kwp" in r.facts_used
    assert r.actions[0].params["id"] == "ac" and r.unverified == ["777"]
    # One model call answers a plain question: the facts were already in the prompt.
    assert "design.panel_count" in client.first_prompt


def test_invalid_proposals_are_returned_to_the_model_as_errors():
    client = Fake([call("propose_action", kind="set_obstacle", obstacle="cây cau", dx=1), {"content": "Không tìm thấy vật cản đó."}])
    r = answer(AssistantRequest(messages=[{"role": "user", "content": "dời cây cau"}], config=CONFIG, panel=PanelSpec(), obstacles=OBSTACLES, design=DESIGN), client=client)
    assert r.actions == [] and "error" in client.seen[1]["content"]
    assert r.mode == "llm"


def test_chat_endpoint_answers_offline():
    client = TestClient(app, headers={"X-SolarOpt-Request": "1"})
    body = {"messages": [{"role": "user", "content": "bóng che thế nào?"}], "config": CONFIG.model_dump(), "panel": PanelSpec().model_dump(),
            "obstacles": [o.model_dump() for o in OBSTACLES], "design": DESIGN.model_dump(), "step": 3}
    res = client.post("/api/assistant/chat", json=body)
    assert res.status_code == 200, res.text
    assert res.json()["mode"] == "rules" and "Tổn thất bóng" in res.json()["reply"]
