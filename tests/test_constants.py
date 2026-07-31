from mcp_calculator.constants import CONSTANTS, list_constants, resolve_constant
from mcp_calculator.rpn import evaluate


def test_every_constant_resolves():
    for name, meta in CONSTANTS.items():
        assert resolve_constant(name) == meta["value"]
        r = evaluate(name)
        assert r["ok"]
        val = r["result"]
        expected = meta["value"]
        if expected == float("inf"):
            assert val == float("inf")
        else:
            assert val == expected


def test_list_constants_nonempty():
    items = list_constants()
    assert len(items) >= 40
    names = {i["name"] for i in items}
    assert "c" in names and "qe" in names and "e" in names


def test_speed_of_light():
    assert resolve_constant("c") == 299792458.0
