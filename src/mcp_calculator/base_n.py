"""BASE-N conversion and arithmetic (2/8/10/16), 32-bit two's complement."""

from __future__ import annotations

from typing import Any

from mcp_calculator.errors import CalcError, ok

BITS = 32
MASK = (1 << BITS) - 1
ALLOWED = {2, 8, 10, 16}


def _parse(value: str | int, base: int) -> int:
    if base not in ALLOWED:
        raise CalcError(
            "invalid_base",
            f"Unsupported base {base}",
            "Use base 2, 8, 10, or 16.",
        )
    s = str(value).strip().lower().replace("_", "")
    if s.startswith("-"):
        raise CalcError(
            "invalid_data",
            "Use two's complement bit patterns; pass unsigned-style digits",
            "For negative values in hex/bin, pass the 32-bit pattern (e.g. FFFFFFFF).",
        )
    digits = "0123456789abcdef"[:base]
    if not s or any(ch not in digits for ch in s):
        raise CalcError(
            "invalid_base",
            f"Invalid digits for base {base}: {value!r}",
            f"Only use characters from {digits!r}.",
            example="FF" if base == 16 else "1010",
        )
    try:
        n = int(s, base)
    except ValueError as exc:
        raise CalcError(
            "invalid_base",
            f"Cannot parse {value!r} in base {base}",
            "Check digits and base.",
        ) from exc
    if n > MASK:
        raise CalcError(
            "overflow",
            f"Value exceeds {BITS}-bit range",
            f"Keep values within 0..{MASK}.",
        )
    return n & MASK


def _fmt(n: int, base: int) -> str:
    n = n & MASK
    if base == 10:
        # signed interpretation for display
        signed = n if n < (1 << (BITS - 1)) else n - (1 << BITS)
        return str(signed) if signed < 0 else str(n)
    if base == 2:
        return format(n, f"0{BITS}b")
    if base == 8:
        return format(n, "o")
    return format(n, "X")


def base_convert(value: str | int, from_base: int, to_base: int) -> dict[str, Any]:
    n = _parse(value, int(from_base))
    return ok(
        value=_fmt(n, int(to_base)),
        decimal=n if n < (1 << 31) else n - (1 << 32),
        decimal_unsigned=n,
        from_base=int(from_base),
        to_base=int(to_base),
        bits=BITS,
    )


def base_arith(op: str, a: str | int, b: str | int | None = None, base: int = 10) -> dict[str, Any]:
    op = (op or "").lower().strip()
    base = int(base)
    xa = _parse(a, base)
    if op == "not":
        res = (~xa) & MASK
        return ok(op=op, result=_fmt(res, base), decimal_unsigned=res, base=base)
    if b is None:
        raise CalcError(
            "invalid_data",
            f"{op} requires two operands",
            "Pass a and b.",
        )
    xb = _parse(b, base)
    if op == "add":
        res = (xa + xb) & MASK
    elif op == "sub":
        res = (xa - xb) & MASK
    elif op == "mul":
        res = (xa * xb) & MASK
    elif op == "div":
        if xb == 0:
            raise CalcError(
                "division_by_zero",
                "Division by zero in base_arith",
                "Ensure divisor is non-zero.",
            )
        # signed division like many calcs
        sa = xa if xa < (1 << 31) else xa - (1 << 32)
        sb = xb if xb < (1 << 31) else xb - (1 << 32)
        res = int(sa / sb) & MASK
    elif op == "and":
        res = xa & xb
    elif op == "or":
        res = xa | xb
    elif op == "xor":
        res = xa ^ xb
    else:
        raise CalcError(
            "unknown_token",
            f"Unknown base op {op!r}",
            "Use add, sub, mul, div, and, or, xor, not.",
            token=op,
        )
    return ok(op=op, result=_fmt(res, base), decimal_unsigned=res, base=base)
