"""Numerical differentiation and adaptive Simpson integration of RPN f(x)."""

from __future__ import annotations

import math
from typing import Any

from mcp_calculator.errors import CalcError, ok
from mcp_calculator.rpn import eval_at

MAX_DEPTH = 40
MAX_EVALS = 100_000


def differentiate(
    expression: str,
    at: float,
    angle_mode: str = "rad",
    h: float | None = None,
) -> dict[str, Any]:
    x = float(at)
    if h is None:
        h = (1.0 + abs(x)) * (1e-16) ** (1 / 3)
    else:
        h = float(h)
        if not math.isfinite(h) or h == 0.0:
            raise CalcError(
                "invalid_data",
                "h must be a finite non-zero step size",
                "Omit h for an automatic step, or pass a small positive value e.g. 1e-6.",
            )
    try:
        fp = eval_at(expression, x + h, angle_mode)
        fm = eval_at(expression, x - h, angle_mode)
    except CalcError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise CalcError(
            "domain_error",
            f"Cannot evaluate expression near x={x}: {exc}",
            "Ensure the RPN expression in x is defined around the point.",
        ) from exc
    deriv = (fp - fm) / (2 * h)
    # rough estimate via second difference
    f0 = eval_at(expression, x, angle_mode)
    est_trunc = abs(fp - 2 * f0 + fm) / (h * h) * h * h / 6  # order-of-magnitude
    if not math.isfinite(deriv):
        raise CalcError(
            "overflow",
            "Derivative not finite",
            "Try a different h or check the expression domain.",
        )
    return ok(
        derivative=deriv,
        at=x,
        h=h,
        truncation_est=est_trunc,
        expression=expression,
        angle_mode=angle_mode,
    )


def integrate(
    expression: str,
    lower: float,
    upper: float,
    angle_mode: str = "rad",
    tol: float = 1e-10,
) -> dict[str, Any]:
    a, b = float(lower), float(upper)
    tol = float(tol)
    if not math.isfinite(tol) or tol <= 0:
        raise CalcError(
            "invalid_data",
            "tol must be a finite positive number",
            "Pass tol > 0, e.g. 1e-10.",
        )
    if a == b:
        return ok(integral=0.0, lower=a, upper=b, error_est=0.0, expression=expression)

    evals = [0]

    def f(x: float) -> float:
        evals[0] += 1
        if evals[0] > MAX_EVALS:
            raise CalcError(
                "convergence_failed",
                "Integration exceeded evaluation budget",
                "Widen tol or simplify the integrand.",
            )
        return eval_at(expression, x, angle_mode)

    def simpson(fa, fm, fb, h):
        return (h / 6.0) * (fa + 4 * fm + fb)

    def adapt(l, r, fl, fr, depth) -> tuple[float, float]:
        m = 0.5 * (l + r)
        fm = f(m)
        h = r - l
        whole = simpson(fl, fm, fr, h)
        lm = 0.5 * (l + m)
        rm = 0.5 * (m + r)
        flm, frm = f(lm), f(rm)
        left = simpson(fl, flm, fm, h / 2)
        right = simpson(fm, frm, fr, h / 2)
        delta = left + right - whole
        if depth <= 0:
            raise CalcError(
                "convergence_failed",
                "Adaptive Simpson hit max depth",
                "Increase tol or check for singularities in the interval.",
            )
        if abs(delta) <= 15 * tol * (abs(r - l) / abs(b - a) if b != a else 1):
            return left + right + delta / 15.0, abs(delta) / 15.0
        il, el = adapt(l, m, fl, fm, depth - 1)
        ir, er = adapt(m, r, fm, fr, depth - 1)
        return il + ir, el + er

    # handle reversed limits
    sign = 1.0
    if b < a:
        a, b = b, a
        sign = -1.0

    fa, fb = f(a), f(b)
    integral, err = adapt(a, b, fa, fb, MAX_DEPTH)
    return ok(
        integral=sign * integral,
        lower=float(lower),
        upper=float(upper),
        error_est=err,
        evaluations=evals[0],
        expression=expression,
        angle_mode=angle_mode,
    )
