"""scientific calculator Table, Σ summation, Pol/Rec, and sexagesimal (DMS) helpers."""

from __future__ import annotations

import math
from typing import Any

from mcp_calculator.errors import CalcError, ok
from mcp_calculator.infix import eval_at, evaluate_infix


def summation(
    expression: str,
    start: int,
    end: int,
    index: str = "x",
    angle_mode: str = "rad",
) -> dict[str, Any]:
    """scientific calculator Σ: sum expression over integer index from start to end inclusive."""
    if index != "x":
        raise CalcError(
            "invalid_data",
            "Only index variable x is supported",
            "Write the summand in x, e.g. x+1.",
        )
    a, b = int(start), int(end)
    if a > b:
        raise CalcError(
            "invalid_data",
            "start must be <= end",
            "scientific calculator Σ requires lower index ≤ upper index.",
        )
    if b - a > 100_000:
        raise CalcError(
            "overflow",
            "Summation range too large",
            "Keep end-start <= 100000.",
        )
    total = 0.0
    for i in range(a, b + 1):
        total += eval_at(expression, float(i), angle_mode=angle_mode)
    return ok(
        sum=total,
        expression=expression,
        index=index,
        start=a,
        end=b,
        angle_mode=angle_mode,
    )


def product(
    expression: str,
    start: int,
    end: int,
    index: str = "x",
    angle_mode: str = "rad",
) -> dict[str, Any]:
    """Product Π: multiply expression over integer index from start to end inclusive."""
    if index != "x":
        raise CalcError(
            "invalid_data",
            "Only index variable x is supported",
            "Write the factor in x.",
        )
    a, b = int(start), int(end)
    if a > b:
        raise CalcError(
            "invalid_data",
            "start must be <= end",
            "Require lower index ≤ upper index.",
        )
    if b - a > 100_000:
        raise CalcError("overflow", "Product range too large", "Keep end-start <= 100000.")
    total = 1.0
    for i in range(a, b + 1):
        total *= eval_at(expression, float(i), angle_mode=angle_mode)
        if not math.isfinite(total):
            raise CalcError("overflow", "Product not finite", "Check expression/range.")
    return ok(
        product=total,
        expression=expression,
        index=index,
        start=a,
        end=b,
        angle_mode=angle_mode,
    )


def factorize(n: int | float) -> dict[str, Any]:
    """scientific calculator-style prime factorization of a positive integer (≤ 10 digits)."""
    if isinstance(n, float) and not n.is_integer():
        raise CalcError("invalid_integer", "factorize requires an integer", "Pass a whole number.")
    ni = int(n)
    if ni <= 1:
        raise CalcError(
            "domain_error",
            "factorize requires an integer > 1",
            "integer FACT applies to positive integers > 1.",
        )
    if abs(ni) >= 10**10:
        raise CalcError("overflow", "Integer has more than 10 digits", "Use ≤ 10-digit values.")
    x = ni
    factors: list[int] = []
    while x % 2 == 0:
        factors.append(2)
        x //= 2
    f = 3
    while f * f <= x:
        while x % f == 0:
            factors.append(f)
            x //= f
        f += 2
    if x > 1:
        factors.append(x)
    # multiplicity map for display
    from collections import Counter

    c = Counter(factors)
    return ok(
        n=ni,
        factors=factors,
        factorization=" * ".join(
            f"{p}^{e}" if e > 1 else str(p) for p, e in sorted(c.items())
        ),
    )


