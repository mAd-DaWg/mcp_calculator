"""Safety: no eval/exec, injection rejected, resource limits, MCP JSON boundary."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from mcp_calculator.calculus import differentiate, integrate
from mcp_calculator.errors import CalcError
from mcp_calculator.infix import evaluate_infix
from mcp_calculator.list_finance import list_op
from mcp_calculator.matrix import matrix_op
from mcp_calculator.rpn import evaluate
from mcp_calculator.solve import solve_linear
from mcp_calculator.stats import stats_1var
from mcp_calculator.calc_extra import table as table_fn

SRC = Path(__file__).resolve().parents[1] / "src" / "mcp_calculator"

FORBIDDEN_CALLS = {"eval", "exec"}
FORBIDDEN_IMPORT_ROOTS = {"subprocess", "pickle", "ctypes", "importlib"}


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
                    root = alias.name.split(".", 1)[0]
                    if root in FORBIDDEN_IMPORT_ROOTS:
                        pytest.fail(f"{path.name} imports {alias.name}")
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".", 1)[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    pytest.fail(f"{path.name} imports from {node.module}")


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


def _assert_tool_error_json(raw: str) -> dict:
    assert isinstance(raw, str)
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload.get("hint")
    assert "Traceback" not in payload.get("message", "")
    assert "Traceback" not in payload.get("hint", "")
    assert "traceback" not in payload
    return payload


def test_server_evaluate_injection_json_boundary():
    from mcp_calculator import server

    _assert_tool_error_json(server.evaluate("__import__('os')"))


def test_server_solve_root_injection():
    from mcp_calculator import server

    _assert_tool_error_json(server.solve_root("__import__('os')", bracket=[0.0, 1.0]))


def test_server_summation_injection():
    from mcp_calculator import server

    _assert_tool_error_json(server.summation("open('/etc/passwd')", start=1, end=2))


def test_server_list_op_seq_injection():
    from mcp_calculator import server

    _assert_tool_error_json(
        server.list_op(op="seq", expression="os.system('id')", start=1.0, end=2.0, step=1.0)
    )


def test_server_division_by_zero_structured():
    from mcp_calculator import server

    payload = _assert_tool_error_json(server.evaluate("1/0"))
    assert payload["error"] in {"division_by_zero", "domain_error", "overflow"}


def test_server_log_zero_structured():
    from mcp_calculator import server

    payload = _assert_tool_error_json(server.evaluate("ln(0)"))
    assert payload["error"] in {"domain_error", "overflow"}


def test_server_inf_constant_is_structured_overflow():
    from mcp_calculator import server

    payload = _assert_tool_error_json(server.evaluate("inf"))
    assert payload["error"] == "overflow"


def test_token_limit(monkeypatch):
    monkeypatch.setattr("mcp_calculator.rpn.MAX_TOKENS", 8)
    with pytest.raises(CalcError) as ei:
        evaluate("1 1 1 1 1 1 1 1 1")
    assert ei.value.code == "overflow"


def test_infix_expression_length_limit(monkeypatch):
    monkeypatch.setattr("mcp_calculator.infix.MAX_EXPR_LEN", 16)
    with pytest.raises(CalcError) as ei:
        evaluate_infix("1" * 20)
    assert ei.value.code == "overflow"


def test_infix_token_flood(monkeypatch):
    monkeypatch.setattr("mcp_calculator.infix.MAX_TOKENS", 8)
    with pytest.raises(CalcError) as ei:
        evaluate_infix("1+1+1+1+1+1+1+1+1")
    assert ei.value.code == "overflow"


def test_stats_sample_size_limit(monkeypatch):
    monkeypatch.setattr("mcp_calculator.stats.MAX_N", 10)
    with pytest.raises(CalcError) as ei:
        stats_1var([0.0] * 11)
    assert ei.value.code == "overflow"


def test_table_range_limit():
    # Early estimate rejects without allocating rows.
    with pytest.raises(CalcError) as ei:
        table_fn("x", start=0.0, end=1e9, step=1.0)
    assert ei.value.code == "overflow"


def test_list_op_seq_length_limit():
    with pytest.raises(CalcError) as ei:
        list_op(op="seq", expression="x", start=0.0, end=1e9, step=1.0)
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
    # Just over MAX_DIM (32); avoid building a huge test matrix.
    n = 33
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
    assert "traceback" not in d
