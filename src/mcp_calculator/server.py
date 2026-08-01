"""MCP server: scientific calculator tools for agent numeric verification."""

from __future__ import annotations

import json
from typing import Any, Optional

from mcp.server.mcpserver import MCPServer

from mcp_calculator import base_n, calculus, matrix, solve, stats, units
from mcp_calculator.calc_extra import (
    decimal_to_dms,
    dms_to_decimal,
    engineering_format as _engineering_format,
    engineering_shift as _engineering_shift,
    evaluate_with_form,
    factorize as _factorize,
    pol as _pol,
    product as _product,
    rec as _rec,
    summation as _summation,
    table as _table,
)
from mcp_calculator.constants import list_constants as _list_constants
from mcp_calculator.distribution import distribution as _distribution
from mcp_calculator.errors import catch_calc, fail
from mcp_calculator.list_finance import finance_tvm as _finance_tvm
from mcp_calculator.list_finance import list_op as _list_op
from mcp_calculator.modes_extra import solve_inequality as _solve_inequality
from mcp_calculator.modes_extra import solve_ratio as _solve_ratio
from mcp_calculator.ops import list_operations as _list_operations
from mcp_calculator.stats_test import stats_test as _stats_test
from mcp_calculator.units import list_unit_conversions as _list_units

mcp = MCPServer(
    "mcp-calculator",
    instructions=(
        "Scientific calculator MCP. Always call a tool for numbers — never invent results. "
        "Menu/editor choices are tool parameters.\n"
        "Routing:\n"
        "- Arithmetic/trig/complex/eng suffixes/∠/°: evaluate "
        "(variables bindings; eng_symbols; complex_form=rectangular|polar). "
        "Do not use evaluate for matrices, stats lists, BASE-N, TVM, or unit tables.\n"
        "- Derivative/integral/fmin/fmax/Σ/Π/factorize/Pol/Rec/DMS/table: "
        "differentiate, integrate, fmin, fmax, summation, product, factorize, pol, rec, "
        "dms_to_decimal, decimal_to_dms, table.\n"
        "- Engineering display helpers: eng_format, eng_shift (or eng suffixes / engshift in evaluate).\n"
        "- Base-N (32-bit fixed): base_convert, base_arith (ops incl. neg, xnor).\n"
        "- Matrix/vector: matrix_op (add/sub/mul/det/inv/ref/rref/eigen/dot/cross/norm/angle/unit/identity).\n"
        "- 1-VAR / Norm Dist PQR: stats_1var (optional freq, norm_x→t/P/Q/R).\n"
        "- Regression: stats_2var (model=linear|quadratic|…; predict_y_at/predict_x_at).\n"
        "- Hypothesis tests: stats_test (type=z_test|t_test|2_samp_t_test|1_prop_z_test|"
        "2_prop_z_test|anova|linreg_ttest).\n"
        "- Distributions: distribution (type=normal_pd/cd|inverse_normal|binomial_*|"
        "poisson_*|geometric_*|t_*|chi2_*|f_*|norm_p/q/r; pass all vars for that type).\n"
        "- EQN: solve_linear, solve_polynomial, solve_root; Inequality: solve_inequality; "
        "Ratio: solve_ratio.\n"
        "- LIST: list_op (seq|cumsum|sort_a|sort_d|delta).\n"
        "- Finance TVM: finance_tvm (solve_for N|I|PV|PMT|FV; provide the other four).\n"
        "- Units: convert_unit; discover ids via list_unit_conversions.\n"
        "- Discovery: list_operations, list_constants, list_unit_conversions.\n"
        "Defaults: angle_mode=rad except pol/rec default deg. Base-N width is not selectable.\n"
        "On ok:false: read message and hint; use example and did_you_mean if present; "
        "call discovery tools for unknown names; fix arguments and retry."
    ),
)


def _json(data: dict[str, Any]) -> str:
    try:
        return json.dumps(data, allow_nan=False)
    except (ValueError, TypeError):
        # Tool boundary must never raise; non-finite slips become structured errors.
        return json.dumps(
            fail(
                "overflow",
                "Result is not JSON-serializable (non-finite or invalid type)",
                "Avoid ±Infinity/NaN; check domain. Call list_constants for finite constants.",
            ),
            allow_nan=False,
        )


