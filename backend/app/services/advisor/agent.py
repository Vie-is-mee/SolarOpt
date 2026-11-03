"""Design advisor: the LLM reasons about the customer's need and picks scenarios, SolarOpt's tools compute them.

Flow: consumption from the bill (tariff formula) -> site facts -> the model calls evaluate_scenario 2-4 times
-> it returns a recommendation, reasons citing fact keys, risks and questions. The server keeps only
citations that exist, fills every number from the tools, and falls back to a rule-based planner (same
output shape) when no model is configured or the model fails, so the feature never blocks the engineer.
"""
from __future__ import annotations

import json
import math
import re
from time import perf_counter

from pydantic import ValidationError

from app.services.advisor.llm import ChatClient, LLMError, default_client
from app.services.advisor.models import NEED_LABEL, AdvisorRequest, Proposal, Reason, Scenario, ScenarioParams
from app.services.advisor.scenarios import ScenarioBook, site_facts, vn as _num

MAX_TURNS = 8
TOOL = {"type": "function", "function": {
    "name": "evaluate_scenario",
    "description": "Chạy bộ tối ưu bố trí của SolarOpt trên mái thật với một kịch bản, trả về số tấm, kWp, sản lượng, tổn thất bóng, vốn đầu tư, tiết kiệm năm đầu, hoàn vốn, NPV. Mỗi lần gọi tốn vài giây; tối đa 4 kịch bản.",
    "parameters": {"type": "object", "properties": {
        "label": {"type": "string", "description": "Tên ngắn tiếng Việt cho kịch bản"},
        "intent": {"type": "string", "description": "Kịch bản này kiểm tra giả thuyết gì"},
        "objective": {"type": "string", "enum": ["max_energy", "min_cost", "robust"], "description": "max_energy: nhiều điện nhất trong ngân sách; min_cost: ít tấm nhất đạt điện năng mục tiêu; robust: chừa dự phòng sai số"},
        "target_energy_kwh_year": {"type": "number", "description": "Chỉ cho min_cost: điện năng cần đạt mỗi năm"},
        "max_investment_vnd": {"type": "number", "description": "Trần tổng vốn đầu tư trọn gói (đồng); bỏ trống = ngân sách khách"},
        "edge_reserve_m": {"type": "number", "description": "Lùi thêm mép mái 0–1 m để chừa lối đi hoặc sai số đo"}},
        "required": ["label", "objective"]}}}

SYSTEM = """Bạn là kỹ sư tư vấn điện mặt trời áp mái của SolarOpt. Nhiệm vụ: đề xuất phương án lắp đặt phù hợp nhất với nhu cầu khách, mái nhà và tấm pin đang chọn.
Quy tắc bắt buộc:
- Không tự tính hay bịa số. Mọi con số về sản lượng, số tấm, vốn, hoàn vốn chỉ lấy từ kết quả công cụ evaluate_scenario và dữ kiện được cung cấp.
- Suy luận trước khi gọi công cụ: nhu cầu khách là gì, mái chứa tối đa bao nhiêu, ngân sách và điện dùng ban ngày giới hạn quy mô thế nào. Thử 2–4 kịch bản khác nhau có chủ đích (ví dụ: vừa đủ điện ban ngày, phủ toàn bộ nhu cầu, tối đa mái trong ngân sách, chừa lối đi/dự phòng).
- Nếu kỹ sư có góp ý, kịch bản mới phải phản ánh góp ý đó và lý do phải nói rõ đã thay đổi gì so với đề xuất trước.
- Điện dư không được trả tiền (trừ khi giá bán > 0), nên quy mô vượt xa điện ban ngày thường làm hoàn vốn chậm.
Khi đã đủ kịch bản, trả lời DUY NHẤT một đối tượng JSON:
{"recommended_id":"S2","summary":"2–3 câu","reasons":[{"text":"lý do","refs":["S2.payback_years","consumption.daytime_kwh_year"]}],"risks":["..."],"questions":["câu hỏi cần hỏi khách"]}
refs phải là khóa dữ kiện có thật (dạng S1.npv_vnd, S2.coverage_pct, site.max_kwp_by_area, consumption.annual_kwh...). Viết tiếng Việt, ngắn gọn, cho kỹ sư đọc."""


