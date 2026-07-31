"""Extra coverage for matrix/errors edge paths."""

import pytest

from mcp_calculator.errors import CalcError, catch_calc, fail, ok
from mcp_calculator.matrix import matrix_op


def test_ok_fail_helpers():
    assert ok(result=1)["ok"] is True
    d = fail("x", "m", "h", example="e")
    assert d["ok"] is False and d["hint"] == "h" and d["example"] == "e"


def test_catch_calc_ok_and_error():
    assert catch_calc(lambda: {"result": 1})["ok"] is True

    def boom():
        raise CalcError("domain_error", "bad", "fix it")

    r = catch_calc(boom)
    assert r["ok"] is False and r["error"] == "domain_error"

    def boom2():
        raise RuntimeError("x")

    r2 = catch_calc(boom2)
    assert r2["error"] == "internal_error"


def test_sub_rref():
    a = [[1, 2], [3, 4]]
    b = [[1, 1], [1, 1]]
    assert matrix_op("sub", [a, b])["result"] == [[0, 1], [2, 3]]
    r = matrix_op("rref", [[[1, 2, 3], [2, 4, 6]]])
    assert r["ok"]


def test_vector_via_matrices_norm():
    # two flat vectors for angle already tested; norm via matrices list
    with pytest.raises(CalcError):
        matrix_op("cross", [[1, 0], [0, 1]])  # not 3d