@mcp.tool()
def evaluate(
    expression: str,
    angle_mode: str = "rad",
    complex_form: str = "rectangular",
    variables: Optional[dict[str, float]] = None,
    eng_symbols: bool = False,
) -> str:
    """When: ordinary infix maths (real/complex), trig, powers, eng suffixes, angle suffixes, polar ∠.
    Not for matrices, stats lists, BASE-N, TVM, or unit conversion tables.
    Params: expression (required); angle_mode=rad|deg|grad (default rad);
    complex_form=rectangular|polar; variables={name:float}; eng_symbols=bool.
    Example: expression=\"sin(30°)\", angle_mode=\"rad\"; or \"500k+10M\"; or \"2∠90\" with angle_mode=\"deg\".
    """
    return _json(
        catch_calc(
            evaluate_with_form,
            expression,
            angle_mode,
            complex_form,
            variables,
            eng_symbols,
        )
    )


@mcp.tool()
def list_operations() -> str:
    """When: unknown function/operator name after evaluate unknown_token, or exploring arity.
    Params: none.
    Example: call with no args → operations[{name,arity,description,angle_sensitive}].
    """
    return _json({"ok": True, "operations": _list_operations()})


@mcp.tool()
def list_constants() -> str:
    """When: need CODATA/math constant names (pi, e, qe, …) usable in evaluate.
    Params: none.
    Example: call with no args → constants[{name,value,unit,…}].
    """
    return _json({"ok": True, "constants": _list_constants()})


@mcp.tool()
def list_unit_conversions() -> str:
    """When: before convert_unit, or unknown conversion_id / unit pair.
    Params: none.
    Example: call with no args → conversions[{id,from,to,…}].
    """
    return _json({"ok": True, "conversions": _list_units()})


@mcp.tool()
def matrix_op(
    op: str,
    matrices: Optional[list[Any]] = None,
    vector: Optional[list[float]] = None,
    n: Optional[int] = None,
    angle_mode: str = "rad",
) -> str:
    """When: matrix/vector algebra (not infix evaluate).
    Params: op=add|sub|mul|transpose|det|inv|identity|ref|rref|eigen|dot|cross|norm|angle|unit;
    matrices=[A] or [A,B]; vector=[…] for norm/unit; n for identity; angle_mode for angle.
    Example: op=\"det\", matrices=[[[1,2],[3,4]]].
    """
    return _json(catch_calc(matrix.matrix_op, op, matrices, vector, n, angle_mode))


@mcp.tool()
def stats_1var(
    data: list[float],
    freq: Optional[list[float]] = None,
    norm_x: Optional[float] = None,
) -> str:
    """When: one-variable summary stats, or STAT Norm Dist t/P/Q/R from a data list.
    Params: data (required); optional freq (same length); optional norm_x → adds t,P,Q,R
    (t=(x−mean)/σ_pop; P:−∞→t, Q:0→t, R:t→+∞).
    Example: data=[1,2,3,4,5], norm_x=4.
    """
    return _json(catch_calc(stats.stats_1var, data, freq, norm_x))


@mcp.tool()
def stats_2var(
    x: list[float],
    y: list[float],
    model: str = "linear",
    freq: Optional[list[float]] = None,
    predict_y_at: Optional[float] = None,
    predict_x_at: Optional[float] = None,
) -> str:
    """When: paired (x,y) stats and regression — not single-list stats_1var.
    Params: x,y equal length; model=linear|quadratic|logarithmic|exp|abexp|power|inverse|
    cubic|quartic|logistic|medmed (default linear); optional freq, predict_y_at, predict_x_at.
    Example: x=[1,2,3], y=[2,4,6], model=\"linear\".
    """
    return _json(
        catch_calc(
            stats.stats_2var,
            x,
            y,
            model,
            freq,
            predict_y_at,
            predict_x_at,
        )
    )


@mcp.tool()
def solve_linear(
    coefficients: Optional[list[list[float]]] = None,
    A: Optional[list[list[float]]] = None,
    b: Optional[list[float]] = None,
) -> str:
    """When: square linear system Ax=b (not polynomial roots or f(x)=0).
    Params: either A (n×n) and b (len n), or coefficients as augmented n×(n+1). Max n=32.
    Example: A=[[2,1],[1,3]], b=[1,2].
    """
    return _json(catch_calc(solve.solve_linear, coefficients, A, b))


