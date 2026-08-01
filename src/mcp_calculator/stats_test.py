"""STAT TESTS (inferential). All editor fields are explicit parameters."""

from __future__ import annotations

import math
from typing import Any

from mcp_calculator.distribution import _t_cdf
from mcp_calculator.errors import CalcError, ok
from mcp_calculator.stats import _data, _linreg


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


def _alt(alternative: str) -> str:
    a = (alternative or "≠").strip().lower()
    a = {"!=": "≠", "<>": "≠", "ne": "≠", "lt": "<", "gt": ">"}.get(a, a)
    if a not in ("≠", "<", ">"):
        raise CalcError(
            "invalid_data",
            f"alternative must be ≠, <, or >; got {alternative!r}",
            'Pass alternative="≠" (two-sided), "<", or ">".',
        )
    return a


def _pvalue_norm(z: float, alt: str) -> float:
    if alt == "≠":
        return 2 * (1 - _norm_cdf(abs(z)))
    if alt == ">":
        return 1 - _norm_cdf(z)
    return _norm_cdf(z)


def _pvalue_t(t: float, df: float, alt: str) -> float:
    if alt == "≠":
        return 2 * (1 - _t_cdf(abs(t), df))
    if alt == ">":
        return 1 - _t_cdf(t, df)
    return _t_cdf(t, df)


