"""Allowlisted RPN operators — no eval; callables only."""

from __future__ import annotations

import math
import cmath
import random
from dataclasses import dataclass
from typing import Any, Callable

from mcp_calculator.errors import CalcError

Number = float | complex

MAX_FACT = 170
MAX_COMB = 1000


def _is_int(x: Number) -> bool:
    if isinstance(x, complex):
        return False
    return abs(x - round(x)) < 1e-12


def _as_real(x: Number, op: str) -> float:
    if isinstance(x, complex):
        if abs(x.imag) < 1e-15:
            return float(x.real)
        raise CalcError(
            "domain_error",
            f"{op} requires a real argument; got complex",
            f"Use re/im to extract parts, or avoid {op} on complex values.",
            op=op,
        )
    return float(x)


def _finite(x: Number, op: str) -> Number:
    if isinstance(x, complex):
        if not (math.isfinite(x.real) and math.isfinite(x.imag)):
            raise CalcError(
                "overflow",
                f"Result of {op} is not finite",
                "Reduce magnitude of inputs or split the calculation.",
                op=op,
            )
        return x
    if not math.isfinite(x):
        raise CalcError(
            "overflow",
            f"Result of {op} is not finite",
            "Reduce magnitude of inputs or split the calculation.",
            op=op,
        )
    return x


@dataclass(frozen=True)
class OpSpec:
    name: str
    arity: int
    description: str
    angle_sensitive: bool = False
    # fn(args, ctx) -> Number | None  (None = mode switch / no push)
    # ctx has: angle_mode (mutable list of one str), rng
    fn: Callable[..., Any] = lambda *a, **k: None  # noqa: E731


def _add(args, ctx):
    return _finite(args[0] + args[1], "+")


def _sub(args, ctx):
    return _finite(args[0] - args[1], "-")


def _mul(args, ctx):
    return _finite(args[0] * args[1], "*")


def _div(args, ctx):
    a, b = args
    if b == 0 or b == 0j:
        raise CalcError(
            "division_by_zero",
            "Division by zero at /",
            "Ensure the divisor is non-zero before / or inv.",
            op="/",
            example="8 2 /",
        )
    return _finite(a / b, "/")


def _pow(args, ctx):
    a, b = args
    try:
        if isinstance(a, complex) or isinstance(b, complex):
            return _finite(a**b, "^")
        return _finite(math.pow(float(a), float(b)), "^")
    except (ValueError, OverflowError, ZeroDivisionError) as exc:
        raise CalcError(
            "domain_error",
            f"Power failed: {exc}",
            "Check bases/exponents (e.g. negative base with non-integer exponent).",
            op="^",
        ) from exc


def _mod(args, ctx):
    a, b = _as_real(args[0], "mod"), _as_real(args[1], "mod")
    if b == 0:
        raise CalcError(
            "division_by_zero",
            "Modulo by zero",
            "Ensure the modulus is non-zero.",
            op="mod",
        )
    return math.fmod(a, b)


def _nroot(args, ctx):
    # x y nroot -> y^(1/x)
    n, y = _as_real(args[0], "nroot"), args[1]
    if n == 0:
        raise CalcError(
            "domain_error",
            "0th root undefined",
            "Use a non-zero root index, e.g. 2 9 nroot for sqrt(9).",
            op="nroot",
        )
    return _pow([y, 1 / n], ctx)


def _neg(args, ctx):
    return -args[0]


def _abs(args, ctx):
    x = args[0]
    return abs(x) if not isinstance(x, complex) else abs(x)


def _inv(args, ctx):
    x = args[0]
    if x == 0 or x == 0j:
        raise CalcError(
            "division_by_zero",
            "inv of zero",
            "Ensure the value is non-zero before inv.",
            op="inv",
        )
    return _finite(1 / x, "inv")


def _sqrt(args, ctx):
    x = args[0]
    if isinstance(x, complex) or (isinstance(x, float) and x < 0):
        return _finite(cmath.sqrt(x if isinstance(x, complex) else complex(x)), "sqrt")
    return _finite(math.sqrt(x), "sqrt")


