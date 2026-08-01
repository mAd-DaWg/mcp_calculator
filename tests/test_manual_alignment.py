"""Tests for selectable STAT models, matrix REF, distribution, table, ratio, etc."""

from __future__ import annotations

import json
import math

import pytest

from mcp_calculator.base_n import base_arith
from mcp_calculator.calc_extra import (
    decimal_to_dms,
    dms_to_decimal,
    evaluate_with_form,
    pol,
    rec,
    summation,
    table,
)
from mcp_calculator.distribution import distribution
from mcp_calculator.errors import CalcError
from mcp_calculator.matrix import matrix_op
from mcp_calculator.modes_extra import solve_inequality, solve_ratio
from mcp_calculator.solve import solve_polynomial
from mcp_calculator.stats import stats_1var, stats_2var


def test_linear_still_default():
    r = stats_2var([1, 2, 3, 4], [3, 5, 7, 9])
    assert r["model"] == "linear"
    assert r["b"] == pytest.approx(2)
    assert r["a"] == pytest.approx(1)
    assert r["equation"] == "y = a + b*x"


def test_linear_predict():
    r = stats_2var([1, 2, 3, 4], [3, 5, 7, 9], predict_y_at=5, predict_x_at=11)
    assert r["y_hat"] == pytest.approx(11)
    assert r["x_hat"] == pytest.approx(5)


def test_logarithmic_model():
    xs = [1.0, math.e, math.e**2]
    ys = [2 + 3 * math.log(x) for x in xs]
    r = stats_2var(xs, ys, model="logarithmic", predict_y_at=math.e, predict_x_at=5)
    assert r["a"] == pytest.approx(2, rel=1e-6)
    assert r["b"] == pytest.approx(3, rel=1e-6)
    assert r["r"] == pytest.approx(1, abs=1e-6)
    assert r["y_hat"] == pytest.approx(5, rel=1e-6)
    assert r["x_hat"] == pytest.approx(math.exp(1), rel=1e-6)


def test_quadratic_and_predict():
    xs = [0.0, 1.0, 2.0, 3.0]
    ys = [1 + 2 * x + 3 * x * x for x in xs]
    r = stats_2var(xs, ys, model="quadratic", predict_y_at=1.0, predict_x_at=6.0)
    assert r["a"] == pytest.approx(1, abs=1e-6)
    assert r["b"] == pytest.approx(2, abs=1e-6)
    assert r["c"] == pytest.approx(3, abs=1e-6)
    assert r["y_hat"] == pytest.approx(6, abs=1e-6)
    assert {"x_hat1", "x_hat2"} <= set(r)


def test_exp_abexp_power_inverse():
    xs = [0.0, 1.0, 2.0, 3.0]
    ys_exp = [2 * math.exp(0.5 * x) for x in xs]
    r = stats_2var(xs, ys_exp, model="exp", predict_y_at=1.0)
    assert r["a"] == pytest.approx(2, rel=1e-5)
    assert r["b"] == pytest.approx(0.5, rel=1e-5)
    assert r["y_hat"] == pytest.approx(2 * math.exp(0.5), rel=1e-5)

    ys_ab = [3 * (2**x) for x in xs]
    r2 = stats_2var(xs, ys_ab, model="abexp", predict_y_at=2)
    assert r2["a"] == pytest.approx(3, rel=1e-5)
    assert r2["b"] == pytest.approx(2, rel=1e-5)
    assert r2["y_hat"] == pytest.approx(12, rel=1e-5)

    xp = [1.0, 2.0, 3.0, 4.0]
    yp = [2 * (x**1.5) for x in xp]
    r3 = stats_2var(xp, yp, model="power", predict_y_at=4)
    assert r3["a"] == pytest.approx(2, rel=1e-5)
    assert r3["b"] == pytest.approx(1.5, rel=1e-5)

    xi = [1.0, 2.0, 4.0, 5.0]
    yi = [1 + 2 / x for x in xi]
    r4 = stats_2var(xi, yi, model="inverse", predict_y_at=2, predict_x_at=2)
    assert r4["a"] == pytest.approx(1, rel=1e-5)
    assert r4["b"] == pytest.approx(2, rel=1e-5)
    assert r4["y_hat"] == pytest.approx(2, rel=1e-5)
    assert r4["x_hat"] == pytest.approx(2, rel=1e-5)


