"""Math and physics constants (NIST CODATA 2022 values where applicable)."""

from __future__ import annotations

import math
from typing import Any

# CODATA 2022 / SI exact values (NIST physics.nist.gov/cuu/Constants)
# Source year documented for agents via list_constants.
CODATA_YEAR = 2022

CONSTANTS: dict[str, dict[str, Any]] = {
    # Math
    "pi": {"value": math.pi, "unit": "1", "note": "Archimedes' constant"},
    "e": {"value": math.e, "unit": "1", "note": "Euler's number (not elementary charge)"},
    "euler": {"value": math.e, "unit": "1", "note": "Alias for e (Euler's number)"},
    "tau": {"value": math.tau, "unit": "1", "note": "2*pi"},
    "phi": {"value": (1 + math.sqrt(5)) / 2, "unit": "1", "note": "Golden ratio"},
    "inf": {"value": math.inf, "unit": "1", "note": "Positive infinity"},
    # Casio-catalog coverage checklist — values from CODATA 2022 / SI
    "mp": {"value": 1.67262192595e-27, "unit": "kg", "note": "proton mass", "casio": 1},
    "mn": {"value": 1.67492750056e-27, "unit": "kg", "note": "neutron mass", "casio": 2},
    "me": {"value": 9.1093837139e-31, "unit": "kg", "note": "electron mass", "casio": 3},
    "mmu": {"value": 1.883531627e-28, "unit": "kg", "note": "muon mass", "casio": 4},
    "a0": {"value": 5.29177210544e-11, "unit": "m", "note": "Bohr radius", "casio": 5},
    "h": {"value": 6.62607015e-34, "unit": "J s", "note": "Planck constant (exact)", "casio": 6},
    "muN": {"value": 5.0507837393e-27, "unit": "J T^-1", "note": "nuclear magneton", "casio": 7},
    "muB": {"value": 9.2740100657e-24, "unit": "J T^-1", "note": "Bohr magneton", "casio": 8},
    "hbar": {"value": 1.0545718176461565e-34, "unit": "J s", "note": "reduced Planck constant", "casio": 9},
    "alpha": {"value": 7.2973525643e-3, "unit": "1", "note": "fine-structure constant", "casio": 10},
    "r_e": {"value": 2.8179403205e-15, "unit": "m", "note": "classical electron radius (token r_e; op 're' is real-part)", "casio": 11},
    "lambdaC": {"value": 2.42631023538e-12, "unit": "m", "note": "Compton wavelength", "casio": 12},
    "gammap": {"value": 2.6752218708e8, "unit": "s^-1 T^-1", "note": "proton gyromagnetic ratio", "casio": 13},
    "lambdaCp": {"value": 1.32140985539e-15, "unit": "m", "note": "proton Compton wavelength", "casio": 14},
    "lambdaCn": {"value": 1.31959090382e-15, "unit": "m", "note": "neutron Compton wavelength", "casio": 15},
    "Rinf": {"value": 10973731.568157, "unit": "m^-1", "note": "Rydberg constant", "casio": 16},
    "u": {"value": 1.66053906892e-27, "unit": "kg", "note": "atomic mass unit", "casio": 17},
    "mup": {"value": 1.41060679545e-26, "unit": "J T^-1", "note": "proton magnetic moment", "casio": 18},
    "mue": {"value": -9.2847646917e-24, "unit": "J T^-1", "note": "electron magnetic moment", "casio": 19},
    "mun": {"value": -9.6623653e-27, "unit": "J T^-1", "note": "neutron magnetic moment", "casio": 20},
    "mumu": {"value": -4.49044830e-26, "unit": "J T^-1", "note": "muon magnetic moment", "casio": 21},
    "F": {"value": 96485.3321, "unit": "C mol^-1", "note": "Faraday constant", "casio": 22},
    "qe": {"value": 1.602176634e-19, "unit": "C", "note": "elementary charge (exact); use qe not e", "casio": 23},
    "echarge": {"value": 1.602176634e-19, "unit": "C", "note": "Alias for qe"},
    "NA": {"value": 6.02214076e23, "unit": "mol^-1", "note": "Avogadro constant (exact)", "casio": 24},
    "k": {"value": 1.380649e-23, "unit": "J K^-1", "note": "Boltzmann constant (exact)", "casio": 25},
    "k_B": {"value": 1.380649e-23, "unit": "J K^-1", "note": "Alias for k"},
    "Vm": {"value": 22.71095464e-3, "unit": "m^3 mol^-1", "note": "molar volume ideal gas (273.15 K, 100 kPa)", "casio": 26},
    "R": {"value": 8.314462618, "unit": "J mol^-1 K^-1", "note": "molar gas constant", "casio": 27},
    "c": {"value": 299792458.0, "unit": "m s^-1", "note": "speed of light (exact)", "casio": 28},
    "c1": {"value": 3.741771852e-16, "unit": "W m^2", "note": "first radiation constant", "casio": 29},
    "c2": {"value": 1.438776877e-2, "unit": "m K", "note": "second radiation constant", "casio": 30},
    "sigma": {"value": 5.670374419e-8, "unit": "W m^-2 K^-4", "note": "Stefan-Boltzmann constant", "casio": 31},
    "eps0": {"value": 8.8541878188e-12, "unit": "F m^-1", "note": "vacuum electric permittivity", "casio": 32},
    "epsilon0": {"value": 8.8541878188e-12, "unit": "F m^-1", "note": "Alias for eps0"},
    "mu0": {"value": 1.25663706127e-6, "unit": "N A^-2", "note": "vacuum magnetic permeability", "casio": 33},
    "Phi0": {"value": 2.067833848e-15, "unit": "Wb", "note": "magnetic flux quantum", "casio": 34},
    "g": {"value": 9.80665, "unit": "m s^-2", "note": "standard acceleration of gravity", "casio": 35},
    "G0": {"value": 7.748091729e-5, "unit": "S", "note": "conductance quantum", "casio": 36},
    "Z0": {"value": 376.730313412, "unit": "ohm", "note": "characteristic impedance of vacuum", "casio": 37},
    "t0C": {"value": 273.15, "unit": "K", "note": "0 °C in kelvin", "casio": 38},
    "G": {"value": 6.67430e-11, "unit": "m^3 kg^-1 s^-2", "note": "Newtonian constant of gravitation", "casio": 39},
    "atm": {"value": 101325.0, "unit": "Pa", "note": "standard atmosphere", "casio": 40},
}

# Case-insensitive lookup only when unambiguous (muN vs mun collide if lowercased)
_LOOKUP: dict[str, str] = {}
_AMBIGUOUS_LOWER: set[str] = set()
for _name in CONSTANTS:
    low = _name.lower()
    if low in _AMBIGUOUS_LOWER:
        continue
    if low in _LOOKUP and _LOOKUP[low] != _name:
        _LOOKUP.pop(low, None)
        _AMBIGUOUS_LOWER.add(low)
    else:
        _LOOKUP[low] = _name


def resolve_constant(token: str) -> float | None:
    if token in CONSTANTS:
        return float(CONSTANTS[token]["value"])
    key = _LOOKUP.get(token.lower())
    if key is None:
        return None
    return float(CONSTANTS[key]["value"])


def list_constants() -> list[dict[str, Any]]:
    out = []
    for name, meta in CONSTANTS.items():
        item = {
            "name": name,
            "value": meta["value"],
            "unit": meta["unit"],
            "note": meta.get("note", ""),
            "codata_year": CODATA_YEAR,
        }
        if "casio" in meta:
            item["casio_index"] = meta["casio"]
        out.append(item)
    return out
