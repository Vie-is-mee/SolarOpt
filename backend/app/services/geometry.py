from __future__ import annotations
import math
from dataclasses import dataclass,field
from shapely.affinity import rotate,scale
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union
from app.schemas import ProjectConfig,RectObstacle,RoofFace,SunPosition

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
    group:str|None=None

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
            result.append(Surface(f.id,f.label,p,f.elevation_m,f.tilt_deg,f.azimuth_deg,center.x,center.y,f.installable,f.group));used.append(p)
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


def direct_sun_reaches(surface,sun,config):
    if sun is None or sun.altitude_deg<=0:return False
    bearing=math.radians(sun.azimuth_deg-config.north_rotation_deg)
    gx,gy=slopes(surface.tilt,surface.azimuth,config.north_rotation_deg)
    return math.tan(math.radians(sun.altitude_deg))-gx*math.sin(bearing)-gy*math.cos(bearing)>1e-8


def _above_receiver(poly,top_z,target,config):
    """Clip affine prism top against the receiver's height half-plane.

    Intersecting a convex clipping box with the source preserves concavity,
    holes and disjoint parts. Buried vertices must not become shadow sources.
    """
    xmin,ymin,xmax,ymax=poly.bounds
    ring=[(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)]
    height=lambda p:top_z(*p)-surface_z(target,*p,config)
    values=[height(p) for p in ring]
    if max(values)<=1e-8:return Polygon()
    if min(values)>=0:return poly
    clipped=[]
    for i,a in enumerate(ring):
        b=ring[(i+1)%4];ha,hb=values[i],values[(i+1)%4]
        if ha>=0:clipped.append(a)
        if (ha>=0)!=(hb>=0):
            t=ha/(ha-hb);clipped.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
    return poly.intersection(Polygon(clipped)) if len(clipped)>=3 else Polygon()

def _project_prism(base,top_z,target,sun,config,bottom_z=None):
    if sun is None or sun.altitude_deg<=0:return None
    angle=math.radians(sun.azimuth_deg-config.north_rotation_deg);ux,uy=math.sin(angle),math.cos(angle)
    gx,gy=slopes(target.tilt,target.azimuth,config.north_rotation_deg)
    denominator=math.tan(math.radians(sun.altitude_deg))-gx*ux-gy*uy
    # This face has no incident direct sun. It must not be attributed as a
    # full-roof shadow from each unrelated obstacle; diffuse light is separate.
    if denominator<=1e-8:return None
    pieces=[]
    exposed=unary_union([_above_receiver(poly,top_z,target,config) for poly in _parts(base)])
    for poly in _parts(exposed):
        rings=[list(poly.exterior.coords)[:-1]]+[list(r.coords)[:-1] for r in poly.interiors]
        if bottom_z:
            # The bottom may cross the receiver between vertices. Insert that
            # crossing so clamping to the receiver remains piecewise affine.
            refined=[]
            for ring in rings:
                points=[]
                for i,a in enumerate(ring):
                    b=ring[(i+1)%len(ring)];points.append(a)
                    ha=bottom_z(*a)-surface_z(target,*a,config)
                    hb=bottom_z(*b)-surface_z(target,*b,config)
                    if (ha>0)!=(hb>0) and abs(ha-hb)>1e-12:
                        t=ha/(ha-hb)
                        if 1e-10<t<1-1e-10:points.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
                refined.append(points)
            rings=refined
        projected_rings=[];bottom_rings=[];above=False
        for coords in rings:
            projected=[];bottom=[]
            for x,y in coords:
                height=top_z(x,y)-surface_z(target,x,y,config)
                above=above or height>1e-6
                distance=min(10000,max(0,height)/denominator)
                projected.append((x-distance*ux,y-distance*uy))
                lower_height=bottom_z(x,y)-surface_z(target,x,y,config) if bottom_z else 0
                lower_distance=min(10000,max(0,lower_height)/denominator)
                bottom.append((x-lower_distance*ux,y-lower_distance*uy))
            projected_rings.append(projected);bottom_rings.append(bottom)
        if not above:continue
        lower=Polygon(bottom_rings[0],bottom_rings[1:])
        if not lower.is_valid:lower=lower.buffer(0)
        pieces.append(lower)
        shifted=Polygon(projected_rings[0],projected_rings[1:])
        if not shifted.is_valid:shifted=shifted.buffer(0)
        pieces.append(shifted)
        for coords,projected in zip(bottom_rings,projected_rings):
            for i,a in enumerate(coords):
                j=(i+1)%len(coords)
                side=Polygon([a,coords[j],projected[j],projected[i]])
                if not side.is_valid:side=side.buffer(0)
                pieces.append(side)
    return unary_union(pieces) if pieces else None

