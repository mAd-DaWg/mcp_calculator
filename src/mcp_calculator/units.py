"""Metric / unit conversion table (scientific calculator breadth)."""

from __future__ import annotations

from typing import Any

from mcp_calculator.errors import CalcError, ok

# factor: multiply value_in_from by factor to get value_in_to
# id -> (from_unit, to_unit, factor)
CONVERSIONS: dict[str, tuple[str, str, float]] = {
    # length
    "in_to_cm": ("in", "cm", 2.54),
    "cm_to_in": ("cm", "in", 1 / 2.54),
    "ft_to_m": ("ft", "m", 0.3048),
    "m_to_ft": ("m", "ft", 1 / 0.3048),
    "yd_to_m": ("yd", "m", 0.9144),
    "m_to_yd": ("m", "yd", 1 / 0.9144),
    "mile_to_km": ("mile", "km", 1.609344),
    "km_to_mile": ("km", "mile", 1 / 1.609344),
    "nmi_to_m": ("nmi", "m", 1852.0),
    "m_to_nmi": ("m", "nmi", 1 / 1852.0),
    "pc_to_km": ("pc", "km", 3.085677581e13),
    "km_to_pc": ("km", "pc", 1 / 3.085677581e13),
    # area
    "acre_to_m2": ("acre", "m2", 4046.8564224),
    "m2_to_acre": ("m2", "acre", 1 / 4046.8564224),
    "ha_to_m2": ("ha", "m2", 10000.0),
    "m2_to_ha": ("m2", "ha", 1 / 10000.0),
    # volume
    "gal_to_L": ("gal", "L", 3.785411784),
    "L_to_gal": ("L", "gal", 1 / 3.785411784),
    "floz_to_mL": ("floz", "mL", 29.5735295625),
    "mL_to_floz": ("mL", "floz", 1 / 29.5735295625),
    # mass
    "oz_to_g": ("oz", "g", 28.349523125),
    "g_to_oz": ("g", "oz", 1 / 28.349523125),
    "lb_to_kg": ("lb", "kg", 0.45359237),
    "kg_to_lb": ("kg", "lb", 1 / 0.45359237),
    # pressure / force / energy-ish
    "atm_to_Pa": ("atm", "Pa", 101325.0),
    "Pa_to_atm": ("Pa", "atm", 1 / 101325.0),
    "mmHg_to_Pa": ("mmHg", "Pa", 133.322387415),
    "Pa_to_mmHg": ("Pa", "mmHg", 1 / 133.322387415),
    "lbf_to_N": ("lbf", "N", 4.4482216152605),
    "N_to_lbf": ("N", "lbf", 1 / 4.4482216152605),
    "kgf_to_N": ("kgf", "N", 9.80665),
    "N_to_kgf": ("N", "kgf", 1 / 9.80665),
    "cal_to_J": ("cal", "J", 4.184),
    "J_to_cal": ("J", "cal", 1 / 4.184),
    "hp_to_W": ("hp", "W", 745.6998715822702),
    "W_to_hp": ("W", "hp", 1 / 745.6998715822702),
    # temperature offsets handled specially
    "C_to_F": ("C", "F", float("nan")),  # special
    "F_to_C": ("F", "C", float("nan")),
    "C_to_K": ("C", "K", float("nan")),
    "K_to_C": ("K", "C", float("nan")),
    "F_to_K": ("F", "K", float("nan")),
    "K_to_F": ("K", "F", float("nan")),
}

_PAIR_INDEX = {(fr, to): cid for cid, (fr, to, _) in CONVERSIONS.items()}


def list_unit_conversions() -> list[dict[str, Any]]:
    out = []
    for cid, (fr, to, factor) in CONVERSIONS.items():
        item: dict[str, Any] = {"id": cid, "from": fr, "to": to}
        if factor == factor:  # not NaN
            item["factor"] = factor
        else:
            item["note"] = "affine temperature conversion"
        out.append(item)
    return out


def _temp_convert(value: float, fr: str, to: str) -> float:
    # normalize to K then out
    if fr == "C":
        k = value + 273.15
    elif fr == "F":
        k = (value - 32) * 5 / 9 + 273.15
    elif fr == "K":
        k = value
    else:
        raise CalcError("unknown_conversion", f"Unknown temp unit {fr}", "Use C, F, or K.")
    if to == "K":
        return k
    if to == "C":
        return k - 273.15
    if to == "F":
        return (k - 273.15) * 9 / 5 + 32
    raise CalcError("unknown_conversion", f"Unknown temp unit {to}", "Use C, F, or K.")


def convert_unit(
    value: float,
    conversion_id: str | None = None,
    from_unit: str | None = None,
    to_unit: str | None = None,
) -> dict[str, Any]:
    if conversion_id:
        cid = conversion_id.strip()
        if cid not in CONVERSIONS:
            raise CalcError(
                "unknown_conversion",
                f"No conversion id {cid!r}",
                "Call list_unit_conversions and pick a listed id.",
                example="mile_to_km",
            )
        fr, to, factor = CONVERSIONS[cid]
    elif from_unit and to_unit:
        fr, to = from_unit.strip(), to_unit.strip()
        cid = _PAIR_INDEX.get((fr, to))
        if cid is None:
            raise CalcError(
                "unknown_conversion",
                f"No conversion {fr}→{to}",
                "Call list_unit_conversions and pick a listed id/pair.",
            )
        factor = CONVERSIONS[cid][2]
    else:
        raise CalcError(
            "invalid_data",
            "Provide conversion_id or from_unit and to_unit",
            "Example: conversion_id='mile_to_km' or from_unit='mile', to_unit='km'.",
        )

    v = float(value)
    if fr in ("C", "F", "K") and to in ("C", "F", "K"):
        out = _temp_convert(v, fr, to)
    else:
        out = v * factor
    return ok(value=out, from_unit=fr, to_unit=to, conversion_id=cid)
