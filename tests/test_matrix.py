import pytest

from mcp_calculator.errors import CalcError
from mcp_calculator.matrix import matrix_op


def test_det():
    r = matrix_op("det", [[[1, 2], [3, 4]]])
    assert r["result"] == pytest.approx(-2)


def test_add_mul_transpose_inv():
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    assert matrix_op("add", [a, b])["result"] == [[6, 8], [10, 12]]
    assert matrix_op("mul", [a, b])["result"][0][0] == pytest.approx(19)
    assert matrix_op("transpose", [a])["result"] == [[1, 3], [2, 4]]
    inv = matrix_op("inv", [a])["result"]
    assert inv[0][0] == pytest.approx(-2)


def test_identity():
    r = matrix_op("identity", n=3)
    assert r["result"] == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def test_dot_cross_norm_angle():
    assert matrix_op("dot", [[1, 0, 0], [0, 1, 0]])["result"] == pytest.approx(0)
    assert matrix_op("cross", [[1, 0, 0], [0, 1, 0]])["result"] == pytest.approx([0, 0, 1])
    assert matrix_op("norm", vector=[3, 4])["result"] == pytest.approx(5)
    assert matrix_op("angle", [[1, 0], [0, 1]])["result"] == pytest.approx(1.57079632679)


def test_dimension_error():
    with pytest.raises(CalcError) as ei:
        matrix_op("mul", [[[1, 2]], [[1], [2], [3]]])
    assert ei.value.code == "dimension_error"
    assert ei.value.hint


def test_singular():
    with pytest.raises(CalcError) as ei:
        matrix_op("inv", [[[1, 2], [2, 4]]])
    assert ei.value.code == "singular_matrix"


def test_oversized():
    with pytest.raises(CalcError) as ei:
        matrix_op("identity", n=100)
    assert ei.value.code == "overflow"