def stats_test(
    type: str,
    *,
    data: list[float] | None = None,
    data2: list[float] | None = None,
    mu0: float | None = None,
    sigma: float | None = None,
    x: float | None = None,
    n: int | None = None,
    p0: float | None = None,
    x1: float | None = None,
    n1: int | None = None,
    x2: float | None = None,
    n2: int | None = None,
    lists: list[list[float]] | None = None,
    alternative: str = "≠",
    pooled: bool = False,
) -> dict[str, Any]:
    """
    type (STAT TESTS style):
      z_test — 1-sample z (data or xbar via mean of data; needs sigma, mu0)
      t_test — 1-sample t (data, mu0)
      2_samp_z_test — needs x1,n1,x2,n2,sigma1=sigma,sigma2 via data2 mean? use sigma for both
        Better: x1,n1,sigma,x2,n2 and sigma2 optional — use sigma for σ1 and pass sigma2 as...
      Simplify:
      z_test: data, sigma, mu0, alternative
      t_test: data, mu0, alternative
      2_samp_t_test: data, data2, alternative, pooled
      1_prop_z_test: x, n, p0, alternative
      2_prop_z_test: x1,n1,x2,n2, alternative
      anova: lists=[[...],[...],...]
      linreg_ttest: data as x, data2 as y
    """
    t = (type or "").lower().strip().replace("-", "_")
    alt = _alt(alternative)

    if t in ("z_test", "ztest"):
        if data is None or sigma is None or mu0 is None:
            raise CalcError(
                "invalid_data",
                "z_test requires data, sigma, mu0",
                "1-sample Z-Test editor fields.",
            )
        if sigma <= 0:
            raise CalcError("domain_error", "sigma must be > 0", "Pass σ > 0.")
        xs = _data(data)
        n_ = len(xs)
        mean = sum(xs) / n_
        z = (mean - float(mu0)) / (float(sigma) / math.sqrt(n_))
        return ok(
            type="z_test",
            z=z,
            p=_pvalue_norm(z, alt),
            mean=mean,
            n=n_,
            mu0=float(mu0),
            sigma=float(sigma),
            alternative=alt,
        )

    if t in ("t_test", "ttest"):
        if data is None or mu0 is None:
            raise CalcError("invalid_data", "t_test requires data, mu0", "1-sample T-Test.")
        xs = _data(data)
        n_ = len(xs)
        if n_ < 2:
            raise CalcError("invalid_data", "Need n≥2 for t_test", "Provide more data.")
        mean = sum(xs) / n_
        s = math.sqrt(sum((v - mean) ** 2 for v in xs) / (n_ - 1))
        if s == 0:
            raise CalcError("domain_error", "Sample stdev is zero", "Data must vary.")
        tv = (mean - float(mu0)) / (s / math.sqrt(n_))
        df = n_ - 1
        return ok(
            type="t_test",
            t=tv,
            p=_pvalue_t(tv, df, alt),
            df=df,
            mean=mean,
            s=s,
            n=n_,
            mu0=float(mu0),
            alternative=alt,
        )

    if t in ("2_samp_t_test", "twosampttest"):
        if data is None or data2 is None:
            raise CalcError("invalid_data", "2_samp_t_test requires data and data2", "Two lists.")
        a, b = _data(data), _data(data2, "data2")
        n1, n2 = len(a), len(b)
        if n1 < 2 or n2 < 2:
            raise CalcError("invalid_data", "Each sample needs n≥2", "Provide more data.")
        m1, m2 = sum(a) / n1, sum(b) / n2
        s1 = math.sqrt(sum((v - m1) ** 2 for v in a) / (n1 - 1))
        s2 = math.sqrt(sum((v - m2) ** 2 for v in b) / (n2 - 1))
        if pooled:
            sp2 = ((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / (n1 + n2 - 2)
            se = math.sqrt(sp2 * (1 / n1 + 1 / n2))
            df = n1 + n2 - 2
        else:
            se = math.sqrt(s1 * s1 / n1 + s2 * s2 / n2)
            # Welch–Satterthwaite
            num = (s1 * s1 / n1 + s2 * s2 / n2) ** 2
            den = (s1 * s1 / n1) ** 2 / (n1 - 1) + (s2 * s2 / n2) ** 2 / (n2 - 1)
            df = num / den if den else n1 + n2 - 2
        if se == 0:
            raise CalcError("domain_error", "Pooled SE is zero", "Check data.")
        tv = (m1 - m2) / se
        return ok(
            type="2_samp_t_test",
            t=tv,
            p=_pvalue_t(tv, df, alt),
            df=df,
            mean1=m1,
            mean2=m2,
            s1=s1,
            s2=s2,
            n1=n1,
            n2=n2,
            pooled=pooled,
            alternative=alt,
        )

    if t in ("1_prop_z_test", "propztest"):
        if x is None or n is None or p0 is None:
            raise CalcError("invalid_data", "1_prop_z_test requires x, n, p0", "1-PropZTest.")
        n_ = int(n)
        xf = float(x)
        if not (0 <= xf <= n_) or not (0 < float(p0) < 1):
            raise CalcError("domain_error", "Need 0≤x≤n and 0<p0<1", "Check inputs.")
        phat = xf / n_
        se = math.sqrt(float(p0) * (1 - float(p0)) / n_)
        z = (phat - float(p0)) / se
        return ok(
            type="1_prop_z_test",
            z=z,
            p=_pvalue_norm(z, alt),
            phat=phat,
            n=n_,
            p0=float(p0),
            alternative=alt,
        )

    if t in ("2_prop_z_test", "twopropztest"):
        if None in (x1, n1, x2, n2):
            raise CalcError(
                "invalid_data",
                "2_prop_z_test requires x1,n1,x2,n2",
                "2-PropZTest.",
            )
        n1i, n2i = int(n1), int(n2)
        p1, p2 = float(x1) / n1i, float(x2) / n2i
        pc = (float(x1) + float(x2)) / (n1i + n2i)
        se = math.sqrt(pc * (1 - pc) * (1 / n1i + 1 / n2i))
        if se == 0:
            raise CalcError("domain_error", "SE is zero", "Check counts.")
        z = (p1 - p2) / se
        return ok(
            type="2_prop_z_test",
            z=z,
            p=_pvalue_norm(z, alt),
            phat1=p1,
            phat2=p2,
            n1=n1i,
            n2=n2i,
            alternative=alt,
        )

    if t == "anova":
        if not lists or len(lists) < 2:
            raise CalcError("invalid_data", "anova requires lists with ≥2 groups", "Pass lists=[[...],[...]].")
        groups = [_data(g, f"lists[{i}]") for i, g in enumerate(lists)]
        k = len(groups)
        ns = [len(g) for g in groups]
        N = sum(ns)
        if any(n < 1 for n in ns) or N <= k:
            raise CalcError("invalid_data", "Not enough data for ANOVA", "Need more observations.")
        means = [sum(g) / len(g) for g in groups]
        grand = sum(sum(g) for g in groups) / N
        ssb = sum(n * (m - grand) ** 2 for n, m in zip(ns, means))
        ssw = sum(sum((v - m) ** 2 for v in g) for g, m in zip(groups, means))
        dfb, dfw = k - 1, N - k
        msb, msw = ssb / dfb, ssw / dfw if dfw else float("nan")
        if msw == 0:
            raise CalcError("domain_error", "Within-group variance is zero", "Groups must vary.")
        f = msb / msw
        # p via F cdf survival
        from mcp_calculator.distribution import _f_cdf

        pval = 1.0 - _f_cdf(f, dfb, dfw)
        return ok(
            type="anova",
            F=f,
            p=pval,
            df_factor=dfb,
            df_error=dfw,
            ms_factor=msb,
            ms_error=msw,
            ss_factor=ssb,
            ss_error=ssw,
            k=k,
            n=N,
        )

    if t in ("linreg_ttest", "linregttest"):
        if data is None or data2 is None:
            raise CalcError("invalid_data", "linreg_ttest requires data=x and data2=y", "Two lists.")
        xs, ys = _data(data, "x"), _data(data2, "y")
        if len(xs) != len(ys) or len(xs) < 3:
            raise CalcError("invalid_data", "Need equal-length lists with n≥3", "Check data.")
        fs = [1.0] * len(xs)
        a, b, r, _, _ = _linreg(xs, ys, fs)
        n_ = len(xs)
        # residual SE
        yhat = [a + b * xv for xv in xs]
        sse = sum((y - yh) ** 2 for y, yh in zip(ys, yhat))
        s = math.sqrt(sse / (n_ - 2)) if sse > 0 else 0.0
        sxx = sum((xv - sum(xs) / n_) ** 2 for xv in xs)
        if sxx == 0:
            raise CalcError("domain_error", "Cannot compute LinRegTTest", "x must vary.")
        se_b = s / math.sqrt(sxx) if sxx else float("inf")
        tv = b / se_b if se_b else float("inf")
        df = n_ - 2
        return ok(
            type="linreg_ttest",
            t=tv if math.isfinite(tv) else None,
            p=_pvalue_t(tv, df, alt) if math.isfinite(tv) else 0.0,
            df=df,
            a=a,
            b=b,
            r=r,
            s=s,
            n=n_,
            alternative=alt,
        )

    raise CalcError(
        "invalid_data",
        f"Unknown stats_test type {type!r}",
        "Use z_test, t_test, 2_samp_t_test, 1_prop_z_test, 2_prop_z_test, anova, linreg_ttest.",
    )