def _parse_json(text: str | None) -> dict | None:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    try:
        value = json.loads(text[start:end + 1]) if start >= 0 else None
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _money(v: float) -> str:
    return f"{_num(v / 1e9, 2)} tỷ đ" if abs(v) >= 1e9 else f"{_num(v / 1e6, 0)} triệu đ"


def computed_risks(book: ScenarioBook, pick: Scenario) -> list[str]:
    """Risks the server states from the numbers, whatever the model wrote."""
    out = list(pick.warnings)
    if pick.npv_vnd < 0:
        out.append(f"NPV âm ({_money(pick.npv_vnd)}): với giả định hiện tại, khoản đầu tư không bù được chi phí vốn trong {book.req.finance.years} năm.")
    if book.cons.daytime_kwh_year is not None and pick.self_use_pct < 50 and not book.req.finance.sell_price_vnd_kwh:
        out.append(f"Chỉ tự dùng {_num(pick.self_use_pct)}% sản lượng; phần dư không được trả tiền nên không tạo tiết kiệm.")
    if pick.average_shading_loss_pct > 3:
        out.append(f"Tổn thất bóng trung bình {_num(pick.average_shading_loss_pct, 2)}%: kiểm tra lại cao độ vật cản trước khi chốt.")
    return out


def _context(req: AdvisorRequest, book: ScenarioBook, site: dict) -> str:
    previous = None
    if req.previous:
        chosen = next((s for s in req.previous.scenarios if s.id == req.previous.recommended_id), None)
        previous = {"summary": req.previous.summary, "recommended": chosen.model_dump(include={"label", "params", "panel_count", "investment_vnd", "payback_years"}) if chosen else None}
    return json.dumps({
        "nhu_cau_khach": NEED_LABEL[req.need], "ghi_chu_khach": req.customer.notes or None,
        "tieu_thu": book.cons.model_dump(), "ngan_sach_khach_vnd": req.customer.budget_vnd,
        "suat_dau_tu_trieu_d_kwp": book.capex, "nguon_suat_dau_tu": book.capex_source,
        "bieu_gia": req.customer.tariff, "gia_ban_dien_du": req.finance.sell_price_vnd_kwh,
        "mai_va_tam_pin": site, "gop_y_ky_su": req.feedback or None, "de_xuat_truoc": previous,
    }, ensure_ascii=False, default=float)


def _llm_plan(req: AdvisorRequest, book: ScenarioBook, site: dict, client: ChatClient, trace: list) -> dict | None:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": _context(req, book, site)}]
    for _ in range(MAX_TURNS):
        message = client.chat(messages, tools=[TOOL] if len(book.items) < book.MAX else None)
        calls = message.get("tool_calls") or []
        if not calls:
            answer = _parse_json(message.get("content"))
            if answer is None:
                messages += [{"role": "assistant", "content": message.get("content") or ""}, {"role": "user", "content": "Trả lời lại đúng một đối tượng JSON theo mẫu, không kèm chữ khác."}]
                answer = _parse_json(client.chat(messages, json_mode=True).get("content"))
            if answer and not book.items:
                trace.append({"step": "llm", "detail": "Mô hình trả lời mà chưa thử kịch bản nào; chuyển sang bộ quy tắc."})
                return None
            return answer
        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": calls})
        for call in calls:
            name = call.get("function", {}).get("name")
            try:
                args = json.loads(call.get("function", {}).get("arguments") or "{}")
                if name != "evaluate_scenario":
                    raise ValueError(f"Không có công cụ {name}.")
                params = ScenarioParams(**{k: args[k] for k in ("objective", "target_energy_kwh_year", "max_investment_vnd", "edge_reserve_m") if args.get(k) is not None})
                item = book.run(params, str(args.get("label", "")), str(args.get("intent", "")))
                trace.append({"step": "tool", "detail": f"{item.id} · {item.label}: {item.panel_count} tấm, {item.investment_vnd / 1e6:.0f} triệu đ"})
                content = json.dumps({**item.model_dump(exclude={"params"}), "fact_keys": f"{item.id}.<truong>"}, ensure_ascii=False)
            except (ValueError, ValidationError, json.JSONDecodeError) as exc:
                content = json.dumps({"error": str(exc)[:300]}, ensure_ascii=False)
                trace.append({"step": "tool", "detail": f"Kịch bản không chạy được: {str(exc)[:120]}"})
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": content})
    trace.append({"step": "llm", "detail": f"Quá {MAX_TURNS} lượt trao đổi; dùng kết quả đã có."})
    return {}


