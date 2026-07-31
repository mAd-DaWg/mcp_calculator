"""Descriptive statistics and linear regression."""

from __future__ import annotations

import math
from typing import Any

from mcp_calculator.errors import CalcError, ok

MAX_N = 100_000


def _data(xs: Any, name: str = "data") -> list[float]:
    if not isinstance(xs, list) or not xs:
        raise CalcError(
            "invalid_data",
            f"{name} must be a non-empty list of numbers",
            "Pass e.g. [1,2,3,4].",
        )
    if len(xs) > MAX_N:
        raise CalcError(
            "overflow",
            f"Too many data points (>{MAX_N})",
            f"Use at most {MAX_N} points.",
        )
    try:
        return [float(x) for x in xs]
    except (TypeError, ValueError) as exc:
        raise CalcError(
            "invalid_data",
            f"{name} contains a non-numeric value",
            "Ensure every element is a number.",
        ) from exc


def stats_1var(data: list[Any]) -> dict[str, Any]:
    xs = _data(data)
    n = len(xs)
    s = sum(xs)
    ssq = sum(x * x for x in xs)
    mean = s / n
    # population and sample variance
    pop_var = sum((x - mean) ** 2 for x in xs) / n
    sample_var = sum((x - mean) ** 2 for x in xs) / (n - 1) if n > 1 else float("nan")
    sorted_x = sorted(xs)
    if n % 2 == 1:
        median = sorted_x[n // 2]
    else:
        median = 0.5 * (sorted_x[n // 2 - 1] + sorted_x[n // 2])
    return ok(
        n=n,
        mean=mean,
        sum=s,
        sumsq=ssq,
        min=min(xs),
        max=max(xs),
        median=median,
        var_pop=pop_var,
        var_sample=sample_var,
        std_pop=math.sqrt(pop_var),
        std_sample=math.sqrt(sample_var) if n > 1 else float("nan"),
    )


def stats_2var(x: list[Any], y: list[Any]) -> dict[str, Any]:
    xs, ys = _data(x, "x"), _data(y, "y")
    if len(xs) != len(ys):
        raise CalcError(
            "invalid_data",
            f"x and y lengths differ ({len(xs)} vs {len(ys)})",
            "Pass equal-length lists for x and y.",
        )
    n = len(xs)
    if n < 2:
        raise CalcError(
            "invalid_data",
            "Need at least 2 points for regression",
            "Provide at least two (x,y) pairs.",
        )
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((xi - mx) ** 2 for xi in xs)
    syy = sum((yi - my) ** 2 for yi in ys)
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(xs, ys))
    if sxx == 0:
        raise CalcError(
            "domain_error",
            "Cannot regress: all x values identical",
            "Provide varying x values.",
        )
    b = sxy / sxx  # slope
    a = my - b * mx  # intercept  y = a + b x
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else float("nan")
    return ok(
        n=n,
        a=a,
        b=b,
        r=r,
        mean_x=mx,
        mean_y=my,
        predict_at_mean=a + b * mx,
        equation="y = a + b*x",
    )