def _cbrt(args, ctx):
    x = _as_real(args[0], "cbrt")
    return math.copysign(abs(x) ** (1 / 3), x)


def _sq(args, ctx):
    return _finite(args[0] * args[0], "sq")


def _cube(args, ctx):
    return _finite(args[0] * args[0] * args[0], "cube")


def _pct(args, ctx):
    x, y = _as_real(args[0], "pct"), _as_real(args[1], "pct")
    return x * y / 100.0


def _pct1(args, ctx):
    return _as_real(args[0], "pct1") / 100.0


def _exp(args, ctx):
    x = args[0]
    if isinstance(x, complex):
        return _finite(cmath.exp(x), "exp")
    return _finite(math.exp(x), "exp")


def _exp10(args, ctx):
    x = _as_real(args[0], "exp10")
    return _finite(10**x, "exp10")


def _ln(args, ctx):
    x = args[0]
    if isinstance(x, complex):
        if x == 0:
            raise CalcError("domain_error", "ln(0) undefined", "Argument must be non-zero.", op="ln")
        return _finite(cmath.log(x), "ln")
    if x <= 0:
        raise CalcError(
            "domain_error",
            "ln undefined for non-positive real",
            "Argument must be > 0 for real ln, or use complex.",
            op="ln",
        )
    return math.log(x)


def _log10(args, ctx):
    x = _as_real(args[0], "log10")
    if x <= 0:
        raise CalcError(
            "domain_error",
            "log10 undefined for non-positive",
            "Argument must be > 0.",
            op="log10",
        )
    return math.log10(x)


def _log2(args, ctx):
    x = _as_real(args[0], "log2")
    if x <= 0:
        raise CalcError(
            "domain_error",
            "log2 undefined for non-positive",
            "Argument must be > 0.",
            op="log2",
        )
    return math.log2(x)


def _log(args, ctx):
    # b a log -> log_b(a)
    b, a = _as_real(args[0], "log"), _as_real(args[1], "log")
    if a <= 0 or b <= 0 or b == 1:
        raise CalcError(
            "domain_error",
            "log base/argument invalid",
            "Require a>0, b>0, b≠1. Order: base value log  →  b a log.",
            op="log",
            example="10 100 log",
        )
    return math.log(a) / math.log(b)


def _to_rad(x: float, mode: str) -> float:
    if mode == "deg":
        return math.radians(x)
    if mode == "grad":
        return x * math.pi / 200.0
    return x


def _from_rad(x: float, mode: str) -> float:
    if mode == "deg":
        return math.degrees(x)
    if mode == "grad":
        return x * 200.0 / math.pi
    return x


def _trig_forward(name, math_fn, cmath_fn):
    def impl(args, ctx):
        x = args[0]
        mode = ctx["angle_mode"][0]
        if isinstance(x, complex):
            return _finite(cmath_fn(x), name)
        return _finite(math_fn(_to_rad(_as_real(x, name), mode)), name)

    return impl


def _trig_inverse(name, math_fn):
    def impl(args, ctx):
        x = _as_real(args[0], name)
        mode = ctx["angle_mode"][0]
        try:
            r = math_fn(x)
        except ValueError as exc:
            raise CalcError(
                "domain_error",
                f"{name} domain error for {x}",
                "asin/acos require argument in [-1,1].",
                op=name,
            ) from exc
        return _from_rad(r, mode)

    return impl


def _atan2(args, ctx):
    # y x atan2 — stack: y x atan2 (x on top)
    y, x = _as_real(args[0], "atan2"), _as_real(args[1], "atan2")
    mode = ctx["angle_mode"][0]
    return _from_rad(math.atan2(y, x), mode)


def _sec(args, ctx):
    c = _trig_forward("cos", math.cos, cmath.cos)(args, ctx)
    if c == 0 or c == 0j:
        raise CalcError("domain_error", "sec undefined (cos=0)", "Avoid angles where cos is zero.", op="sec")
    return 1 / c