# ---- rule-based planner (no model, or model failure) -------------------------------------------------

def _feedback_params(req: AdvisorRequest) -> tuple[float | None, float]:
    """Budget cap and edge reserve read from the engineer's notes ('ngân sách 120 triệu', 'chừa lối đi')."""
    cap, reserve = None, 0.0
    for note in req.feedback:
        text = note.lower()
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(tỷ|ty|triệu|trieu|tr)\b", text)
        if m and re.search(r"ngân sách|ngan sach|tối đa|toi da|trần|không quá|khong qua", text):
            value = float(m.group(1).replace(",", "."))
            cap = value * (1e9 if m.group(2) in ("tỷ", "ty") else 1e6)
        if re.search(r"lối đi|loi di|lùi mép|lui mep|dự phòng|du phong|sai số|sai so", text):
            reserve = 0.15
    return cap, reserve


def _rules_scenarios(req: AdvisorRequest, book: ScenarioBook) -> None:
    cap, reserve = _feedback_params(req)
    daytime, annual = book.cons.daytime_kwh_year, book.cons.annual_kwh
    plans: list[tuple[ScenarioParams, str, str]] = []
    if req.need == "max_energy":
        plans.append((ScenarioParams(objective="max_energy", max_investment_vnd=cap, edge_reserve_m=reserve), "Tối đa mái trong ngân sách", "Khách ưu tiên sản lượng: lấp mái nhiều nhất có thể."))
        if annual:
            plans.append((ScenarioParams(objective="min_cost", target_energy_kwh_year=annual, max_investment_vnd=cap, edge_reserve_m=reserve), "Vừa đủ nhu cầu cả năm", "So sánh: dừng ở mức điện cả năm thì vốn giảm bao nhiêu."))
    elif req.need == "min_cost":
        if daytime:
            plans.append((ScenarioParams(objective="min_cost", target_energy_kwh_year=daytime, max_investment_vnd=cap, edge_reserve_m=reserve), "Vừa đủ điện ban ngày", "Điện dư không được trả tiền: quy mô theo điện dùng ban ngày cho hoàn vốn nhanh nhất."))
        if annual:
            plans.append((ScenarioParams(objective="min_cost", target_energy_kwh_year=annual, max_investment_vnd=cap, edge_reserve_m=reserve), "Phủ toàn bộ nhu cầu", "Nếu khách muốn hóa đơn gần bằng 0 thì cần thêm bao nhiêu vốn."))
        if not plans:
            plans.append((ScenarioParams(objective="max_energy", max_investment_vnd=cap, edge_reserve_m=reserve), "Tối đa mái trong ngân sách", "Chưa biết nhu cầu: tham chiếu theo sức chứa của mái."))
    else:
        plans.append((ScenarioParams(objective="robust", max_investment_vnd=cap, edge_reserve_m=reserve), "Dự phòng sai số", "Chừa biên cho sai số đo mái, kích thước tấm và ngân sách."))
        plans.append((ScenarioParams(objective="robust", max_investment_vnd=cap, edge_reserve_m=max(reserve, 0.3)), "Dự phòng + lối đi bảo trì", "Thêm 30 cm quanh mép để đi lại vệ sinh, đổi lại ít tấm hơn."))
    plans.append((ScenarioParams(objective="max_energy", max_investment_vnd=cap, edge_reserve_m=reserve), "Tham chiếu: tối đa trong ngân sách", "Mốc so sánh quy mô lớn nhất khách có thể đầu tư."))
    seen = set()
    for params, label, intent in plans:
        key = params.model_dump_json()
        if key in seen:
            continue
        seen.add(key)
        try:
            book.run(params, label, intent)
        except ValueError:
            continue


