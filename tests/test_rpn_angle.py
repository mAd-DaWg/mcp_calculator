import math

import pytest

from mcp_calculator.rpn import evaluate


def test_deg_sin_30():
    r = evaluate("30 sin", angle_mode="deg")
    assert r["result"] == pytest.approx(0.5)


def test_grad_sin_30deg_equiv():
    # 100/3 grads = 30 degrees
    r = evaluate("100 3 / sin", angle_mode="grad")
    assert r["result"] == pytest.approx(0.5)


def test_grad_sin_50_is_half_sqrt2():
    r = evaluate("50 sin", angle_mode="grad")
    assert r["result"] == pytest.approx(0.5 ** 0.5)  # 50 grad = 45°


def test_rad_sin_pi_over_6():
    r = evaluate("pi 6 / sin", angle_mode="rad")
    assert r["result"] == pytest.approx(0.5)


def test_mid_expression_deg_token():
    r = evaluate("DEG 30 sin")
    assert r["result"] == pytest.approx(0.5)
    assert r["angle_mode"] == "deg"


def test_hyperbolic_ignores_deg_mode():
    r = evaluate("1 sinh", angle_mode="deg")
    assert r["result"] == pytest.approx(math.sinh(1))


def test_inverse_trig_returns_degrees():
    r = evaluate("0.5 asin", angle_mode="deg")
    assert r["result"] == pytest.approx(30.0)
