"""Compare independent, non-overlapping grids in drawing coordinates.

Every panel keeps its physical width/height; rotation is in the roof plane.
Ranking is exact for each grid's additive score and equal per-panel cost.
Grids are alternatives, never combined into overlapping candidate sets.
"""
import math
from time import perf_counter
from shapely import prepare
from shapely.affinity import rotate
from app.schemas import CandidatePanel
from app.services.geometry import panel_shape, overlap_ratio, _parts, TOP_PREFIX, installable_regions, contour_angle, footprint_dims, SLOPED_TILT
from app.services.energy import EnergyContext
from app.services.design_policy import capacity, select_for_target, robust_contexts, robust_position


def same_position(a, b, tol=.02):
    angle = abs((a.rotation_deg-b.rotation_deg+90) % 180-90)
    return (abs(a.x-b.x)<=tol and abs(a.y-b.y)<=tol
            and abs(a.width_m-b.width_m)<=tol and abs(a.height_m-b.height_m)<=tol
            and angle<=.01)


# Near-ties on energy (common on unshaded flat roofs) are broken towards a compact block in the
# middle of each face, away from edges, as installers group arrays. Capped at 0.3 % of a panel's
# energy score, so it never gives up more than that to move a panel.
PLACEMENT_WEIGHT = .003

SHADING_LIMITS = {'max_energy': 70, 'min_cost': 70, 'robust': 10, 'balanced': 18, 'durability': 10}


def score(req, candidate):
    value = int(round(candidate.annual_energy_kwh*100))
    if req.objective == 'durability':
        value = int(round(value*(1-min(candidate.shading_loss_pct,50)/120)))
    if req.objective == 'min_cost':return value
    value += int(round(value*PLACEMENT_WEIGHT*candidate.placement))
    # Balanced maximizes energy within its shade cap. A fixed subtraction per
    # panel was an undocumented cost penalty despite identical panel prices.
    return value + (int(round(req.minimal_repair_weight*100)) if candidate.preserved else 0)


