"""Descriptive statistics and selectable regression models (scientific calculator STAT / STAT CALC)."""

from __future__ import annotations

import math
from typing import Any

from mcp_calculator.errors import CalcError, ok

MAX_N = 100_000

# scientific calculator STAT Select Type + graphing-calculator STAT CALC extras
MODELS = {
    "linear": "y = a + b*x",
    "quadratic": "y = a + b*x + c*x^2",
    "logarithmic": "y = a + b*ln(x)",
    "exp": "y = a*e^(b*x)",
    "abexp": "y = a*b^x",
    "power": "y = a*x^b",
    "inverse": "y = a + b/x",
    "cubic": "y = a*x^3 + b*x^2 + c*x + d",
    "quartic": "y = a*x^4 + b*x^3 + c*x^2 + d*x + e",
    "logistic": "y = c/(1+a*e^(-b*x))",
    "medmed": "y = a*x + b",
}


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


def _freq(freq: list[Any] | None, n: int) -> list[float]:
    if freq is None:
        return [1.0] * n
    fs = _data(freq, "freq")
    if len(fs) != n:
        raise CalcError(
            "invalid_data",
            f"freq length {len(fs)} != data length {n}",
            "Pass freq with the same length as x (and y).",
        )
    if any(f < 0 for f in fs):
        raise CalcError(
            "invalid_data",
            "Frequencies must be non-negative",
            "Use FREQ values >= 0 as on scientific calculator STAT.",
        )
    if sum(fs) <= 0:
        raise CalcError(
            "invalid_data",
            "Sum of frequencies must be positive",
            "Provide at least one positive frequency.",
        )
    return fs


def _expand(xs: list[float], fs: list[float]) -> list[float]:
    """Expand by integer frequencies when all freqs are integers; else weight later."""
    if all(abs(f - round(f)) < 1e-12 for f in fs):
        out: list[float] = []
        for x, f in zip(xs, fs):
            out.extend([x] * int(round(f)))
        if not out:
            raise CalcError("invalid_data", "No points after applying freq", "Check freq.")
        return out
    return xs  # weighted path uses fs directly


