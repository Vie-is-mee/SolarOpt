import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon
from app.services.roof_extract import TraceRequest, data_url, extract_roof
from app.schemas import ProjectConfig
from app.services.geometry import roof_polygon


def rectangle(x0,y0,x1,y1):
    return [{'x':x0,'y':y0},{'x':x1,'y':y0},{'x':x1,'y':y1},{'x':x0,'y':y1}]


def image_url():
    image=np.full((400,600,3),30,np.uint8)
    cv2.rectangle(image,(60,40),(540,360),(100,180,120),-1)
    cv2.rectangle(image,(240,140),(360,260),(30,30,30),-1)
    return data_url(image)


@pytest.mark.parametrize('method',['manual','grabcut'])
def test_trace_preserves_courtyard_in_common_coordinate_frame(method):
    result=extract_roof(TraceRequest(image_data_url=image_url(),method=method,
        rect=[8,8,84,84],polygon=rectangle(10,10,90,90) if method=='manual' else [],
        openings=[rectangle(40,35,60,65)] if method=='manual' else [],
        foreground=[{'x':20,'y':20}],background=[{'x':50,'y':50}]))
    assert len(result['roof_openings_pct'])==1
    boundary=Polygon([(p['x'],p['y']) for p in result['roof_polygon_pct']])
    hole=Polygon([(p['x'],p['y']) for p in result['roof_openings_pct'][0]])
    assert boundary.contains(hole)
    assert hole.area==pytest.approx(25*37.5,rel=.06)
    cfg=ProjectConfig(roof_width_m=12,roof_height_m=8,
        roof_polygon=[{'x':p['x']*.12,'y':p['y']*.08} for p in result['roof_polygon_pct']],
        roof_openings=[[{'x':p['x']*.12,'y':p['y']*.08} for p in ring] for ring in result['roof_openings_pct']])
    assert roof_polygon(cfg).area==pytest.approx(87,abs=.6)


@pytest.mark.parametrize('holes',[
    [rectangle(80,80,95,95)],
    [rectangle(30,30,50,50),rectangle(40,40,60,60)],
    [[{'x':30,'y':30},{'x':50,'y':50},{'x':30,'y':50},{'x':50,'y':30}]],
    [[{'x':30,'y':30},{'x':50,'y':50}]],
])
def test_invalid_manual_openings_are_rejected(holes):
    with pytest.raises(ValueError):
        extract_roof(TraceRequest(image_data_url=image_url(),method='manual',polygon=rectangle(10,10,90,90),openings=holes))


def test_multiple_significant_regions_are_reported_not_silently_merged():
    image=np.full((400,600,3),20,np.uint8)
    cv2.rectangle(image,(60,60),(260,330),(100,180,120),-1)
    cv2.rectangle(image,(360,60),(540,330),(100,180,120),-1)
    result=extract_roof(TraceRequest(image_data_url=data_url(image),rect=[5,5,90,90],foreground=[{'x':20,'y':40},{'x':70,'y':40}]))
    assert result['discarded_regions']==1
    assert any('vùng rời' in note for note in result['notes'])
