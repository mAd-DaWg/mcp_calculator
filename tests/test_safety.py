"""Safety: no eval/exec, injection rejected, resource limits."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from mcp_calculator.calculus import differentiate, integrate
from mcp_calculator.errors import CalcError
from mcp_calculator.infix import evaluate_infix
from mcp_calculator.matrix import matrix_op
from mcp_calculator.rpn import evaluate
from mcp_calculator.solve import solve_linear

SRC = Path(__file__).resolve().parents[1] / "src" / "mcp_calculator"

FORBIDDEN_CALLS = {"eval", "exec"}


def test_no_unsafe_eval_in_source():
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                    pytest.fail(f"{path.name} calls {node.func.id}")
                if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_CALLS:
                    pytest.fail(f"{path.name} calls .{node.func.attr}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "subprocess":
                        pytest.fail(f"{path.name} imports subprocess")
            if isinstance(node, ast.ImportFrom) and node.module == "subprocess":
                pytest.fail(f"{path.name} imports from subprocess")


@pytest.mark.parametrize(
    "payload",
    [
        "__import__('os')",
        "open('/etc/passwd')",
        "lambda x: x",
        "3;4",
        "().__class__",
        "os.system('id')",
    ],
)
def test_injection_rejected(payload):
    with pytest.raises(CalcError) as ei:
        evaluate_infix(payload)
    assert ei.value.code in {
        "unknown_token",
        "empty_expression",
        "leftover_stack",
        "stack_underflow",
        "invalid_data",
    }
    assert ei.value.hint


@pytest.mark.parametrize(
    "payload",
    [
        "__import__('os')",
        "open('/etc/passwd')",
        "3;4",
    ],
)
def test_rpn_engine_injection_still_rejected(payload):
    with pytest.raises(CalcError) as ei:
        evaluate(payload)
    assert ei.value.code in {"unknown_token", "empty_expression", "leftover_stack", "stack_underflow"}
    assert ei.value.hint


def test_calculus_injection():
    with pytest.raises(CalcError):
        differentiate("__import__('os')", at=1)
    with pytest.raises(CalcError):
        integrate("open('/etc/passwd')", 0, 1)


def test_token_limit():
    with pytest.raises(CalcError) as ei:
        evaluate("1 " * 10001)
    assert ei.value.code == "overflow"


def test_huge_factorial():
    with pytest.raises(CalcError) as ei:
        evaluate("500 fact")
    assert ei.value.code == "invalid_factorial"


def test_huge_matrix():
    with pytest.raises(CalcError) as ei:
        matrix_op("identity", n=1000)
    assert ei.value.code == "overflow"


def test_huge_linear_system():
    n = 100
    A = [[float(i == j) for j in range(n)] for i in range(n)]
    b = [1.0] * n
    with pytest.raises(CalcError) as ei:
        solve_linear(A=A, b=b)
    assert ei.value.code == "overflow"


def test_differentiate_rejects_bad_h():
    with pytest.raises(CalcError) as ei:
        differentiate("x", at=1, h=0)
    assert ei.value.code == "invalid_data"
    with pytest.raises(CalcError) as ei:
        differentiate("x", at=1, h=float("nan"))
    assert ei.value.code == "invalid_data"


def test_integrate_rejects_bad_tol():
    with pytest.raises(CalcError) as ei:
        integrate("x", 0, 1, tol=0)
    assert ei.value.code == "invalid_data"
    with pytest.raises(CalcError) as ei:
        integrate("x", 0, 1, tol=-1e-10)
    assert ei.value.code == "invalid_data"
    with pytest.raises(CalcError) as ei:
        integrate("x", 0, 1, tol=float("inf"))
    assert ei.value.code == "invalid_data"


def test_error_has_hint_not_traceback():
    with pytest.raises(CalcError) as ei:
        evaluate("1 0 /")
    d = ei.value.to_dict()
    assert d["ok"] is False
    assert "hint" in d
    assert "Traceback" not in d["message"]
    assert "hint" in d and d["hint"]