def table(
    expression: str,
    start: float,
    end: float,
    step: float,
    expression2: str | None = None,
    angle_mode: str = "rad",
) -> dict[str, Any]:
    """scientific calculator Table mode: f(x) and optional g(x) from start to end by step."""
    if step == 0:
        raise CalcError("invalid_data", "step must be non-zero", "Pass step ≠ 0.")
    if (end - start) * step < 0:
        raise CalcError(
            "invalid_data",
            "step sign must move from start toward end",
            "If end > start, use positive step.",
        )
    est = int(abs((float(end) - float(start)) / float(step))) + 2
    if est > 100_000:
        raise CalcError(
            "overflow",
            "Table too large",
            "Increase step or shrink range (max 100000 rows).",
        )
    rows: list[dict[str, Any]] = []
    x = float(start)
    end = float(end)
    step = float(step)
    guard = 0
    while (step > 0 and x <= end + 1e-12) or (step < 0 and x >= end - 1e-12):
        row: dict[str, Any] = {"x": x, "f": eval_at(expression, x, angle_mode=angle_mode)}
        if expression2 is not None:
            row["g"] = eval_at(expression2, x, angle_mode=angle_mode)
        rows.append(row)
        x += step
        guard += 1
        if guard > 100_000:
            raise CalcError("overflow", "Table too large", "Increase step or shrink range.")
    return ok(
        expression=expression,
        expression2=expression2,
        start=float(start),
        end=end,
        step=step,
        rows=rows,
        angle_mode=angle_mode,
    )


def _to_rad(theta: float, angle_mode: str) -> float:
    if angle_mode == "rad":
        return theta
    if angle_mode == "deg":
        return theta * math.pi / 180.0
    if angle_mode == "grad":
        return theta * math.pi / 200.0
    raise CalcError(
        "invalid_angle_mode",
        f"angle_mode must be rad|deg|grad; got {angle_mode!r}",
        'Pass angle_mode="deg".',
    )


def _from_rad(radians: float, angle_mode: str) -> float:
    if angle_mode == "rad":
        return radians
    if angle_mode == "deg":
        return radians * 180.0 / math.pi
    if angle_mode == "grad":
        return radians * 200.0 / math.pi
    raise CalcError(
        "invalid_angle_mode",
        f"angle_mode must be rad|deg|grad; got {angle_mode!r}",
        'Pass angle_mode="deg".',
    )


def pol(x: float, y: float, angle_mode: str = "deg") -> dict[str, Any]:
    """scientific calculator Pol(x,y): rectangular → polar. θ in current angle unit (-180 < θ ≤ 180 for deg)."""
    r = math.hypot(float(x), float(y))
    theta_rad = math.atan2(float(y), float(x))
    theta = _from_rad(theta_rad, angle_mode)
    # scientific calculator: -180 < θ ≤ 180 in degrees
    if angle_mode == "deg":
        if theta <= -180:
            theta += 360
        if theta > 180:
            theta -= 360
    return ok(r=r, theta=theta, x=float(x), y=float(y), angle_mode=angle_mode)


def rec(r: float, theta: float, angle_mode: str = "deg") -> dict[str, Any]:
    """scientific calculator Rec(r,θ): polar → rectangular."""
    if float(r) < 0:
        raise CalcError("domain_error", "r must be >= 0", "Pass non-negative r.")
    tr = _to_rad(float(theta), angle_mode)
    x = float(r) * math.cos(tr)
    y = float(r) * math.sin(tr)
    return ok(x=x, y=y, r=float(r), theta=float(theta), angle_mode=angle_mode)


def dms_to_decimal(degrees: float, minutes: float = 0.0, seconds: float = 0.0) -> dict[str, Any]:
    """Convert sexagesimal ° ′ ″ to decimal degrees."""
    d, m, s = float(degrees), float(minutes), float(seconds)
    sign = -1.0 if d < 0 or m < 0 or s < 0 else 1.0
    decimal = sign * (abs(d) + abs(m) / 60.0 + abs(s) / 3600.0)
    return ok(decimal=decimal, degrees=d, minutes=m, seconds=s)


def decimal_to_dms(decimal: float) -> dict[str, Any]:
    """Convert decimal degrees to ° ′ ″."""
    sign = -1 if decimal < 0 else 1
    x = abs(float(decimal))
    d = int(x)
    rem = (x - d) * 60
    m = int(rem)
    s = (rem - m) * 60
    return ok(degrees=sign * d, minutes=m, seconds=s, decimal=float(decimal))


