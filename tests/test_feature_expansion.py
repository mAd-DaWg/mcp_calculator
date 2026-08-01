"""Tests for new scientific calculator floor + expansion features."""

from __future__ import annotations

import math

import pytest

from mcp_calculator.base_n import base_arith
from mcp_calculator.calc_extra import evaluate_with_form, factorize, product
from mcp_calculator.calculus import fmax, fmin
from mcp_calculator.distribution import distribution
from mcp_calculator.list_finance import finance_tvm, list_op
from mcp_calculator.matrix import matrix_op
from mcp_calculator.stats import stats_1var, stats_2var
from mcp_calculator.stats_test import stats_test


def test_quartiles_and_mode():
    r = stats_1var([1, 2, 2, 3, 3, 3, 4, 4, 5], freq=None)
    # expand isn't needed; data as-is
    r = stats_1var([1, 2, 2, 3, 4])
    assert "q1" in r and "q3" in r and "mode" in r
    assert r["mode"] == 2.0 or 2 in (r["mode"] if isinstance(r["mode"], list) else [r["mode"]])


def test_2var_sums():
    r = stats_2var([1, 2, 3], [2, 4, 6])
    assert r["sum_y"] == pytest.approx(12)
    assert r["sum_xy"] == pytest.approx(28)
    assert r["min_y"] == 2
    assert r["std_pop_y"] == pytest.approx(math.sqrt(8 / 3))


def test_factorize_product_fminmax():
    assert factorize(1014)["factors"] == [2, 3, 13, 13]
    assert product("x", 1, 4)["product"] == pytest.approx(24)
    assert fmin("x^2", -1, 1)["x"] == pytest.approx(0, abs=1e-5)
    assert fmax("-(x-1)^2", 0, 2)["x"] == pytest.approx(1, abs=1e-5)


def test_variables_and_neg():
    r = evaluate_with_form("A+B", variables={"A": 2, "B": 3})
    assert r["result"] == 5
    assert base_arith("neg", "5", base=10)["decimal_unsigned"] == (-5) & 0xFFFFFFFF


def test_distribution_extras():
    assert distribution("geometric_pd", x=2, p=0.5)["probability"] == pytest.approx(0.25)
    inv = distribution("inverse_normal", area=0.95, sigma=1, mu=0, tail="right")
    assert inv["x"] == pytest.approx(distribution("inverse_normal", area=0.05, sigma=1, mu=0)["x"], rel=1e-5)
    center = distribution("inverse_normal", area=0.9, sigma=1, mu=0, tail="center")
    assert center["lower"] < 0 < center["upper"]
    ib = distribution("inverse_binomial", area=0.95, n=30, p=0.5)
    assert ib["x"] == 19
    t = distribution("t_cd", lower=-1, upper=1, df=10)
    assert 0.5 < t["p"] < 1
    assert distribution("chi2_pd", x=2, df=2)["p"] > 0
    assert distribution("f_cd", lower=0, upper=1, df1=5, df2=10)["p"] > 0


def test_stats_test_and_list_tvm():
    z = stats_test("z_test", data=[1, 2, 3, 4, 5], sigma=1.5, mu0=3)
    assert "z" in z and "p" in z
    tt = stats_test("t_test", data=[1, 2, 3, 4, 5], mu0=0)
    assert tt["t"] > 0
    t2 = stats_test("2_samp_t_test", data=[1, 2, 3, 4], data2=[2, 3, 4, 5], pooled=True)
    assert "t" in t2
    p1 = stats_test("1_prop_z_test", x=40, n=100, p0=0.5)
    assert "z" in p1
    p2 = stats_test("2_prop_z_test", x1=40, n1=100, x2=50, n2=100)
    assert "z" in p2
    an = stats_test("anova", lists=[[1, 2, 3], [2, 3, 4], [3, 4, 5]])
    assert an["F"] > 0
    lr = stats_test("linreg_ttest", data=[1, 2, 3, 4], data2=[2.1, 3.9, 6.2, 7.8])
    assert abs(lr["b"] - 2) < 0.2
    assert list_op("seq", expression="2*x", start=1, end=3)["result"] == pytest.approx([2, 4, 6])
    assert list_op("cumsum", data=[1, 2, 3])["result"] == pytest.approx([1, 3, 6])
    assert list_op("sort_a", data=[3, 1, 2])["result"] == [1, 2, 3]
    assert list_op("sort_d", data=[3, 1, 2])["result"] == [3, 2, 1]
    assert list_op("delta", data=[1, 3, 6])["result"] == pytest.approx([2, 3])
    fv = finance_tvm("FV", N=12, I=0, PV=-100, PMT=0)
    assert fv["FV"] == pytest.approx(100)
    pv = finance_tvm("PV", N=1, I=0, PMT=0, FV=50)
    assert pv["PV"] == pytest.approx(-50)
    pmt = finance_tvm("PMT", N=2, I=0, PV=-100, FV=0)
    assert pmt["PMT"] == pytest.approx(50)
    nsol = finance_tvm("N", I=0, PV=-100, PMT=25, FV=0)
    assert nsol["N"] == pytest.approx(4)


def test_eigen():
    r = matrix_op("eigen", [[[2, 0], [0, 3]]])
    assert sorted(r["eigenvalues"]) == pytest.approx([2.0, 3.0])
