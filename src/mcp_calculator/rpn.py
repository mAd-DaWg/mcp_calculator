"""Safe RPN stack evaluator — tokenize + allowlist only (no eval)."""

from __future__ import annotations

import random
import re
from typing import Any

from mcp_calculator.constants import resolve_constant
from mcp_calculator.errors import CalcError, ok
from mcp_calculator.ops import get_op, Number

MAX_TOKENS = 10_000
MAX_EXPR_LEN = 100_000

# Numbers: optional sign handled as unary neg op preferred; allow 3, -2.5, 1e-3, 3+4j
_NUM_RE = re.compile(
    r"""
    ^
    (?:
        (?:[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)   # real
        (?:[+-](?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[jJ])?  # optional +imag j on same token
      | (?:[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[jJ])  # pure imag 4j
    )
    $
    """,
    re.VERBOSE,
)


def _parse_number(token: str) -> Number | None:
    if not _NUM_RE.match(token):
        return None
    try:
        if "j" in token.lower() and not token.lower().endswith("j"):
            return None
        # complex() accepts 3+4j, 4j, etc.
        if "j" in token.lower():
            return complex(token.replace("J", "j"))
        return float(token)
    except ValueError:
        return None


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


def serialize_number(x: Number) -> Any:
    if isinstance(x, complex):
        if abs(x.imag) < 1e-15:
            return float(x.real)
        return {"re": float(x.real), "im": float(x.imag)}
    return float(x)


def evaluate(
    expression: str,
    angle_mode: str = "rad",
    *,
    bindings: dict[str, float] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    if angle_mode not in ("rad", "deg", "grad"):
        raise CalcError(
            "invalid_angle_mode",
            f"angle_mode must be rad, deg, or grad; got {angle_mode!r}",
            'Pass angle_mode="deg" (or rad/grad), or insert token DEG/RAD/GRAD.',
            example='rpn_eval("30 sin", angle_mode="deg")',
        )

    if expression is None or not str(expression).strip():
        raise CalcError(
            "empty_expression",
            "Expression is empty",
            "Provide space-separated RPN tokens, e.g. 3 4 +.",
            example="3 4 +",
        )

    expr = str(expression)
    if len(expr) > MAX_EXPR_LEN:
        raise CalcError(
            "overflow",
            "Expression too long",
            f"Keep expression under {MAX_EXPR_LEN} characters.",
        )

    tokens = expr.split()
    if len(tokens) > MAX_TOKENS:
        raise CalcError(
            "overflow",
            "Too many tokens",
            f"Keep token count under {MAX_TOKENS}.",
        )

    stack: list[Number] = []
    mode = [angle_mode]
    ctx = {"angle_mode": mode, "rng": rng or random.Random()}
    bindings = bindings or {}

    from mcp_calculator.ops import OPS

    op_names = list(OPS.keys())
    from mcp_calculator.constants import CONSTANTS

    const_names = list(CONSTANTS.keys())

    for pos, token in enumerate(tokens):
        # Variable binding (calculus)
        if token in bindings or token.lower() in {k.lower(): k for k in bindings}:
            key = token if token in bindings else next(k for k in bindings if k.lower() == token.lower())
            stack.append(float(bindings[key]))
            continue

        num = _parse_number(token)
        if num is not None:
            stack.append(num)
            continue

        # Operators before constants so tokens like 're' mean real-part, not a constant name.
        op = get_op(token)
        if op is None:
            const = resolve_constant(token)
            if const is not None:
                stack.append(const)
                continue
            suggestion = _closest_name(token, op_names + const_names)
            raise CalcError(
                "unknown_token",
                f"Unknown token {token!r} at position {pos}",
                "Use list_operations / list_constants; RPN tokens only (no infix like 3+4).",
                token=token,
                position=pos,
                did_you_mean=suggestion,
                example="3 4 +",
            )

        if len(stack) < op.arity:
            raise CalcError(
                "stack_underflow",
                f"{op.name} needs {op.arity} value(s); stack had {len(stack)}",
                f"Push operands before {op.name}.",
                token=op.name,
                position=pos,
                op=op.name,
                arity=op.arity,
                stack_size=len(stack),
                example="30 sin" if op.name == "sin" else f"... {op.name}",
            )

        args = [stack.pop() for _ in range(op.arity)]
        args.reverse()
        result = op.fn(args, ctx)
        if result is not None:
            stack.append(result)

    if len(stack) == 0:
        raise CalcError(
            "stack_underflow",
            "No value left on stack",
            "Expression must leave exactly one result.",
            example="3 4 +",
        )
    if len(stack) > 1:
        raise CalcError(
            "leftover_stack",
            f"{len(stack)} values left after expression",
            "Combine leftovers with an op, or split into separate rpn_eval calls.",
            stack_size=len(stack),
            example="3 4 +",
        )

    return ok(
        result=serialize_number(stack[0]),
        expression=expr,
        angle_mode=mode[0],
    )


def eval_at(expression: str, x: float, angle_mode: str = "rad") -> float:
    """Evaluate RPN f(x) at a real x; used by calculus/solvers."""
    res = evaluate(expression, angle_mode=angle_mode, bindings={"x": x})
    val = res["result"]
    if isinstance(val, dict):
        raise CalcError(
            "domain_error",
            "Expression produced a complex value where a real was required",
            "Use a real-valued RPN expression in x.",
        )
    return float(val)