def _median(sorted_x: list[float]) -> float:
    m = len(sorted_x)
    if m == 0:
        raise CalcError("invalid_data", "Empty data for median", "Provide data.")
    if m % 2 == 1:
        return sorted_x[m // 2]
    return 0.5 * (sorted_x[m // 2 - 1] + sorted_x[m // 2])


def _quartiles(sorted_x: list[float]) -> tuple[float, float, float]:
    """scientific calculator-style: Q1/Q3 = medians of lower/upper halves (exclude overall median if odd n)."""
    n = len(sorted_x)
    med = _median(sorted_x)
    if n % 2 == 1:
        lower, upper = sorted_x[: n // 2], sorted_x[n // 2 + 1 :]
    else:
        lower, upper = sorted_x[: n // 2], sorted_x[n // 2 :]
    q1 = _median(lower) if lower else med
    q3 = _median(upper) if upper else med
    return q1, med, q3


def _mode(sorted_x: list[float]) -> list[float]:
    """Most frequent value(s); multimodal returns all modes sorted."""
    from collections import Counter

    counts = Counter(sorted_x)
    mx = max(counts.values())
    return sorted(v for v, c in counts.items() if c == mx)


def stats_1var(
    data: list[Any],
    freq: list[Any] | None = None,
    norm_x: float | None = None,
) -> dict[str, Any]:
    xs = _data(data)
    fs = _freq(freq, len(xs))
    n_eff = sum(fs)
    s = sum(x * f for x, f in zip(xs, fs))
    ssq = sum(x * x * f for x, f in zip(xs, fs))
    mean = s / n_eff
    pop_var = sum(f * (x - mean) ** 2 for x, f in zip(xs, fs)) / n_eff
    sample_var = (
        sum(f * (x - mean) ** 2 for x, f in zip(xs, fs)) / (n_eff - 1)
        if n_eff > 1
        else None
    )
    expanded = _expand(xs, fs)
    sorted_x = sorted(expanded)
    q1, median, q3 = _quartiles(sorted_x)
    modes = _mode(sorted_x)
    std_pop = math.sqrt(pop_var)
    out = ok(
        n=n_eff,
        mean=mean,
        sum=s,
        sumsq=ssq,
        min=min(xs),
        max=max(xs),
        q1=q1,
        median=median,
        q3=q3,
        mode=modes[0] if len(modes) == 1 else modes,
        modes=modes,
        var_pop=pop_var,
        var_sample=sample_var,
        std_pop=std_pop,
        std_sample=math.sqrt(sample_var) if sample_var is not None else None,
    )
    if norm_x is not None:
        # STAT Norm Dist: t = (x - x̄) / σx  (population σ)
        if std_pop == 0:
            raise CalcError(
                "domain_error",
                "Cannot compute normalized variate: σx is 0",
                "Provide data with non-zero population standard deviation.",
            )
        from mcp_calculator.distribution import norm_pqr

        t = (float(norm_x) - mean) / std_pop
        pqr = norm_pqr(t)
        out.update(norm_x=float(norm_x), t=t, P=pqr["P"], Q=pqr["Q"], R=pqr["R"])
    return out


def _linreg(xs: list[float], ys: list[float], fs: list[float]) -> tuple[float, float, float, float, float]:
    n = sum(fs)
    mx = sum(x * f for x, f in zip(xs, fs)) / n
    my = sum(y * f for y, f in zip(ys, fs)) / n
    sxx = sum(f * (x - mx) ** 2 for x, f in zip(xs, fs))
    syy = sum(f * (y - my) ** 2 for y, f in zip(ys, fs))
    sxy = sum(f * (x - mx) * (y - my) for x, y, f in zip(xs, ys, fs))
    if sxx == 0:
        raise CalcError(
            "domain_error",
            "Cannot regress: all x values identical",
            "Provide varying x values.",
        )
    b = sxy / sxx
    a = my - b * mx
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else None
    return a, b, r, mx, my


def _poly_fit(xs: list[float], ys: list[float], fs: list[float], degree: int) -> list[float]:
    """Weighted least squares polynomial y = c0 + c1 x + ... + cd x^d. Returns [c0..cd]."""
    n_pts = len(xs)
    if n_pts < degree + 1:
        raise CalcError(
            "invalid_data",
            f"Need at least {degree + 1} points for degree {degree}",
            f"Provide more (x,y) pairs.",
        )
    m = degree + 1
    # Normal equations A^T W A c = A^T W y
    ata = [[0.0] * m for _ in range(m)]
    aty = [0.0] * m
    for x, y, f in zip(xs, ys, fs):
        row = [x**k for k in range(m)]
        for i in range(m):
            aty[i] += f * row[i] * y
            for j in range(m):
                ata[i][j] += f * row[i] * row[j]
    # Gaussian eliminate
    aug = [ata[i][:] + [aty[i]] for i in range(m)]
    for col in range(m):
        pivot = max(range(col, m), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-14:
            raise CalcError(
                "domain_error",
                "Polynomial fit is singular for this data",
                "Check that x values vary enough for the model degree.",
            )
        aug[col], aug[pivot] = aug[pivot], aug[col]
        piv = aug[col][col]
        for j in range(col, m + 1):
            aug[col][j] /= piv
        for r in range(m):
            if r == col:
                continue
            factor = aug[r][col]
            for j in range(col, m + 1):
                aug[r][j] -= factor * aug[col][j]
    return [aug[i][m] for i in range(m)]


def _require_positive(vals: list[float], name: str) -> None:
    if any(v <= 0 for v in vals):
        raise CalcError(
            "domain_error",
            f"{name} must be positive for this regression model",
            f"Ensure every {name} > 0.",
        )


def stats_2var(
    x: list[Any],
    y: list[Any],
    model: str = "linear",
    freq: list[Any] | None = None,
    predict_y_at: float | None = None,
    predict_x_at: float | None = None,
) -> dict[str, Any]:
    model = (model or "linear").lower().strip()
    if model not in MODELS:
        raise CalcError(
            "invalid_data",
            f"Unknown regression model {model!r}",
            "Use linear, quadratic, logarithmic, exp, abexp, power, inverse, "
            "cubic, quartic, logistic, or medmed (scientific calculator STAT / STAT CALC).",
            example="model='logarithmic'",
        )
    xs, ys = _data(x, "x"), _data(y, "y")
    if len(xs) != len(ys):
        raise CalcError(
            "invalid_data",
            f"x and y lengths differ ({len(xs)} vs {len(ys)})",
            "Pass equal-length lists for x and y.",
        )
    fs = _freq(freq, len(xs))
    n = sum(fs)
    if n < 2 and model not in ("quadratic", "cubic", "quartic"):
        raise CalcError(
            "invalid_data",
            "Need at least 2 points for regression",
            "Provide at least two (x,y) pairs.",
        )

    equation = MODELS[model]
    # scientific calculator 2-Variable Calc summations / y dispersion (always available)
    sum_x = sum(x * f for x, f in zip(xs, fs))
    sum_y = sum(y * f for y, f in zip(ys, fs))
    sumsq_x = sum(x * x * f for x, f in zip(xs, fs))
    sumsq_y = sum(y * y * f for y, f in zip(ys, fs))
    sum_xy = sum(x * y * f for x, y, f in zip(xs, ys, fs))
    sum_x3 = sum(x**3 * f for x, f in zip(xs, fs))
    sum_x2y = sum(x * x * y * f for x, y, f in zip(xs, ys, fs))
    sum_x4 = sum(x**4 * f for x, f in zip(xs, fs))
    mean_x = sum_x / n
    mean_y = sum_y / n
    var_pop_y = sum(f * (y - mean_y) ** 2 for y, f in zip(ys, fs)) / n
    var_sample_y = (
        sum(f * (y - mean_y) ** 2 for y, f in zip(ys, fs)) / (n - 1) if n > 1 else None
    )
    out: dict[str, Any] = {
        "model": model,
        "equation": equation,
        "n": n,
        "sum_x": sum_x,
        "sum_y": sum_y,
        "sumsq_x": sumsq_x,
        "sumsq_y": sumsq_y,
        "sum_xy": sum_xy,
        "sum_x3": sum_x3,
        "sum_x2y": sum_x2y,
        "sum_x4": sum_x4,
        "mean_x": mean_x,
        "mean_y": mean_y,
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "var_pop_y": var_pop_y,
        "var_sample_y": var_sample_y,
        "std_pop_y": math.sqrt(var_pop_y),
        "std_sample_y": math.sqrt(var_sample_y) if var_sample_y is not None else None,
    }

    if model == "linear":
        a, b, r, mx, my = _linreg(xs, ys, fs)
        out.update(a=a, b=b, r=r, predict_at_mean=a + b * mx)
        if predict_y_at is not None:
            out["y_hat"] = a + b * float(predict_y_at)
        if predict_x_at is not None:
            if abs(b) < 1e-15:
                raise CalcError("domain_error", "Cannot estimate x: slope is zero", "b≠0 required.")
            out["x_hat"] = (float(predict_x_at) - a) / b

    elif model == "quadratic":
        c0, c1, c2 = _poly_fit(xs, ys, fs, 2)
        out.update(a=c0, b=c1, c=c2)  # scientific calculator A,B,C
        if predict_y_at is not None:
            xv = float(predict_y_at)
            out["y_hat"] = c0 + c1 * xv + c2 * xv * xv
        if predict_x_at is not None:
            # solve c2 x^2 + c1 x + (c0 - y) = 0
            yv = float(predict_x_at)
            aa, bb, cc = c2, c1, c0 - yv
            if abs(aa) < 1e-15:
                if abs(bb) < 1e-15:
                    raise CalcError("domain_error", "Cannot estimate x for this quadratic", "Degenerate.")
                out["x_hat"] = -cc / bb
            else:
                disc = bb * bb - 4 * aa * cc
                if disc < 0:
                    raise CalcError("domain_error", "No real x for this y", "Check predict_x_at.")
                sd = math.sqrt(disc)
                out["x_hat1"] = (-bb + sd) / (2 * aa)
                out["x_hat2"] = (-bb - sd) / (2 * aa)

    elif model == "logarithmic":
        _require_positive(xs, "x")
        a, b, r, mx, my = _linreg([math.log(x) for x in xs], ys, fs)
        out.update(a=a, b=b, r=r, mean_x=sum(x * f for x, f in zip(xs, fs)) / n, mean_y=my)
        if predict_y_at is not None:
            out["y_hat"] = a + b * math.log(float(predict_y_at))
        if predict_x_at is not None:
            out["x_hat"] = math.exp((float(predict_x_at) - a) / b)

    elif model == "exp":
        _require_positive(ys, "y")
        a_ln, b, r, mx, my = _linreg(xs, [math.log(y) for y in ys], fs)
        a = math.exp(a_ln)
        out.update(a=a, b=b, r=r, mean_x=mx, mean_y=sum(y * f for y, f in zip(ys, fs)) / n)
        if predict_y_at is not None:
            out["y_hat"] = a * math.exp(b * float(predict_y_at))
        if predict_x_at is not None:
            out["x_hat"] = (math.log(float(predict_x_at) / a)) / b

    elif model == "abexp":
        # y = a * b^x  => ln y = ln a + x ln b
        _require_positive(ys, "y")
        ln_a, ln_b, r, mx, my = _linreg(xs, [math.log(y) for y in ys], fs)
        a, b = math.exp(ln_a), math.exp(ln_b)
        out.update(a=a, b=b, r=r, mean_x=mx, mean_y=sum(y * f for y, f in zip(ys, fs)) / n)
        if predict_y_at is not None:
            out["y_hat"] = a * (b ** float(predict_y_at))
        if predict_x_at is not None:
            out["x_hat"] = math.log(float(predict_x_at) / a) / math.log(b)

    elif model == "power":
        _require_positive(xs, "x")
        _require_positive(ys, "y")
        ln_a, b, r, _, _ = _linreg([math.log(x) for x in xs], [math.log(y) for y in ys], fs)
        a = math.exp(ln_a)
        out.update(a=a, b=b, r=r)
        if predict_y_at is not None:
            out["y_hat"] = a * (float(predict_y_at) ** b)
        if predict_x_at is not None:
            out["x_hat"] = (float(predict_x_at) / a) ** (1 / b)

    elif model == "inverse":
        if any(abs(x) < 1e-15 for x in xs):
            raise CalcError("domain_error", "x must be non-zero for inverse regression", "Remove x=0.")
        a, b, r, _, my = _linreg([1 / x for x in xs], ys, fs)
        out.update(a=a, b=b, r=r, mean_y=my)
        if predict_y_at is not None:
            out["y_hat"] = a + b / float(predict_y_at)
        if predict_x_at is not None:
            out["x_hat"] = b / (float(predict_x_at) - a)

    elif model == "cubic":
        coeffs = _poly_fit(xs, ys, fs, 3)  # d, c, b, a in low-to-high: c0..c3
        # CubicReg: ax^3+bx^2+cx+d — map a=c3,b=c2,c=c1,d=c0
        out.update(a=coeffs[3], b=coeffs[2], c=coeffs[1], d=coeffs[0])
        if predict_y_at is not None:
            xv = float(predict_y_at)
            out["y_hat"] = sum(coeffs[k] * xv**k for k in range(4))

    elif model == "quartic":
        coeffs = _poly_fit(xs, ys, fs, 4)
        out.update(a=coeffs[4], b=coeffs[3], c=coeffs[2], d=coeffs[1], e=coeffs[0])
        if predict_y_at is not None:
            xv = float(predict_y_at)
            out["y_hat"] = sum(coeffs[k] * xv**k for k in range(5))

    elif model == "logistic":
        # Logistic: y = c/(1+a*e^(-b*x)); nonlinear LS via grid+refine on transformed guess
        _require_positive(ys, "y")
        c_est = max(ys) * 1.1
        # Fit ln((c-y)/y) = ln a - b x  for y < c
        best = None
        for scale in (1.05, 1.1, 1.2, 1.5, 2.0):
            c_try = max(ys) * scale
            if any(y >= c_try for y in ys):
                continue
            zs = [math.log((c_try - y) / y) for y in ys]
            try:
                ln_a, neg_b, r, _, _ = _linreg(xs, zs, fs)
                a_try, b_try = math.exp(ln_a), -neg_b
                sse = sum(
                    f * (y - c_try / (1 + a_try * math.exp(-b_try * x))) ** 2
                    for x, y, f in zip(xs, ys, fs)
                )
                if best is None or sse < best[0]:
                    best = (sse, a_try, b_try, c_try, r)
            except CalcError:
                continue
        if best is None:
            raise CalcError(
                "convergence_failed",
                "Logistic regression failed for this data",
                "Ensure y values are positive and not all equal.",
            )
        _, a, b, c, r = best
        out.update(a=a, b=b, c=c, r=r)
        if predict_y_at is not None:
            out["y_hat"] = c / (1 + a * math.exp(-b * float(predict_y_at)))

    elif model == "medmed":
        # Med-Med: median-median line
        pairs = sorted(zip(xs, ys), key=lambda t: t[0])
        n_pts = len(pairs)
        third = n_pts // 3
        if third < 1:
            raise CalcError("invalid_data", "Need enough points for Med-Med", "Use more data.")
        g1, g3 = pairs[:third], pairs[-third:]
        # middle group unused for slope (classic med-med)
        def med(vals: list[float]) -> float:
            s = sorted(vals)
            m = len(s)
            return s[m // 2] if m % 2 else 0.5 * (s[m // 2 - 1] + s[m // 2])

        x1, y1 = med([p[0] for p in g1]), med([p[1] for p in g1])
        x3, y3 = med([p[0] for p in g3]), med([p[1] for p in g3])
        if abs(x3 - x1) < 1e-15:
            raise CalcError("domain_error", "Med-Med slope undefined", "x medians coincide.")
        a_slope = (y3 - y1) / (x3 - x1)
        # b intercept from median of residuals
        b_int = med([y - a_slope * x for x, y in pairs])
        out.update(a=a_slope, b=b_int)  # y = a*x + b per Med-Med(ax+b)
        if predict_y_at is not None:
            out["y_hat"] = a_slope * float(predict_y_at) + b_int
        if predict_x_at is not None:
            out["x_hat"] = (float(predict_x_at) - b_int) / a_slope

    return ok(**out)
