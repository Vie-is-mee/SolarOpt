import json

import pytest

from app.services import vision
from app.services.dimensions import analyze_dimensions, parse_length
from tests.test_studio import client, image_bytes  # noqa: F401  (fixture reuse)


@pytest.mark.parametrize("text,value,unit,expected", [
    ("12000", None, "unknown", 12.0),
    ("12.000", None, None, 12.0),
    ("3,6 m", None, None, 3.6),
    ("450 cm", None, None, 4.5),
    ("9000mm", None, "m", 9.0),          # unit written in the text wins over the model's guess
    ("", 7.2, "m", 7.2),
    ("12", None, None, 12.0),
])
def test_parse_length_units(text, value, unit, expected):
    metres, _ = parse_length(text, value, unit)
    assert metres == pytest.approx(expected)


def test_parse_length_refuses_ambiguous_numbers():
    metres, how = parse_length("85")
    assert metres is None and "Không rõ" in how


def _label(text, x1, y1, x2, y2):
    return {"text": text, "unit": "unknown", "start": {"x": x1, "y": y1}, "end": {"x": x2, "y": y2}}


def test_consistent_labels_give_roof_size_from_overall_dimensions():
    # 1000 x 800 px image; roof bbox 10..90 % wide, 10..85 % tall; 12 m over 800 px, 9 m over 600 px.
    labels = [_label("12000", 10, 95, 90, 95), _label("9000", 95, 10, 95, 85), _label("6000", 10, 5, 50, 5)]
    out = analyze_dimensions(labels, 1000, 800, [10, 10, 80, 75])
    assert out["consistent"] is True
    assert out["suggested_width_m"] == pytest.approx(12.0)
    assert out["suggested_height_m"] == pytest.approx(9.0)
    assert [r["axis"] for r in out["labels"]] == ["horizontal", "vertical", "horizontal"]


def test_misread_label_is_flagged_and_not_used():
    # "1200" was meant to be 12000: it disagrees with the other two labels on scale.
    labels = [_label("1200", 10, 95, 90, 95), _label("9000", 95, 10, 95, 85), _label("6000", 10, 5, 50, 5)]
    out = analyze_dimensions(labels, 1000, 800, [10, 10, 80, 75])
    assert out["consistent"] is False
    assert out["labels"][0]["outlier"] is True
    assert out["suggested_width_m"] is None
    assert out["notes"] and "lệch tỉ lệ" in out["notes"][0]


def test_vision_returns_dimension_check(authenticated_client, monkeypatch):
    client=authenticated_client
    monkeypatch.setenv('AI_PROVIDER', 'groq'); monkeypatch.setenv('GROQ_API_KEY', 'test-dims'); vision._cache.clear()
    payload = {'is_roof_or_plan': True, 'image_type': 'roof_drawing', 'roof_confidence': .8, 'obstacles': [],
               'dimension_labels': [_label('12000', 10, 95, 90, 95), _label('9000', 95, 10, 95, 85)]}

    class Response:
        def raise_for_status(self): pass
        def json(self): return {'choices': [{'message': {'content': json.dumps(payload)}}]}
    monkeypatch.setattr(vision.requests, 'post', lambda *a, **kw: Response())
    body = client.post('/api/vision/analyze', files={'file': ('plan.png', image_bytes(), 'image/png')}, data={'input_kind': 'plan'}).json()
    dims = body['dimensions']
    assert [r['value_m'] for r in dims['labels']] == [12.0, 9.0]
    assert any(e['stage'] == 'dimensions' for e in body['events'])