def _csc(args, ctx):
    s = _trig_forward("sin", math.sin, cmath.sin)(args, ctx)
    if s == 0 or s == 0j:
        raise CalcError("domain_error", "csc undefined (sin=0)", "Avoid angles where sin is zero.", op="csc")
    return 1 / s


def _cot(args, ctx):
    t = _trig_forward("tan", math.tan, cmath.tan)(args, ctx)
    if t == 0 or t == 0j:
        raise CalcError("domain_error", "cot undefined (tan=0)", "Avoid angles where tan is zero.", op="cot")
    return 1 / t


def _hyp(name, math_fn, cmath_fn, real_check=None):
    def impl(args, ctx):
        x = args[0]
        if isinstance(x, complex):
            return _finite(cmath_fn(x), name)
        xr = _as_real(x, name)
        if real_check:
            real_check(xr, name)
        try:
            return _finite(math_fn(xr), name)
        except ValueError as exc:
            raise CalcError(
                "domain_error",
                f"{name} domain error",
                "Check the valid domain for this hyperbolic function.",
                op=name,
            ) from exc

    return impl


def _acosh_check(x, name):
    if x < 1:
        raise CalcError(
            "domain_error",
            "acosh requires argument >= 1",
            "Pass a value >= 1.",
            op=name,
        )


def _atanh_check(x, name):
    if x <= -1 or x >= 1:
        raise CalcError(
            "domain_error",
            "atanh requires |argument| < 1",
            "Pass a value strictly between -1 and 1.",
            op=name,
        )


def _sech(args, ctx):
    c = _hyp("cosh", math.cosh, cmath.cosh)(args, ctx)
    return 1 / c


def _csch(args, ctx):
    s = _hyp("sinh", math.sinh, cmath.sinh)(args, ctx)
    if s == 0 or s == 0j:
        raise CalcError("domain_error", "csch undefined at 0", "Argument must be non-zero.", op="csch")
    return 1 / s


def _coth(args, ctx):
    t = _hyp("tanh", math.tanh, cmath.tanh)(args, ctx)
    if t == 0 or t == 0j:
        raise CalcError("domain_error", "coth undefined at 0", "Argument must be non-zero.", op="coth")
    return 1 / t


def _d2r(args, ctx):
    return math.radians(_as_real(args[0], "d2r"))


def _r2d(args, ctx):
    return math.degrees(_as_real(args[0], "r2d"))


def _g2r(args, ctx):
    return _as_real(args[0], "g2r") * math.pi / 200.0


def _r2g(args, ctx):
    return _as_real(args[0], "r2g") * 200.0 / math.pi


def _d2g(args, ctx):
    return _as_real(args[0], "d2g") * 10.0 / 9.0


def _g2d(args, ctx):
    return _as_real(args[0], "g2d") * 9.0 / 10.0


def _floor(args, ctx):
    return math.floor(_as_real(args[0], "floor"))


def _ceil(args, ctx):
    return math.ceil(_as_real(args[0], "ceil"))


def _round(args, ctx):
    return float(round(_as_real(args[0], "round")))


def _trunc(args, ctx):
    return math.trunc(_as_real(args[0], "trunc"))


def _frac(args, ctx):
    x = _as_real(args[0], "frac")
    return x - math.trunc(x)


def _int(args, ctx):
    return float(math.floor(_as_real(args[0], "int")))


def _fact(args, ctx):
    x = _as_real(args[0], "fact")
    if not _is_int(x) or x < 0:
        raise CalcError(
            "invalid_factorial",
            "fact requires non-negative integer",
            "Push an integer >= 0, e.g. 5 fact.",
            op="fact",
            example="5 fact",
        )
    n = int(round(x))
    if n > MAX_FACT:
        raise CalcError(
            "invalid_factorial",
            f"factorial too large (n>{MAX_FACT})",
            f"Use n <= {MAX_FACT}.",
            op="fact",
        )
    return float(math.factorial(n))


