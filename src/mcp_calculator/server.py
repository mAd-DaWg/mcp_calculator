"""MCP server: scientific RPN calculator tools over stdio."""

from __future__ import annotations

import json
from typing import Any, Optional

from mcp.server.mcpserver import MCPServer

from mcp_calculator import base_n, calculus, matrix, solve, stats, units
from mcp_calculator.constants import list_constants as _list_constants
from mcp_calculator.errors import catch_calc
from mcp_calculator.ops import list_operations as _list_operations
from mcp_calculator.rpn import evaluate
from mcp_calculator.units import list_unit_conversions as _list_units

mcp = MCPServer(
    "mcp-calculator",
    instructions=(
        "Scientific calculator for verifying numeric work. "
        "Use RPN (postfix) for rpn_eval — e.g. '3 4 +' not '3+4'. "
        "Set angle_mode to rad, deg, or grad for trig. "
        "On ok:false, read message and hint before retrying. "
        "Call list_operations / list_constants / list_unit_conversions to discover tokens."
    ),
)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, allow_nan=False)


@mcp.tool()
def rpn_eval(expression: str, angle_mode: str = "rad") -> str:
    """Evaluate a space-separated RPN expression (real/complex). angle_mode: rad|deg|grad.

    On failure returns ok:false with message and hint for how to fix the call.
    """
    def run():
        return evaluate(expression, angle_mode=angle_mode)

    return _json(catch_calc(run))


@mcp.tool()
def list_operations() -> str:
    """List all RPN operators with arity and descriptions."""
    return _json({"ok": True, "operations": _list_operations()})


@mcp.tool()
def list_constants() -> str:
    """List math/physics constants (CODATA) available as RPN tokens."""
    return _json({"ok": True, "constants": _list_constants()})


@mcp.tool()
def list_unit_conversions() -> str:
    """List available unit conversion ids and from/to pairs."""
    return _json({"ok": True, "conversions": _list_units()})


@mcp.tool()
def matrix_op(
    op: str,
    matrices: Optional[list[Any]] = None,
    vector: Optional[list[float]] = None,
    n: Optional[int] = None,
) -> str:
    """Matrix/vector op: add,sub,mul,transpose,det,inv,identity,rref,dot,cross,norm,angle."""
    return _json(catch_calc(matrix.matrix_op, op, matrices, vector, n))


@mcp.tool()
def stats_1var(data: list[float]) -> str:
    """One-variable stats: n, mean, sum, sumsq, std/var, min/max/median."""
    return _json(catch_calc(stats.stats_1var, data))


@mcp.tool()
def stats_2var(x: list[float], y: list[float]) -> str:
    """Two-variable stats and linear regression y = a + b*x with correlation r."""
    return _json(catch_calc(stats.stats_2var, x, y))


@mcp.tool()
def solve_linear(
    coefficients: Optional[list[list[float]]] = None,
    A: Optional[list[list[float]]] = None,
    b: Optional[list[float]] = None,
) -> str:
    """Solve linear system Ax=b. Pass augmented matrix as coefficients, or A and b."""
    return _json(catch_calc(solve.solve_linear, coefficients, A, b))


@mcp.tool()
def solve_root(
    expression: str,
    guess: Optional[float] = None,
    bracket: Optional[list[float]] = None,
    angle_mode: str = "rad",
) -> str:
    """Numeric root of RPN f(x)=0. Prefer bracket=[a,b] (Brent); else Newton with guess."""
    return _json(
        catch_calc(
            solve.solve_root,
            expression,
            "x",
            guess,
            bracket,
            angle_mode,
        )
    )


@mcp.tool()
def solve_polynomial(coefficients: list[float]) -> str:
    """Roots of polynomial a0 + a1 x + ... + an x^n. coefficients=[a0,...,an], degree 1–4."""
    return _json(catch_calc(solve.solve_polynomial, coefficients))


@mcp.tool()
def base_convert(value: str, from_base: int, to_base: int) -> str:
    """Convert value between bases 2, 8, 10, 16 (32-bit)."""
    return _json(catch_calc(base_n.base_convert, value, from_base, to_base))


@mcp.tool()
def base_arith(op: str, a: str, b: Optional[str] = None, base: int = 10) -> str:
    """BASE-N arithmetic: add,sub,mul,div,and,or,xor,not in the given base."""
    return _json(catch_calc(base_n.base_arith, op, a, b, base))


@mcp.tool()
def differentiate(
    expression: str,
    at: float,
    angle_mode: str = "rad",
    h: Optional[float] = None,
) -> str:
    """Numerical d/dx of RPN expression in x at a point (central difference)."""
    return _json(catch_calc(calculus.differentiate, expression, at, angle_mode, h))


@mcp.tool()
def integrate(
    expression: str,
    lower: float,
    upper: float,
    angle_mode: str = "rad",
    tol: float = 1e-10,
) -> str:
    """Numerical definite integral of RPN f(x) from lower to upper (adaptive Simpson)."""
    return _json(catch_calc(calculus.integrate, expression, lower, upper, angle_mode, tol))


@mcp.tool()
def convert_unit(
    value: float,
    conversion_id: Optional[str] = None,
    from_unit: Optional[str] = None,
    to_unit: Optional[str] = None,
) -> str:
    """Convert value using conversion_id or from_unit/to_unit. See list_unit_conversions."""
    return _json(catch_calc(units.convert_unit, value, conversion_id, from_unit, to_unit))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
