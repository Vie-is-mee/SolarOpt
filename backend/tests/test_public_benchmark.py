"""Protocol checks independent of the optional public imagery download."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('public_benchmark', Path(__file__).parents[1]/'scripts'/'benchmark_public_roofs.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_geographic_image_transform_preserves_direction_and_pixel_offset():
    points = benchmark.pixel_ring([[40.1,-14.2],[40.10002,-14.20003]], [0.00001,0.00001,0], [2,3,0,40.1,-14.2,0])
    assert points == pytest.approx(np.array([[2,3],[4,6]]))


def test_iou_counts_missing_prediction_as_zero_and_does_not_align():
    ref = np.zeros((10,10),bool)
    ref[1:4,1:4] = True
    pred = np.zeros_like(ref)
    assert benchmark.iou(ref,pred) == 0
    pred[6:9,6:9] = True
    assert benchmark.iou(ref,pred) == 0
    assert benchmark.iou(ref,ref) == 1


def test_iou_is_json_serializable_and_measures_overlap():
    import json
    result = benchmark.iou(np.array([1,1,0],bool),np.array([0,1,1],bool))
    assert result == pytest.approx(1/3)
    assert json.loads(json.dumps({'iou':result}))['iou'] == result


def test_cached_data_with_wrong_checksum_is_rejected(tmp_path):
    (tmp_path/'LICENSE').write_text('modified source')
    with pytest.raises(ValueError,match='Checksum mismatch'):
        benchmark.fetch(tmp_path)