def _rules_pick(req: AdvisorRequest, book: ScenarioBook) -> Scenario:
    usable = [s for s in book.items if s.panel_count] or book.items
    if req.need == "max_energy":
        return max(usable, key=lambda s: s.annual_energy_kwh)
    if req.need == "min_cost":
        met = [s for s in usable if s.target_met] or usable
        return max(met, key=lambda s: (s.npv_vnd, -s.investment_vnd))
    robust = [s for s in usable if s.params.objective == "robust"] or usable
    return min(robust, key=lambda s: (len(s.warnings), -s.annual_energy_kwh))


def _rules_text(req: AdvisorRequest, book: ScenarioBook, pick: Scenario) -> dict:
    sid = pick.id
    reasons = [{"text": f"Nhu cầu “{NEED_LABEL[req.need]}” → chọn “{pick.label}”: {pick.panel_count} tấm, {_num(pick.peak_power_kwp, 2)} kWp, khoảng {_num(pick.annual_energy_kwh, 0)} kWh/năm.", "refs": [f"{sid}.panel_count", f"{sid}.annual_energy_kwh"]}]
    if pick.coverage_pct is not None:
        reasons.append({"text": f"Đáp ứng {_num(pick.coverage_pct)}% điện cả năm; điện dùng ban ngày khoảng {_num(book.cons.daytime_share_pct)}% nên tự dùng được {_num(pick.self_use_pct)}% sản lượng.", "refs": [f"{sid}.coverage_pct", "consumption.daytime_share_pct", f"{sid}.self_use_pct"]})
    if pick.payback_years is not None:
        reasons.append({"text": f"Vốn {_money(pick.investment_vnd)}, hoàn vốn khoảng {_num(pick.payback_years)} năm, NPV {_money(pick.npv_vnd)}.", "refs": [f"{sid}.investment_vnd", f"{sid}.payback_years", f"{sid}.npv_vnd"]})
    others = [s for s in book.items if s.id != sid and s.panel_count]
    if others:
        o = max(others, key=lambda s: s.panel_count)
        reasons.append({"text": f"So với “{o.label}” ({o.panel_count} tấm, {_money(o.investment_vnd)}): {'hoàn vốn ' + _num(o.payback_years) + ' năm' if o.payback_years else 'chưa hoàn vốn trong kỳ phân tích'}, NPV {_money(o.npv_vnd)}.", "refs": [f"{o.id}.panel_count", f"{o.id}.investment_vnd", f"{o.id}.npv_vnd"]})
    questions = []
    if book.cons.annual_kwh is None:
        questions.append("Tiền điện hoặc số kWh mỗi tháng của khách là bao nhiêu?")
    if req.customer.daytime_share_pct is None:
        questions.append("Khách dùng điện ban ngày (7h–17h) khoảng bao nhiêu phần trăm? Đề xuất đang giả định theo loại biểu giá.")
    if req.customer.capex_million_per_kwp is None:
        questions.append("Nhà thầu báo giá trọn gói bao nhiêu triệu đ/kWp?")
    return {"recommended_id": sid, "summary": f"Đề xuất “{pick.label}”: {pick.panel_count} tấm ({_num(pick.peak_power_kwp, 2)} kWp), vốn khoảng {_money(pick.investment_vnd)}.",
            "reasons": reasons, "risks": [], "questions": questions}


# ---- assembly ----------------------------------------------------------------------------------------

