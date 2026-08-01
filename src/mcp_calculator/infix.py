"""Infix expression lexer + shunting-yard → RPN tokens (no eval)."""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from typing import Any

from mcp_calculator.constants import CONSTANTS, resolve_constant
from mcp_calculator.errors import CalcError
from mcp_calculator.ops import OPS, get_op
from mcp_calculator import rpn as rpn_mod

MAX_EXPR_LEN = 100_000
MAX_TOKENS = 10_000

# Real or complex number literals (same spirit as rpn._NUM_RE)
_NUM_RE = re.compile(
    r"""
    (?:
        (?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?          # real
        (?:[+-](?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[jJ])?  # optional +imagj
      | (?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[jJ]       # pure imag
    )
    """,
    re.VERBOSE,
)

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# SI engineering prefixes (scientific calculator Engineer Symbol)
_ENG_PREFIX = {
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "μ": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
    "P": 1e15,
    "E": 1e18,
}

_ANGLE_SUFFIX_WORD = {"deg": "deg", "rad": "rad", "grad": "grad"}


def _to_rad(value: float, unit: str) -> float:
    if unit == "deg":
        return value * math.pi / 180.0
    if unit == "grad":
        return value * math.pi / 200.0
    return value


def _from_rad(radians: float, unit: str) -> float:
    if unit == "deg":
        return radians * 180.0 / math.pi
    if unit == "grad":
        return radians * 200.0 / math.pi
    return radians


def _convert_angle_value(value: float, from_unit: str, to_unit: str) -> float:
    return _from_rad(_to_rad(value, from_unit), to_unit)


def _parse_real_token(text: str) -> float:
    return float(text)


@dataclass(frozen=True)
class Tok:
    kind: str  # num, ident, op, lparen, rparen, comma, bang, pow
    value: str
    pos: int


def _closest_name(token: str, names: list[str]) -> str | None:
    t = token.lower()
    best = None
    best_score = 0
    for name in names:
        n = name.lower()
        if n.startswith(t) or t.startswith(n):
            score = min(len(n), len(t))
            if score > best_score:
                best_score = score
                best = name
        elif t in n or n in t:
            score = 1
            if score > best_score:
                best_score = score
                best = name
    return best if best_score > 0 else None


def _match_eng_suffix(s: str, i: int) -> tuple[str, float] | None:
    """Return (suffix, factor) if s[i:] starts with an engineering symbol suffix."""
    if i >= len(s):
        return None
    ch = s[i]
    if ch in _ENG_PREFIX:
        # glued suffix: not followed by another letter/digit/_ (except μ is one char)
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if nxt and (nxt.isalnum() or nxt == "_"):
            return None
        return ch, _ENG_PREFIX[ch]
    return None


def _match_angle_suffix(s: str, i: int) -> tuple[str, int] | None:
    """Return (unit, end_index) for ° / r / g / deg / rad / grad after a number."""
    if i >= len(s):
        return None
    ch = s[i]
    if ch in ("°", "˚"):
        return "deg", i + 1
    # word suffixes deg/rad/grad
    m = _IDENT_RE.match(s, i)
    if m:
        word = m.group(0).lower()
        if word in _ANGLE_SUFFIX_WORD:
            return _ANGLE_SUFFIX_WORD[word], m.end()
    # single-letter r / g (not start of a longer identifier)
    if ch in ("r", "g"):
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if nxt and (nxt.isalnum() or nxt == "_"):
            return None
        return ("rad" if ch == "r" else "grad"), i + 1
    return None