@mcp.tool()
def solve_root(
    expression: str,
    guess: Optional[float] = None,
    bracket: Optional[list[float]] = None,
    angle_mode: str = "rad",
) -> str:
    """When: numeric root of infix f(x)=0 (prefer over guessing).
    Params: expression in x; prefer bracket=[a,b]; else guess; angle_mode for trig in f.
    Example: expression=\"x^2-2\", bracket=[0,2].
    """
    return _json(
        catch_calc(solve.solve_root, expression, "x", guess, bracket, angle_mode)
    )


@mcp.tool()
def solve_polynomial(
    coefficients: list[float],
    allow_complex: bool = True,
) -> str:
    """When: roots of a polynomial a0+…+an x^n (degree 1–4), not general f(x).
    Params: coefficients=[a0,...,an]; allow_complex=bool (default true).
    Example: coefficients=[-2,0,1] for x^2-2=0.
    """
    return _json(catch_calc(solve.solve_polynomial, coefficients, allow_complex))


@mcp.tool()
def base_convert(value: str, from_base: int, to_base: int) -> str:
    """When: convert an integer string between bases 2/8/10/16 (32-bit two's complement fixed).
    Params: value (digit string, no leading '-'; use FFFFFFFF-style for negatives);
    from_base, to_base in {2,8,10,16}.
    Example: value=\"FF\", from_base=16, to_base=10.
    """
    return _json(catch_calc(base_n.base_convert, value, from_base, to_base))


@mcp.tool()
def base_arith(op: str, a: str, b: Optional[str] = None, base: int = 10) -> str:
    """When: integer/bitwise arithmetic in a chosen base (32-bit), not floating evaluate.
    Params: op=add|sub|mul|div|and|or|xor|xnor|not|neg; a; b (except not/neg); base=2|8|10|16.
    Example: op=\"add\", a=\"A\", b=\"5\", base=16.
    """
    return _json(catch_calc(base_n.base_arith, op, a, b, base))


