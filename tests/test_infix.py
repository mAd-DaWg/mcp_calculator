"""Infix → RPN conversion and evaluation."""

from __future__ import annotations

import math

import pytest

from mcp_calculator.errors import CalcError
from mcp_calculator.infix import eval_at, evaluate_infix, to_rpn


def test_basic_arithmetic():
    r = evaluate_infix("90+(40-30)")
    assert r["ok"] is True
    assert r["result"] == 100.0
    assert r["expression"] == "90+(40-30)"
    assert r["rpn"] == "90 40 30 - +"


def test_precedence():
    assert evaluate_infix("2+3*4")["result"] == 14.0
    assert to_rpn("2+3*4") == ["2", "3", "4", "*", "+"]


def test_unary_minus():
    assert evaluate_infix("-5")["result"] == -5.0
    assert evaluate_infix("2*-3")["result"] == -6.0
    assert evaluate_infix("-2^2")["result"] == -4.0


def test_functions():
    assert evaluate_infix("sin(0)")["result"] == pytest.approx(0.0)
    assert evaluate_infix("sqrt(9)")["result"] == 3.0
    assert evaluate_infix("abs(-7)")["result"] == 7.0


def test_sin_degrees():
    r = evaluate_infix("sin(30)", angle_mode="deg")
    assert r["result"] == pytest.approx(0.5)


def test_factorial():
    assert evaluate_infix("5!")["result"] == 120.0


def test_constants():
    assert evaluate_infix("pi/6")["result"] == pytest.approx(math.pi / 6)


def test_implicit_multiply():
    assert evaluate_infix("2pi")["result"] == pytest.approx(2 * math.pi)
    assert evaluate_infix("2(3+4)")["result"] == 14.0
    assert evaluate_infix("(1+2)(3)")["result"] == 9.0


def test_variable_x():
    assert eval_at("2x", 3) == 6.0
    assert eval_at("x^2-2", 3) == 7.0
    assert evaluate_infix("x^2-2", bindings={"x": math.sqrt(2)})["result"] == pytest.approx(0.0)


def test_multi_arg():
    assert evaluate_infix("atan2(0,1)")["result"] == pytest.approx(0.0)
    assert evaluate_infix("log(10,100)")["result"] == 2.0
    r = evaluate_infix("cmplx(3,4)")
    assert r["result"] == {"re": 3.0, "im": 4.0}


def test_pow_starstar():
    assert evaluate_infix("2**3")["result"] == 8.0


def test_arity_error():
    with pytest.raises(CalcError) as ei:
        to_rpn("sin(1,2)")
    assert ei.value.code == "invalid_data"


def test_unknown_function():
    with pytest.raises(CalcError) as ei:
        to_rpn("foo(1)")
    assert ei.value.code == "unknown_token"
    assert ei.value.hint


def test_mismatched_paren():
    with pytest.raises(CalcError) as ei:
        to_rpn("(1+2")
    assert ei.value.code == "invalid_data"


def test_empty():
    with pytest.raises(CalcError) as ei:
        to_rpn("   ")
    assert ei.value.code == "empty_expression"


def test_injection_chars():
    with pytest.raises(CalcError):
        evaluate_infix("3;4")
    with pytest.raises(CalcError):
        evaluate_infix("__import__('os')")