def _clean_reasons(raw: list, facts: dict) -> list[Reason]:
    out = []
    for item in raw[:8] if isinstance(raw, list) else []:
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            continue
        refs = [r for r in item.get("refs", []) if isinstance(r, str) and facts.get(r) is not None]
        text = str(item["text"]).strip()[:500]
        # A sentence with figures must cite at least one computed fact, otherwise it is not shown.
        if re.search(r"\d", text) and not refs:
            continue
        out.append(Reason(text=text, refs=refs[:6]))
    return out


def propose(req: AdvisorRequest, client: ChatClient | None = None) -> Proposal:
    started = perf_counter()
    book, site = ScenarioBook(req), site_facts(req)
    trace = [{"step": "consumption", "detail": book.cons.source}, {"step": "capex", "detail": book.capex_source}]
    client = client if client is not None else (default_client() if req.use_llm else None)
    answer, mode, notice = None, "rules", ""
    if client is not None:
        try:
            answer = _llm_plan(req, book, site, client, trace)
            mode = "llm" if answer is not None else "rules"
        except LLMError as exc:
            notice = f"Trợ lý AI tạm không dùng được ({exc}); đề xuất dưới đây do bộ quy tắc của SolarOpt lập."
            trace.append({"step": "llm", "detail": str(exc)})
    elif req.use_llm:
        notice = "Chưa cấu hình mô hình AI trên máy chủ; đề xuất do bộ quy tắc của SolarOpt lập, cùng công cụ tính toán."
    if not book.items:
        _rules_scenarios(req, book)
    if not book.items:
        raise ValueError("Không chạy được kịch bản nào; kiểm tra mái, vật cản và thông số tấm pin.")
    facts = {**site, **book.facts()}
    pick = book.get(str((answer or {}).get("recommended_id", ""))) or _rules_pick(req, book)
    rules = _rules_text(req, book, pick)
    reasons = _clean_reasons((answer or {}).get("reasons"), facts) if mode == "llm" else []
    if mode == "llm" and not reasons:
        trace.append({"step": "llm", "detail": "Lý do của mô hình không trích dẫn dữ kiện tính được; dùng lý do của bộ quy tắc."})
    if not reasons:
        reasons = _clean_reasons(rules["reasons"], facts)
    text = answer if mode == "llm" else rules
    budget = math.ceil(pick.investment_vnd * 1.1 / 5e6) * 5e6 if pick.investment_vnd else 0.0
    facts["recommended.budget_vnd"] = budget
    assumptions = [book.cons.source, book.capex_source,
                   f"Điện dùng ban ngày {_num(book.cons.daytime_share_pct)}%" + (" (kỹ sư nhập)." if req.customer.daytime_share_pct is not None else " (giả định theo loại biểu giá, cần hỏi khách)."),
                   f"Suy giảm {_num(req.finance.degradation_pct)}%/năm, bảo trì {_num(req.finance.maintenance_vnd_per_kwp_year, 0)} đ/kWp/năm, chiết khấu {_num(req.finance.discount_pct)}%/năm, "
                   f"điện dư {'không được trả tiền' if not req.finance.sell_price_vnd_kwh else _num(req.finance.sell_price_vnd_kwh, 0) + ' đ/kWh'}.",
                   "Ngân sách đề xuất = vốn phương án chọn + 10% dự phòng, làm tròn lên 5 triệu."]
    return Proposal(
        mode=mode, model=getattr(client, "model", "") if mode == "llm" else "", need=req.need, consumption=book.cons,
        capex_million_per_kwp=book.capex, capex_source=book.capex_source, scenarios=book.items,
        recommended_id=pick.id, recommended_budget_vnd=budget,
        summary=str(text.get("summary") or rules["summary"])[:600], reasons=reasons,
        risks=list(dict.fromkeys(computed_risks(book, pick) + [str(r)[:300] for r in (text.get("risks") or [])]))[:8], questions=[str(q)[:300] for q in (text.get("questions") or rules["questions"])][:6],
        assumptions=assumptions, facts=facts,
        apply=book.applied[pick.id],   # reproduces the chosen scenario exactly when the engineer presses "Áp dụng"
        trace=trace, notice=notice, elapsed_ms=round((perf_counter() - started) * 1000),
    )
