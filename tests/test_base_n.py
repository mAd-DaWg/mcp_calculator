import pytest

from mcp_calculator.base_n import base_arith, base_convert
from mcp_calculator.errors import CalcError


@pytest.mark.parametrize(
    "value,fb,tb,expected",
    [
        ("FF", 16, 10, "255"),
        ("255", 10, 16, "FF"),
        ("1010", 2, 10, "10"),
        ("10", 10, 2, "00000000000000000000000000001010"),
        ("17", 8, 10, "15"),
    ],
)
def test_convert_pairs(value, fb, tb, expected):
    r = base_convert(value, fb, tb)
    assert r["value"] == expected


def test_all_base_pairs_roundtrip():
    for fb in (2, 8, 10, 16):
        for tb in (2, 8, 10, 16):
            r = base_convert("42", 10, fb)
            back = base_convert(r["value"], fb, 10)
            assert int(back["value"]) == 42 or back["decimal_unsigned"] == 42


def test_arith():
    r = base_arith("add", "A", "5", base=16)
    assert r["result"] == "F"
    r = base_arith("and", "F0", "0F", base=16)
    assert r["result"] == "0"
    r = base_arith("not", "0", base=16)
    assert r["result"] == "FFFFFFFF"


def test_invalid_digit():
    with pytest.raises(CalcError) as ei:
        base_convert("2", 2, 10)
    assert ei.value.code == "invalid_base"


def test_div_zero():
    with pytest.raises(CalcError) as ei:
        base_arith("div", "1", "0", base=10)
    assert ei.value.code == "division_by_zero"