def test_cubic_quartic_medmed_logistic():
    xs = [0.0, 1.0, 2.0, 3.0, 4.0]
    ys = [1 + 2 * x + 3 * x**2 + 0.5 * x**3 for x in xs]
    r = stats_2var(xs, ys, model="cubic", predict_y_at=1)
    assert r["y_hat"] == pytest.approx(1 + 2 + 3 + 0.5, rel=1e-4)

    xq = list(range(6))
    yq = [1 + x + 0.1 * x**2 + 0.01 * x**3 + 0.001 * x**4 for x in xq]
    rq = stats_2var(xq, yq, model="quartic", predict_y_at=2)
    assert "a" in rq and rq["y_hat"] == pytest.approx(yq[2], rel=1e-3)

    xm = list(range(9))
    ym = [2 * x + 1 for x in xm]
    rm = stats_2var(xm, ym, model="medmed", predict_y_at=3, predict_x_at=7)
    assert rm["a"] == pytest.approx(2, abs=0.5)
    assert rm["y_hat"] == pytest.approx(2 * 3 + rm["b"], abs=1e-6)

    # logistic-ish sigmoid data
    xl = [-2.0, -1.0, 0.0, 1.0, 2.0]
    c, a, b = 10.0, 2.0, 1.0
    yl = [c / (1 + a * math.exp(-b * x)) for x in xl]
    rl = stats_2var(xl, yl, model="logistic", predict_y_at=0)
    assert rl["c"] > max(yl)
    assert rl["y_hat"] == pytest.approx(
        rl["c"] / (1 + rl["a"] * math.exp(-rl["b"] * 0)), rel=1e-9
    )


def test_freq_1var_and_2var():
    r = stats_1var([1, 2, 3], freq=[1, 2, 1])
    assert r["n"] == 4
    assert r["mean"] == pytest.approx(2.0)
    r2 = stats_2var([1, 2, 3], [2, 4, 6], freq=[1, 1, 1], model="linear")
    assert r2["b"] == pytest.approx(2)


def test_1var_single_point_no_nan_json():
    r = stats_1var([5])
    assert r["var_sample"] is None
    assert r["std_sample"] is None
    json.dumps(r, allow_nan=False)


def test_unknown_model():
    with pytest.raises(CalcError) as ei:
        stats_2var([1, 2], [1, 2], model="nope")
    assert ei.value.code == "invalid_data"


def test_ref_not_rref():
    m = [[1, 2, 3], [2, 4, 7]]
    ref = matrix_op("ref", [m])["result"]
    rref = matrix_op("rref", [m])["result"]
    assert matrix_op("ref", [m])["op"] == "ref"
    assert matrix_op("rref", [m])["op"] == "rref"
    assert abs(ref[1][0]) < 1e-9
    assert abs(rref[0][0] - 1) < 1e-9
    # RREF zeros above pivots more aggressively than REF for this matrix
    assert abs(rref[0][1]) < 1e-9 or abs(ref[0][1] - rref[0][1]) > 1e-9 or ref != rref


def test_angle_mode_deg():
    r = matrix_op("angle", [[1, 0], [0, 1]], angle_mode="deg")
    assert r["unit"] == "deg"
    assert r["result"] == pytest.approx(90, abs=1e-6)


def test_unit_vector():
    r = matrix_op("unit", vector=[3, 4])
    assert r["result"] == pytest.approx([0.6, 0.8])


def test_pol_rec_example():
    p = pol(2, 2, angle_mode="deg")
    assert p["r"] == pytest.approx(2 * math.sqrt(2))
    assert p["theta"] == pytest.approx(45, abs=1e-6)
    r = rec(2, 45, angle_mode="deg")
    assert r["x"] == pytest.approx(math.sqrt(2), rel=1e-6)
    assert r["y"] == pytest.approx(math.sqrt(2), rel=1e-6)
    p_rad = pol(1, 0, angle_mode="rad")
    assert p_rad["theta"] == pytest.approx(0)
    with pytest.raises(CalcError):
        rec(-1, 0)
    with pytest.raises(CalcError):
        pol(1, 0, angle_mode="bogus")


def test_summation_style():
    r = summation("x+1", 1, 5)
    assert r["sum"] == pytest.approx(20)
    with pytest.raises(CalcError):
        summation("x", 5, 1)
    with pytest.raises(CalcError):
        summation("x", 1, 2, index="k")


def test_table_basic():
    r = table("2*x", 0, 2, 1, expression2="x^2")
    assert len(r["rows"]) == 3
    assert r["rows"][1]["f"] == pytest.approx(2)
    assert r["rows"][1]["g"] == pytest.approx(1)
    with pytest.raises(CalcError):
        table("x", 0, 1, 0)
    with pytest.raises(CalcError):
        table("x", 0, 1, -1)


