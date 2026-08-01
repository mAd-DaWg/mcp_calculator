"""Engineering symbols, polar ∠, angle suffixes, STAT Norm Dist P/Q/R/t."""

from __future__ import annotations

import math

import pytest

from mcp_calculator.calc_extra import engineering_format, engineering_shift, evaluate_with_form
from mcp_calculator.distribution import distribution, norm_pqr
from mcp_calculator.infix import evaluate_infix
from mcp_calculator.stats import stats_1var


def test_engineering_suffix_input():
    assert evaluate_infix("500k")["result"] == 500_000.0
    assert evaluate_infix("500k+10M")["result"] == 10_500_000.0
    assert evaluate_infix("3u")["result"] == pytest.approx(3e-6)
    assert evaluate_infix("3μ")["result"] == pytest.approx(3e-6)


def test_engineering_format_and_shift():
    fmt = engineering_format(1_024_000)
    assert fmt["symbol"] == "M"
    assert fmt["significand"] == pytest.approx(1.024)
    assert fmt["display"] == "1.024M"
    sh = engineering_shift(1234, -1)
    assert sh["value"] == pytest.approx(1.234)
    assert evaluate_infix("engshift(1234, -1)")["result"] == pytest.approx(1.234)


def test_evaluate_eng_symbols_flag():
    r = evaluate_with_form("999k+25k", eng_symbols=True)
    assert r["result"] == pytest.approx(1_024_000)
    assert r["eng"]["display"] == "1.024M"


def test_angle_suffix_degree_in_rad_mode():
    assert evaluate_infix("sin(30°)", angle_mode="rad")["result"] == pytest.approx(0.5)
    assert evaluate_infix("1r", angle_mode="deg")["result"] == pytest.approx(180.0 / math.pi)
    assert evaluate_infix("100g", angle_mode="deg")["result"] == pytest.approx(90.0)


def test_polar_literal():
    r = evaluate_infix("2∠90", angle_mode="deg")
    assert r["result"]["re"] == pytest.approx(0.0, abs=1e-10)
    assert r["result"]["im"] == pytest.approx(2.0)
    r2 = evaluate_with_form("2∠30", angle_mode="deg", complex_form="polar")
    assert r2["result"]["r"] == pytest.approx(2.0)
    assert r2["result"]["theta"] == pytest.approx(30.0)


def test_stat_norm_dist_pqr_manual_example():
    # Manual Ex: data with freq; x=3 → t≈-0.762, P≈0.223
    data = [0, 1, 2, 3, 4, 5, 6, 7, 9, 10]
    freq = [1, 2, 1, 2, 2, 2, 3, 4, 2, 1]
    r = stats_1var(data, freq, norm_x=3)
    assert r["t"] == pytest.approx(-0.762, abs=1e-3)
    assert r["P"] == pytest.approx(0.223, abs=1e-3)
    assert r["Q"] == pytest.approx(r["P"] - 0.5)
    assert r["R"] == pytest.approx(1 - r["P"])


def test_norm_pqr_distribution_types():
    areas = norm_pqr(1.04)
    assert areas["P"] == pytest.approx(0.8508, abs=1e-3)
    assert distribution("norm_p", x=1.04)["p"] == pytest.approx(areas["P"])
    assert distribution("norm_q", x=1.04)["p"] == pytest.approx(areas["Q"])
    assert distribution("norm_r", x=1.04)["p"] == pytest.approx(areas["R"])
