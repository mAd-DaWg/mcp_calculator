import math

import pytest

from mcp_calculator.calculus import differentiate, integrate
from mcp_calculator.errors import CalcError


def test_diff_x_cubed():
    r = differentiate("x^3", at=2)
    assert r["derivative"] == pytest.approx(12, rel=1e-6)


def test_diff_sin():
    r = differentiate("sin(x)", at=0)
    assert r["derivative"] == pytest.approx(1, rel=1e-6)


def test_integrate_x_sq():
    r = integrate("x^2", 0, 1)
    assert r["integral"] == pytest.approx(1 / 3, rel=1e-8)


def test_integrate_sin():
    r = integrate("sin(x)", 0, math.pi)
    assert r["integral"] == pytest.approx(2, rel=1e-8)



def test_bad_expression():
    with pytest.raises(CalcError):
        differentiate("__import__('os')", at=0)