def _nPr(args, ctx):
    n, r = _as_real(args[0], "nPr"), _as_real(args[1], "nPr")
    if not (_is_int(n) and _is_int(r)) or n < 0 or r < 0 or r > n:
        raise CalcError(
            "invalid_combinatorics",
            "nPr requires integers 0 <= r <= n",
            "Order: n r nPr. Example: 5 2 nPr.",
            op="nPr",
            example="5 2 nPr",
        )
    ni, ri = int(round(n)), int(round(r))
    if ni > MAX_COMB:
        raise CalcError("overflow", "n too large for nPr", f"Use n <= {MAX_COMB}.", op="nPr")
    return float(math.perm(ni, ri))


def _nCr(args, ctx):
    n, r = _as_real(args[0], "nCr"), _as_real(args[1], "nCr")
    if not (_is_int(n) and _is_int(r)) or n < 0 or r < 0 or r > n:
        raise CalcError(
            "invalid_combinatorics",
            "nCr requires integers 0 <= r <= n",
            "Order: n r nCr. Example: 5 2 nCr.",
            op="nCr",
            example="5 2 nCr",
        )
    ni, ri = int(round(n)), int(round(r))
    if ni > MAX_COMB:
        raise CalcError("overflow", "n too large for nCr", f"Use n <= {MAX_COMB}.", op="nCr")
    return float(math.comb(ni, ri))


def _rand(args, ctx):
    return ctx["rng"].random()


def _randint(args, ctx):
    a, b = _as_real(args[0], "randint"), _as_real(args[1], "randint")
    if not (_is_int(a) and _is_int(b)):
        raise CalcError(
            "invalid_integer",
            "randint requires integer bounds",
            "Push two integers: lo hi randint.",
            op="randint",
            example="1 6 randint",
        )
    lo, hi = int(round(a)), int(round(b))
    if lo > hi:
        lo, hi = hi, lo
    return float(ctx["rng"].randint(lo, hi))


def _min(args, ctx):
    return min(_as_real(args[0], "min"), _as_real(args[1], "min"))


def _max(args, ctx):
    return max(_as_real(args[0], "max"), _as_real(args[1], "max"))


def _hypot(args, ctx):
    return math.hypot(_as_real(args[0], "hypot"), _as_real(args[1], "hypot"))


def _sgn(args, ctx):
    x = _as_real(args[0], "sgn")
    if x > 0:
        return 1.0
    if x < 0:
        return -1.0
    return 0.0


def _gcd(args, ctx):
    a, b = _as_real(args[0], "gcd"), _as_real(args[1], "gcd")
    if not (_is_int(a) and _is_int(b)):
        raise CalcError(
            "invalid_integer",
            "gcd requires integers",
            "Push integer operands.",
            op="gcd",
        )
    return float(math.gcd(int(round(a)), int(round(b))))


def _lcm(args, ctx):
    a, b = _as_real(args[0], "lcm"), _as_real(args[1], "lcm")
    if not (_is_int(a) and _is_int(b)):
        raise CalcError(
            "invalid_integer",
            "lcm requires integers",
            "Push integer operands.",
            op="lcm",
        )
    return float(math.lcm(int(round(a)), int(round(b))))


def _cmplx(args, ctx):
    re, im = _as_real(args[0], "cmplx"), _as_real(args[1], "cmplx")
    return complex(re, im)


def _polar(args, ctx):
    """r ∠ θ → complex; θ uses current angle_mode."""
    r = _as_real(args[0], "polar")
    th = _as_real(args[1], "polar")
    mode = ctx["angle_mode"][0]
    if mode == "deg":
        rad = th * math.pi / 180.0
    elif mode == "grad":
        rad = th * math.pi / 200.0
    else:
        rad = th
    return complex(r * math.cos(rad), r * math.sin(rad))


def _engshift(args, ctx):
    """Engineering shift: multiply by 1000^steps (ENG / ENG←)."""
    x = _as_real(args[0], "engshift")
    steps = _as_real(args[1], "engshift")
    if not _is_int(steps):
        raise CalcError(
            "invalid_integer",
            "engshift steps must be an integer",
            "Example: engshift(1234, 1) → 1.234e6 style shift by ×1000.",
            op="engshift",
        )
    return _finite(x * (1000.0 ** int(round(steps))), "engshift")


