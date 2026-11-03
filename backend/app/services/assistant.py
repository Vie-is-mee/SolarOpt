"""Chat assistant: answers questions about the open project and proposes edits the engineer confirms.

Same rule as the design advisor: the model never computes. It reads facts through tools (site, layout,
shading, economics, electrical), may run a what-if layout, and may propose actions; every number in a reply
is checked against what the tools returned and what the engineer typed, and unmatched numbers are flagged.
Actions are only proposals: the app shows them as buttons and nothing changes until the engineer presses one.
Without a model, or when it fails, a rule-based reader answers the common questions from the same facts.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.schemas import DesignRequest, DesignResult, PanelSpec, ProjectConfig, RectObstacle
from app.services.advisor.llm import ChatClient, LLMError, default_client
from app.services.advisor.scenarios import site_facts, vn
from app.services.electrical import ElectricalRequest, design_electrical
from app.services.optimizer import generate_design

MAX_TURNS = 4
TIME_BUDGET_S = 45
DEMO_BUDGET_S = 25
STEP_NAMES = ["Dữ liệu đầu vào", "Xác nhận bản vẽ", "Nắng và bóng che", "Bố trí tấm pin", "Kiểm tra & bàn giao"]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AssistantRequest(BaseModel):
    messages: list[ChatTurn] = Field(min_length=1, max_length=20)
    config: ProjectConfig
    panel: PanelSpec
    obstacles: list[RectObstacle] = Field(default_factory=list, max_length=100)
    design: DesignResult | None = None
    economics: dict[str, float | str | None] = Field(default_factory=dict, description="Summary the app computed from the engineer's estimate")
    step: int = Field(default=0, ge=0, le=4)
    demo: bool = False
    use_llm: bool = True


ActionKind = Literal["go_to_step", "set_target_energy", "set_budget", "set_edge_reserve", "set_obstacle", "run_design", "run_electrical"]


class AssistantAction(BaseModel):
    kind: ActionKind
    label: str
    params: dict[str, float | str | int] = Field(default_factory=dict)


class AssistantReply(BaseModel):
    mode: Literal["llm", "rules"]
    model: str = ""
    reply: str
    facts_used: list[str] = Field(default_factory=list)
    facts: dict[str, float | str | None] = Field(default_factory=dict)
    actions: list[AssistantAction] = Field(default_factory=list)
    unverified: list[str] = Field(default_factory=list)
    notice: str = ""
    elapsed_ms: float = 0
    replay: str = ""


# ---- facts --------------------------------------------------------------------------------------

def _label(index: int) -> str:
    return "P" + str(index + 1).zfill(3)


def project_facts(req: AssistantRequest) -> dict[str, dict[str, float | str | None]]:
    """Facts grouped by section; keys are what reply chips show."""
    site = dict(site_facts(req))
    faces = req.config.roof_faces
    site["site.roof_faces"] = len(faces) or 1
    site["site.obstacle_list"] = "; ".join(f"{o.label} (cao {vn(o.height_m)} m, tại x {vn(o.x)} m, y {vn(o.y)} m)"
                                           for o in req.obstacles if o.scope == "roof") or "không có"
    site["site.setback_m"] = req.config.setback_m
    site["site.edge_reserve_m"] = req.config.layout_edge_reserve_m
    site["site.budget_vnd"] = req.config.budget_vnd
    site["site.target_energy_kwh_year"] = getattr(req.config, "target_energy_kwh_year", None)
    out = {"site": site, "design": {}, "shading": {}, "economics": {}, "electrical": {}}
    d = req.design
    if d and d.panels:
        m = d.metrics
        per_face: dict[str, int] = {}
        for p in d.panels:
            per_face[p.face_id] = per_face.get(p.face_id, 0) + 1
        out["design"] = {"design.panel_count": m.panel_count, "design.peak_power_kwp": m.peak_power_kwp,
                         "design.annual_energy_kwh": round(m.annual_energy_kwh), "design.panel_cost_vnd": m.estimated_cost_vnd,
                         "design.area_upper_bound_panels": m.area_upper_bound_panels, "design.roof_utilization_pct": m.roof_utilization_pct,
                         "design.objective": {"max_energy": "sản lượng cao nhất", "min_cost": "đáp ứng nhu cầu, giảm chi phí", "robust": "dự phòng sai số"}.get(d.objective or "", d.objective or ""),
                         "design.target_met": None if d.target_met is None else ("đạt" if d.target_met else "không đạt — mái không xếp thêm được tấm"),
                         "design.panels_per_face": "; ".join(f"{k}: {v}" for k, v in per_face.items())}
        worst = sorted(enumerate(d.panels), key=lambda ip: -ip[1].shading_loss_pct)[:3]
        out["shading"] = {"shading.average_loss_pct": m.average_shading_loss_pct, "shading.max_loss_pct": m.maximum_shading_loss_pct,
                          "shading.worst_panels": "; ".join(f"{_label(i)} {vn(p.shading_loss_pct)}%" for i, p in worst),
                          "shading.tallest_obstacle_m": site.get("site.tallest_obstacle_m")}
        try:
            e = design_electrical(ElectricalRequest(config=req.config, panel=req.panel, design=d))
            out["electrical"] = {"electrical.summary": e.summary, "electrical.inverter": f"{e.inverter_count} × {e.inverter.manufacturer} {e.inverter.model}",
                                 "electrical.strings": len(e.strings), "electrical.dc_ac_ratio": e.dc_ac_ratio,
                                 "electrical.warnings": "; ".join(c.label for c in e.checks if c.status != "PASS") or "không có",
                                 "electrical.bom_vnd": sum(v for k, v in e.cost_by_group.items() if k != "panel")}
        except ValueError:
            pass
    out["economics"] = {f"economics.{k}": v for k, v in req.economics.items()}
    return out


def _flat(sections: dict) -> dict[str, float | str | None]:
    return {k: v for part in sections.values() for k, v in part.items()}


# ---- number check -------------------------------------------------------------------------------

NUMBER = re.compile(r"(?<![\w.,])\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?(?![\d])|(?<![\w.,])\d+(?:[.,]\d+)?(?![\d])")


def _numbers(text: str) -> list[tuple[str, float]]:
    out = []
    for raw in NUMBER.findall(text or ""):
        s = raw.strip()
        if re.fullmatch(r"\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?", s):
            value = float(s.replace(".", "").replace(" ", "").replace(",", "."))
        else:
            value = float(s.replace(",", "."))
        out.append((s, value))
    return out


def _known(values: list[float], v: float) -> bool:
    if v <= 31 and float(v).is_integer():          # small counts, ids, step numbers, days: not worth flagging
        return True
    for k in values:
        for scale in (1, 1e3, 1e6, 1e9, 0.01, 100):
            target = k / scale
            if target and abs(v - target) <= max(0.011 * abs(target), 0.051):
                return True
    return False


def unverified_numbers(reply: str, sources: list[str]) -> list[str]:
    values = [v for text in sources for _, v in _numbers(text)]
    return list(dict.fromkeys(raw for raw, v in _numbers(reply) if not _known(values, v)))[:6]


# ---- actions ------------------------------------------------------------------------------------

def _plain(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in text if not unicodedata.combining(c))


def find_obstacle(req: AssistantRequest, name: str) -> RectObstacle | None:
    key = _plain(name).strip()
    if not key:
        return None
    for o in req.obstacles:
        if o.id == name or _plain(o.label).split("·")[0].strip() == key:
            return o
    hits = [o for o in req.obstacles if key in _plain(o.label) or _plain(o.label).split("·")[0].strip() in key]
    return hits[0] if hits else None


def make_action(req: AssistantRequest, kind: str, params: dict) -> AssistantAction:
    """Validate a proposed action against the project; raises ValueError with a reason the model can read."""
    if kind == "go_to_step":
        step = int(params.get("step", -1))
        if not 0 <= step <= 4:
            raise ValueError("step phải từ 0 đến 4.")
        return AssistantAction(kind=kind, label=f"Mở bước {step + 1}: {STEP_NAMES[step]}", params={"step": step})
    if kind == "set_target_energy":
        v = float(params["value"])
        if not 1 <= v <= 10_000_000:
            raise ValueError("Điện năng mục tiêu phải trong 1–10.000.000 kWh/năm.")
        return AssistantAction(kind=kind, label=f"Đặt điện năng mục tiêu {vn(v, 0)} kWh/năm", params={"value": v})
    if kind == "set_budget":
        v = float(params["value"])
        if not 1e6 <= v <= 1e12:
            raise ValueError("Ngân sách phải từ 1 triệu đến 1.000 tỷ đồng.")
        return AssistantAction(kind=kind, label=f"Đặt ngân sách tấm pin {vn(v / 1e6, 1)} triệu đ", params={"value": v})
    if kind == "set_edge_reserve":
        v = float(params["value"])
        if not 0 <= v <= 5:
            raise ValueError("Khoảng lùi mép phải từ 0 đến 5 m.")
        return AssistantAction(kind=kind, label=f"Lùi mép thêm {vn(v * 100, 0)} cm", params={"value": v})
    if kind == "set_obstacle":
        o = find_obstacle(req, str(params.get("obstacle", "")))
        if o is None:
            raise ValueError("Không tìm thấy vật cản; dùng id hoặc tên trong site.obstacle_list.")
        patch: dict[str, float | str] = {"id": o.id}
        parts = []
        if params.get("dx") or params.get("dy"):
            dx, dy = float(params.get("dx") or 0), float(params.get("dy") or 0)
            if max(abs(dx), abs(dy)) > 20:
                raise ValueError("Mỗi lần chỉ dời tối đa 20 m.")
            x = min(max(0.0, o.x + dx), max(0.0, req.config.roof_width_m - o.width_m))
            y = min(max(0.0, o.y + dy), max(0.0, req.config.roof_height_m - o.depth_m))
            patch.update(x=round(x, 2), y=round(y, 2))
            parts.append(f"dời tới x {vn(x)} m, y {vn(y)} m")
        if params.get("height_m") is not None:
            h = float(params["height_m"])
            if not 0 < h <= 100:
                raise ValueError("Chiều cao phải trong 0–100 m.")
            patch["height_m"] = h
            parts.append(f"đặt cao {vn(h)} m")
        if not parts:
            raise ValueError("Cần dx/dy hoặc height_m.")
        return AssistantAction(kind=kind, label=f"{o.label}: " + ", ".join(parts), params=patch)
    if kind == "run_design":
        objective = str(params.get("objective") or "max_energy")
        if objective not in ("max_energy", "min_cost", "robust"):
            raise ValueError("objective là max_energy, min_cost hoặc robust.")
        return AssistantAction(kind=kind, label="Tính lại phương án", params={"objective": objective})
    if kind == "run_electrical":
        return AssistantAction(kind=kind, label="Mở thiết kế điện ở bước Bàn giao", params={})
    raise ValueError(f"Không có loại thao tác {kind}.")


# ---- what-if ------------------------------------------------------------------------------------

def what_if(req: AssistantRequest, args: dict) -> dict:
    """Run the optimizer on a changed copy of the project; nothing in the app changes."""
    update = {}
    if args.get("budget_vnd") is not None:
        update["budget_vnd"] = float(args["budget_vnd"])
    if args.get("edge_reserve_m") is not None:
        update["layout_edge_reserve_m"] = float(args["edge_reserve_m"])
    target = args.get("target_energy_kwh_year") or getattr(req.config, "target_energy_kwh_year", None)
    config = req.config.model_copy(update={**update, "geometry_confirmed": True, "target_energy_kwh_year": target})
    obstacles = list(req.obstacles)
    if args.get("without_obstacle"):
        gone = find_obstacle(req, str(args["without_obstacle"]))
        obstacles = [o for o in obstacles if gone is None or o.id != gone.id]
    # Same objective as the layout on screen, so the comparison changes one thing only.
    objective = args.get("objective") or (req.design.objective if req.design and req.design.objective in ("max_energy", "min_cost", "robust") else "max_energy")
    d = generate_design(DesignRequest(config=config, panel=req.panel, obstacles=obstacles, objective=objective))
    return {"panel_count": d.metrics.panel_count, "peak_power_kwp": d.metrics.peak_power_kwp,
            "annual_energy_kwh": round(d.metrics.annual_energy_kwh), "panel_cost_vnd": d.metrics.estimated_cost_vnd,
            "average_shading_loss_pct": d.metrics.average_shading_loss_pct, "objective": objective,
            "current_panel_count": req.design.metrics.panel_count if req.design else None,
            "changed": {**update, "without_obstacle": args.get("without_obstacle")}}


# ---- model loop ---------------------------------------------------------------------------------

TOOLS = [
    {"type": "function", "function": {"name": "what_if", "description": "Chạy bộ tối ưu trên bản sao dự án với thay đổi giả định (không đổi dự án thật). Mất vài giây.",
     "parameters": {"type": "object", "properties": {"budget_vnd": {"type": "number"}, "edge_reserve_m": {"type": "number"}, "target_energy_kwh_year": {"type": "number"},
                                                     "without_obstacle": {"type": "string", "description": "id hoặc tên vật cản bỏ đi để xem ảnh hưởng"},
                                                     "objective": {"type": "string", "enum": ["max_energy", "min_cost", "robust"]}}}}},
    {"type": "function", "function": {"name": "propose_action", "description": "Đề xuất một thao tác; ứng dụng hiện thành nút để kỹ sư bấm duyệt, không tự áp dụng.",
     "parameters": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": ["go_to_step", "set_target_energy", "set_budget", "set_edge_reserve", "set_obstacle", "run_design", "run_electrical"]},
         "step": {"type": "integer", "description": "0..4 cho go_to_step"}, "value": {"type": "number", "description": "kWh/năm, đồng, hoặc mét"},
         "obstacle": {"type": "string", "description": "tên vật cản như trong site.obstacle_list"}, "dx": {"type": "number", "description": "mét, dương là sang phải"},
         "dy": {"type": "number", "description": "mét, dương là xuống dưới (về phía Nam khi Bắc ở trên)"}, "height_m": {"type": "number"},
         "objective": {"type": "string", "enum": ["max_energy", "min_cost", "robust"]}}, "required": ["kind"]}}},
]

SYSTEM = """Bạn là trợ lý kỹ thuật của SolarOpt, giúp kỹ sư điện mặt trời hiểu và chỉnh thiết kế mái đang mở.
Quy tắc bắt buộc:
- Không tự tính hay đoán số. Mọi con số chỉ lấy từ DỮ KIỆN bên dưới, kết quả công cụ what_if hoặc câu kỹ sư viết. Thiếu dữ kiện thì nói rõ là chưa có.
- Chỉ gọi what_if khi kỹ sư hỏi giả định (bỏ vật cản, đổi ngân sách, lùi mép); câu hỏi thường thì trả lời ngay.
- Muốn thay đổi dự án thì gọi propose_action; không bao giờ nói là đã thay đổi, vì kỹ sư phải bấm duyệt.
- Tọa độ bản vẽ: x tăng sang phải, y tăng xuống dưới. "Sang trái 1 m" là dx=-1.
- Trả lời tiếng Việt, ngắn gọn (tối đa 6 câu), có thể gạch đầu dòng. Viết số theo kiểu Việt Nam (1.234,5).
- Không suy diễn nguyên nhân ngoài dữ kiện. Số tấm do bộ tối ưu xếp theo hình mái, khoảng lùi mép, vật cản, bóng che, ngân sách và mục tiêu; inverter được chọn SAU theo số tấm nên không bao giờ là lý do giới hạn số tấm.
- Nếu design.target_met là "không đạt": mái không chứa thêm tấm; muốn biết vật cản nào gây ra thì gọi what_if với without_obstacle.
- design.area_upper_bound_panels chỉ tính diện tích, chưa trừ khe giữa tấm, hình dạng mặt mái và bóng che, nên luôn lớn hơn số tấm xếp được.
- Bộ tối ưu chọn tốt nhất trong các lưới vị trí đã thử; đừng nói nó đã xét mọi cách xếp.
- Không nhắc tên trường dữ liệu (như area_upper_bound_panels); nói bằng lời thường.
- Các bước của ứng dụng: 1 Dữ liệu đầu vào, 2 Xác nhận bản vẽ, 3 Nắng và bóng che, 4 Bố trí tấm pin, 5 Kiểm tra & bàn giao. Không có thao tác xóa vật cản; kỹ sư tự xóa ở bước 2.
- Câu hỏi ngoài thiết kế điện mặt trời của dự án: từ chối lịch sự."""


def _context(req: AssistantRequest, sections: dict) -> str:
    # Facts go in the prompt so a plain question needs one model call; slow free models make every turn count.
    d = req.design
    return (f"Kỹ sư đang ở bước {req.step + 1} ({STEP_NAMES[req.step]}). Dự án: {req.config.project_name}. "
            + (f"Đã có phương án {d.metrics.panel_count} tấm." if d and d.panels else "Chưa có phương án xếp tấm.")
            + "\nDỮ KIỆN (do SolarOpt tính):\n" + json.dumps(_flat(sections), ensure_ascii=False))


def _llm_reply(req: AssistantRequest, client: ChatClient, sections: dict, started: float):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "system", "content": _context(req, sections)}]
    messages += [{"role": t.role, "content": t.content} for t in req.messages[-10:]]
    used, actions, outputs = [], [], []
    budget = DEMO_BUDGET_S if req.demo else TIME_BUDGET_S
    for _ in range(MAX_TURNS):
        left = budget - (perf_counter() - started)
        if left < 5:
            return None, used, actions, outputs
        if hasattr(client, "read_timeout"):
            client.read_timeout = left      # a slow call ends at the budget instead of holding the chat
        message = client.chat(messages, tools=TOOLS)
        calls = message.get("tool_calls") or []
        if not calls:
            return (message.get("content") or "").strip(), used, actions, outputs
        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": calls})
        for call in calls:
            name = call.get("function", {}).get("name")
            try:
                args = json.loads(call.get("function", {}).get("arguments") or "{}")
                if name == "what_if":
                    content = json.dumps(what_if(req, args), ensure_ascii=False)
                elif name == "propose_action":
                    action = make_action(req, str(args.pop("kind", "")), args)
                    actions.append(action)
                    content = json.dumps({"ok": True, "label": action.label}, ensure_ascii=False)
                else:
                    raise ValueError(f"Không có công cụ {name}.")
            except (ValueError, KeyError, TypeError, ValidationError, json.JSONDecodeError) as exc:
                content = json.dumps({"error": str(exc)[:300]}, ensure_ascii=False)
            outputs.append(content)
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": content})
    return None, used, actions, outputs


# ---- rule-based reader --------------------------------------------------------------------------

DIRECTIONS = {"trai": (-1, 0), "phai": (1, 0), "len": (0, -1), "tren": (0, -1), "xuong": (0, 1), "duoi": (0, 1),
              "bac": (0, -1), "nam": (0, 1), "dong": (1, 0), "tay": (-1, 0)}


def _num(text: str) -> float:
    return float(text.replace(".", "").replace(",", ".")) if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", text) else float(text.replace(",", "."))


def _rules_reply(req: AssistantRequest, sections: dict) -> tuple[str, list[str], list[AssistantAction]]:
    text = req.messages[-1].content
    q = _plain(text)
    f = _flat(sections)
    actions: list[AssistantAction] = []

    def add(kind, **params):
        try:
            actions.append(make_action(req, kind, params))
        except (ValueError, KeyError):
            pass

    move = re.search(r"(doi|di chuyen|dich|chuyen|keo)\s+(.+?)\s+(sang|ve|len|xuong|qua)\s*(phia\s+)?(trai|phai|tren|duoi|bac|nam|dong|tay)?\s*(?:(\d+(?:[.,]\d+)?)\s*(cm|m))?", q)
    height = (re.search(r"(?:chieu cao|cao)\s+(?:cua\s+)?(.+?)\s+(?:la\s+|thanh\s+)?(\d+(?:[.,]\d+)?)\s*m\b", q)
              or re.search(r"(.+?)\s+(?:cao|chieu cao)\s+(?:la\s+)?(\d+(?:[.,]\d+)?)\s*m\b", q))
    if move:
        name, word = move.group(2), move.group(5) or ("xuong" if move.group(3) == "xuong" else "len" if move.group(3) == "len" else "")
        dist = _num(move.group(6)) / (100 if move.group(7) == "cm" else 1) if move.group(6) else 0.5
        dx, dy = DIRECTIONS.get(word, (0, 0))
        o = find_obstacle(req, name)
        if o and (dx or dy):
            add("set_obstacle", obstacle=o.id, dx=dx * dist, dy=dy * dist)
            return (f"Đề xuất dời {o.label} {vn(dist)} m. Bấm nút bên dưới để áp dụng; sau đó xác nhận lại vật cản và tính lại phương án để xem số tấm thay đổi.",
                    ["site.obstacle_list"], actions + ([make_action(req, "run_design", {})] if req.design else []))
        return "Chưa nhận ra vật cản hoặc hướng dời. Ví dụ: “dời bồn nước sang phải 1 m”. Vật cản hiện có: " + str(f.get("site.obstacle_list")) + ".", ["site.obstacle_list"], []
    if height and (o := find_obstacle(req, height.group(1))):
        add("set_obstacle", obstacle=o.id, height_m=_num(height.group(2)))
        return f"Đề xuất đặt {o.label} cao {vn(_num(height.group(2)))} m (hiện {vn(o.height_m)} m). Bóng che sẽ được tính lại sau khi bạn áp dụng và tính lại phương án.", ["site.obstacle_list"], actions
    if m := re.search(r"ngan sach\D{0,20}(\d+(?:[.,]\d+)?)\s*(trieu|tr|ty)", q):
        value = _num(m.group(1)) * (1e9 if m.group(2) == "ty" else 1e6)
        add("set_budget", value=value)
        add("run_design")
        return f"Đề xuất đặt ngân sách tấm pin {vn(value / 1e6, 1)} triệu đ rồi tính lại phương án (hiện {vn((f.get('site.budget_vnd') or 0) / 1e6, 1)} triệu đ).", ["site.budget_vnd"], actions
    if m := re.search(r"(\d+(?:[.,]\d+)*)\s*kwh", q):
        value = _num(m.group(1)) * (12 if "thang" in q else 1)
        add("set_target_energy", value=value)
        return f"Đề xuất đặt điện năng mục tiêu {vn(value, 0)} kWh/năm" + (" (quy từ kWh/tháng × 12)" if "thang" in q else "") + ".", ["site.target_energy_kwh_year"], actions
    if m := re.search(r"lui mep\D{0,10}(\d+(?:[.,]\d+)?)\s*(cm|m)", q):
        value = _num(m.group(1)) / (100 if m.group(2) == "cm" else 1)
        add("set_edge_reserve", value=value)
        add("run_design")
        return f"Đề xuất lùi thêm {vn(value * 100, 0)} cm quanh mép mái rồi tính lại; số tấm có thể giảm.", ["site.edge_reserve_m"], actions
    if re.search(r"tinh lai|tinh phuong an|toi uu lai", q):
        add("run_design")
        return "Bấm nút bên dưới để tính lại phương án với dữ liệu hiện tại.", [], actions
    d = sections["design"]
    if not d:
        add("go_to_step", step=3)
        return ("Dự án chưa có phương án xếp tấm nên chưa có số tấm, sản lượng hay bóng che để giải thích. Xác nhận bản vẽ rồi tính phương án ở bước Bố trí tấm pin. "
                f"Mái hiện có {f.get('site.obstacles')} vật cản, diện tích {vn(f.get('site.roof_area_m2') or 0)} m²."), ["site.obstacles", "site.roof_area_m2"], actions
    if (gone := re.search(r"(?:neu|gia su)\s+(?:bo|khong co|xoa|bo di|di doi)\s+(.+?)(?:\s+(?:thi|di)\b|\?|$)", q)) and (o := find_obstacle(req, gone.group(1))):
        alt = what_if(req, {"without_obstacle": o.id})
        sections["whatif"] = {"whatif.panel_count": alt["panel_count"], "whatif.annual_energy_kwh": alt["annual_energy_kwh"]}
        gain = alt["panel_count"] - d["design.panel_count"]
        return (f"Nếu không có {o.label}, bộ tối ưu xếp được {alt['panel_count']} tấm ({vn(alt['peak_power_kwp'], 2)} kWp, khoảng {vn(alt['annual_energy_kwh'], 0)} kWh/năm), "
                + (f"thêm {gain} tấm so với hiện tại." if gain > 0 else "không tăng số tấm so với hiện tại.")
                + " Đây là thử trên bản sao, dự án chưa thay đổi."), ["design.panel_count", "whatif.panel_count", "whatif.annual_energy_kwh"], actions
    if re.search(r"inverter|chuoi|dien\b|thiet ke dien|dc/ac|bien tan", q) and sections["electrical"]:
        e = sections["electrical"]
        add("run_electrical")
        return (f"Thiết kế điện sơ bộ: {e['electrical.summary']} Lưu ý: {e['electrical.warnings']}. "
                f"Vật tư điện và khung khoảng {vn(e['electrical.bom_vnd'] / 1e6, 1)} triệu đ."), ["electrical.summary", "electrical.warnings", "electrical.bom_vnd"], actions
    if re.search(r"bong|che|shad", q):
        s = sections["shading"]
        return (f"Tổn thất bóng trung bình {vn(s['shading.average_loss_pct'])}%, tấm bị che nhiều nhất {vn(s['shading.max_loss_pct'])}%. "
                f"Ba tấm chịu bóng nhiều nhất: {s['shading.worst_panels']}. Vật cản cao nhất {vn(s['shading.tallest_obstacle_m'] or 0)} m."), list(s), actions
    if re.search(r"hoan von|chi phi|von|tien|npv|loi|kinh te|tiet kiem", q):
        e = sections["economics"]
        if not e or e.get("economics.missing"):
            add("go_to_step", step=4)
            return ("Dự toán chưa đủ số liệu để tính hoàn vốn" + (f" (còn thiếu: {e.get('economics.missing')})" if e.get("economics.missing") else "")
                    + f". Riêng tiền tấm pin của phương án là {vn(d['design.panel_cost_vnd'] / 1e6, 1)} triệu đ."), ["design.panel_cost_vnd"], actions
        return (f"Tổng đầu tư {vn((e.get('economics.total_vnd') or 0) / 1e6, 1)} triệu đ, hoàn vốn "
                + (f"{vn(e['economics.payback_years'])} năm" if e.get("economics.payback_years") else "chưa đạt trong kỳ phân tích")
                + f", NPV {vn((e.get('economics.npv_vnd') or 0) / 1e6, 1)} triệu đ."), [k for k in e], actions
    if re.search(r"vi sao|tai sao|it tam|chi co|so tam|bao nhieu tam|toi da", q):
        bound = d.get("design.area_upper_bound_panels")
        return (f"Phương án có {d['design.panel_count']} tấm ({vn(d['design.peak_power_kwp'], 2)} kWp)"
                + (f", trong khi riêng diện tích mái cho phép tối đa {bound} tấm" if bound else "") + ". Phần chênh lệch đến từ: "
                + f"{f.get('site.obstacles')} vật cản trên mái và khoảng hở an toàn quanh chúng, khoảng lùi mép {vn(f.get('site.setback_m') or 0)} m, "
                + "mặt mái dốc hẹp và các vị trí bị bóng che quá ngưỡng"
                + (", cùng ngân sách và điện năng mục tiêu" if req.design and req.design.objective in ("min_cost", "robust") else "")
                + (". Phương án chưa đạt điện năng mục tiêu, tức là mái không xếp thêm được tấm" if req.design and req.design.target_met is False else "")
                + ". Hỏi “nếu bỏ bồn nước thì sao” hoặc “dời … sang phải 1 m” để xem ảnh hưởng."), ["design.panel_count", "design.peak_power_kwp", "design.area_upper_bound_panels", "site.obstacles", "site.setback_m"], actions
    if re.search(r"san luong|kwh|dien nang|bao nhieu dien", q):
        return f"Phương án {d['design.panel_count']} tấm cho khoảng {vn(d['design.annual_energy_kwh'], 0)} kWh/năm, tổn thất bóng trung bình {vn(sections['shading']['shading.average_loss_pct'])}%.", ["design.annual_energy_kwh", "design.panel_count", "shading.average_loss_pct"], actions
    return (f"Dự án đang có {d['design.panel_count']} tấm, {vn(d['design.peak_power_kwp'], 2)} kWp, khoảng {vn(d['design.annual_energy_kwh'], 0)} kWh/năm. "
            "Bạn có thể hỏi: vì sao chỉ có bấy nhiêu tấm, bóng che ở đâu, hoàn vốn bao lâu, inverter nào; hoặc yêu cầu: dời vật cản, đổi ngân sách, lùi mép, tính lại."), ["design.panel_count", "design.peak_power_kwp", "design.annual_energy_kwh"], actions


# ---- entry point --------------------------------------------------------------------------------

def assistant_client() -> ChatClient | None:
    # ASSISTANT_MODEL may name a faster chat model; it falls back to ADVISOR_MODEL.
    return default_client("ASSISTANT_MODEL")


def cited_facts(text: str, facts: dict) -> list[str]:
    """Numeric facts whose value appears in the reply: the chips under an answer show where its numbers come from."""
    said = [v for _, v in _numbers(text)]
    return [k for k, v in facts.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and v and any((n > 31 or not float(n).is_integer()) and _known([float(v)], n) for n in said)][:10]


def answer(req: AssistantRequest, client: ChatClient | None = None) -> AssistantReply:
    started = perf_counter()
    sections = project_facts(req)
    facts = _flat(sections)
    client = client if client is not None else (assistant_client() if req.use_llm else None)
    notice = ""
    if client is not None:
        try:
            text, used, actions, outputs = _llm_reply(req, client, sections, started)
            if text:
                sources = outputs + [json.dumps(facts, ensure_ascii=False)] + [t.content for t in req.messages if t.role == "user"]
                return AssistantReply(mode="llm", model=getattr(client, "model", ""), reply=text[:3000], facts_used=list(dict.fromkeys(used + cited_facts(text, facts)))[:12],
                                      facts=facts, actions=actions[:4], unverified=unverified_numbers(text, sources),
                                      elapsed_ms=round((perf_counter() - started) * 1000))
            notice = "Trợ lý AI trả lời quá lâu; câu trả lời dưới đây do bộ quy tắc của SolarOpt lập từ cùng số liệu."
        except LLMError as exc:
            slow = "Timeout" in str(exc)
            notice = ("Trợ lý AI trả lời quá lâu" if slow else f"Trợ lý AI tạm không dùng được ({exc})") + "; câu trả lời dưới đây do bộ quy tắc lập từ cùng số liệu."
    elif req.use_llm:
        notice = "Máy chủ chưa có mô hình AI; câu trả lời do bộ quy tắc của SolarOpt lập từ số liệu đã tính."
    text, used, actions = _rules_reply(req, sections)
    return AssistantReply(mode="rules", reply=text, facts_used=used, facts=_flat(sections), actions=actions[:4], notice=notice,
                          elapsed_ms=round((perf_counter() - started) * 1000))
