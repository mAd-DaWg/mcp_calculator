from mcp_calculator.constants import CONSTANTS
from mcp_calculator.ops import OPS, list_operations
from mcp_calculator.units import CONVERSIONS, list_unit_conversions


def test_ops_list_matches_registry():
    listed = {o["name"] for o in list_operations()}
    assert listed == set(OPS.keys())


def test_constants_nonempty():
    assert "pi" in CONSTANTS
    assert "c" in CONSTANTS


def test_units_list_matches():
    ids = {c["id"] for c in list_unit_conversions()}
    assert ids == set(CONVERSIONS.keys())
