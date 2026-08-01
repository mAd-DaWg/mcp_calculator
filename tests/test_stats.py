import pytest

from mcp_calculator.errors import CalcError
from mcp_calculator.stats import stats_1var, stats_2var


def test_1var():
    r = stats_1var([1, 2, 3, 4])
    assert r["n"] == 4
    assert r["mean"] == pytest.approx(2.5)
    assert r["sum"] == 10
    assert r["median"] == pytest.approx(2.5)


def test_1var_empty():
    with pytest.raises(CalcError) as ei:
        stats_1var([])
    assert ei.value.code == "invalid_data"


def test_2var_regression():
    # y = 2x + 1
    x = [1, 2, 3, 4]
    y = [3, 5, 7, 9]
    r = stats_2var(x, y)
    assert r["b"] == pytest.approx(2)
    assert r["a"] == pytest.approx(1)
    assert r["r"] == pytest.approx(1)
    assert r["model"] == "linear"
    assert r["equation"] == "y = a + b*x"


def test_2var_mismatch():
    with pytest.raises(CalcError) as ei:
        stats_2var([1, 2], [1])
    assert ei.value.code == "invalid_data"
