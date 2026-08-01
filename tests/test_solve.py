import math

import pytest

from mcp_calculator.errors import CalcError
from mcp_calculator.solve import solve_linear, solve_polynomial, solve_root


def test_linear_unique():
    r = solve_linear(A=[[2, 1], [1, 3]], b=[1, 2])
    assert r["status"] == "unique"
    assert r["solution"][0] == pytest.approx(0.2)
    assert r["solution"][1] == pytest.approx(0.6)


def test_linear_augmented():
    r = solve_linear(coefficients=[[1, 0, 3], [0, 1, 4]])
    assert r["solution"] == pytest.approx([3, 4])


def test_linear_singular():
    with pytest.raises(CalcError) as ei:
        solve_linear(A=[[1, 2], [2, 4]], b=[1, 2])
    assert ei.value.code == "no_unique_solution"


def test_root_brent_sqrt2():
    r = solve_root("x^2-2", bracket=[0, 2])
    assert r["root"] == pytest.approx(math.sqrt(2), rel=1e-10)
    assert r["method"] == "brent"
    assert r["abs_f"] < 1e-10


def test_root_newton():
    r = solve_root("x^2-2", guess=1.0)
    assert r["root"] == pytest.approx(math.sqrt(2), rel=1e-8)


def test_root_no_sign_change():
    with pytest.raises(CalcError) as ei:
        solve_root("x^2+2", bracket=[0, 1])
    assert ei.value.code == "no_root"
    assert ei.value.hint


def test_poly_linear():
    r = solve_polynomial([-2, 1])  # x - 2 = 0
    assert r["roots"][0] == pytest.approx(2)


def test_poly_quadratic():
    r = solve_polynomial([-2, 0, 1])  # x^2 - 2
    roots = sorted(r["roots"])
    assert roots[0] == pytest.approx(-math.sqrt(2))
    assert roots[1] == pytest.approx(math.sqrt(2))


def test_poly_cubic_factors():
    # (x-1)(x-2)(x-3) = x^3 - 6x^2 + 11x - 6
    r = solve_polynomial([-6, 11, -6, 1])
    roots = sorted(float(x) if not isinstance(x, dict) else x["re"] for x in r["roots"])
    assert roots == pytest.approx([1, 2, 3], abs=1e-6)


def test_poly_quartic():
    # (x-1)(x-2)(x-3)(x-4)
    # expand: x^4 - 10x^3 + 35x^2 - 50x + 24
    r = solve_polynomial([24, -50, 35, -10, 1])
    roots = sorted(float(x) if not isinstance(x, dict) else x["re"] for x in r["roots"])
    assert roots == pytest.approx([1, 2, 3, 4], abs=1e-5)
