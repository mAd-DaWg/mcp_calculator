from mcp_calculator.constants import CONSTANTS, list_constants, resolve_constant
from mcp_calculator.errors import CalcError
from mcp_calculator.rpn import evaluate

import pytest


def test_every_constant_resolves():
    for name, meta in CONSTANTS.items():
        assert resolve_constant(name) == meta["value"]
        if meta["value"] == float("inf"):
            # Constant loads as Infinity but must not serialize as a success JSON number.
            with pytest.raises(CalcError) as ei:
                evaluate(name)
            assert ei.value.code == "overflow"
            continue
        r = evaluate(name)
        assert r["ok"]
        assert r["result"] == meta["value"]


def test_list_constants_nonempty():
    items = list_constants()
    assert len(items) >= 40
    names = {i["name"] for i in items}
    assert "c" in names and "qe" in names and "e" in names
    inf_item = next(i for i in items if i["name"] == "inf")
    assert inf_item["value"] == "Infinity"
    import json

    json.dumps({"constants": items}, allow_nan=False)


def test_speed_of_light():
    assert resolve_constant("c") == 299792458.0