def search_layouts(req, ctx, shade_contexts, *, budget_seconds=25., diagnostics=None):
    started=perf_counter()
    # Limit candidate search, not safety checks. Never rank an unfinished grid.
    class SearchBudgetReached(Exception):pass
    cfg, spec = req.config, req.panel
    energy_context = EnergyContext(cfg, req.obstacles, ctx, shade_contexts)
    # Directions modulo 90 identify both portrait and landscape orientations.
    directions={0.0:0.0}
    if cfg.layout_angle_deg is None:
        weights={}
        for part in _parts(ctx.roof):
            coords=list(part.exterior.coords)
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
    regions=installable_regions(ctx.surfaces,margin)
    # Obstacle tops and sloped faces get their own grid: tops sit inside a blocked footprint, and on a
    # slope the panel's plan footprint shrinks along the fall line, so it must follow that face's contour.
    own=lambda s:s.id.startswith(TOP_PREFIX) or s.tilt>SLOPED_TILT
    surfaces=[(s,r) for s,r in regions if not own(s)]
    tops=[(s,r) for s,r in regions if own(s)]
    centres={s.id:_face_centre(region) for s,region in surfaces+tops}
    for region in [ctx.usable_roof,ctx.obstacle_union,*(r for _,r in surfaces)]:prepare(region)
    max_count=capacity(req)
    robust=robust_contexts(req) if req.objective=='robust' else []
    trials=[];best=[];best_rank=None;best_index=0;visited=0
    refined=False
    try:
        for angle in angles:
            radians=math.radians(angle);co,si=math.cos(radians),math.sin(radians)
            minx,miny,maxx,maxy=rotate(ctx.roof,-angle,origin=(0,0)).bounds
            anchorx,anchory=minx+margin,miny+margin
            sx,sy=spec.width_m+cfg.panel_gap_m,spec.height_m+cfg.panel_gap_m
            if robust:sx+=spec.width_m*.01;sy+=spec.height_m*.01
            phases=([(0,0),(.5,0),(0,.5),(.5,.5)] if not refined else [(x,y) for x in (0,.25,.5,.75) for y in (0,.25,.5,.75)])
            # A narrow face may fit panels only at a phase absent from the
            # whole-roof grid. Try face-aligned origins, still as separate grids.
            for _, region in surfaces[:8]:
                if region.is_empty:continue
                left,bottom,_,_=rotate(region,-angle,origin=(0,0)).bounds
                phase=(((left+1e-6-anchorx)%sx)/sx,((bottom+1e-6-anchory)%sy)/sy)
                if not any(abs(phase[0]-x)<1e-7 and abs(phase[1]-y)<1e-7 for x,y in phases):
                    phases.append(phase)
            # Also test the original grid phase when repairing a rotated layout.
            for p in req.previous_panels:
                if abs((p.rotation_deg-angle+90)%180-90)<.01:
                    cx,cy=p.x+p.width_m/2,p.y+p.height_m/2
                    phases.append((((cx*co+cy*si-spec.width_m/2-anchorx)%sx)/sx,
                                   ((-cx*si+cy*co-spec.height_m/2-anchory)%sy)/sy))
                    break
            for fx,fy in phases:
                index=len(trials);candidates=[];geometry_count=0;shade_rejected=0;robust_rejected=0
                y=anchory+fy*sy;row=0
                while y+spec.height_m<=maxy-margin+1e-7:
                    x=anchorx+fx*sx;col=0
                    while x+spec.width_m<=maxx-margin+1e-7:
                        visited+=1
                        if visited>200000 or (visited % 32 == 1 and perf_counter()-started>=budget_seconds):raise SearchBudgetReached()
                        cx,cy=x+spec.width_m/2,y+spec.height_m/2
                        px=round(cx*co-cy*si-spec.width_m/2,6)
                        py=round(cx*si+cy*co-spec.height_m/2,6)
                        shape=panel_shape(px,py,spec.width_m,spec.height_m,angle)
                        surface=next((s for s,region in surfaces if region.covers(shape)),None)
                        if surface and ctx.usable_roof.covers(shape) and overlap_ratio(shape,ctx.obstacle_union)<=1e-9:
                            geometry_count+=1
                            if robust and not robust_position(px,py,angle,req,robust):
                                robust_rejected+=1
                                col+=1;x=anchorx+fx*sx+col*sx
                                continue
                            value=energy_context.evaluate(shape,spec.power_w,surface)
                            mean,worst,loss=value.mean_cover,value.worst_cover,value.loss_pct
                            limit=SHADING_LIMITS[req.objective]
                            if mean<.55 and worst<.50 and loss<=limit:
                                candidate=CandidatePanel(id=f'g{index}r{row}c{col}',x=px,y=py,width_m=spec.width_m,height_m=spec.height_m,
                                    rotation_deg=angle,face_id=surface.id,shading_loss_pct=round(loss,2),
                                    annual_energy_kwh=value.annual_kwh)
                                candidate.preserved=any(same_position(candidate,p) for p in req.previous_panels)
                                candidate.placement=_placement(centres[surface.id],cx*co-cy*si,cx*si+cy*co)
                                candidates.append(candidate)
                            else:
                                shade_rejected+=1
                        col+=1;x=anchorx+fx*sx+col*sx
                    row+=1;y=anchory+fy*sy+row*sy
                selected=sorted((p for p in candidates if score(req,p)>0),key=lambda p:score(req,p),reverse=True)[:max_count]
                value=sum(score(req,p) for p in selected)
                target_met=None;rank=(value,)
                if req.objective=='min_cost':
                    selected,target_met=select_for_target(req,candidates)
                    energy=sum(p.annual_energy_kwh for p in selected)
                    rank=(target_met,-len(selected) if target_met else energy,energy)
                    value=(-len(selected)*spec.price_vnd if target_met else -1e15+energy)*100
                trials.append(dict(search_stage='refined' if refined else 'coarse',angle_deg=angle,offset_x_m=round(fx*sx,4),offset_y_m=round(fy*sy,4),
                    candidate_count=len(candidates),geometry_candidate_count=geometry_count,shading_rejected_count=shade_rejected,robustness_rejected_count=robust_rejected,target_met=target_met,panel_count=len(selected),annual_energy_kwh=round(sum(p.annual_energy_kwh for p in selected),1),
                    objective_score=value/100,selected=False))
                if best_rank is None or rank>best_rank:
                    best,best_rank,best_index=candidates,rank,index
            # Refine only after evaluating all coarse grids. Keep their winner.
            if not refined and angle==angles[-1]:
                refined=True
                center=trials[best_index]['angle_deg']
                angles.extend([round((center+d)%180,3) for d in ((0,-2,-1,1,2) if cfg.layout_angle_deg is None else (0,))])
    except SearchBudgetReached:
        if not trials:
            raise ValueError('Mái quá phức tạp để hoàn tất một lưới trong thời gian cho phép. Chọn góc xếp thủ công hoặc giảm phạm vi mái rồi thử lại.')
        if diagnostics is not None:diagnostics['limited']=True
    # Own-grid faces are disjoint from each other and from the main-grid faces, so their best grids
    # can be added without overlap; grouped seams keep half a gap on each side.
    extra=[]
    for t,(surface,region) in enumerate(tops):
        if not region.is_empty and perf_counter()-started<budget_seconds+5:
            extra+=_best_top_grid(req,ctx,energy_context,surface,region,f't{t}',robust,centres[surface.id])
    if diagnostics is not None:
        diagnostics.update(positions=visited, elapsed_ms=round((perf_counter()-started)*1000), obstacle_top_candidates=len(extra))
    trials[best_index]['selected']=True
    return best+extra,trials


