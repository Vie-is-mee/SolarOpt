"""Compare independent, non-overlapping grids in drawing coordinates.

Every panel keeps its physical width/height; rotation is in the roof plane.
Ranking is exact for each grid's additive score and equal per-panel cost.
Grids are alternatives, never combined into overlapping candidate sets.
"""
import hashlib
import json
import math
from collections import OrderedDict
from threading import Lock
from time import perf_counter
from typing import NamedTuple
from shapely import prepare
from shapely.affinity import rotate
from app.schemas import CandidatePanel
from app.services.geometry import panel_shape, panel_shapes, overlap_ratio, overlap_ratios, _parts, TOP_PREFIX, installable_regions, contour_angle, footprint_dims, row_spacing, own_grid
from app.services.energy import EnergyContext
from app.services.design_policy import capacity, select_for_target, robust_contexts, robust_position, robust_positions


class Grid(NamedTuple):
    """One evaluated grid, kept as arrays: a Python tuple per position costs ten times the memory on a large roof."""
    total: int          # positions tried, fitting or not
    row: object
    col: object
    px: object
    py: object
    cx: object
    cy: object
    face: object        # index into the surfaces of the search
    annual: object
    loss: object
    mean: object
    worst: object


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
    own=lambda s:s.id.startswith(TOP_PREFIX) or own_grid(s)
    surfaces=[(s,r) for s,r in regions if not own(s)]
    tops=[(s,r) for s,r in regions if own(s)]
    centres={s.id:_face_centre(region) for s,region in surfaces+tops}
    for region in [ctx.usable_roof,ctx.obstacle_union,*(r for _,r in surfaces)]:prepare(region)
    cache=_grid_cache(req,ctx,shade_contexts,surfaces)
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
                if perf_counter()-started>=budget_seconds:raise SearchBudgetReached()
                index=len(trials);candidates=[];geometry_count=0;shade_rejected=0;robust_rejected=0
                key=(angle,round(fx,9),round(fy,9),round(sx,9),round(sy,9))
                grid=cache.get(key)
                if grid is None:
                    grid=_evaluate_grid(spec,ctx,surfaces,energy_context,angle,co,si,anchorx+fx*sx,anchory+fy*sy,sx,sy,maxx-margin,maxy-margin)
                    cache[key]=grid
                visited+=grid.total
                if visited>200000:raise SearchBudgetReached()
                limit=SHADING_LIMITS[req.objective]
                allowed=robust_positions(grid.px,grid.py,angle,req,robust) if robust else None
                for i,(row,col,px,py,cx,cy,face,annual,loss,mean,worst) in enumerate(zip(*(a.tolist() for a in grid[1:]))):
                    surface=surfaces[face][0]
                    geometry_count+=1
                    if robust and not allowed[i]:
                        robust_rejected+=1
                        continue
                    if mean<.55 and worst<.50 and loss<=limit:
                        candidate=CandidatePanel(id=f'g{index}r{row}c{col}',x=px,y=py,width_m=spec.width_m,height_m=spec.height_m,
                            rotation_deg=angle,face_id=surface.id,shading_loss_pct=round(loss,2),
                            annual_energy_kwh=annual)
                        candidate.preserved=any(same_position(candidate,p) for p in req.previous_panels)
                        candidate.placement=_placement(centres[surface.id],cx*co-cy*si,cx*si+cy*co)
                        candidates.append(candidate)
                    else:
                        shade_rejected+=1
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


