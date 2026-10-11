"""Explicit design goals. Legacy shading objectives remain API compatible."""
import math
from app.services.geometry import build_context, panel_shape, overlap_ratio


def capacity(req):
    budget=req.config.budget_vnd*(.85 if req.objective=='robust' else 1)
    return max(0,math.floor((budget+1e-7)/req.panel.price_vnd))


def select_for_target(req,candidates):
    # Equal unit prices: the highest-energy prefix uses the fewest panels.
    ordered=sorted(candidates,key=lambda p:(p.annual_energy_kwh,p.preserved),reverse=True)[:capacity(req)]
    selected=[];energy_cents=0
    target_cents=math.ceil(req.config.target_energy_kwh_year*100-1e-7)
    for p in ordered:
        selected.append(p);energy_cents+=round(p.annual_energy_kwh*100)
        if energy_cents>=target_cents:return selected,True
    return selected,False


def robust_contexts(req):
    small=req.config.model_copy(deep=True)
    small.roof_width_m*=.98;small.roof_height_m*=.98
    for point in small.roof_polygon:point.x*=.98;point.y*=.98
    for face in small.roof_faces:
        for point in face.polygon:point.x*=.98;point.y*=.98
    for opening in small.roof_openings:
        for point in opening:point.x*=.98;point.y*=.98
    setback=req.config.model_copy(update={'setback_m':req.config.setback_m+.15})
    return [build_context(cfg,req.obstacles,None) for cfg in (small,setback,req.config)]


def robust_position(x,y,angle,req,contexts):
    for i,ctx in enumerate(contexts):
        scale=1.01 if i==2 else 1
        shape=panel_shape(x,y,req.panel.width_m*scale,req.panel.height_m*scale,angle)
        setback=req.config.setback_m+(.15 if i==1 else 0)
        if (not ctx.usable_roof.covers(shape)
            or not any(s.installable and s.polygon.buffer(-setback,join_style=2).covers(shape) for s in ctx.surfaces)
            or overlap_ratio(shape,ctx.obstacle_union)>1e-9):return False
    return True
