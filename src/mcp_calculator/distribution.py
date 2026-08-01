"""Distribution mode: Normal/Binomial/Poisson plus t/χ²/F/geometric/invBinom/tails."""

from __future__ import annotations

import math
from typing import Any

from mcp_calculator.errors import CalcError, ok

TYPES = {
    "normal_pd",
    "normal_cd",
    "inverse_normal",
    "binomial_pd",
    "binomial_cd",
    "inverse_binomial",
    "poisson_pd",
    "poisson_cd",
    "geometric_pd",
    "geometric_cd",
    "t_pd",
    "t_cd",
    "chi2_pd",
    "chi2_cd",
    "f_pd",
    "f_cd",
    # STAT Norm Dist areas for standardized t (P/Q/R)
    "norm_p",
    "norm_q",
    "norm_r",
}


def _phi(z: float) -> float:
    return math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def _cdf_standard(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


def norm_pqr(t: float) -> dict[str, float]:
    """Standard-normal P/Q/R for standardized variate t (STAT Distr).

    P(t): area −∞ → t
    Q(t): area 0 → t  (= P(t) − 0.5)
    R(t): area t → +∞ (= 1 − P(t))
    """
    p = _cdf_standard(float(t))
    return {"t": float(t), "P": p, "Q": p - 0.5, "R": 1.0 - p}


def _inv_cdf_standard(p: float) -> float:
    if not 0 < p < 1:
        raise CalcError(
            "domain_error",
            "Area (probability) must be in (0,1) for inverse normal",
            "Pass Area between 0 and 1 exclusive.",
        )
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577459590671e02,
        -3.066479806614736e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580577e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    ) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _binom_pmf(k: int, n: int, p: float) -> float:
    if k < 0 or k > n:
        return 0.0
    if p == 0:
        return 1.0 if k == 0 else 0.0
    if p == 1:
        return 1.0 if k == n else 0.0
    logc = math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    return math.exp(logc + k * math.log(p) + (n - k) * math.log(1 - p))


def _poisson_pmf(k: int, lam: float) -> float:
    if k < 0:
        return 0.0
    if lam == 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def _betacf(a: float, b: float, x: float) -> float:
    max_it, eps, fpmin = 200, 3e-12, 1e-30
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_it + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    )
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def _t_cdf(t: float, df: float) -> float:
    x = df / (df + t * t)
    a = 0.5 * _betai(0.5 * df, 0.5, x)
    return 0.5 + (0.5 - a) if t >= 0 else a


def _t_pdf(t: float, df: float) -> float:
    return (
        math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2))
        / math.sqrt(df * math.pi)
        / (1 + t * t / df) ** ((df + 1) / 2)
    )


def _chi2_cdf(x: float, df: float) -> float:
    if x <= 0:
        return 0.0
    return _gammp(0.5 * df, 0.5 * x)


def _chi2_pdf(x: float, df: float) -> float:
    if x <= 0:
        return 0.0
    return math.exp(-0.5 * x + (0.5 * df - 1) * math.log(x) - 0.5 * df * math.log(2) - math.lgamma(0.5 * df))


def _gammp(a: float, x: float) -> float:
    if x < 0 or a <= 0:
        raise CalcError("domain_error", "Invalid gamma args", "Check df/x.")
    if x == 0:
        return 0.0
    if x < a + 1:
        return _gser(a, x)
    return 1.0 - _gcf(a, x)


def _gser(a: float, x: float) -> float:
    gln = math.lgamma(a)
    ap, summ, delta = a, 1.0 / a, 1.0 / a
    for _ in range(200):
        ap += 1
        delta *= x / ap
        summ += delta
        if abs(delta) < abs(summ) * 3e-12:
            return summ * math.exp(-x + a * math.log(x) - gln)
    return summ * math.exp(-x + a * math.log(x) - gln)


def _gcf(a: float, x: float) -> float:
    gln = math.lgamma(a)
    b, c, d, h = x + 1 - a, 1e30, 1.0 / (x + 1 - a), 1.0 / (x + 1 - a)
    for i in range(1, 201):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 3e-12:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def _f_cdf(x: float, d1: float, d2: float) -> float:
    if x <= 0:
        return 0.0
    return 1.0 - _betai(0.5 * d2, 0.5 * d1, d2 / (d2 + d1 * x))