def _face_centre(region):
    """Centroid of a usable face and the distance from it to the farthest usable point."""
    if region.is_empty:return None
    c=region.centroid
    reach=max((math.hypot(x-c.x,y-c.y) for part in _parts(region) for x,y in part.exterior.coords),default=0)
    return c.x,c.y,reach


def _placement(centre,x,y):
    if not centre or centre[2]<=0:return 0.0
    return round(max(0.0,1-math.hypot(x-centre[0],y-centre[1])/centre[2]),4)


def _best_top_grid(req,ctx,energy_context,surface,region,tag,robust,centre=None):
    """Small exhaustive grid on one face (obstacle top or sloped face): edge or contour aligned,
    portrait/landscape, edge or centred offsets. Sloped faces use the plan footprint of the panel."""
    cfg,spec=req.config,req.panel
    region=region.intersection(surface.polygon.buffer(-cfg.panel_gap_m/2,join_style=2))
    if region.is_empty:return []
    if surface.tilt>SLOPED_TILT:
        level=round(contour_angle(surface,cfg),3);angles={level,round((level+90)%180,3)}
    else:
        edge=max(zip(region.minimum_rotated_rectangle.exterior.coords,list(region.minimum_rotated_rectangle.exterior.coords)[1:]),
                 key=lambda e:math.hypot(e[1][0]-e[0][0],e[1][1]-e[0][1]))
        lead=round(math.degrees(math.atan2(edge[1][1]-edge[0][1],edge[1][0]-edge[0][0]))%180,3)
        angles={0.0,90.0,lead,round((lead+90)%180,3)}
    best,best_value=[],0
    for angle in sorted(angles):
        radians=math.radians(angle);co,si=math.cos(radians),math.sin(radians)
        minx,miny,maxx,maxy=rotate(region,-angle,origin=(0,0)).bounds
        pw,ph=footprint_dims(spec.width_m,spec.height_m,angle,surface,cfg)
        sx,sy=pw+cfg.panel_gap_m,ph+cfg.panel_gap_m
        if robust:sx+=pw*.01;sy+=ph*.01
        nx,ny=int((maxx-minx+cfg.panel_gap_m+1e-7)//sx),int((maxy-miny+cfg.panel_gap_m+1e-7)//sy)
        if not nx or not ny:continue
        spare_x,spare_y=maxx-minx-(nx*sx-cfg.panel_gap_m),maxy-miny-(ny*sy-cfg.panel_gap_m)
        for ox in {0.0,spare_x/2}:
            for oy in {0.0,spare_y/2}:
                candidates=[]
                for row in range(ny):
                    for col in range(nx):
                        x,y=minx+ox+col*sx,miny+oy+row*sy
                        cx,cy=x+pw/2,y+ph/2
                        px,py=round(cx*co-cy*si-pw/2,6),round(cx*si+cy*co-ph/2,6)
                        shape=panel_shape(px,py,pw,ph,angle)
                        if not(region.covers(shape) and ctx.usable_roof.covers(shape) and overlap_ratio(shape,ctx.obstacle_union)<=1e-9):continue
                        if robust and not robust_position(px,py,angle,req,robust,pw,ph):continue
                        value=energy_context.evaluate(shape,spec.power_w,surface)
                        if value.mean_cover<.55 and value.worst_cover<.50 and value.loss_pct<=SHADING_LIMITS[req.objective]:
                            candidate=CandidatePanel(id=f'{tag}r{row}c{col}',x=px,y=py,width_m=round(pw,6),height_m=round(ph,6),
                                rotation_deg=angle,face_id=surface.id,shading_loss_pct=round(value.loss_pct,2),annual_energy_kwh=value.annual_kwh)
                            candidate.preserved=any(same_position(candidate,p) for p in req.previous_panels)
                            candidate.placement=_placement(centre,px+pw/2,py+ph/2)
                            candidates.append(candidate)
                total=sum(max(0,score(req,c)) for c in candidates)
                if total>best_value:best,best_value=candidates,total
    return best