_ENG_SYMBOLS = [
    ("E", 1e18),
    ("P", 1e15),
    ("T", 1e12),
    ("G", 1e9),
    ("M", 1e6),
    ("k", 1e3),
    ("", 1.0),
    ("m", 1e-3),
    ("μ", 1e-6),
    ("n", 1e-9),
    ("p", 1e-12),
    ("f", 1e-15),
]


def engineering_format(value: float | int) -> dict[str, Any]:
    """Format a real into engineering notation (exponent multiple of 3) + SI symbol."""
    x = float(value)
    if not math.isfinite(x):
        raise CalcError("domain_error", "eng format needs a finite real", "Pass a finite value.")
    if x == 0:
        return ok(value=0.0, significand=0.0, exponent=0, symbol="", display="0")
    sign = -1.0 if x < 0 else 1.0
    ax = abs(x)
    # Choose exponent multiple of 3 so significand in [1, 1000)
    exp3 = int(math.floor(math.log10(ax) / 3.0) * 3)
    significand = sign * ax / (10.0**exp3)
    symbol = ""
    for sym, factor in _ENG_SYMBOLS:
        if factor == 0:
            continue
        e = int(round(math.log10(factor))) if factor != 1 else 0
        if e == exp3:
            symbol = sym
            break
    display = f"{significand:g}{symbol}" if symbol else (
        f"{significand:g}" if exp3 == 0 else f"{significand:g}e{exp3}"
    )
    return ok(
        value=x,
        significand=significand,
        exponent=exp3,
        symbol=symbol,
        display=display,
    )


def engineering_shift(value: float | int, steps: int = 1) -> dict[str, Any]:
    """ENG shift: multiply by 1000^steps (positive → larger unit / decimal left)."""
    x = float(value) * (1000.0 ** int(steps))
    fmt = engineering_format(x)
    return ok(value=x, steps=int(steps), significand=fmt["significand"], exponent=fmt["exponent"], symbol=fmt["symbol"], display=fmt["display"])


def evaluate_with_form(
    expression: str,
    angle_mode: str = "rad",
    complex_form: str = "rectangular",
    variables: dict[str, float] | None = None,
    eng_symbols: bool = False,
) -> dict[str, Any]:
    """evaluate + optional polar complex result formatting (scientific calculator Complex a+bi / r∠θ)."""
    form = (complex_form or "rectangular").lower().strip()
    if form not in ("rectangular", "polar", "a+bi", "r∠θ", "r_theta"):
        raise CalcError(
            "invalid_data",
            f"Unknown complex_form {complex_form!r}",
            'Use "rectangular" (a+bi) or "polar" (r∠θ).',
        )
    if form in ("a+bi",):
        form = "rectangular"
    if form in ("r∠θ", "r_theta"):
        form = "polar"
    bindings = None
    if variables:
        bindings = {str(k): float(v) for k, v in variables.items()}
    res = evaluate_infix(expression, angle_mode=angle_mode, bindings=bindings)
    res["complex_form"] = form
    if bindings:
        res["variables"] = bindings
    val = res.get("result")
    if form == "polar" and isinstance(val, dict) and "re" in val and "im" in val:
        re, im = float(val["re"]), float(val["im"])
        r = math.hypot(re, im)
        theta = _from_rad(math.atan2(im, re), angle_mode)
        res["result"] = {"r": r, "theta": theta, "unit": angle_mode}
    if eng_symbols and isinstance(val, (int, float)) and not isinstance(val, bool):
        fmt = engineering_format(float(val))
        res["eng"] = {
            "significand": fmt["significand"],
            "exponent": fmt["exponent"],
            "symbol": fmt["symbol"],
            "display": fmt["display"],
        }
    return res