def _evaluate_grid(spec,ctx,surfaces,energy_context,angle,co,si,startx,starty,sx,sy,limitx,limity):
    """The positions of one grid where a panel fits, in row order. Geometry and shading run as array
    operations; positions and results are identical to checking each panel on its own."""
    import numpy as np
    import shapely
    w,h=spec.width_m,spec.height_m;positions=[]
    y=starty;row=0
    while y+h<=limity+1e-7:
        x=startx;col=0
        while x+w<=limitx+1e-7:
            cx,cy=x+w/2,y+h/2
            positions.append((row,col,round(cx*co-cy*si-w/2,6),round(cx*si+cy*co-h/2,6),cx,cy))
            col+=1;x=startx+col*sx
        row+=1;y=starty+row*sy
    if not positions:
        empty=np.empty(0)
        return Grid(0,*[empty]*11)
    shapes=panel_shapes([p[2] for p in positions],[p[3] for p in positions],w,h,angle)
    owner=np.full(len(shapes),-1)
    for i,(_,region) in enumerate(surfaces):
        free=owner<0
        if free.any():owner[free]=np.where(shapely.covers(region,shapes[free]),i,-1)
    fits=(owner>=0)&shapely.covers(ctx.usable_roof,shapes)&(overlap_ratios(shapes,ctx.obstacle_union)<=1e-9)
    index=np.flatnonzero(fits)
    values=energy_context.evaluate_many(shapes[index],spec.power_w,[surfaces[owner[i]][0] for i in index])
    fitted=np.array([positions[i] for i in index],dtype=float).reshape(-1,6)
    return Grid(len(positions),fitted[:,0].astype(np.int32),fitted[:,1].astype(np.int32),fitted[:,2],fitted[:,3],fitted[:,4],fitted[:,5],owner[index].astype(np.int16),
                np.array([v.annual_kwh for v in values],dtype=float),np.array([v.loss_pct for v in values],dtype=float),
                np.array([v.mean_cover for v in values],dtype=float),np.array([v.worst_cover for v in values],dtype=float))


# Grid evaluations depend only on geometry, panel and shading, not on the objective, so the three
# options of one "Tính phương án" (three requests) share them. Two recent projects are kept.
_GRID_CACHE=OrderedDict();_GRID_LOCK=Lock()
NOT_IN_GRID={'project_name','budget_vnd','target_energy_kwh_year','geometry_confirmed','dimensions_source','dimensions_verified','calibration_reference_m'}


def _grid_cache(req,ctx,shade_contexts,surfaces):
    digest=hashlib.sha256()
    # Budget and target pick among the positions; they never change what a position yields.
    digest.update(json.dumps([req.config.model_dump(mode='json',exclude=NOT_IN_GRID),req.panel.model_dump(mode='json'),
                              [o.model_dump(mode='json') for o in req.obstacles]],sort_keys=True).encode())
    for geometry in [ctx.usable_roof,ctx.obstacle_union,*(region for _,region in surfaces),*(c.shadow_union for c in shade_contexts or [])]:
        digest.update(b'|'+(geometry.wkb if geometry is not None else b''))
    digest.update(('|'.join(s.id for s,_ in surfaces)+('|hourly' if shade_contexts is None else '|instants')).encode())
    key=digest.hexdigest()
    with _GRID_LOCK:
        bucket=_GRID_CACHE.pop(key,None)
        _GRID_CACHE[key]=bucket=bucket if bucket is not None else {}
        while len(_GRID_CACHE)>2:_GRID_CACHE.popitem(last=False)
    return bucket


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
    if own_grid(surface):
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
        # Round once, before building shapes, so stored panels are exactly the shapes that were checked.
        pw,ph=(round(v,6) for v in footprint_dims(spec.width_m,spec.height_m,angle,surface,cfg))
        sx,sy=row_spacing(spec.width_m,spec.height_m,angle,surface,cfg)
        if robust:sx+=pw*.01;sy+=ph*.01
        # Rows fit while (n-1) steps plus one panel stay inside; steps may exceed panel+gap (row pitch).
        nx=int((maxx-minx-pw+1e-7)//sx)+1 if maxx-minx>=pw-1e-7 else 0
        ny=int((maxy-miny-ph+1e-7)//sy)+1 if maxy-miny>=ph-1e-7 else 0
        if not nx or not ny:continue
        spare_x,spare_y=maxx-minx-((nx-1)*sx+pw),maxy-miny-((ny-1)*sy+ph)
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
                            candidate=CandidatePanel(id=f'{tag}r{row}c{col}',x=px,y=py,width_m=pw,height_m=ph,
                                rotation_deg=angle,face_id=surface.id,shading_loss_pct=round(value.loss_pct,2),annual_energy_kwh=value.annual_kwh)
                            candidate.preserved=any(same_position(candidate,p) for p in req.previous_panels)
                            candidate.placement=_placement(centre,px+pw/2,py+ph/2)
                            candidates.append(candidate)
                total=sum(max(0,score(req,c)) for c in candidates)
                if total>best_value:best,best_value=candidates,total
    return best
