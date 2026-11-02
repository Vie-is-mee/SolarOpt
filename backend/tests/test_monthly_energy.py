import pytest
from app.schemas import DesignRequest
from app.services.optimizer import generate_design


@pytest.mark.parametrize('extra', [{}, {'mounting': 'tilted_rack'}])
def test_monthly_energy_spreads_the_annual_total(extra):
    req = DesignRequest.model_validate({'config': {'project_name': 'p', 'roof_width_m': 12, 'roof_height_m': 9,
                                                   'geometry_confirmed': True, **extra},
                                        'panel': {}, 'obstacles': [], 'objective': 'max_energy'})
    design = generate_design(req)
    assert len(design.monthly_energy_kwh) == 12
    assert sum(design.monthly_energy_kwh) == pytest.approx(design.metrics.annual_energy_kwh, abs=1)
    assert min(design.monthly_energy_kwh) > 0
