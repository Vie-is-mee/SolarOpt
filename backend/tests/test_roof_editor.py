import base64
import io

import numpy as np
import pytest
from PIL import Image, ImageDraw
from pydantic import ValidationError
from shapely.geometry import Polygon, box

from app.schemas import ProjectConfig, PanelSpec, RectObstacle, SunPosition, DesignRequest, VerifyRequest
from app.services.geometry import build_context, obstacle_polygon, panel_shape
from app.services.optimizer import generate_design
from app.services.verifier import verify_design
from app.services.roof_extract import TraceRequest, extract_roof


def fixture_image():
    # Synthetic concave roof, no photographic accuracy claim.
    image=Image.new('RGB',(600,400),'#303c4a')
    points=[(90,60),(510,60),(510,190),(320,190),(320,340),(90,340)]
    ImageDraw.Draw(image).polygon(points,fill='#91b77d')
    stream=io.BytesIO();image.save(stream,'PNG')
    return 'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode(),points


@pytest.mark.parametrize('method',['manual','grabcut','plan'])
def test_trace_preserves_concavity_and_one_pixel_scale(method):
    url,points=fixture_image()
    result=extract_roof(TraceRequest(image_data_url=url,method=method,
        rect=[10,10,80,80],polygon=[{'x':x/6,'y':y/4} for x,y in points] if method=='manual' else [],
        foreground=[{'x':30,'y':30}],background=[{'x':75,'y':75}]))
    actual=Polygon([(p['x']*6,p['y']*4) for p in result['polygon_image_pct']])
    expected=Polygon(points)
    assert actual.intersection(expected).area/actual.union(expected).area>.97
    assert len(result['roof_polygon_pct'])>=6
    assert result['roof_aspect_ratio']==pytest.approx(420/280,rel=.02)
    assert max(p['x'] for p in result['roof_polygon_pct'])==100
    assert min(p['y'] for p in result['roof_polygon_pct'])==0


def test_perspective_rectification_uses_known_edge_ratio():
    url,_=fixture_image()
    result=extract_roof(TraceRequest(image_data_url=url,method='rectify',
        quad=[{'x':15,'y':15},{'x':85,'y':15},{'x':70,'y':85},{'x':20,'y':85}],quad_aspect_ratio=2))
    assert result['rectified']
    assert result['width_px']/result['height_px']==pytest.approx(2,rel=.01)


def test_invalid_manual_outline_is_not_replaced_by_rectangle():
    url,_=fixture_image()
    with pytest.raises(ValueError):
        extract_roof(TraceRequest(image_data_url=url,method='manual',polygon=[
            {'x':10,'y':10},{'x':90,'y':90},{'x':10,'y':90},{'x':90,'y':10}]))


def test_shapes_and_rotation_change_actual_collision_geometry():
    rect=RectObstacle(id='a',x=1,y=1,width_m=4,depth_m=2)
    ellipse=rect.model_copy(update={'shape':'ellipse'})
    rotated=rect.model_copy(update={'rotation_deg':90})
    assert obstacle_polygon(ellipse).area==pytest.approx(2*np.pi,rel=.01)
    assert obstacle_polygon(rotated).bounds==pytest.approx((2,0,4,4))
    assert not obstacle_polygon(ellipse).covers(box(1,1,1.1,1.1))


def face(**kw):
    return dict(id='upper',label='Upper roof',polygon=[{'x':6,'y':0},{'x':12,'y':0},{'x':12,'y':9},{'x':6,'y':9}],elevation_m=8,**kw)


def test_elevated_roof_casts_shadow_and_height_changes_extent():
    sun=SunPosition(altitude_deg=45,azimuth_deg=90,zenith_deg=45)
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,roof_elevation_m=6,roof_faces=[face()])
    ctx=build_context(cfg,[],sun)
    assert ctx.shadow_union.area==pytest.approx(18)
    assert ctx.shadow_union.bounds==pytest.approx((4,0,6,9))
    taller=cfg.model_copy(deep=True);taller.roof_faces[0].elevation_m=9
    assert build_context(taller,[],sun).shadow_union.area==pytest.approx(27)


def test_base_roof_casts_partial_shadow_into_lower_internal_face():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,roof_elevation_m=8,roof_faces=[dict(
        id='pit',polygon=[{'x':4,'y':2},{'x':8,'y':2},{'x':8,'y':6},{'x':4,'y':6}],elevation_m=6)])
    sun=SunPosition(altitude_deg=45,azimuth_deg=90,zenith_deg=45)
    assert build_context(cfg,[],sun).shadow_union.area==pytest.approx(8)


def test_openings_and_face_boundaries_constrain_optimizer_and_verifier():
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=9,setback_m=0,budget_vnd=500_000_000,
        roof_faces=[face()],roof_openings=[[{'x':1,'y':1},{'x':3,'y':1},{'x':3,'y':4},{'x':1,'y':4}]])
    result=generate_design(DesignRequest(config=cfg,panel=PanelSpec(),objective='max_energy'))
    ctx=build_context(cfg,[],None)
    assert result.panels
    for panel in result.panels:
        shape=panel_shape(panel.x,panel.y,panel.width_m,panel.height_m,panel.rotation_deg)
        assert any(s.polygon.covers(shape) for s in ctx.surfaces)
        assert not shape.intersection(box(1,1,3,4)).area
    assert verify_design(VerifyRequest(config=cfg,panel=PanelSpec(),design=result)).valid
    # Deliberately forge a panel spanning a roof height step: hard failure.
    result.panels[0].x=5.5;result.panels[0].y=5
    checks=verify_design(VerifyRequest(config=cfg,panel=PanelSpec(),design=result)).checks
    assert next(c for c in checks if c.id=='roof_boundary').status=='FAIL'


def test_overlapping_or_external_faces_rejected():
    with pytest.raises(ValidationError):
        ProjectConfig(roof_width_m=12,roof_height_m=9,roof_faces=[face(),{**face(),'id':'other'}])
    with pytest.raises(ValidationError):
        ProjectConfig(roof_width_m=5,roof_height_m=9,roof_faces=[face()])