def test_complex_form_polar():
    r = evaluate_with_form("cmplx(0,1)", complex_form="polar")
    assert r["complex_form"] == "polar"
    assert r["result"]["r"] == pytest.approx(1)
    assert r["result"]["theta"] == pytest.approx(math.pi / 2)
    with pytest.raises(CalcError):
        evaluate_with_form("1", complex_form="hex")


def test_normal_pd_example():
    r = distribution("normal_pd", x=36, sigma=2, mu=35)
    assert r["p"] == pytest.approx(0.1760326634, rel=1e-5)


def test_normal_cd_and_inverse():
    r = distribution("normal_cd", lower=34, upper=36, sigma=2, mu=35)
    assert 0 < r["p"] < 1
    inv = distribution("inverse_normal", area=0.5, sigma=1, mu=0)
    assert inv["x"] == pytest.approx(0, abs=1e-6)
    inv_lo = distribution("inverse_normal", area=0.01, sigma=1, mu=0)
    assert inv_lo["x"] < 0
    inv_hi = distribution("inverse_normal", area=0.99, sigma=1, mu=0)
    assert inv_hi["x"] > 0
    with pytest.raises(CalcError):
        distribution("inverse_normal", area=0, sigma=1, mu=0)
    with pytest.raises(CalcError):
        distribution("normal_pd", x=0, sigma=-1, mu=0)
    with pytest.raises(CalcError):
        distribution("normal_pd", x=0)
    with pytest.raises(CalcError):
        distribution("nope")


def test_binomial_poisson():
    bp = distribution("binomial_pd", x=2, n=5, p=0.5)
    assert bp["probability"] == pytest.approx(10 / 32)
    bc = distribution("binomial_cd", x=2, n=5, p=0.5)
    assert bc["probability"] == pytest.approx((1 + 5 + 10) / 32)
    bl = distribution("binomial_pd", x=[0, 1], n=2, p=0.5)
    assert len(bl["probability"]) == 2
    pp = distribution("poisson_pd", x=2, lambda_=2)
    assert pp["probability"] == pytest.approx(math.exp(-2) * 2, rel=1e-6)
    pc = distribution("poisson_cd", x=1, lambda_=1)
    assert pc["probability"] == pytest.approx(math.exp(-1) * (1 + 1), rel=1e-6)
    pl = distribution("poisson_pd", x=[0, 1], lambda_=1)
    assert len(pl["probability"]) == 2
    with pytest.raises(CalcError):
        distribution("binomial_pd", x=1, n=2, p=2)
    with pytest.raises(CalcError):
        distribution("poisson_pd", x=1, lambda_=-1)


def test_ratio():
    r = solve_ratio(a=2, b=3, d=6, solve_for="c")
    assert r["value"] == pytest.approx(4)
    assert r["c"] == pytest.approx(4)
    rx = solve_ratio(a=2, b=3, c=4, d=None, solve_for="x")
    assert rx["solve_for"] == "d"
    assert rx["value"] == pytest.approx(6)
    ra = solve_ratio(b=3, c=4, d=6, solve_for="a")
    assert ra["value"] == pytest.approx(2)
    rb = solve_ratio(a=2, c=4, d=6, solve_for="b")
    assert rb["value"] == pytest.approx(3)
    with pytest.raises(CalcError):
        solve_ratio(a=1, solve_for="x")
    with pytest.raises(CalcError):
        solve_ratio(a=1, b=2, c=3, d=4, solve_for="z")


def test_inequality_linear():
    r = solve_inequality([-1, 1], ">")
    assert r["relation"] == ">"
    assert any(iv.get("low") == 1.0 or iv.get("type") == "interval" for iv in r["solution"])
    r2 = solve_inequality([-1, 1], ">=")
    assert r2["relation"] == ">="
    with pytest.raises(CalcError):
        solve_inequality([1], ">")
    with pytest.raises(CalcError):
        solve_inequality([-1, 1], "??")


def test_dms():
    r = dms_to_decimal(10, 30, 0)
    assert r["decimal"] == pytest.approx(10.5)
    back = decimal_to_dms(10.5)
    assert back["degrees"] == 10
    assert back["minutes"] == 30
    neg = dms_to_decimal(-10, 30, 0)
    assert neg["decimal"] < 0


def test_poly_allow_complex():
    r = solve_polynomial([1, 0, 1], allow_complex=True)  # x^2+1=0
    assert len(r["roots"]) == 2
    r2 = solve_polynomial([1, 0, 1], allow_complex=False)
    assert r2["ok"] is True


def test_base_xnor_32bit():
    r = base_arith("xnor", "0", "0", base=10)
    assert r["ok"] is True
