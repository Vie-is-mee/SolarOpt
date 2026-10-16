"""Analytical, surveyed-input geometry checks; no image/field accuracy claims."""
import math
from datetime import date
import pytest
from shapely.geometry import box,Polygon,Point
from app.schemas import ProjectConfig,RectObstacle,SunPosition,SceneRequest
from app.services.geometry import Surface,shadow_polygon,build_context,obstacle_elevations
from app.services.scene import simulate_scene,regions


def sun(azimuth=90,altitude=45):
    return SunPosition(altitude_deg=altitude,azimuth_deg=azimuth,zenith_deg=90-altitude)


@pytest.mark.parametrize('azimuth,rotation,bounds',[
    (90,0,(3,5,6,7)),(0,0,(5,3,6,7)),(270,0,(5,5,8,7)),(180,0,(5,5,6,9)),
    (90,90,(5,3,6,7)),(0,90,(5,5,8,7)),(270,90,(5,5,6,9)),(180,90,(3,5,6,7)),
])
def test_cardinal_direction_and_rotated_drawing(azimuth,rotation,bounds):
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=12,north_rotation_deg=rotation)
    obstacle=RectObstacle(id='block',x=5,y=5,width_m=1,depth_m=2,height_m=2)
    actual=shadow_polygon(obstacle,sun(azimuth),cfg)
    assert actual.bounds==pytest.approx(bounds)
    assert actual.area==pytest.approx(box(*bounds).area)


@pytest.mark.parametrize('altitude',[15,30,45,60,85])
def test_flat_roof_shadow_length_matches_height_over_tangent(altitude):
    cfg=ProjectConfig(roof_width_m=20,roof_height_m=12)
    obstacle=RectObstacle(id='block',x=10,y=5,width_m=1,depth_m=2,height_m=2)
    actual=shadow_polygon(obstacle,sun(90,altitude),cfg)
    length=2/math.tan(math.radians(altitude))
    assert actual.bounds==pytest.approx((10-length,5,11,7))
    assert actual.area==pytest.approx((1+length)*2)


def test_partly_buried_prism_does_not_shade_roof_above_its_top():
    # Roof z=6+0.5x; object top z=8, so only x<=4 can occlude it.
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=8,roof_tilt_deg=math.degrees(math.atan(.5)),roof_azimuth_deg=270,roof_elevation_m=6)
    obstacle=RectObstacle(id='wall',scope='neighbor',x=2,y=2,width_m=4,depth_m=1,height_m=8)
    actual=shadow_polygon(obstacle,sun(270),cfg)
    assert actual.bounds==pytest.approx((2,2,4,3))
    assert actual.area==pytest.approx(2)


def test_receiver_facing_away_is_not_reported_as_fully_occluded_by_one_object():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=8,roof_tilt_deg=60,roof_azimuth_deg=270)
    obstacle=RectObstacle(id='tiny',x=2,y=2,width_m=1,depth_m=1,height_m=1)
    # Rising toward East more steeply than the sun: no direct light reaches it.
    assert shadow_polygon(obstacle,sun(90,20),cfg) is None


def test_unassigned_roof_obstacle_base_is_independent_of_receiver():
    cfg=ProjectConfig(roof_width_m=10,roof_height_m=8,roof_elevation_m=6)
    obstacle=RectObstacle(id='outside',x=11,y=2,width_m=1,depth_m=1,height_m=1)
    high=Surface('high','High receiver',box(0,0,10,8),8,0,180)
    assert shadow_polygon(obstacle,sun(),cfg,target=high) is None


def test_neighbor_explicit_ground_base_changes_effective_height():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=8,roof_elevation_m=6)
    low=RectObstacle(id='neighbor',scope='neighbor',x=14,y=2,width_m=2,depth_m=2,height_m=5)
    assert shadow_polygon(low,sun(),cfg) is None
    high=low.model_copy(update={'base_elevation_m':4})
    assert shadow_polygon(high,sun(),cfg).bounds==pytest.approx((11,2,16,4))


def test_explicit_raised_base_projects_bottom_instead_of_filling_gap_to_footprint():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=8,roof_elevation_m=6)
    obstacle=RectObstacle(id='raised',x=8,y=3,width_m=2,depth_m=2,height_m=2,base_elevation_m=10)
    actual=shadow_polygon(obstacle,sun(),cfg)
    assert actual.bounds==pytest.approx((2,3,6,5))
    assert actual.area==pytest.approx(8)


def test_night_cells_agree_with_night_shadow_summary():
    result=simulate_scene(SceneRequest(config=ProjectConfig(),date=date(2026,10,10),hour_local=0))
    assert result['sun']['altitude_deg']<0
    assert result['shaded_pct']==100
    assert result['cells'] and all(cell['shade_fraction']==1 for cell in result['cells'])