TOP_PREFIX='top-'


def obstacle_source_surface(o,config,all_surfaces=None):
    base=obstacle_polygon(o)
    # An obstacle stands on the roof below it, never on the installable top derived from itself.
    return next((s for s in (all_surfaces or surfaces(config)) if not s.id.startswith(TOP_PREFIX) and s.polygon.covers(base.centroid)),
        Surface('base','Mái cơ sở (ngoại suy)',roof_polygon(config),config.roof_elevation_m,config.roof_tilt_deg,config.roof_azimuth_deg))


def obstacle_base_z(o,x,y,source,config):
    return o.base_elevation_m if o.base_elevation_m is not None else (0 if o.scope=='neighbor' else surface_z(source,x,y,config))


def obstacle_elevations(config,obstacles,planes=None):
    planes=planes or surfaces(config);roof=roof_polygon(config);records=[]
    for o in obstacles:
        footprint=obstacle_polygon(o);source=obstacle_source_surface(o,config,planes)
        bases=[obstacle_base_z(o,x,y,source,config) for x,y in footprint.exterior.coords]
        warnings=[]
        if o.scope=='roof' and o.base_elevation_m is None:
            if not roof.buffer(1e-7).covers(footprint):warnings.append('Mặt bằng vượt biên mái hoặc khoảng trống; cao độ mặc định có phần ngoại suy. Cần kiểm tra hoặc nhập cao độ chân riêng.')
            if sum(footprint.intersection(s.polygon).area>1e-6 for s in planes)>1:warnings.append('Vật thể bắc qua nhiều phần mái. Cao độ chân đang theo mặt mái chứa tâm vật thể; cần đo và xác nhận riêng.')
        if min(bases)<-1e-6:warnings.append('Cao độ chân có điểm thấp hơn mặt đất; kiểm tra cao độ và hướng dốc.')
        records.append({'id':o.id,'label':o.label,'base_source':'explicit' if o.base_elevation_m is not None else 'ground' if o.scope=='neighbor' else 'roof',
            'source_label':'Cao độ nhập riêng' if o.base_elevation_m is not None else 'Mặt đất' if o.scope=='neighbor' else source.label,
            'base_min_m':round(min(bases),3),'base_max_m':round(max(bases),3),'top_min_m':round(min(bases)+o.height_m,3),'top_max_m':round(max(bases)+o.height_m,3),'height_m':o.height_m,'warnings':warnings})
    return records


def shadow_polygon(o:RectObstacle,sun:SunPosition|None,config:ProjectConfig|None=None,target:Surface|None=None,all_surfaces=None):
    cfg=config or ProjectConfig(roof_elevation_m=0)
    target=target or Surface('base','Mái',roof_polygon(cfg),cfg.roof_elevation_m,cfg.roof_tilt_deg,cfg.roof_azimuth_deg)
    base=obstacle_polygon(o)
    source=obstacle_source_surface(o,cfg,all_surfaces)
    def top(x,y):
        return obstacle_base_z(o,x,y,source,cfg)+o.height_m
    return _project_prism(base,top,target,sun,cfg,lambda x,y:obstacle_base_z(o,x,y,source,cfg))

