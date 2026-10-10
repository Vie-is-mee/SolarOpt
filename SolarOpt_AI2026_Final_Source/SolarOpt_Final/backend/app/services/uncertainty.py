from __future__ import annotations

from copy import deepcopy

from app.schemas import DesignRequest, UncertaintyRequest, UncertaintyResult, VerifyRequest
from app.services.optimizer import generate_design
from app.services.verifier import verify_design


def evaluate_uncertainty(req: UncertaintyRequest) -> UncertaintyResult:
    low_obs = deepcopy(req.obstacles)
    high_obs = deepcopy(req.obstacles)
    found = False
    for o in low_obs:
        if o.id == req.obstacle_id:
            o.height_m = req.low_height_m
            found = True
    for o in high_obs:
        if o.id == req.obstacle_id:
            o.height_m = req.high_height_m
    if not found:
        raise ValueError(f"Không tìm thấy obstacle_id={req.obstacle_id}")

    low = generate_design(DesignRequest(config=req.config, panel=req.panel, obstacles=low_obs, objective=req.objective))
    high = generate_design(DesignRequest(config=req.config, panel=req.panel, obstacles=high_obs, objective=req.objective))
    low_v = verify_design(VerifyRequest(config=req.config, panel=req.panel, obstacles=low_obs, design=low))
    high_v = verify_design(VerifyRequest(config=req.config, panel=req.panel, obstacles=high_obs, design=high))

    low_ids = {p.id for p in low.panels}
    high_ids = {p.id for p in high.panels}
    union = low_ids | high_ids
    same = low_ids & high_ids
    layout_diff = 100.0 * (1.0 - len(same) / max(1, len(union)))
    base_energy = max(1.0, low.metrics.annual_energy_kwh)
    energy_diff = 100.0 * abs(high.metrics.annual_energy_kwh - low.metrics.annual_energy_kwh) / base_energy
    validity_changed = low_v.valid != high_v.valid

    impact_score = (
        0.50 * min(1.0, layout_diff / 30.0)
        + 0.30 * min(1.0, energy_diff / 10.0)
        + 0.20 * (1.0 if validity_changed else 0.0)
    )
    ask = validity_changed or impact_score >= 0.25
    action = "ASK_ENGINEER" if ask else "AUTO_CONTINUE"
    explanation = (
        f"Biên {req.low_height_m:.2f}–{req.high_height_m:.2f} m làm thay đổi {layout_diff:.1f}% layout, "
        f"{energy_diff:.1f}% năng lượng; trạng thái hợp lệ {'có' if validity_changed else 'không'} đổi."
    )
    return UncertaintyResult(
        obstacle_id=req.obstacle_id,
        low_design=low,
        high_design=high,
        layout_difference_pct=round(layout_diff, 1),
        energy_difference_pct=round(energy_diff, 1),
        validity_changed=validity_changed,
        impact_score=round(impact_score, 3),
        action=action,
        explanation=explanation,
    )
