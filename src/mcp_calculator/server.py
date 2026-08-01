"""MCP server: scientific calculator tools over stdio."""

from __future__ import annotations

import json
from typing import Any, Optional

from mcp.server.mcpserver import MCPServer

from mcp_calculator import base_n, calculus, matrix, solve, stats, units
from mcp_calculator.constants import list_constants as _list_constants
from mcp_calculator.errors import catch_calc
from mcp_calculator.infix import evaluate_infix
from mcp_calculator.ops import list_operations as _list_operations
from mcp_calculator.units import list_unit_conversions as _list_units

mcp = MCPServer(
    "mcp-calculator",
    instructions=(
        "Scientific calculator for verifying numeric work — do not invent answers; call these tools.\n"
        "Primary tool: evaluate with ordinary infix maths "
        "(e.g. 90+(40-30), sin(30), 2*pi, x^2-2). Not Reverse Polish Notation.\n"
        "Supports: + - * / ^ ** % ! parentheses, unary minus, functions like sin(x)/sqrt(x)/cmplx(a,b), "
        "constants (pi, e, qe, …), implicit multiply (2pi, 2x), variable x for calculus/roots.\n"
        "angle_mode on evaluate/trig/calculus/roots: rad (default), deg, or grad.\n"
        "All tools return a JSON string. Parse it. On ok:false, read message and hint, then retry.\n"
        "If unsure of a name, call list_operations, list_constants, or list_unit_conversions first.\n"
        "Pick the specialized tool when it fits: matrix_op, stats_*, solve_*, base_*, "
        "differentiate, integrate, convert_unit — do not reinvent those in evaluate alone."
    ),
)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, allow_nan=False)


@mcp.tool()
def evaluate(expression: str, angle_mode: str = "rad") -> str:
    """Main calculator: evaluate ordinary infix maths (real or complex).

    Use for arithmetic, trig, logs, factorials, complex numbers, and physics constants.
    Write normal expressions — e.g. 90+(40-30), sin(30), 2*pi, abs(cmplx(3,4)), 5!.
    Not RPN / postfix. angle_mode: rad|deg|grad (circular trig only).

    Returns JSON: ok, result, expression, angle_mode, rpn (internal form).
    On failure: ok:false with error, message, hint (and often example / did_you_mean).
    """
    def run():
        return evaluate_infix(expression, angle_mode=angle_mode)

    return _json(catch_calc(run))


@mcp.tool()
def list_operations() -> str:
    """Discover operators and function names usable inside evaluate / calculus / solve_root.

    Call when unsure whether a function exists or what arity it needs.
    Returns JSON: ok, operations[] each with name, arity, description, angle_sensitive.
    Infix usage: binary symbols (+, ^, …) or name(args) matching arity — e.g. sin(30), log(10,100), rand().
    """
    return _json({"ok": True, "operations": _list_operations()})


@mcp.tool()
def list_constants() -> str:
    """Discover math/physics constant names for use in infix expressions (CODATA 2022).

    Call when unsure of a constant token. Use names like pi, e, qe, c, NA inside evaluate.
    Note: e is Euler's number; elementary charge is qe. re is the real-part operator; r_e is electron radius.
    Returns JSON: ok, constants[] with name, value, unit, note, codata_year.
    """
    return _json({"ok": True, "constants": _list_constants()})


@mcp.tool()
def list_unit_conversions() -> str:
    """Discover supported unit conversion ids and from/to pairs for convert_unit.

    Call before convert_unit if you do not know a valid id (e.g. mile_to_km, C_to_F).
    Returns JSON: ok, conversions[] with id, from, to, and factor (or note for temperature).
    Only listed pairs work — no free-form dimensional analysis.
    """
    return _json({"ok": True, "conversions": _list_units()})


@mcp.tool()
def matrix_op(
    op: str,
    matrices: Optional[list[Any]] = None,
    vector: Optional[list[float]] = None,
    n: Optional[int] = None,
) -> str:
    """Matrix and vector algebra on small dense arrays (max dimension 32).

    op: add, sub, mul, transpose, det, inv, identity, rref, dot, cross, norm, angle.
    Matrices: pass matrices=[A] or matrices=[A,B] as nested lists of numbers.
    Vectors: for norm use vector=[…]; for dot/cross/angle pass two vectors in matrices.
    identity requires n (size). cross requires 3-vectors. angle result is in radians (unit=rad).

    Examples: det of [[1,2],[3,4]]; norm of [3,4]; identity n=2; cross [[1,0,0],[0,1,0]].
    Returns JSON: ok, op, result (and unit for angle).
    """
    return _json(catch_calc(matrix.matrix_op, op, matrices, vector, n))


@mcp.tool()
def stats_1var(data: list[float]) -> str:
    """One-variable descriptive statistics for a list of numbers (max 100000 points).

    Use to summarize a sample: count, mean, sum, sum of squares, min, max, median,
    population and sample variance/standard deviation.
    Pass data as a non-empty list of floats, e.g. [1,2,3,4].
    Returns JSON with fields n, mean, sum, sumsq, min, max, median, var_pop, var_sample, std_pop, std_sample.
    """
    return _json(catch_calc(stats.stats_1var, data))


