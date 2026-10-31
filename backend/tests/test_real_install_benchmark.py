import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('bench', ROOT / 'backend/scripts/benchmark_real_installs.py')
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)


def test_snapshot_is_attributed_and_cases_have_arrays():
    snap = json.loads(bench.SNAPSHOT.read_text(encoding='utf-8'))
    assert 'OpenStreetMap' in snap['license'] and snap['retrieved']
    assert len(snap['cases']) >= 3 and all(c['arrays'] for c in snap['cases'])


def test_small_case_metrics_are_bounded_and_same_area_matches_real_area():
    snap = json.loads(bench.SNAPSHOT.read_text(encoding='utf-8'))
    case = min(snap['cases'], key=lambda c: len(c['building_lonlat']))
    r = bench.run_case(case)
    same = r['runs']['same_area']
    assert 0 <= same['iou'] <= 1 and 0 <= r['baseline_roof_fill_iou'] <= 1
    assert abs(same['panel_m2'] - r['real_array_m2']) <= bench.PANEL.width_m * bench.PANEL.height_m
    assert r['runs']['max']['panels'] >= same['panels']
