"""scientific calculator Inequality and Ratio modes."""

from __future__ import annotations

import math
from typing import Any

from mcp_calculator.errors import CalcError, ok
from mcp_calculator.solve import solve_polynomial


RELATIONS = {">", ">=", "<", "<=", "＞", "≥", "＜", "≤"}


def _norm_rel(relation: str) -> str:
    r = (relation or "").strip()
    r = {"＞": ">", "≥": ">=", "＜": "<", "≤": "<="}.get(r, r)
    if r not in {">", ">=", "<", "<="}:
        raise CalcError(
            "invalid_data",
            f"Unknown relation {relation!r}",
            'Use ">", ">=", "<", or "<=" (scientific calculator Inequality Type).',
            example='relation=">="',
        )
    return r


def solve_inequality(
    coefficients: list[float],
    relation: str,
) -> dict[str, Any]:
    """Solve polynomial inequality a0 + a1 x + ... >= 0 etc. (scientific calculator Inequality).

    coefficients are low-to-high [a0,...,an], degree 1–4.
    """
    rel = _norm_rel(relation)
    if not coefficients or len(coefficients) - 1 < 1 or len(coefficients) - 1 > 4:
        raise CalcError(
            "invalid_data",
            "Provide coefficients for degree 1–4",
            "Pass [a0,...,an] like Equation/Inequality Coefficient Editor.",
        )
    # Critical points = real roots of the polynomial
    poly = solve_polynomial(coefficients)
    roots_raw = poly["roots"]
    real_roots: list[float] = []
    for rt in roots_raw:
        if isinstance(rt, dict):
            continue
        real_roots.append(float(rt))
    real_roots = sorted(set(round(r, 12) for r in real_roots))  # unique-ish

    def f(x: float) -> float:
        s = 0.0
        for i, c in enumerate(coefficients):
            s += float(c) * (x**i)
        return s

    # Test intervals (-inf, r0), (r0,r1), ..., (rn, +inf)
    points = real_roots
    tests: list[float] = []
    if not points:
        tests = [0.0]
    else:
        tests.append(points[0] - 1.0)
        for i in range(len(points) - 1):
            tests.append(0.5 * (points[i] + points[i + 1]))
        tests.append(points[-1] + 1.0)

    def satisfies(val: float) -> bool:
        if rel == ">":
            return val > 0
        if rel == ">=":
            return val >= 0
        if rel == "<":
            return val < 0
        return val <= 0

    intervals: list[dict[str, Any]] = []
    # Build interval descriptions
    bounds = [-math.inf] + points + [math.inf]
    for i in range(len(bounds) - 1):
        lo, hi = bounds[i], bounds[i + 1]
        mid = tests[i]
        ok_open = satisfies(f(mid))
        include_lo = lo in points and satisfies(0.0) and rel in (">=", "<=")
        include_hi = hi in points and satisfies(0.0) and rel in (">=", "<=")
        # At a root f=0; for strict inequalities roots excluded
        if ok_open or (rel in (">=", "<=") and (include_lo or include_hi)):
            if not ok_open and rel in (">=", "<="):
                # only roots
                if include_lo and lo != -math.inf:
                    intervals.append({"type": "point", "x": lo})
                continue
            intervals.append(
                {
                    "type": "interval",
                    "low": None if lo == -math.inf else lo,
                    "high": None if hi == math.inf else hi,
                    "include_low": bool(include_lo and lo != -math.inf),
                    "include_high": bool(include_hi and hi != math.inf),
                }
            )

    return ok(
        coefficients=[float(c) for c in coefficients],
        relation=rel,
        roots=real_roots,
        solution=intervals,
        degree=len(coefficients) - 1,
    )


def solve_ratio(
    a: float | None = None,
    b: float | None = None,
    c: float | None = None,
    d: float | None = None,
    solve_for: str = "x",
) -> dict[str, Any]:
    """scientific calculator Ratio: A:B = X:D or A:B = C:X (and permutations via solve_for).

    Provide three of a,b,c,d and set solve_for to the missing one among a,b,c,d
    (scientific calculator uses X for the unknown; map x→ the missing slot via solve_for).
    Convention: ratio a:b = c:d, so a/b = c/d ⇒ a*d = b*c.
    """
    key = (solve_for or "x").lower().strip()
    vals = {"a": a, "b": b, "c": c, "d": d}
    # Allow solve_for 'x' meaning the single None among a,b,c,d
    if key == "x":
        missing = [k for k, v in vals.items() if v is None]
        if len(missing) != 1:
            raise CalcError(
                "invalid_data",
                "Provide exactly three of a,b,c,d when solve_for='x'",
                "scientific calculator Ratio: enter known values; X is the unknown.",
            )
        key = missing[0]
    if key not in vals:
        raise CalcError(
            "invalid_data",
            f"solve_for must be a, b, c, d, or x; got {solve_for!r}",
            "Example: a=2, b=3, d=6, solve_for='c' for 2:3 = C:6.",
        )
    known = {k: float(v) for k, v in vals.items() if k != key and v is not None}
    if len(known) != 3:
        raise CalcError(
            "invalid_data",
            "Provide the other three of a,b,c,d",
            "Ratio needs three known values and one unknown.",
        )
    # a/b = c/d
    if key == "a":
        if known["b"] == 0:
            raise CalcError("division_by_zero", "b is zero", "b≠0.")
        x = known["b"] * known["c"] / known["d"]
    elif key == "b":
        if known["a"] == 0:
            raise CalcError("domain_error", "a is zero", "Check inputs.")
        x = known["a"] * known["d"] / known["c"]
    elif key == "c":
        if known["d"] == 0:
            raise CalcError("division_by_zero", "d is zero", "d≠0.")
        x = known["a"] * known["d"] / known["b"]
    else:  # d
        if known["c"] == 0:
            raise CalcError("division_by_zero", "c is zero", "c≠0.")
        x = known["b"] * known["c"] / known["a"]
    result = {"a": a, "b": b, "c": c, "d": d}
    result[key] = x
    return ok(
        a=result["a"],
        b=result["b"],
        c=result["c"],
        d=result["d"],
        solve_for=key,
        value=x,
    )
