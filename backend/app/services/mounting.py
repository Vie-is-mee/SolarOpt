"""Compare mounting options on the same roof: flush, tilted racks in rows, 1-axis trackers.

Each option is a full layout run (same roof, obstacles, panel, budget; objective max energy), so
the comparison shows the real trade-off on an area-limited roof: racks and trackers raise energy
per panel but need row spacing, which removes panels. Mounting hardware cost is not modelled.
"""
from __future__ import annotations

from app.schemas import DesignRequest
from app.services.optimizer import generate_design

RACK_TILTS = (10.0, 15.0, 20.0)
TRACKER_GCRS = (0.3, 0.4, 0.5)


def variants(cfg):
    facing = 180.0 if cfg.latitude >= 0 else 0.0
    yield "Lắp sát mái", {"mounting": "flush"}
    for tilt in RACK_TILTS:
        yield f"Giá nghiêng {tilt:.0f}°", {"mounting": "tilted_rack", "rack_tilt_deg": tilt, "rack_azimuth_deg": facing}
    for gcr in TRACKER_GCRS:
        yield f"Pin xoay 1 trục, GCR {gcr:.1f}", {"mounting": "tracker", "tracker_gcr": gcr}


def compare_mountings(req: DesignRequest) -> dict:
    roof_area = None
    rows = []
    for label, overrides in variants(req.config):
        cfg = req.config.model_copy(update=overrides)
        design = generate_design(req.model_copy(update={"config": cfg, "objective": "max_energy", "previous_panels": []}))
        m = design.metrics
        if roof_area is None:
            roof_area = m.usable_area_m2 or 0
        rows.append({"label": label, "settings": overrides, "panels": m.panel_count, "kwp": m.peak_power_kwp,
                     "annual_kwh": m.annual_energy_kwh, "kwh_per_panel": round(m.annual_energy_kwh / m.panel_count, 1) if m.panel_count else 0,
                     "kwh_per_m2_roof": round(m.annual_energy_kwh / roof_area, 1) if roof_area else 0, "solver": design.solver_status})
    best = max(rows, key=lambda r: r["annual_kwh"]) if rows else None
    flush = rows[0] if rows else None
    for r in rows:
        r["vs_flush_pct"] = round(100 * (r["annual_kwh"] / flush["annual_kwh"] - 1), 1) if flush and flush["annual_kwh"] else None
    has_flat = any(abs(r["annual_kwh"] - flush["annual_kwh"]) > 1e-6 for r in rows[1:]) if flush else False
    notes = ["Giá nghiêng và pin xoay chỉ áp dụng cho mặt mái bằng; mặt dốc vẫn lắp sát mái.",
             "Khoảng cách hàng giá nghiêng tránh bóng ngày đông chí 9h–15h; pin xoay có lùi góc tránh che (backtracking).",
             "Tấm nghiêng từ khoảng 10° trở lên giúp nước mưa tự rửa bụi; lắp phẳng sát mái bằng dễ đọng bụi, nước.",
             "Chưa tính chi phí giá đỡ/bộ xoay, tải gió và bảo trì; pin xoay trên mái thường cần gia cố và chi phí cao hơn đáng kể."]
    if not has_flat:
        notes.insert(0, "Mái không có mặt bằng phẳng nên các cách lắp cho kết quả như nhau.")
    return {"options": rows, "best": best["label"] if best else None, "notes": notes}