def _re(args, ctx):
    x = args[0]
    return float(x.real) if isinstance(x, complex) else float(x)


def _im(args, ctx):
    x = args[0]
    return float(x.imag) if isinstance(x, complex) else 0.0


def _conj(args, ctx):
    x = args[0]
    return complex(x).conjugate()


def _arg(args, ctx):
    x = args[0]
    mode = ctx["angle_mode"][0]
    return _from_rad(cmath.phase(complex(x)), mode)


def _set_mode(mode: str):
    def impl(args, ctx):
        ctx["angle_mode"][0] = mode
        return None  # no push

    return impl


def _build_ops() -> dict[str, OpSpec]:
    specs = [
        OpSpec("+", 2, "Addition", fn=_add),
        OpSpec("-", 2, "Subtraction", fn=_sub),
        OpSpec("*", 2, "Multiplication", fn=_mul),
        OpSpec("/", 2, "Division", fn=_div),
        OpSpec("^", 2, "Power a^b (a b ^)", fn=_pow),
        OpSpec("pow", 2, "Alias for ^", fn=_pow),
        OpSpec("%", 2, "Remainder (fmod)", fn=_mod),
        OpSpec("mod", 2, "Modulo", fn=_mod),
        OpSpec("nroot", 2, "y^(1/x): x y nroot", fn=_nroot),
        OpSpec("neg", 1, "Negate", fn=_neg),
        OpSpec("abs", 1, "Absolute value / modulus", fn=_abs),
        OpSpec("inv", 1, "Reciprocal 1/x", fn=_inv),
        OpSpec("sqrt", 1, "Square root", fn=_sqrt),
        OpSpec("cbrt", 1, "Cube root", fn=_cbrt),
        OpSpec("sq", 1, "Square", fn=_sq),
        OpSpec("cube", 1, "Cube", fn=_cube),
        OpSpec("pct", 2, "x * y / 100", fn=_pct),
        OpSpec("pct1", 1, "x / 100", fn=_pct1),
        OpSpec("exp", 1, "e^x", fn=_exp),
        OpSpec("exp10", 1, "10^x", fn=_exp10),
        OpSpec("ln", 1, "Natural log", fn=_ln),
        OpSpec("log10", 1, "Log base 10", fn=_log10),
        OpSpec("log2", 1, "Log base 2", fn=_log2),
        OpSpec("log", 2, "log_b(a): b a log", fn=_log),
        OpSpec("sin", 1, "Sine (angle mode)", True, _trig_forward("sin", math.sin, cmath.sin)),
        OpSpec("cos", 1, "Cosine (angle mode)", True, _trig_forward("cos", math.cos, cmath.cos)),
        OpSpec("tan", 1, "Tangent (angle mode)", True, _trig_forward("tan", math.tan, cmath.tan)),
        OpSpec("asin", 1, "Arcsine → angle mode", True, _trig_inverse("asin", math.asin)),
        OpSpec("acos", 1, "Arccosine → angle mode", True, _trig_inverse("acos", math.acos)),
        OpSpec("atan", 1, "Arctangent → angle mode", True, _trig_inverse("atan", math.atan)),
        OpSpec("atan2", 2, "atan2(y,x): y x atan2", True, _atan2),
        OpSpec("sec", 1, "Secant", True, _sec),
        OpSpec("csc", 1, "Cosecant", True, _csc),
        OpSpec("cot", 1, "Cotangent", True, _cot),
        OpSpec("sinh", 1, "Hyperbolic sine", fn=_hyp("sinh", math.sinh, cmath.sinh)),
        OpSpec("cosh", 1, "Hyperbolic cosine", fn=_hyp("cosh", math.cosh, cmath.cosh)),
        OpSpec("tanh", 1, "Hyperbolic tangent", fn=_hyp("tanh", math.tanh, cmath.tanh)),
        OpSpec("asinh", 1, "Inverse hyp sine", fn=_hyp("asinh", math.asinh, cmath.asinh)),
        OpSpec(
            "acosh",
            1,
            "Inverse hyp cosine",
            fn=_hyp("acosh", math.acosh, cmath.acosh, _acosh_check),
        ),
        OpSpec(
            "atanh",
            1,
            "Inverse hyp tangent",
            fn=_hyp("atanh", math.atanh, cmath.atanh, _atanh_check),
        ),
        OpSpec("sech", 1, "Hyperbolic secant", fn=_sech),
        OpSpec("csch", 1, "Hyperbolic cosecant", fn=_csch),
        OpSpec("coth", 1, "Hyperbolic cotangent", fn=_coth),
        OpSpec("d2r", 1, "Degrees to radians", fn=_d2r),
        OpSpec("r2d", 1, "Radians to degrees", fn=_r2d),
        OpSpec("g2r", 1, "Grads to radians", fn=_g2r),
        OpSpec("r2g", 1, "Radians to grads", fn=_r2g),
        OpSpec("d2g", 1, "Degrees to grads", fn=_d2g),
        OpSpec("g2d", 1, "Grads to degrees", fn=_g2d),
        OpSpec("floor", 1, "Floor", fn=_floor),
        OpSpec("ceil", 1, "Ceiling", fn=_ceil),
        OpSpec("round", 1, "Round to nearest", fn=_round),
        OpSpec("trunc", 1, "Truncate toward zero", fn=_trunc),
        OpSpec("frac", 1, "Fractional part", fn=_frac),
        OpSpec("int", 1, "Integer part (floor)", fn=_int),
        OpSpec("fact", 1, "Factorial n!", fn=_fact),
        OpSpec("nPr", 2, "Permutations nPr", fn=_nPr),
        OpSpec("nCr", 2, "Combinations nCr", fn=_nCr),
        OpSpec("rand", 0, "Random float [0,1)", fn=_rand),
        OpSpec("randint", 2, "Random int inclusive", fn=_randint),
        OpSpec("min", 2, "Minimum", fn=_min),
        OpSpec("max", 2, "Maximum", fn=_max),
        OpSpec("hypot", 2, "Hypotenuse", fn=_hypot),
        OpSpec("sgn", 1, "Sign (-1,0,1)", fn=_sgn),
        OpSpec("gcd", 2, "Greatest common divisor", fn=_gcd),
        OpSpec("lcm", 2, "Least common multiple", fn=_lcm),
        OpSpec("cmplx", 2, "Pack re im → complex", fn=_cmplx),
        OpSpec("polar", 2, "r∠θ → complex (θ uses angle_mode)", True, _polar),
        OpSpec("engshift", 2, "Engineering shift: x * 1000^n", fn=_engshift),
        OpSpec("re", 1, "Real part", fn=_re),
        OpSpec("im", 1, "Imaginary part", fn=_im),
        OpSpec("conj", 1, "Complex conjugate", fn=_conj),
        OpSpec("arg", 1, "Argument (angle mode)", True, _arg),
        OpSpec("RAD", 0, "Set angle mode to radians", True, _set_mode("rad")),
        OpSpec("DEG", 0, "Set angle mode to degrees", True, _set_mode("deg")),
        OpSpec("GRAD", 0, "Set angle mode to grads", True, _set_mode("grad")),
    ]
    out: dict[str, OpSpec] = {}
    for s in specs:
        out[s.name.lower()] = s
        out[s.name] = s
    # Preserve canonical names for listing
    return {s.name: s for s in specs}


OPS: dict[str, OpSpec] = _build_ops()
_OPS_LOOKUP = {k.lower(): v for k, v in OPS.items()}


def get_op(token: str) -> OpSpec | None:
    return _OPS_LOOKUP.get(token.lower())


def list_operations() -> list[dict[str, Any]]:
    return [
        {
            "name": op.name,
            "arity": op.arity,
            "description": op.description,
            "angle_sensitive": op.angle_sensitive,
        }
        for op in OPS.values()
    ]
