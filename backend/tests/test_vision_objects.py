import base64,io,json
import pytest
from PIL import Image
from app.schemas import RectObstacle
from app.services import vision
from app.services.object_kinds import clean_obstacles,infer_kind,merge_boxes,scope_of


def box(**kw):
    return dict(id='a',label='Bồn nước',x_pct=10,y_pct=10,width_pct=10,depth_pct=10,confidence=.8,**kw)


@pytest.mark.parametrize('label,kind',[('Bồn nước inox','tank'),('bon nuoc','tank'),('Bồn nằm ngang','tank_flat'),('Tum thang','stair'),('Dàn nóng máy lạnh','ac'),
    ('Giếng trời','skylight'),('Cây bàng','tree_round'),('Cây dừa','tree_palm'),('Nhà bên cạnh','house'),('Vết bẩn lạ','other')])
def test_label_decides_the_kind_when_the_model_gives_none(label,kind):
    assert infer_kind(label)==kind


def test_a_tree_stands_around_the_roof_and_an_unknown_keeps_what_the_model_said():
    assert scope_of('tree_round','roof')=='around' and scope_of('tank','around')=='roof'
    assert scope_of('other','around')=='around' and scope_of('other',None)=='roof'


def test_one_broken_box_does_not_cost_the_good_ones():
    kept,dropped,_=clean_obstacles([box(),{'label':'không có tọa độ'},'rác',dict(box(),id='b',x_pct=50,width_pct=0),dict(box(),id='c',x_pct=95,width_pct=50)])
    assert [k['id'] for k in kept]==['a'] and dropped==4


def test_a_box_past_the_edge_is_trimmed_and_sent_for_placement():
    kept,_,trimmed=clean_obstacles([dict(box(),x_pct=95)])
    assert kept[0]['width_pct']==5 and kept[0]['requires_placement'] and trimmed==['Bồn nước']


def test_height_is_never_invented():
    kept,_,_=clean_obstacles([box()])
    assert kept[0]['height_m'] is None


def test_the_same_object_reported_twice_stays_one_and_keeps_the_better_box():
    low=dict(box(),id='low',confidence=.4,x_pct=11,y_pct=11,kind='tank',scope='roof')
    high=dict(box(),id='high',confidence=.9,kind='tank',scope='roof')
    assert [b['id'] for b in merge_boxes([low,high])]==['high']


def test_two_units_side_by_side_stay_two():
    kept,_,_=clean_obstacles([dict(box(),id='a',label='Dàn nóng',x_pct=10),dict(box(),id='b',label='Dàn nóng',x_pct=22)])
    assert len(kept)==2


def test_reply_inside_a_code_fence_still_parses():
    assert vision.parse_reply('Kết quả:\n```json\n{"obstacles":[]}\n```')=={'obstacles':[]}
    with pytest.raises(ValueError):vision.parse_reply('xin lỗi')


def test_new_ai_fields_default_for_older_projects():
    o=RectObstacle(id='x',x=0,y=0)
    assert o.ai_ref is None and not o.ai_edited and not o.height_assumed and not o.position_assumed


def roof_image(w=2000,h=2000):
    out=io.BytesIO();Image.new('RGB',(w,h),'#88aa88').save(out,'PNG');return out.getvalue()


class Reply:
    status_code=200
    def __init__(self,payload):self.payload=payload
    def raise_for_status(self):pass
    def json(self):return {'choices':[{'message':{'content':json.dumps(self.payload)}}]}


def small_roof(monkeypatch,second):
    """First pass sees a roof filling 16% of the frame and one tank; the second call is the crop."""
    calls=[]
    first={'is_roof_or_plan':True,'roof_polygon_image_pct':[{'x':30,'y':30},{'x':70,'y':30},{'x':70,'y':70},{'x':30,'y':70}],
           'obstacles':[dict(box(),x_pct=40,y_pct=40,width_pct=4,depth_pct=4)]}
    def post(url,headers=None,json=None,timeout=None):
        calls.append(json);return Reply(first) if len(calls)==1 else second(len(calls))
    monkeypatch.setenv('AI_PROVIDER','groq');monkeypatch.setenv('GROQ_API_KEY','t');monkeypatch.setenv('AI_MODEL','m1');vision._cache.clear()
    monkeypatch.setattr(vision.requests,'post',post)
    monkeypatch.setattr('app.services.roof_extract.extract_roof',lambda req:(_ for _ in ()).throw(ValueError('skip')))
    return calls


def test_a_small_roof_is_read_again_from_a_crop_and_adds_what_was_missed(monkeypatch):
    # The crop covers x,y 26..74: its (50,50) is the image centre, far from the first tank.
    found={'obstacles':[dict(box(),id='ac',label='Dàn nóng',x_pct=50,y_pct=50,width_pct=5,depth_pct=5)]}
    calls=small_roof(monkeypatch,lambda n:Reply(found))
    result=vision.analyze_images([(roof_image(),'image/png')],'drone',12,9)
    assert len(calls)==2
    assert sorted(o.kind for o in result.obstacles)==['ac','tank']
    crop=base64.b64decode(calls[1]['messages'][0]['content'][1]['image_url']['url'].split(',')[1])
    assert max(Image.open(io.BytesIO(crop)).size)==1600


def test_a_failed_second_look_keeps_the_first_reading(monkeypatch):
    calls=small_roof(monkeypatch,lambda n:Reply({'obstacles':'sai'}))
    result=vision.analyze_images([(roof_image(),'image/png')],'drone',12,9)
    assert len(calls)==2 and [o.kind for o in result.obstacles]==['tank']


def test_busy_free_models_get_a_second_round_before_giving_up(monkeypatch):
    class Busy(Reply):
        status_code=429
    seen=[]
    def post(url,headers=None,json=None,timeout=None):
        seen.append(json['model'])
        return Busy({}) if len(seen)<3 else Reply({'obstacles':[]})
    monkeypatch.setattr(vision.requests,'post',post);monkeypatch.setattr(vision,'sleep',lambda s:None);monkeypatch.setattr(vision,'RETRY_WAIT_S',0)
    monkeypatch.setenv('AI_BASE_URL','http://x/v1')
    events=[]
    reply,used=vision.ask_model('openai','a,b','k','hỏi',[b'x'],events)
    assert seen==['a','b','a'] and used=='a' and reply=={'obstacles':[]} and len(events)==2


def test_a_slow_model_hands_over_to_the_next(monkeypatch):
    def post(url,headers=None,json=None,timeout=None):
        if json['model']=='slow':raise vision.requests.Timeout()
        return Reply({'obstacles':[]})
    monkeypatch.setattr(vision.requests,'post',post);monkeypatch.setenv('AI_BASE_URL','http://x/v1')
    assert vision.ask_model('openai','slow,ok','k','hỏi',[b'x'],[])[1]=='ok'