def test_diagonal_sweep_area_and_bounds_match_analytical_rectangle():
    obstacle=RectObstacle(id='block',x=5,y=5,width_m=1,depth_m=2,height_m=2)
    actual=shadow_polygon(obstacle,sun(45),ProjectConfig())
    delta=math.sqrt(2)
    assert actual.area==pytest.approx(2+3*delta)
    assert actual.bounds==pytest.approx((5-delta,5-delta,6,7))


def test_shadow_union_does_not_double_count_overlapping_sources(monkeypatch):
    from app.services import scene
    monkeypatch.setattr(scene,'sun_position',lambda req:sun())
    obstacles=[RectObstacle(id=name,x=5,y=3,width_m=1,depth_m=2,height_m=2) for name in ['a','b']]
    result=simulate_scene(SceneRequest(config=ProjectConfig(),obstacles=obstacles,date=date(2026,10,10),hour_local=9,heatmap=False))
    assert result['shaded_area_m2']==pytest.approx(6)
    assert sum(s['area_m2'] for s in result['shadows'])==pytest.approx(12)


def test_obstacle_crossing_roof_step_exposes_assumption_until_explicit_base():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=8,roof_elevation_m=6,roof_faces=[dict(id='high',polygon=[dict(x=6,y=0),dict(x=12,y=0),dict(x=12,y=8),dict(x=6,y=8)],elevation_m=8)])
    obstacle=RectObstacle(id='step',x=5,y=2,width_m=2,depth_m=1,height_m=2)
    auto=obstacle_elevations(cfg,[obstacle])[0]
    assert auto['base_min_m']==8 and auto['top_max_m']==10
    assert any('nhiều phần mái' in warning for warning in auto['warnings'])
    explicit=obstacle_elevations(cfg,[obstacle.model_copy(update={'base_elevation_m':7})])[0]
    assert explicit['base_source']=='explicit' and explicit['base_min_m']==7
    assert not explicit['warnings']


def test_shadow_serialization_keeps_holes_and_disconnected_parts():
    shape=box(0,0,10,10).difference(box(2,2,8,8)).union(box(12,0,13,1))
    packed=regions(shape)
    assert len(packed)==2
    assert sum(len(r['openings']) for r in packed)==1
    restored=sum(Polygon(r['boundary'],r['openings']).area for r in packed)
    assert restored==pytest.approx(shape.area)


def test_invalid_sloping_roof_height_is_visible_even_without_obstacles():
    cfg=ProjectConfig(roof_elevation_m=1,roof_tilt_deg=45,roof_azimuth_deg=90)
    result=simulate_scene(SceneRequest(config=cfg,date=date(2026,10,10),hour_local=9,heatmap=False))
    assert any('thấp hơn mặt đất' in note for note in result['notes'])


@pytest.mark.parametrize('gx,gy,azimuth,altitude,base,top',[(.3,.1,50,35,8,10),(.3,.1,50,55,8,10),(-.2,.15,130,35,6,9),(.1,-.2,320,25,7,11)])
def test_sloped_receiver_with_raised_block_matches_independent_ray_box_intersection(gx,gy,azimuth,altitude,base,top):
    # Independent slab ray/AABB intersection, not a copy of polygon projection.
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=8,roof_elevation_m=6,
        roof_tilt_deg=math.degrees(math.atan(math.hypot(gx,gy))),roof_azimuth_deg=math.degrees(math.atan2(-gx,-gy))%360)
    obstacle=RectObstacle(id='raised',x=3,y=2,width_m=4,depth_m=4,height_m=top-base,base_elevation_m=base)
    solar=sun(azimuth,altitude)
    actual=shadow_polygon(obstacle,solar,cfg)
    vector=(math.sin(math.radians(azimuth)),math.cos(math.radians(azimuth)),math.tan(math.radians(altitude)))
    mismatches=[]
    for i in range(36):
        for j in range(24):
            x,y=(i+.37)/3,(j+.29)/3
            origin=(x,y,6+gx*x+gy*y)
            intervals=[sorted(((lo-pos)/direction,(hi-pos)/direction)) for pos,direction,(lo,hi) in zip(origin,vector,[(3,7),(2,6),(base,top)])]
            enter=max(0,*(pair[0] for pair in intervals));leave=min(pair[1] for pair in intervals)
            if abs(leave-enter)<.01 or actual.boundary.distance(Point(x,y))<.01:continue
            if actual.covers(Point(x,y))!=(leave>enter):mismatches.append((x,y))
    assert not mismatches,mismatches[:10]