def tokenize(expression: str, *, angle_mode: str = "rad") -> list[Tok]:
    s = expression
    i = 0
    n = len(s)
    out: list[Tok] = []
    mode = angle_mode if angle_mode in ("rad", "deg", "grad") else "rad"
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "(":
            out.append(Tok("lparen", "(", i))
            i += 1
            continue
        if ch == ")":
            out.append(Tok("rparen", ")", i))
            i += 1
            continue
        if ch == ",":
            out.append(Tok("comma", ",", i))
            i += 1
            continue
        if ch == "!":
            out.append(Tok("bang", "!", i))
            i += 1
            continue
        if ch in ("∠", "∟"):
            out.append(Tok("op", "∠", i))
            i += 1
            continue
        if ch == "*" and i + 1 < n and s[i + 1] == "*":
            out.append(Tok("op", "^", i))
            i += 2
            continue
        if ch in "+-*/^%":
            out.append(Tok("op", ch, i))
            i += 1
            continue
        m = _NUM_RE.match(s, i)
        if m:
            raw = m.group(0)
            pos = i
            i = m.end()
            # skip complex literals for eng/angle suffixes
            if "j" in raw.lower():
                out.append(Tok("num", raw, pos))
                continue
            eng = _match_eng_suffix(s, i)
            # apply eng and/or angle suffix if glued to the number
            j = i
            val = None
            if eng is not None:
                suf, factor = eng
                val = _parse_real_token(raw) * factor
                j = i + len(suf)
            ang = _match_angle_suffix(s, j)
            if ang is not None:
                unit, end = ang
                if val is None:
                    val = _parse_real_token(raw)
                val = _convert_angle_value(val, unit, mode)
                j = end
            if eng is not None or ang is not None:
                # normalized float token after suffix conversion
                if val is not None and abs(val - round(val)) < 1e-12 and abs(val) < 1e15:
                    num_s = str(int(round(val)))
                else:
                    num_s = repr(float(val))
                out.append(Tok("num", num_s, pos))
                i = j
            else:
                out.append(Tok("num", raw, pos))
                i = m.end()
            continue
        m = _IDENT_RE.match(s, i)
        if m:
            out.append(Tok("ident", m.group(0), i))
            i = m.end()
            continue
        raise CalcError(
            "unknown_token",
            f"Unexpected character {ch!r} at position {i}",
            "Use infix maths like 90+(40-30), sin(30°), 2∠30, or 500k.",
            example="90+(40-30)",
            position=i,
            token=ch,
        )
    return out


def _insert_implicit_mul(tokens: list[Tok]) -> list[Tok]:
    """Insert * between juxtaposed factors: 2pi, 2(3), (1)(2), 2x, )sin, etc."""
    if not tokens:
        return tokens
    out: list[Tok] = [tokens[0]]
    for tok in tokens[1:]:
        prev = out[-1]
        left_val = prev.kind in ("num", "ident", "rparen", "bang")
        right_val = tok.kind in ("num", "ident", "lparen")
        if left_val and right_val:
            if not (prev.kind == "ident" and tok.kind == "lparen"):
                out.append(Tok("op", "*", prev.pos))
        out.append(tok)
    return out


# Binary op precedence (higher = tighter). Unary handled separately.
# ∠ binds like a tight constructor between r and θ (above *).
_PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "%": 2, "∠": 3, "^": 4}
_RIGHT_ASSOC = {"^"}


def _is_value_token(kind: str) -> bool:
    return kind in ("num", "ident", "rparen", "bang")


