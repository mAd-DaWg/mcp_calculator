"""Agent-facing instructions, tool docstrings, and actionable error recovery."""

from __future__ import annotations

import json

from mcp_calculator import server
from mcp_calculator.distribution import distribution
from mcp_calculator.errors import catch_calc
from mcp_calculator.list_finance import finance_tvm
from mcp_calculator.matrix import matrix_op


def _registered_tool_fns():
    names = sorted(server.mcp._tool_manager._tools.keys())
    return [getattr(server, name) for name in names]


def test_server_instructions_route_and_recover() -> None:
    text = server.mcp.instructions or ""
    for needle in (
        "evaluate",
        "matrix_op",
        "stats_1var",
        "finance_tvm",
        "eng_format",
        "ok:false",
        "hint",
        "example",
        "did_you_mean",
        "list_operations",
        "list_constants",
        "never invent",
    ):
        assert needle in text, f"instructions missing {needle!r}"
    assert "scientific calculator scientific" not in text


def test_all_tool_docstrings_have_when_params_example() -> None:
    tools = _registered_tool_fns()
    assert len(tools) >= 30
    for fn in tools:
        doc = fn.__doc__ or ""
        assert "When:" in doc, f"{fn.__name__} missing When:"
        assert "Params:" in doc, f"{fn.__name__} missing Params:"
        assert "Example:" in doc, f"{fn.__name__} missing Example:"


def test_unknown_distribution_type_is_actionable() -> None:
    err = catch_calc(distribution, "not_a_type")
    assert err["ok"] is False
    assert err["error"] == "invalid_data"
    assert "normal_pd" in err["hint"]
    assert err.get("example")
    assert "type=" in err["example"]


def test_bad_tvm_solve_for_is_actionable() -> None:
    err = catch_calc(
        finance_tvm,
        "XYZ",
        N=12,
        I=6,
        PV=-1000,
        PMT=None,
        FV=0,
    )
    assert err["ok"] is False
    assert "solve_for" in err["message"]
    assert "N" in err["message"] or "N" in err["hint"]
    assert err.get("example")
    assert "solve_for=" in err["example"]
    assert len(err["hint"]) > 10


def test_unknown_matrix_op_has_example() -> None:
    err = catch_calc(matrix_op, "nope", [[[1]]])
    assert err["ok"] is False
    assert "det" in err["hint"]
    assert err.get("example")
    assert "op=" in err["example"]


def test_evaluate_tool_json_still_ok() -> None:
    payload = json.loads(server.evaluate("2+2"))
    assert payload["ok"] is True
    assert payload["result"] == 4.0


def test_server_wrappers_smoke_for_coverage() -> None:
    """Hit a few distinct server.py tool wrappers (keep this small — no megasuites)."""
    for raw in (
        server.list_operations(),
        server.list_constants(),
        server.matrix_op("det", matrices=[[[1, 2], [3, 4]]]),
        server.stats_1var([1.0, 2.0, 3.0]),
        server.eng_format(12345.0),
        server.finance_tvm(solve_for="FV", N=1.0, I=0.0, PV=-100.0, PMT=0.0),
    ):
        payload = json.loads(raw)
        assert "ok" in payload

    err = json.loads(server.evaluate("__import__('os')"))
    assert err["ok"] is False
    assert err.get("hint")
    assert "Traceback" not in err.get("message", "")
    assert "traceback" not in err
