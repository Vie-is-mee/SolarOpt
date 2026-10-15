import json
from pathlib import Path
import subprocess
import sys
import pytest
from pydantic import ValidationError
from shapely.geometry import Polygon,box
from shapely.affinity import translate

from app.services.validation import ValidationCase,compare_regions,evaluate_case,Region,ShadowReference
from app.services.validation_report import render_report

ROOT=Path(__file__).resolve().parents[2]


def synthetic(index=0):
    return ValidationCase.model_validate(json.loads((ROOT/'sample_data/validation/synthetic_cases.json').read_text(encoding='utf-8'))['cases'][index])


def test_three_analytic_cases_match_independent_shadow_areas():
    for i,area in enumerate((3,0,30)):
        result=evaluate_case(synthetic(i))
        assert result['status']=='SYNTHETIC_PASS'
        assert result['shadows'][0]['predicted_area_m2']==pytest.approx(area)
        assert result['shadows'][0]['reference_area_m2']==area
        assert result['kind']=='synthetic'
    assert evaluate_case(synthetic(1))['roof']['predicted_area_m2']==86


def test_shifted_outline_is_not_auto_aligned_or_rescaled():
    # Same area but wrong position: intersection 1.5*2, union 5 square metres.
    result=compare_regions(translate(box(0,0,2,2),xoff=.5),box(0,0,2,2))
    assert result['iou']==pytest.approx(.6)
    assert result['boundary_error_m']==pytest.approx(.5)
    assert result['area_difference_m2']==0


def test_empty_shadow_does_not_make_missing_shadow_look_correct():
    assert compare_regions(Polygon(),Polygon())['iou']==1
    wrong=compare_regions(Polygon(),box(0,0,2,2))
    assert wrong['iou']==0 and wrong['boundary_error_m'] is None


def test_holes_are_included_in_area_and_boundary_error():
    with_hole=Region(boundary=[{'x':0,'y':0},{'x':4,'y':0},{'x':4,'y':4},{'x':0,'y':4}],
        openings=[[{'x':1,'y':1},{'x':3,'y':1},{'x':3,'y':3},{'x':1,'y':3}]]).shape()
    result=compare_regions(box(0,0,4,4),with_hole)
    assert result['iou']==pytest.approx(.75)
    assert result['boundary_error_m']>0


def test_bad_reference_exceeds_declared_tolerances():
    case=synthetic()
    case.reference_roof.boundary[1].x=10
    result=evaluate_case(case)
    assert result['status']=='OUTSIDE_TOLERANCES'


def test_field_template_stays_incomplete_instead_of_passing():
    raw=json.loads((ROOT/'sample_data/validation/field_template.json').read_text(encoding='utf-8'))
    result=evaluate_case(ValidationCase.model_validate(raw['cases'][0]))
    assert result['status']=='INCOMPLETE'
    assert result['roof'] is None and result['energy'] is None
    assert len(result['missing'])>=5


def test_no_agreed_tolerances_never_produces_a_pass():
    case=synthetic();case.tolerances.roof_iou_min=None
    assert evaluate_case(case)['status']=='INCOMPLETE'


def test_energy_from_different_inputs_is_not_compared():
    case=synthetic();case.energy_reference.same_weather_inputs_confirmed=False
    result=evaluate_case(case)
    assert result['energy'] is None and result['status']=='INCOMPLETE'


def test_reference_is_not_clipped_to_wrong_prediction():
    case=synthetic()
    # Prediction loses x=3..4, but independently observed shadow must retain it.
    case.project.config=case.project.config.model_validate({**case.project.config.model_dump(),
        'roof_polygon':[{'x':4,'y':0},{'x':12,'y':0},{'x':12,'y':9},{'x':4,'y':9}]})
    result=evaluate_case(case)
    assert result['shadows'][0]['reference_area_m2']==3
    assert result['shadows'][0]['predicted_area_m2']==pytest.approx(2)
    assert result['shadows'][0]['iou']==pytest.approx(2/3)


@pytest.mark.parametrize('change',[
    {'date':'2026-10-15'},
    {'analytical_sun':{'altitude_deg':45,'azimuth_deg':90,'zenith_deg':44}},
    {'analytical_sun':{'altitude_deg':float('nan'),'azimuth_deg':90,'zenith_deg':45}},
])
def test_invalid_time_or_sun_rejected(change):
    with pytest.raises(ValidationError):ShadowReference(source='test source',**change)


def test_real_roof_cannot_use_a_synthetic_sun():
    raw=synthetic().model_dump();raw['kind']='field'
    with pytest.raises(ValidationError):ValidationCase.model_validate(raw)


def test_report_escapes_input_and_has_no_external_dependencies():
    result=evaluate_case(synthetic());result['label']='<script>alert(1)</script>'
    report=render_report([result],'test time')
    assert '<script>' not in report and '&lt;script&gt;' in report
    assert 'Ca nhân tạo kiểm tra thuật toán' in report
    assert '<svg' in report and 'src="http' not in report


def test_validation_does_not_mutate_input():
    case=synthetic();before=case.model_dump()
    evaluate_case(case)
    assert case.model_dump()==before


def test_cli_writes_reports_and_nonzero_exit_for_missing_references(tmp_path):
    script=ROOT/'backend/scripts/validate_roofs.py'
    for name,expected in [('synthetic_cases',0),('field_template',2)]:
        output=tmp_path/name
        process=subprocess.run([sys.executable,str(script),str(ROOT/f'sample_data/validation/{name}.json'),
            '--out',str(output)],capture_output=True)
        assert process.returncode==expected,process.stderr.decode(errors='replace')
        assert (output/'report.html').exists()
        data=json.loads((output/'results.json').read_text(encoding='utf-8'))
        assert data['format']=='solaropt-validation-result-v1'