def to_rpn(
    expression: str,
    *,
    allow_bindings: set[str] | None = None,
    angle_mode: str = "rad",
) -> list[str]:
    """Convert infix expression to RPN token list."""
    if expression is None or not str(expression).strip():
        raise CalcError(
            "empty_expression",
            "Expression is empty",
            "Provide an infix expression, e.g. 90+(40-30).",
            example="90+(40-30)",
        )
    expr = str(expression)
    if len(expr) > MAX_EXPR_LEN:
        raise CalcError(
            "overflow",
            "Expression too long",
            f"Keep expression under {MAX_EXPR_LEN} characters.",
        )

    raw = tokenize(expr, angle_mode=angle_mode)
    tokens = _insert_implicit_mul(raw)
    if len(tokens) > MAX_TOKENS:
        raise CalcError(
            "overflow",
            "Too many tokens",
            f"Keep token count under {MAX_TOKENS}.",
        )

    bindings = {b.lower() for b in (allow_bindings or set())} | {"x"}
    output: list[str] = []
    ops: list[Any] = []  # Tok | ("fn", name, arity_slots, pos) | ("unary", pos)

    def tip_is_lparen() -> bool:
        return bool(ops) and isinstance(ops[-1], Tok) and ops[-1].kind == "lparen"

    def flush_until_lparen() -> None:
        while ops and not tip_is_lparen():
            _pop_op(ops, output)
        if not ops:
            raise CalcError(
                "invalid_data",
                "Mismatched parentheses",
                "Check that every '(' has a matching ')'.",
                example="90+(40-30)",
            )

    expect_operand = True  # start expecting a value / unary / function
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.kind == "num":
            if not expect_operand:
                raise CalcError(
                    "invalid_data",
                    f"Unexpected number {tok.value!r} at position {tok.pos}",
                    "Insert an operator between values, e.g. 2*3.",
                    example="2*3",
                    position=tok.pos,
                )
            output.append(tok.value)
            expect_operand = False
            i += 1
            continue

        if tok.kind == "ident":
            # Function call if followed by (
            if i + 1 < len(tokens) and tokens[i + 1].kind == "lparen":
                if not expect_operand:
                    raise CalcError(
                        "invalid_data",
                        f"Unexpected function {tok.value!r} at position {tok.pos}",
                        "Insert an operator before the function, e.g. 2*sin(x).",
                        example="2*sin(x)",
                        position=tok.pos,
                    )
                name = tok.value
                op = get_op(name)
                if op is None:
                    suggestion = _closest_name(name, list(OPS.keys()) + list(CONSTANTS.keys()))
                    raise CalcError(
                        "unknown_token",
                        f"Unknown function {name!r} at position {tok.pos}",
                        "Call list_operations for function names, e.g. sin(30), sqrt(9).",
                        token=name,
                        position=tok.pos,
                        did_you_mean=suggestion,
                        example="sin(30)",
                    )
                # Push function frame: after '(', we track args
                ops.append(("fn", op.name, op.arity, tok.pos, [0]))  # last: arg count box
                ops.append(Tok("lparen", "(", tokens[i + 1].pos))
                expect_operand = True
                i += 2  # skip ident and (
                continue

            # Bare identifier: constant or binding
            if not expect_operand:
                raise CalcError(
                    "invalid_data",
                    f"Unexpected name {tok.value!r} at position {tok.pos}",
                    "Insert an operator, or use function call syntax name(...).",
                    example="2*pi",
                    position=tok.pos,
                )
            low = tok.value.lower()
            if low in bindings or resolve_constant(tok.value) is not None:
                output.append(tok.value)
                expect_operand = False
                i += 1
                continue
            suggestion = _closest_name(tok.value, list(OPS.keys()) + list(CONSTANTS.keys()))
            raise CalcError(
                "unknown_token",
                f"Unknown name {tok.value!r} at position {tok.pos}",
                "Use a constant (list_constants), variable x, or function call like sin(x).",
                token=tok.value,
                position=tok.pos,
                did_you_mean=suggestion,
                example="pi/2",
            )

        if tok.kind == "op":
            if expect_operand:
                if tok.value == "-":
                    # unary minus — precedence between * and ^ so -2^2 → -(2^2)
                    while ops and isinstance(ops[-1], tuple) and ops[-1][0] == "unary":
                        _pop_op(ops, output)
                    # also pop higher-precedence binary? unary shouldn't sit under higher on stack incorrectly
                    ops.append(("unary", tok.pos))
                    expect_operand = True
                    i += 1
                    continue
                if tok.value == "+":
                    # unary plus: no-op
                    i += 1
                    continue
                raise CalcError(
                    "invalid_data",
                    f"Unexpected operator {tok.value!r} at position {tok.pos}",
                    "Expected a value, unary minus, or function call.",
                    example="90+(40-30)",
                    position=tok.pos,
                )
            # binary
            prec = _PREC[tok.value]
            while ops:
                top = ops[-1]
                if isinstance(top, tuple) and top[0] == "unary":
                    # unary prec 3; binary * is 2, ∠ is 3, ^ is 4
                    u_prec = 3
                    if u_prec > prec or (u_prec == prec and tok.value not in _RIGHT_ASSOC):
                        _pop_op(ops, output)
                        continue
                    break
                if isinstance(top, Tok) and top.kind == "op":
                    top_prec = _PREC[top.value]
                    if top_prec > prec or (
                        top_prec == prec and top.value not in _RIGHT_ASSOC
                    ):
                        _pop_op(ops, output)
                        continue
                    break
                break
            ops.append(tok)
            expect_operand = True
            i += 1
            continue

        if tok.kind == "bang":
            if expect_operand:
                raise CalcError(
                    "invalid_data",
                    f"Unexpected '!' at position {tok.pos}",
                    "Factorial is postfix, e.g. 5!.",
                    example="5!",
                    position=tok.pos,
                )
            # pop unaries of higher/equal — factorial binds tightest on the value
            while ops and isinstance(ops[-1], tuple) and ops[-1][0] == "unary":
                _pop_op(ops, output)
            output.append("fact")
            expect_operand = False
            i += 1
            continue

        if tok.kind == "lparen":
            if not expect_operand:
                raise CalcError(
                    "invalid_data",
                    f"Unexpected '(' at position {tok.pos}",
                    "Insert '*' for implicit products if needed, e.g. 2*(3+4).",
                    example="2*(3+4)",
                    position=tok.pos,
                )
            ops.append(tok)
            expect_operand = True
            i += 1
            continue

        if tok.kind == "comma":
            flush_until_lparen()
            # increment enclosing function arg count
            if len(ops) >= 2 and isinstance(ops[-2], tuple) and ops[-2][0] == "fn":
                ops[-2][4][0] += 1
            else:
                raise CalcError(
                    "invalid_data",
                    f"Unexpected ',' at position {tok.pos}",
                    "Commas separate function arguments, e.g. atan2(y, x).",
                    example="atan2(1, 2)",
                    position=tok.pos,
                )
            expect_operand = True
            i += 1
            continue

        if tok.kind == "rparen":
            flush_until_lparen()
            ops.pop()  # '('
            # function close?
            if ops and isinstance(ops[-1], tuple) and ops[-1][0] == "fn":
                fn = ops.pop()
                _, name, arity, pos, box = fn
                # arg count: if we saw any content since '(', args = commas+1; empty = 0
                # Heuristic: if expect_operand is True right after '(', empty call.
                # We track commas in box[0]. Empty: never got an operand after '('.
                # Simpler: use a flag on fn frame for "seen_arg".
                n_commas = box[0]
                # Determine empty vs non-empty: if still expect_operand and n_commas==0
                # and nothing was pushed for this arg — empty call.
                # Actually after parsing an arg, expect_operand is False.
                # After '(' or ',', expect_operand True.
                # On ')': if expect_operand and n_commas==0 → empty (0 args)
                # if expect_operand and n_commas>0 → trailing comma error
                # if not expect_operand → args = n_commas+1
                if expect_operand:
                    if n_commas == 0:
                        nargs = 0
                    else:
                        raise CalcError(
                            "invalid_data",
                            f"Trailing comma in {name}(...) at position {tok.pos}",
                            f"Pass {arity} argument(s) to {name}.",
                            example=f"{name}(" + ",".join(["…"] * arity) + ")",
                            position=tok.pos,
                        )
                else:
                    nargs = n_commas + 1
                if nargs != arity:
                    raise CalcError(
                        "invalid_data",
                        f"{name} expects {arity} argument(s), got {nargs}",
                        f"Call {name} with {arity} argument(s).",
                        example=(
                            f"{name}()"
                            if arity == 0
                            else f"{name}(" + ", ".join(f"a{j+1}" for j in range(arity)) + ")"
                        ),
                        position=pos,
                    )
                output.append(name)
                expect_operand = False
            else:
                # grouping paren
                if expect_operand:
                    raise CalcError(
                        "invalid_data",
                        f"Empty parentheses at position {tok.pos}",
                        "Parentheses must contain an expression.",
                        example="(1+2)",
                        position=tok.pos,
                    )
                expect_operand = False
            i += 1
            continue

        raise CalcError(
            "internal_error",
            f"Unhandled token kind {tok.kind}",
            "Retry with a simpler expression.",
        )

    if expect_operand and (output or ops):
        raise CalcError(
            "invalid_data",
            "Expression ends unexpectedly",
            "Check for a trailing operator or missing operand.",
            example="90+(40-30)",
        )

    while ops:
        top = ops[-1]
        if isinstance(top, Tok) and top.kind == "lparen":
            raise CalcError(
                "invalid_data",
                "Mismatched parentheses",
                "Check that every '(' has a matching ')'.",
                example="90+(40-30)",
            )
        if isinstance(top, tuple) and top[0] == "fn":
            raise CalcError(
                "invalid_data",
                "Mismatched parentheses in function call",
                "Close every function call with ')'.",
                example="sin(30)",
            )
        _pop_op(ops, output)

    if not output:
        raise CalcError(
            "empty_expression",
            "Expression is empty",
            "Provide an infix expression, e.g. 90+(40-30).",
            example="90+(40-30)",
        )
    if len(output) > MAX_TOKENS:
        raise CalcError(
            "overflow",
            "Too many tokens",
            f"Keep token count under {MAX_TOKENS}.",
        )
    return output