@mcp.tool()
def differentiate(
    expression: str,
    at: float,
    angle_mode: str = "rad",
    h: Optional[float] = None,
) -> str:
    """When: numerical derivative df/dx of infix f(x) at a point (not symbolic).
    Params: expression in x; at; angle_mode; optional h step.
    Example: expression=\"x^3\", at=2.
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
    """When: numerical definite integral of infix f(x) on [lower, upper].
    Params: expression in x; lower; upper; angle_mode; tol (default 1e-10).
    Example: expression=\"x^2\", lower=0, upper=1.
    """
    return _json(
        catch_calc(calculus.integrate, expression, lower, upper, angle_mode, tol)
    )


@mcp.tool()
def summation(
    expression: str,
    start: int,
    end: int,
    angle_mode: str = "rad",
) -> str:
    """When: discrete sum Σ f(x) for integer x from start to end inclusive.
    Params: expression in x; start; end; angle_mode.
    Example: expression=\"x+1\", start=1, end=5.
    """
    return _json(catch_calc(_summation, expression, start, end, "x", angle_mode))


@mcp.tool()
def product(
    expression: str,
    start: int,
    end: int,
    angle_mode: str = "rad",
) -> str:
    """When: discrete product Π f(x) for integer x from start to end inclusive.
    Params: expression in x; start; end; angle_mode.
    Example: expression=\"x\", start=1, end=4 → 24.
    """
    return _json(catch_calc(_product, expression, start, end, "x", angle_mode))


@mcp.tool()
def factorize(n: float) -> str:
    """When: prime factorization of a positive integer (not evaluate fact()).
    Params: n (positive integer, ≤10 digits).
    Example: n=12 → factors with multiplicity.
    """
    return _json(catch_calc(_factorize, n))


@mcp.tool()
def fmin(
    expression: str,
    lower: float,
    upper: float,
    angle_mode: str = "rad",
    tol: float = 1e-10,
) -> str:
    """When: approximate minimum of infix f(x) on a closed interval.
    Params: expression in x; lower; upper; angle_mode; tol.
    Example: expression=\"(x-1)^2\", lower=0, upper=2.
    """
    return _json(catch_calc(calculus.fmin, expression, lower, upper, angle_mode, tol))


@mcp.tool()
def fmax(
    expression: str,
    lower: float,
    upper: float,
    angle_mode: str = "rad",
    tol: float = 1e-10,
) -> str:
    """When: approximate maximum of infix f(x) on a closed interval.
    Params: expression in x; lower; upper; angle_mode; tol.
    Example: expression=\"-(x-1)^2\", lower=0, upper=2.
    """
    return _json(catch_calc(calculus.fmax, expression, lower, upper, angle_mode, tol))


@mcp.tool()
def pol(x: float, y: float, angle_mode: str = "deg") -> str:
    """When: convert rectangular (x,y) to polar (r,θ). Prefer over manual atan2 for this mode.
    Params: x, y; angle_mode for θ (default deg).
    Example: x=2, y=2, angle_mode=\"deg\" → r≈2.828, θ=45.
    """
    return _json(catch_calc(_pol, x, y, angle_mode))


@mcp.tool()
def rec(r: float, theta: float, angle_mode: str = "deg") -> str:
    """When: convert polar (r,θ) to rectangular (x,y).
    Params: r, theta; angle_mode for θ (default deg).
    Example: r=2, theta=90, angle_mode=\"deg\".
    """
    return _json(catch_calc(_rec, r, theta, angle_mode))


@mcp.tool()
def dms_to_decimal(
    degrees: float,
    minutes: float = 0.0,
    seconds: float = 0.0,
) -> str:
    """When: sexagesimal ° ′ ″ → decimal degrees.
    Params: degrees; optional minutes, seconds (default 0).
    Example: degrees=10, minutes=30, seconds=0 → 10.5.
    """
    return _json(catch_calc(dms_to_decimal, degrees, minutes, seconds))


@mcp.tool()
def decimal_to_dms(decimal: float) -> str:
    """When: decimal degrees → ° ′ ″ components.
    Params: decimal.
    Example: decimal=10.5 → degrees=10, minutes=30, seconds=0.
    """
    return _json(catch_calc(decimal_to_dms, decimal))


@mcp.tool()
def convert_unit(
    value: float,
    conversion_id: Optional[str] = None,
    from_unit: Optional[str] = None,
    to_unit: Optional[str] = None,
) -> str:
    """When: convert between listed measurement units (not free-form dimensional analysis).
    Params: value; either conversion_id OR from_unit+to_unit. Call list_unit_conversions first if unsure.
    Example: value=1, conversion_id=\"mile_to_km\".
    """
    return _json(catch_calc(units.convert_unit, value, conversion_id, from_unit, to_unit))


@mcp.tool()
def distribution(
    type: str,
    x: Optional[Any] = None,
    sigma: Optional[float] = None,
    mu: Optional[float] = None,
    lower: Optional[float] = None,
    upper: Optional[float] = None,
    area: Optional[float] = None,
    n: Optional[int] = None,
    p: Optional[float] = None,
    lambda_: Optional[float] = None,
    df: Optional[float] = None,
    df1: Optional[float] = None,
    df2: Optional[float] = None,
    tail: str = "left",
) -> str:
    """When: probability densities/CDFs/inverses (DISTR), or norm_p/q/r for standardized t.
    For Norm Dist from a data list use stats_1var(norm_x=…) instead.
    Params: type selects screen — pass every variable that type needs.
    Types: normal_pd (x,sigma,mu), normal_cd (lower,upper,sigma,mu),
    inverse_normal (area,sigma,mu,tail), binomial_pd/cd (x,n,p), inverse_binomial,
    poisson_*, geometric_*, t_pd/cd, chi2_pd/cd, f_pd/cd, norm_p/q/r (x=t).
    Example: type=\"normal_pd\", x=36, sigma=2, mu=35.
    """
    return _json(
        catch_calc(
            _distribution,
            type,
            x,
            sigma,
            mu,
            lower,
            upper,
            area,
            n,
            p,
            lambda_,
            df,
            df1,
            df2,
            tail,
        )
    )


@mcp.tool()
def eng_format(value: float) -> str:
    """When: show a real number in engineering form (significand + SI symbol). Prefer evaluate eng_symbols for expression results.
    Params: value.
    Example: value=12345 → display \"12.345k\".
    """
    return _json(catch_calc(_engineering_format, value))


@mcp.tool()
def eng_shift(value: float, steps: int = 1) -> str:
    """When: ENG / ENG← style shift: multiply by 1000^steps (also engshift(x,n) in evaluate).
    Params: value; steps (default 1; negative shifts down).
    Example: value=1234, steps=1 → 1.234e6-style shift.
    """
    return _json(catch_calc(_engineering_shift, value, steps))


@mcp.tool()
def stats_test(
    type: str,
    data: Optional[list[float]] = None,
    data2: Optional[list[float]] = None,
    mu0: Optional[float] = None,
    sigma: Optional[float] = None,
    x: Optional[float] = None,
    n: Optional[int] = None,
    p0: Optional[float] = None,
    x1: Optional[float] = None,
    n1: Optional[int] = None,
    x2: Optional[float] = None,
    n2: Optional[int] = None,
    lists: Optional[list[list[float]]] = None,
    alternative: str = "≠",
    pooled: bool = False,
) -> str:
    """When: STAT hypothesis tests (not descriptive stats_1var / regression stats_2var).
    Params: type=z_test|t_test|2_samp_t_test|1_prop_z_test|2_prop_z_test|anova|linreg_ttest;
    pass editor fields for that type (data/sigma/mu0, x/n/p0, lists for ANOVA, …);
    alternative; pooled for two-sample.
    Example: type=\"t_test\", data=[1,2,3], mu0=0.
    """
    return _json(
        catch_calc(
            _stats_test,
            type,
            data=data,
            data2=data2,
            mu0=mu0,
            sigma=sigma,
            x=x,
            n=n,
            p0=p0,
            x1=x1,
            n1=n1,
            x2=x2,
            n2=n2,
            lists=lists,
            alternative=alternative,
            pooled=pooled,
        )
    )


@mcp.tool()
def list_op(
    op: str,
    data: Optional[list[float]] = None,
    expression: Optional[str] = None,
    start: Optional[float] = None,
    end: Optional[float] = None,
    step: float = 1.0,
    angle_mode: str = "rad",
) -> str:
    """When: LIST utilities (sequence, cumsum, sort, ΔList) — not stats summaries.
    Params: op=seq|cumsum|sort_a|sort_d|delta; seq needs expression,start,end[,step];
    others need data; angle_mode for seq expressions.
    Example: op=\"cumsum\", data=[1,2,3]; or op=\"seq\", expression=\"2*x\", start=1, end=3.
    """
    return _json(
        catch_calc(
            _list_op,
            op,
            data=data,
            expression=expression,
            start=start,
            end=end,
            step=step,
            angle_mode=angle_mode,
        )
    )


@mcp.tool()
def finance_tvm(
    solve_for: str,
    N: Optional[float] = None,
    I: Optional[float] = None,
    PV: Optional[float] = None,
    PMT: Optional[float] = None,
    FV: Optional[float] = None,
    P_Y: float = 1.0,
    C_Y: Optional[float] = None,
    begin: bool = False,
) -> str:
    """When: time-value-of-money (loan/annuity) — solve one of N,I,PV,PMT,FV.
    Params: solve_for=N|I|PV|PMT|FV; provide the other four; I is annual %;
    P_Y payments/year (default 1); C_Y compounds/year (default=P_Y); begin=True for BGN.
    Signs: outflow negative / inflow positive, kept consistent.
    Example: solve_for=\"PMT\", N=12, I=6, PV=-1000, FV=0.
    """
    return _json(
        catch_calc(
            _finance_tvm,
            solve_for,
            N=N,
            I=I,
            PV=PV,
            PMT=PMT,
            FV=FV,
            P_Y=P_Y,
            C_Y=C_Y,
            begin=begin,
        )
    )


@mcp.tool()
def table(
    expression: str,
    start: float,
    end: float,
    step: float,
    expression2: Optional[str] = None,
    angle_mode: str = "rad",
) -> str:
    """When: generate f(x) [and optional g(x)] values from start to end by step.
    Params: expression in x; start; end; step; optional expression2; angle_mode.
    Example: expression=\"2*x\", start=0, end=2, step=1, expression2=\"x^2\".
    """
    return _json(
        catch_calc(_table, expression, start, end, step, expression2, angle_mode)
    )


@mcp.tool()
def solve_inequality(coefficients: list[float], relation: str) -> str:
    """When: solve polynomial inequality a0+…+an x^n (degree 1–4).
    Params: coefficients=[a0,...,an]; relation=\">\"|\">=\"|\"<\"|\"<=\".
    Example: coefficients=[-1,1], relation=\">\" for x-1>0.
    """
    return _json(catch_calc(_solve_inequality, coefficients, relation))


@mcp.tool()
def solve_ratio(
    a: Optional[float] = None,
    b: Optional[float] = None,
    c: Optional[float] = None,
    d: Optional[float] = None,
    solve_for: str = "x",
) -> str:
    """When: proportion a:b = c:d with one unknown.
    Params: three of a,b,c,d known; solve_for=a|b|c|d|x (x = the single missing slot).
    Example: a=2, b=3, d=6, solve_for=\"c\".
    """
    return _json(catch_calc(_solve_ratio, a, b, c, d, solve_for))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