def _f_pdf(x: float, d1: float, d2: float) -> float:
    if x <= 0:
        return 0.0
    return math.exp(
        math.lgamma((d1 + d2) / 2)
        - math.lgamma(d1 / 2)
        - math.lgamma(d2 / 2)
        + (d1 / 2) * math.log(d1 / d2)
        + (d1 / 2 - 1) * math.log(x)
        - ((d1 + d2) / 2) * math.log(1 + (d1 / d2) * x)
    )


def distribution(
    type: str,
    x: float | list[float] | None = None,
    sigma: float | None = None,
    mu: float | None = None,
    lower: float | None = None,
    upper: float | None = None,
    area: float | None = None,
    n: int | None = None,
    p: float | None = None,
    lambda_: float | None = None,
    df: float | None = None,
    df1: float | None = None,
    df2: float | None = None,
    tail: str = "left",
) -> dict[str, Any]:
    """Distribution calculations. Pass every variable the chosen type needs."""
    t = (type or "").lower().strip().replace("chi²", "chi2").replace("χ2", "chi2")
    if t not in TYPES:
        raise CalcError(
            "invalid_data",
            f"Unknown distribution type {type!r}",
            "Set type to one of: normal_pd, normal_cd, inverse_normal, binomial_pd, "
            "binomial_cd, inverse_binomial, poisson_pd, poisson_cd, geometric_pd, "
            "geometric_cd, t_pd, t_cd, chi2_pd, chi2_cd, f_pd, f_cd, norm_p, norm_q, norm_r.",
            example="type='normal_pd', x=36, sigma=2, mu=35",
        )

    if t == "normal_pd":
        if x is None or sigma is None or mu is None:
            raise CalcError(
                "invalid_data",
                "normal_pd requires x, sigma, mu",
                "Pass all three: x (value), sigma (>0), mu (mean).",
                example="type='normal_pd', x=36, sigma=2, mu=35",
            )
        if sigma <= 0:
            raise CalcError(
                "domain_error",
                "sigma must be > 0",
                "Pass a positive standard deviation sigma.",
                example="sigma=2",
            )
        z = (float(x) - float(mu)) / float(sigma)
        return ok(type=t, p=_phi(z) / float(sigma), x=float(x), sigma=float(sigma), mu=float(mu))

    if t == "normal_cd":
        if lower is None or upper is None or sigma is None or mu is None:
            raise CalcError(
                "invalid_data",
                "normal_cd requires lower, upper, sigma, mu",
                "Pass lower and upper bounds plus sigma (>0) and mu.",
                example="type='normal_cd', lower=30, upper=40, sigma=2, mu=35",
            )
        if sigma <= 0:
            raise CalcError(
                "domain_error",
                "sigma must be > 0",
                "Pass a positive standard deviation sigma.",
                example="sigma=2",
            )
        lo = (float(lower) - float(mu)) / float(sigma)
        up = (float(upper) - float(mu)) / float(sigma)
        return ok(
            type=t,
            p=_cdf_standard(up) - _cdf_standard(lo),
            lower=float(lower),
            upper=float(upper),
            sigma=float(sigma),
            mu=float(mu),
        )

    if t == "inverse_normal":
        if area is None or sigma is None or mu is None:
            raise CalcError(
                "invalid_data",
                "inverse_normal requires area, sigma, mu",
                "Pass area in (0,1], sigma>0, mu; optional tail=left|right|center.",
                example="type='inverse_normal', area=0.975, sigma=1, mu=0, tail='left'",
            )
        if sigma <= 0:
            raise CalcError(
                "domain_error",
                "sigma must be > 0",
                "Pass a positive standard deviation sigma.",
                example="sigma=1",
            )
        tl = (tail or "left").lower().strip()
        area_f = float(area)
        mu_f, sig = float(mu), float(sigma)
        if tl == "left":
            z = _inv_cdf_standard(area_f)
            return ok(type=t, x=mu_f + sig * z, area=area_f, sigma=sig, mu=mu_f, tail="left")
        if tl == "right":
            z = _inv_cdf_standard(1.0 - area_f)
            return ok(type=t, x=mu_f + sig * z, area=area_f, sigma=sig, mu=mu_f, tail="right")
        if tl == "center":
            z = _inv_cdf_standard(0.5 + area_f / 2.0)
            return ok(
                type=t,
                lower=mu_f - sig * z,
                upper=mu_f + sig * z,
                area=area_f,
                sigma=sig,
                mu=mu_f,
                tail="center",
            )
        raise CalcError(
            "invalid_data",
            f"Unknown tail {tail!r}",
            "Set tail to left, right, or center.",
            example="tail='left'",
        )

    if t in ("binomial_pd", "binomial_cd"):
        if x is None or n is None or p is None:
            raise CalcError(
                "invalid_data",
                f"{t} requires x, n, p",
                "Pass x (count or list), n (trials), p (success probability in [0,1]).",
                example=f"type='{t}', x=3, n=10, p=0.5",
            )
        if not (0 <= p <= 1):
            raise CalcError(
                "domain_error",
                "p must be in [0,1]",
                "Pass success probability p between 0 and 1 inclusive.",
                example="p=0.5",
            )
        N = int(n)
        xs = x if isinstance(x, list) else [x]
        results = []
        for xi in xs:
            k = int(xi)
            if t == "binomial_pd":
                results.append(_binom_pmf(k, N, float(p)))
            else:
                results.append(sum(_binom_pmf(i, N, float(p)) for i in range(0, k + 1)))
        if not isinstance(x, list):
            return ok(
                type=t,
                x=float(xs[0]),
                n=N,
                success_p=float(p),
                probability=results[0],
            )
        return ok(type=t, x=[float(v) for v in xs], n=N, success_p=float(p), probability=results)

    if t == "inverse_binomial":
        if area is None or n is None or p is None:
            raise CalcError(
                "invalid_data",
                "inverse_binomial requires area, n, p",
                "Pass area in (0,1], n (trials), p in [0,1]; returns min k with CDF ≥ area.",
                example="type='inverse_binomial', area=0.5, n=10, p=0.5",
            )
        if not (0 < float(area) <= 1) or not (0 <= float(p) <= 1):
            raise CalcError(
                "domain_error",
                "area in (0,1], p in [0,1]",
                "Fix area (probability) and/or p (success probability).",
                example="area=0.5, p=0.5",
            )
        N = int(n)
        target = float(area)
        cdf = 0.0
        k_out = N
        for k in range(0, N + 1):
            cdf += _binom_pmf(k, N, float(p))
            if cdf >= target:
                k_out = k
                break
        return ok(type=t, x=k_out, n=N, success_p=float(p), area=target, cdf=cdf)

    if t in ("poisson_pd", "poisson_cd"):
        lam = lambda_
        if x is None or lam is None:
            raise CalcError(
                "invalid_data",
                f"{t} requires x and lambda_",
                "Pass x (count or list) and lambda_ (≥0 mean rate). Parameter name is lambda_.",
                example=f"type='{t}', x=2, lambda_=3",
            )
        if lam < 0:
            raise CalcError(
                "domain_error",
                "lambda must be >= 0",
                "Pass a non-negative rate lambda_.",
                example="lambda_=3",
            )
        xs = x if isinstance(x, list) else [x]
        results = []
        for xi in xs:
            k = int(xi)
            if t == "poisson_pd":
                results.append(_poisson_pmf(k, float(lam)))
            else:
                results.append(sum(_poisson_pmf(i, float(lam)) for i in range(0, k + 1)))
        if not isinstance(x, list):
            return ok(type=t, x=float(xs[0]), lambda_=float(lam), probability=results[0])
        return ok(type=t, x=[float(v) for v in xs], lambda_=float(lam), probability=results)

    if t in ("geometric_pd", "geometric_cd"):
        if x is None or p is None:
            raise CalcError("invalid_data", f"{t} requires x, p", "geomet*: trial number x≥1, p.")
        if not (0 < float(p) <= 1):
            raise CalcError("domain_error", "p must be in (0,1]", "Pass success probability.")
        xs = x if isinstance(x, list) else [x]
        results = []
        pf = float(p)
        for xi in xs:
            k = int(xi)
            if k < 1:
                results.append(0.0)
                continue
            if t == "geometric_pd":
                results.append(((1 - pf) ** (k - 1)) * pf)
            else:
                results.append(1.0 - (1 - pf) ** k)
        if not isinstance(x, list):
            return ok(type=t, x=float(xs[0]), success_p=pf, probability=results[0])
        return ok(type=t, x=[float(v) for v in xs], success_p=pf, probability=results)

    if t in ("t_pd", "t_cd"):
        if df is None:
            raise CalcError("invalid_data", f"{t} requires df", "Pass degrees of freedom df.")
        if df <= 0:
            raise CalcError("domain_error", "df must be > 0", "Pass positive df.")
        if t == "t_pd":
            if x is None:
                raise CalcError("invalid_data", "t_pd requires x", "Pass x.")
            return ok(type=t, x=float(x), df=float(df), p=_t_pdf(float(x), float(df)))
        if lower is None or upper is None:
            raise CalcError("invalid_data", "t_cd requires lower, upper, df", "Pass bounds.")
        return ok(
            type=t,
            lower=float(lower),
            upper=float(upper),
            df=float(df),
            p=_t_cdf(float(upper), float(df)) - _t_cdf(float(lower), float(df)),
        )

    if t in ("chi2_pd", "chi2_cd"):
        if df is None:
            raise CalcError("invalid_data", f"{t} requires df", "Pass df.")
        if df <= 0:
            raise CalcError("domain_error", "df must be > 0", "Pass positive df.")
        if t == "chi2_pd":
            if x is None:
                raise CalcError("invalid_data", "chi2_pd requires x", "Pass x.")
            return ok(type=t, x=float(x), df=float(df), p=_chi2_pdf(float(x), float(df)))
        if lower is None or upper is None:
            raise CalcError("invalid_data", "chi2_cd requires lower, upper, df", "Pass bounds.")
        return ok(
            type=t,
            lower=float(lower),
            upper=float(upper),
            df=float(df),
            p=_chi2_cdf(float(upper), float(df)) - _chi2_cdf(float(lower), float(df)),
        )

    if t in ("f_pd", "f_cd"):
        if df1 is None or df2 is None:
            raise CalcError("invalid_data", f"{t} requires df1, df2", "Pass both dfs.")
        if df1 <= 0 or df2 <= 0:
            raise CalcError("domain_error", "df1 and df2 must be > 0", "Pass positive dfs.")
        if t == "f_pd":
            if x is None:
                raise CalcError("invalid_data", "f_pd requires x", "Pass x.")
            return ok(
                type=t,
                x=float(x),
                df1=float(df1),
                df2=float(df2),
                p=_f_pdf(float(x), float(df1), float(df2)),
            )
        if lower is None or upper is None:
            raise CalcError("invalid_data", "f_cd requires lower, upper, df1, df2", "Pass bounds.")
        return ok(
            type=t,
            lower=float(lower),
            upper=float(upper),
            df1=float(df1),
            df2=float(df2),
            p=_f_cdf(float(upper), float(df1), float(df2))
            - _f_cdf(float(lower), float(df1), float(df2)),
        )

    if t in ("norm_p", "norm_q", "norm_r"):
        if x is None:
            raise CalcError(
                "invalid_data",
                f"{t} requires x (= standardized t)",
                "Pass standardized t as x, or use stats_1var with norm_x on a data list.",
                example=f"type='{t}', x=1.0",
            )
        areas = norm_pqr(float(x))
        key = {"norm_p": "P", "norm_q": "Q", "norm_r": "R"}[t]
        return ok(type=t, t=areas["t"], p=areas[key], P=areas["P"], Q=areas["Q"], R=areas["R"])

    raise CalcError(
        "internal_error",
        f"Unhandled type {t}",
        "Retry with a supported type; see distribution tool docstring for the type list.",
        example="type='normal_pd', x=0, sigma=1, mu=0",
    )
