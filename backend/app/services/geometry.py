from __future__ import annotations
import math
from dataclasses import dataclass,field
from shapely.affinity import rotate,scale
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union
from app.schemas import ProjectConfig,RectObstacle,SunPosition

@dataclass
class Surface:
    id:str
    label:str
    polygon:Polygon
    elevation:float
    tilt:float
    azimuth:float
    origin_x:float=0
    origin_y:float=0
    installable:bool=True

@dataclass
class GeometryContext:
    roof:Polygon
    usable_roof:Polygon
    obstacle_union:Polygon|None
    shadow_union:Polygon|None
    forbidden:Polygon|None
    surfaces:list[Surface]=field(default_factory=list)
    shadows:list[dict]=field(default_factory=list)

def obstacle_polygon(o:RectObstacle)->Polygon:
    if o.shape=='polygon' and o.points:
        p=Polygon([(o.x+t.x,o.y+t.y) for t in o.points])
    elif o.shape=='ellipse':
        p=scale(Point(o.x+o.width_m/2,o.y+o.depth_m/2).buffer(1,quad_segs=12),o.width_m/2,o.depth_m/2)
    else:p=box(o.x,o.y,o.x+o.width_m,o.y+o.depth_m)
    return rotate(p,o.rotation_deg,origin=(o.x+o.width_m/2,o.y+o.depth_m/2)) if o.rotation_deg else p

def roof_polygon(config:ProjectConfig)->Polygon:
    p=Polygon([(t.x,t.y) for t in config.roof_polygon]) if config.roof_polygon else box(0,0,config.roof_width_m,config.roof_height_m)
    if config.roof_openings:p=p.difference(unary_union([Polygon([(t.x,t.y) for t in hole]) for hole in config.roof_openings]))
    return p

def surfaces(config:ProjectConfig)->list[Surface]:
    roof=roof_polygon(config);result=[];used=[]
    for f in config.roof_faces:
        p=Polygon([(t.x,t.y) for t in f.polygon]).intersection(roof)
        if not p.is_empty:
            center=p.centroid
            result.append(Surface(f.id,f.label,p,f.elevation_m,f.tilt_deg,f.azimuth_deg,center.x,center.y,f.installable));used.append(p)
    remaining=roof.difference(unary_union(used)) if used else roof
    if remaining.area>1e-8:result.append(Surface('base','Mái cơ sở',remaining,config.roof_elevation_m,config.roof_tilt_deg,config.roof_azimuth_deg))
    return result

def slopes(tilt,azimuth,rotation):
    bearing=math.radians(azimuth-rotation);gradient=-math.tan(math.radians(tilt))
    return gradient*math.sin(bearing),gradient*math.cos(bearing)

def roof_slopes(config):return slopes(config.roof_tilt_deg,config.roof_azimuth_deg,config.north_rotation_deg)

def surface_z(s,x,y,config):
    gx,gy=slopes(s.tilt,s.azimuth,config.north_rotation_deg)
    return s.elevation+gx*(x-s.origin_x)+gy*(y-s.origin_y)

def _parts(shape):
    if shape.is_empty:return []
    if shape.geom_type=='Polygon':return [shape]
    return [p for g in getattr(shape,'geoms',[]) for p in _parts(g)]

def _project_prism(base,top_z,target,sun,config):
    if sun is None or sun.altitude_deg<=0:return None
    angle=math.radians(sun.azimuth_deg-config.north_rotation_deg);ux,uy=math.sin(angle),math.cos(angle)
    gx,gy=slopes(target.tilt,target.azimuth,config.north_rotation_deg)
    denominator=math.tan(math.radians(sun.altitude_deg))-gx*ux-gy*uy
    if denominator<=1e-6:return target.polygon
    pieces=[]
    for poly in _parts(base):
        rings=[list(poly.exterior.coords)[:-1]]+[list(r.coords)[:-1] for r in poly.interiors]
        projected_rings=[];above=False
        for coords in rings:
            projected=[]
            for x,y in coords:
                height=top_z(x,y)-surface_z(target,x,y,config)
                above=above or height>1e-6
                distance=min(10000,max(0,height)/denominator)
                projected.append((x-distance*ux,y-distance*uy))
            projected_rings.append(projected)
        if not above:continue
        pieces.append(poly)
        shifted=Polygon(projected_rings[0],projected_rings[1:])
        if not shifted.is_valid:shifted=shifted.buffer(0)
        pieces.append(shifted)
        for coords,projected in zip(rings,projected_rings):
            for i,a in enumerate(coords):
                j=(i+1)%len(coords)
                side=Polygon([a,coords[j],projected[j],projected[i]])
                if not side.is_valid:side=side.buffer(0)
                pieces.append(side)
    return unary_union(pieces) if pieces else None

def shadow_polygon(o:RectObstacle,sun:SunPosition|None,config:ProjectConfig|None=None,target:Surface|None=None,all_surfaces=None):
    cfg=config or ProjectConfig(roof_elevation_m=0)
    target=target or Surface('base','Mái',roof_polygon(cfg),cfg.roof_elevation_m,cfg.roof_tilt_deg,cfg.roof_azimuth_deg)
    base=obstacle_polygon(o)
    source=next((s for s in (all_surfaces or surfaces(cfg)) if s.polygon.covers(base.centroid)),target)
    def top(x,y):
        elevation=o.base_elevation_m if o.base_elevation_m is not None else (0 if o.scope=='neighbor' else surface_z(source,x,y,cfg))
        return elevation+o.height_m
    return _project_prism(base,top,target,sun,cfg)

def build_context(config:ProjectConfig,obstacles:list[RectObstacle],sun:SunPosition|None)->GeometryContext:
    roof=roof_polygon(config);planes=surfaces(config)
    usable_parts=[s.polygon.buffer(-config.setback_m,join_style=2) for s in planes if s.installable]
    usable=unary_union(usable_parts) if usable_parts else Polygon()
    obstacle_shapes=[obstacle_polygon(o).buffer(config.obstacle_clearance_m,join_style=2) for o in obstacles]
    records=[]
    for o in obstacles:
        shapes=[]
        for target in planes:
            shadow=shadow_polygon(o,sun,config,target,planes)
            if shadow is not None:shapes.append(shadow.intersection(target.polygon))
        records.append({'id':o.id,'label':o.label,'shape':unary_union(shapes) if shapes else None})
    for source in planes:
        shapes=[]
        for target in planes:
            if target.id==source.id:continue
            shadow=_project_prism(source.polygon,lambda x,y:surface_z(source,x,y,config),target,sun,config)
            if shadow is not None:shapes.append(shadow.intersection(target.polygon))
        records.append({'id':'face-'+source.id,'label':source.label,'shape':unary_union(shapes) if shapes else None})
    obstacle_union=unary_union(obstacle_shapes) if obstacle_shapes else None
    shadow_shapes=[r['shape'] for r in records if r['shape'] is not None and not r['shape'].is_empty]
    shadow_union=unary_union(shadow_shapes) if shadow_shapes else None
    pieces=[g for g in [obstacle_union,shadow_union] if g is not None and not g.is_empty]
    return GeometryContext(roof,usable,obstacle_union,shadow_union,unary_union(pieces) if pieces else None,planes,records)

def panel_shape(x,y,width,height,rotation_deg=0):
    shape=box(x,y,x+width,y+height)
    return rotate(shape,rotation_deg,origin=(x+width/2,y+height/2)) if rotation_deg else shape

def overlap_ratio(shape,other):
    if other is None or other.is_empty or shape.area<=0:return 0.0
    return max(0,min(1,shape.intersection(other).area/shape.area))
