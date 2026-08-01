"""Per-op happy-path RPN tests driven by OPS registry."""

from __future__ import annotations

import math
import random

import pytest

from mcp_calculator.ops import OPS, list_operations
from mcp_calculator.rpn import evaluate


# Minimal expressions that leave exactly one stack value for each op
OP_CASES = {
    "+": ("3 4 +", 7),
    "-": ("10 3 -", 7),
    "*": ("3 4 *", 12),
    "/": ("8 2 /", 4),
    "^": ("2 3 ^", 8),
    "pow": ("2 3 pow", 8),
    "%": ("10 3 %", 1),
    "mod": ("10 3 mod", 1),
    "nroot": ("2 9 nroot", 3),
    "neg": ("5 neg", -5),
    "abs": ("5 neg abs", 5),
    "inv": ("4 inv", 0.25),
    "sqrt": ("9 sqrt", 3),
    "cbrt": ("8 cbrt", 2),
    "sq": ("5 sq", 25),
    "cube": ("3 cube", 27),
    "pct": ("200 10 pct", 20),
    "pct1": ("25 pct1", 0.25),
    "exp": ("0 exp", 1),
    "exp10": ("2 exp10", 100),
    "ln": ("1 ln", 0),
    "log10": ("100 log10", 2),
    "log2": ("8 log2", 3),
    "log": ("10 100 log", 2),
    "sin": ("0 sin", 0),
    "cos": ("0 cos", 1),
    "tan": ("0 tan", 0),
    "asin": ("0 asin", 0),
    "acos": ("1 acos", 0),
    "atan": ("0 atan", 0),
    "atan2": ("1 1 atan2", math.pi / 4),
    "sec": ("0 sec", 1),
    "csc": ("DEG 90 csc", 1),
    "cot": ("DEG 45 cot", 1),
    "sinh": ("0 sinh", 0),
    "cosh": ("0 cosh", 1),
    "tanh": ("0 tanh", 0),
    "asinh": ("0 asinh", 0),
    "acosh": ("1 acosh", 0),
    "atanh": ("0 atanh", 0),
    "sech": ("0 sech", 1),
    "csch": ("1 csch", 1 / math.sinh(1)),
    "coth": ("1 coth", 1 / math.tanh(1)),
    "d2r": ("180 d2r", math.pi),
    "r2d": ("pi r2d", 180),
    "g2r": ("200 g2r", math.pi),
    "r2g": ("pi r2g", 200),
    "d2g": ("90 d2g", 100),
    "g2d": ("100 g2d", 90),
    "floor": ("3.7 floor", 3),
    "ceil": ("3.2 ceil", 4),
    "round": ("3.6 round", 4),
    "trunc": ("3.9 trunc", 3),
    "frac": ("3.25 frac", 0.25),
    "int": ("3.9 int", 3),
    "fact": ("5 fact", 120),
    "nPr": ("5 2 nPr", 20),
    "nCr": ("5 2 nCr", 10),
    "rand": ("rand", None),
    "randint": ("1 1 randint", 1),
    "min": ("3 5 min", 3),
    "max": ("3 5 max", 5),
    "hypot": ("3 4 hypot", 5),
    "sgn": ("5 neg sgn", -1),
    "gcd": ("12 8 gcd", 4),
    "lcm": ("4 6 lcm", 12),
    "cmplx": ("3 4 cmplx re", 3),
    "polar": ("2 0 polar re", 2),
    "engshift": ("1234 -1 engshift", 1.234),
    "re": ("3 4 cmplx re", 3),
    "im": ("3 4 cmplx im", 4),
    "conj": ("3 4 cmplx conj re", 3),
    "arg": ("0 1 cmplx arg", math.pi / 2),
    "RAD": ("RAD 0 sin", 0),
    "DEG": ("DEG 30 sin", 0.5),
    "GRAD": ("GRAD 100 3 / sin", 0.5),  # 100/3 grad = 30°
}


def test_list_operations_covers_ops():
    names = {o["name"] for o in list_operations()}
    assert names == set(OPS.keys())


@pytest.mark.parametrize("op_name", list(OPS.keys()))
def test_every_op_has_case(op_name):
    assert op_name in OP_CASES, f"Missing happy-path case for {op_name}"


@pytest.mark.parametrize("op_name,case", list(OP_CASES.items()))
def test_op_happy_path(op_name, case):
    expr, expected = case
    res = evaluate(expr, angle_mode="rad", rng=random.Random(0))
    assert res["ok"] is True
    if expected is None:
        assert 0 <= res["result"] < 1
    else:
        assert res["result"] == pytest.approx(expected, rel=1e-9, abs=1e-9)
