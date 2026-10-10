"""Compare independent, non-overlapping grids in drawing coordinates.

Every panel keeps its physical width/height; rotation is in the roof plane.
Ranking is exact for each grid's additive score and equal per-panel cost.
Grids are alternatives, never combined into overlapping candidate sets.
"""
import math
from shapely.affinity import rotate
from app.schemas import CandidatePanel
from app.services.geometry import panel_shape, overlap_ratio


def same_position(a, b, tol=.02):
    angle = abs((a.rotation_deg-b.rotation_deg+90) % 180-90)
    return (abs(a.x-b.x)<=tol and abs(a.y-b.y)<=tol
            and abs(a.width_m-b.width_m)<=tol and abs(a.height_m-b.height_m)<=tol
            and angle<=.01)


def score(req, candidate):
    value = int(round(candidate.annual_energy_kwh*100))
    if req.objective == 'durability':
        value = int(round(value*(1-min(candidate.shading_loss_pct,50)/120)))
    elif req.objective == 'balanced':
        value = int(round(value-req.panel.power_w/1000*req.config.annual_irradiance_kwh_m2*req.config.performance_ratio*35))
    return value + (int(round(req.minimal_repair_weight*100)) if candidate.preserved else 0)


def search_layouts(req, ctx, shade_contexts):
    cfg, spec = req.config, req.panel
    # Directions modulo 90 identify both portrait and landscape orientations.
    directions={0.0:0.0}
    if cfg.layout_angle_deg is None:
        coords=list(ctx.roof.exterior.coords)
        weights={}
        for a,b in zip(coords,coords[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1]
            direction=round(math.degrees(math.atan2(dy,dx))%90,1)
            if direction>=89.9 or direction<.1:direction=0.0
            weights[direction]=weights.get(direction,0)+math.hypot(dx,dy)
        for angle in sorted(weights,key=weights.get,reverse=True)[:2]:
            directions[angle]=weights[angle]
        angles=sorted({round((a+d)%180,3) for a in directions for d in (0,90)})
    else:
        angles=[cfg.layout_angle_deg%180]
    if cfg.layout_angle_deg is None:
        angles=sorted(set(angles+[p.rotation_deg%180 for p in req.previous_panels]))
    margin=cfg.setback_m+cfg.layout_edge_reserve_m
    surfaces=[(s,s.polygon.buffer(-margin,join_style=2)) for s in ctx.surfaces if s.installable]
    capacity=(int(round(cfg.budget_vnd))//int(round(spec.price_vnd)) if spec.price_vnd>=1 else 100000)
    trials=[];best=[];best_score=-1;best_index=0;visited=0
    refined=False
    for angle in angles:
        radians=math.radians(angle);co,si=math.cos(radians),math.sin(radians)
        minx,miny,maxx,maxy=rotate(ctx.roof,-angle,origin=(0,0)).bounds
        anchorx,anchory=minx+margin,miny+margin
        sx,sy=spec.width_m+cfg.panel_gap_m,spec.height_m+cfg.panel_gap_m
        phases=([(0,0),(.5,0),(0,.5),(.5,.5)] if not refined else [(x,y) for x in (0,.25,.5,.75) for y in (0,.25,.5,.75)])
        # Also test the original grid phase when repairing a rotated layout.
        for p in req.previous_panels:
            if abs((p.rotation_deg-angle+90)%180-90)<.01:
                cx,cy=p.x+p.width_m/2,p.y+p.height_m/2
                phases.append((((cx*co+cy*si-spec.width_m/2-anchorx)%sx)/sx,
                               ((-cx*si+cy*co-spec.height_m/2-anchory)%sy)/sy))
                break
        for fx,fy in phases:
            index=len(trials);candidates=[]
            y=anchory+fy*sy;row=0
            while y+spec.height_m<=maxy-margin+1e-7:
                x=anchorx+fx*sx;col=0
                while x+spec.width_m<=maxx-margin+1e-7:
                    visited+=1
                    if visited>200000:raise ValueError('Quá nhiều vị trí cần thử; giảm quy mô mái hoặc tăng kích thước tấm pin.')
                    cx,cy=x+spec.width_m/2,y+spec.height_m/2
                    px=round(cx*co-cy*si-spec.width_m/2,6)
                    py=round(cx*si+cy*co-spec.height_m/2,6)
                    shape=panel_shape(px,py,spec.width_m,spec.height_m,angle)
                    surface=next((s for s,region in surfaces if region.covers(shape)),None)
                    if surface and ctx.usable_roof.covers(shape) and overlap_ratio(shape,ctx.obstacle_union)<=1e-9:
                        overlaps=[overlap_ratio(shape,c.shadow_union) for c in shade_contexts]
                        mean=sum(overlaps)/max(1,len(overlaps));worst=max(overlaps,default=0)
                        loss=min(70,(.72*mean+.28*worst)*78)
                        limit=10 if req.objective=='durability' else 18 if req.objective=='balanced' else 70
                        if mean<.55 and worst<.50 and loss<=limit:
                            candidate=CandidatePanel(id=f'g{index}r{row}c{col}',x=px,y=py,width_m=spec.width_m,height_m=spec.height_m,
                                rotation_deg=angle,face_id=surface.id,shading_loss_pct=round(loss,2),
                                annual_energy_kwh=round(spec.power_w/1000*cfg.annual_irradiance_kwh_m2*cfg.performance_ratio*(1-loss/100),2))
                            candidate.preserved=any(same_position(candidate,p) for p in req.previous_panels)
                            candidates.append(candidate)
                    col+=1;x=anchorx+fx*sx+col*sx
                row+=1;y=anchory+fy*sy+row*sy
            selected=sorted((p for p in candidates if score(req,p)>0),key=lambda p:score(req,p),reverse=True)[:capacity]
            value=sum(score(req,p) for p in selected)
            trials.append(dict(search_stage='refined' if refined else 'coarse',angle_deg=angle,offset_x_m=round(fx*sx,4),offset_y_m=round(fy*sy,4),
                candidate_count=len(candidates),panel_count=len(selected),annual_energy_kwh=round(sum(p.annual_energy_kwh for p in selected),1),
                objective_score=value/100,selected=False))
            if value>best_score:
                best,best_score,best_index=candidates,value,index
        # Refine only after evaluating all coarse grids. Keep their winner.
        if not refined and angle==angles[-1]:
            refined=True
            center=trials[best_index]['angle_deg']
            angles.extend([round((center+d)%180,3) for d in ((0,-2,-1,1,2) if cfg.layout_angle_deg is None else (0,))])
    trials[best_index]['selected']=True
    return best,trials
