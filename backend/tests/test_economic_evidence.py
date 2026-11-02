import pytest
from pydantic import ValidationError

from app.economic_evidence import EconomicAssumptions


def test_older_drafts_without_a_cost_mode_stay_itemised():
    value = EconomicAssumptions(costs=[{'name': 'Inverter', 'amount': None}])
    assert value.cost_mode == 'itemized' and value.capex_million_per_kwp is None


def test_all_in_price_per_kwp_is_stored_and_bounded():
    value = EconomicAssumptions(costs=[], cost_mode='per_kwp', capex_million_per_kwp=12.5)
    assert value.capex_million_per_kwp == 12.5
    with pytest.raises(ValidationError):
        EconomicAssumptions(costs=[], cost_mode='per_kwp', capex_million_per_kwp=-1)
    with pytest.raises(ValidationError):
        EconomicAssumptions(costs=[], cost_mode='per_watt')