def top_installable_obstacles(config:ProjectConfig,obstacles:list[RectObstacle]):
    roof=roof_polygon(config)
    return [o for o in obstacles if o.top_installable and o.scope=='roof' and o.height_m>0 and roof.covers(obstacle_polygon(o).centroid)]


def with_obstacle_tops(config:ProjectConfig,obstacles:list[RectObstacle])->ProjectConfig:
    """Add each flat, installable obstacle top as a horizontal roof face at its top elevation.
    The obstacle itself still blocks the roof below and casts its shadow."""
    tops=top_installable_obstacles(config,obstacles)
    if not tops:return config
    planes=surfaces(config);faces=list(config.roof_faces)
    for o in tops:
        footprint=obstacle_polygon(o);source=obstacle_source_surface(o,config,planes)
        top=max(obstacle_base_z(o,x,y,source,config) for x,y in footprint.exterior.coords)+o.height_m
        coords=[(round(x,4),round(y,4)) for x,y in footprint.exterior.coords[:-1]][:80]
        faces.append(RoofFace(id=TOP_PREFIX+o.id,label=f'Nóc {o.label}',polygon=[{'x':x,'y':y} for x,y in coords],
                              elevation_m=min(300,top),tilt_deg=0,azimuth_deg=180,installable=True))
    return config.model_copy(update={'roof_faces':faces})


def installable_regions(planes,margin):
    """Usable part of each installable face. Grouped faces (one continuous surface split into strips)
    are set back only from the group's outer edge, never along their shared seams."""
    groups={}
    for s in planes:
        if s.installable and s.group:groups.setdefault(s.group,[]).append(s.polygon)
    shrunk={g:unary_union(parts).buffer(-margin,join_style=2) for g,parts in groups.items()}
    return [(s,s.polygon.intersection(shrunk[s.group]) if s.group else s.polygon.buffer(-margin,join_style=2)) for s in planes if s.installable]


def build_context(config:ProjectConfig,obstacles:list[RectObstacle],sun:SunPosition|None)->GeometryContext:
    config=with_obstacle_tops(config,obstacles)
    roof=roof_polygon(config);planes=surfaces(config)
    usable_parts=[region for _,region in installable_regions(planes,config.setback_m)]
    usable=unary_union(usable_parts) if usable_parts else Polygon()
    def blocked(o):
        shape=obstacle_polygon(o).buffer(config.obstacle_clearance_m,join_style=2)
        # Installable top: only the clearance ring and the top's own edge setback stay blocked.
        return shape.difference(obstacle_polygon(o).buffer(-config.setback_m,join_style=2)) if o.top_installable and o.scope=='roof' else shape
    obstacle_shapes=[blocked(o) for o in obstacles]
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

SLOPED_TILT=1.0


def contour_angle(surface,config):
    """Drawing direction (degrees, CCW from +x, mod 180) along which a face stays level."""
    return (-(surface.azimuth-config.north_rotation_deg))%180


def footprint_dims(width,height,angle,surface,config):
    """Plan footprint of a physical width x height panel lying on a face, its local x axis at angle.
    The side running down the fall line shrinks by cos(tilt). Panels on sloped faces are only laid
    along or across the fall line; any other angle returns None."""
    c=math.cos(math.radians(surface.tilt)) if surface is not None else 1.0
    if surface is None or surface.tilt<=SLOPED_TILT:return width,height
    d=abs((angle-contour_angle(surface,config)+90)%180-90)
    if d<.01:return width,height*c
    if abs(d-90)<.01:return width*c,height
    return None


def panel_shape(x,y,width,height,rotation_deg=0):
    shape=box(x,y,x+width,y+height)
    return rotate(shape,rotation_deg,origin=(x+width/2,y+height/2)) if rotation_deg else shape

def overlap_ratio(shape,other):
    if other is None or other.is_empty or shape.area<=0:return 0.0
    if not other.intersects(shape):return 0
    return max(0,min(1,shape.intersection(other).area/shape.area))