def _pop_op(ops: list[Any], output: list[str]) -> None:
    top = ops.pop()
    if isinstance(top, tuple) and top[0] == "unary":
        output.append("neg")
        return
    if isinstance(top, Tok) and top.kind == "op":
        if top.value == "∠":
            output.append("polar")
        else:
            output.append(top.value)
        return
    raise CalcError(
        "internal_error",
        f"Cannot pop {top!r}",
        "Retry with a simpler expression.",
    )


def evaluate_infix(
    expression: str,
    angle_mode: str = "rad",
    *,
    bindings: dict[str, float] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Parse infix → RPN tokens → evaluate with the stack engine."""
    allow = set(bindings.keys()) if bindings else set()
    tokens = to_rpn(expression, allow_bindings=allow, angle_mode=angle_mode)
    rpn_str = " ".join(tokens)
    result = rpn_mod.evaluate(
        rpn_str,
        angle_mode=angle_mode,
        bindings=bindings,
        rng=rng,
    )
    result["expression"] = str(expression)
    result["rpn"] = rpn_str
    return result


def eval_at(expression: str, x: float, angle_mode: str = "rad") -> float:
    """Evaluate infix f(x) at a real x; used by calculus/solvers."""
    res = evaluate_infix(expression, angle_mode=angle_mode, bindings={"x": x})
    val = res["result"]
    if isinstance(val, dict):
        raise CalcError(
            "domain_error",
            "Expression produced a complex value where a real was required",
            "Use a real-valued expression in x.",
        )
    return float(val)