@mcp.tool()
def stats_2var(x: list[float], y: list[float]) -> str:
    """Two-variable stats and ordinary least-squares linear regression.

    Fits y = a + b*x. Needs at least 2 points and equal-length x and y lists.
    Returns JSON: n, a (intercept), b (slope), r (correlation), mean_x, mean_y,
    predict_at_mean, equation.
    Example: x=[1,2,3], y=[2,4,6] → a=0, b=2, r=1.
    """
    return _json(catch_calc(stats.stats_2var, x, y))


@mcp.tool()
def solve_linear(
    coefficients: Optional[list[list[float]]] = None,
    A: Optional[list[list[float]]] = None,
    b: Optional[list[float]] = None,
) -> str:
    """Solve a square linear system Ax=b (unique solution when A is invertible; max n=32).

    Pass either:
    - A (n×n) and b (length n), e.g. A=[[2,1],[1,3]], b=[1,2], or
    - coefficients as an augmented matrix n×(n+1), each row [a_i1,…,a_in,b_i].

    Returns JSON: solution, residual, status (e.g. unique).
    """
    return _json(catch_calc(solve.solve_linear, coefficients, A, b))


@mcp.tool()
def solve_root(
    expression: str,
    guess: Optional[float] = None,
    bracket: Optional[list[float]] = None,
    angle_mode: str = "rad",
) -> str:
    """Find a real root of infix f(x)=0 (numeric, not symbolic).

    expression uses variable x, e.g. x^2-2 or sin(x)-0.5.
    Prefer bracket=[a,b] with a sign change (Brent). Otherwise pass guess for Newton.
    angle_mode: rad|deg|grad when the expression uses circular trig.

    Returns JSON: root, abs_f, iterations, method (brent|newton), expression, angle_mode.
    """
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
    """Find all roots of a polynomial a0 + a1*x + … + an*x^n (degree 1–4 only).

    Pass coefficients=[a0,…,an] with the constant term first.
    Example: x^2-2 → [-2, 0, 1]. Roots may be complex objects {re, im}.

    Returns JSON: degree, roots, coefficients.
    """
    return _json(catch_calc(solve.solve_polynomial, coefficients))


@mcp.tool()
def base_convert(value: str, from_base: int, to_base: int) -> str:
    """Convert an integer between bases 2, 8, 10, and 16 (32-bit two's complement).

    value is a digit string in from_base (e.g. FF in hex). For negatives use the unsigned
    bit pattern (e.g. FFFFFFFF), not a leading minus.
    Returns JSON: value (in to_base), decimal, decimal_unsigned, from_base, to_base, bits.
    Example: value=FF, from_base=16, to_base=10 → 255.
    """
    return _json(catch_calc(base_n.base_convert, value, from_base, to_base))


@mcp.tool()
def base_arith(op: str, a: str, b: Optional[str] = None, base: int = 10) -> str:
    """Integer arithmetic and bitwise ops on base-2/8/10/16 values (32-bit, wraps).

    op: add, sub, mul, div, and, or, xor, or not (not is unary — omit b).
    a and b are digit strings in the given base. div uses signed interpretation.
    Example: op=add, a=A, b=5, base=16 → F.
    Returns JSON: op, result, decimal_unsigned, base.
    """
    return _json(catch_calc(base_n.base_arith, op, a, b, base))


@mcp.tool()
def differentiate(
    expression: str,
    at: float,
    angle_mode: str = "rad",
    h: Optional[float] = None,
) -> str:
    """Approximate df/dx of an infix function of x at a point (central difference).

    Not symbolic differentiation — numerical check only. expression uses x, e.g. x^3 or sin(x).
    at is the evaluation point. Optional h overrides the automatic step size.
    Returns JSON: derivative, at, h, truncation_est, expression, angle_mode.
    """
    return _json(catch_calc(calculus.differentiate, expression, at, angle_mode, h))


@mcp.tool()
def integrate(
    expression: str,
    lower: float,
    upper: float,
    angle_mode: str = "rad",
    tol: float = 1e-10,
) -> str:
    """Approximate the definite integral of infix f(x) from lower to upper (adaptive Simpson).

    Not symbolic integration — numerical check only. expression uses x, e.g. x^2 or sin(x).
    Optional tol sets accuracy target (default 1e-10).
    Returns JSON: integral, lower, upper, error_est, evaluations, expression, angle_mode.
    """
    return _json(catch_calc(calculus.integrate, expression, lower, upper, angle_mode, tol))


@mcp.tool()
def convert_unit(
    value: float,
    conversion_id: Optional[str] = None,
    from_unit: Optional[str] = None,
    to_unit: Optional[str] = None,
) -> str:
    """Convert a number between listed measurement units (length, mass, temp, …).

    Pass conversion_id (e.g. mile_to_km, C_to_F) OR from_unit and to_unit.
    Call list_unit_conversions if you need a valid id/pair. Temperature uses affine formulas.
    Returns JSON: value (converted), from_unit, to_unit, conversion_id.
    """
    return _json(catch_calc(units.convert_unit, value, conversion_id, from_unit, to_unit))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
