"""Structured agent-facing error and success helpers."""

from __future__ import annotations

from typing import Any


def ok(**fields: Any) -> dict[str, Any]:
    return {"ok": True, **fields}


def fail(
    code: str,
    message: str,
    hint: str,
    *,
    example: str | None = None,
    did_you_mean: str | None = None,
    **context: Any,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": False,
        "error": code,
        "message": message,
        "hint": hint,
    }
    if example is not None:
        out["example"] = example
    if did_you_mean is not None:
        out["did_you_mean"] = did_you_mean
    for key, value in context.items():
        if value is not None:
            out[key] = value
    return out


class CalcError(Exception):
    """Raised inside calculators; converted to fail() dicts at tool boundary."""

    def __init__(
        self,
        code: str,
        message: str,
        hint: str,
        *,
        example: str | None = None,
        did_you_mean: str | None = None,
        **context: Any,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.example = example
        self.did_you_mean = did_you_mean
        self.context = context

    def to_dict(self) -> dict[str, Any]:
        return fail(
            self.code,
            self.message,
            self.hint,
            example=self.example,
            did_you_mean=self.did_you_mean,
            **self.context,
        )


def catch_calc(fn, *args, **kwargs) -> dict[str, Any]:
    try:
        result = fn(*args, **kwargs)
        if isinstance(result, dict) and "ok" in result:
            return result
        return ok(**result) if isinstance(result, dict) else ok(result=result)
    except CalcError as exc:
        return exc.to_dict()
    except Exception as exc:  # noqa: BLE001 — tool boundary must never crash
        return fail(
            "internal_error",
            f"Unexpected failure: {type(exc).__name__}",
            "Retry with simpler inputs. For unknown names call list_operations or "
            "list_constants; for units call list_unit_conversions. Read any prior hint/example.",
        )
