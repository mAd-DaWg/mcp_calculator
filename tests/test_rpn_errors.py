import pytest

from mcp_calculator.errors import CalcError
from mcp_calculator.rpn import evaluate


def _fail(expr, code, **kw):
    with pytest.raises(CalcError) as ei:
        evaluate(expr, **kw)
    assert ei.value.code == code
    assert ei.value.hint
    assert len(ei.value.hint) > 5
    return ei.value


def test_empty():
    e = _fail("   ", "empty_expression")
    assert "3 4 +" in (e.example or "")


def test_unknown_token():
    e = _fail("3 foo +", "unknown_token")
    assert "list_operations" in e.hint


def test_underflow():
    e = _fail("sin", "stack_underflow")
    assert e.context.get("arity") == 1


def test_leftover():
    _fail("1 2", "leftover_stack")


def test_div_zero():
    _fail("1 0 /", "division_by_zero")


def test_domain_ln():
    _fail("0 ln", "domain_error")


def test_invalid_fact():
    _fail("2.5 fact", "invalid_factorial")


def test_invalid_comb():
    _fail("2 5 nCr", "invalid_combinatorics")


def test_invalid_angle():
    _fail("1 sin", "invalid_angle_mode", angle_mode="bogus")


def test_invalid_gcd():
    _fail("1.5 2 gcd", "invalid_integer")
