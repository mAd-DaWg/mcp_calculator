import pytest

from mcp_calculator.errors import CalcError
from mcp_calculator.units import CONVERSIONS, convert_unit, list_unit_conversions


def test_list_all():
    items = list_unit_conversions()
    assert len(items) == len(CONVERSIONS)


@pytest.mark.parametrize("cid", list(CONVERSIONS.keys()))
def test_every_conversion(cid):
    fr, to, factor = CONVERSIONS[cid]
    r = convert_unit(1.0, conversion_id=cid)
    assert r["ok"]
    assert r["from_unit"] == fr
    assert r["to_unit"] == to
    if factor == factor:  # not NaN temperature
        assert r["value"] == pytest.approx(factor)


def test_mile_km():
    r = convert_unit(1, from_unit="mile", to_unit="km")
    assert r["value"] == pytest.approx(1.609344)


def test_temp_c_f():
    r = convert_unit(100, conversion_id="C_to_F")
    assert r["value"] == pytest.approx(212)


def test_unknown():
    with pytest.raises(CalcError) as ei:
        convert_unit(1, from_unit="foo", to_unit="bar")
    assert ei.value.code == "unknown_conversion"
    assert "list_unit_conversions" in ei.value.hint
