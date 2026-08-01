"""LIST utilities and Finance TVM solver."""

from __future__ import annotations

import math
from typing import Any

from mcp_calculator.errors import CalcError, ok
from mcp_calculator.infix import eval_at
from mcp_calculator.stats import _data


def list_op(
    op: str,
    *,
    data: list[float] | None = None,
    expression: str | None = None,
    start: float | None = None,
    end: float | None = None,
    step: float = 1.0,
    angle_mode: str = "rad",
) -> dict[str, Any]:
    """
    op: seq | cumsum | sort_a | sort_d | delta
    seq needs expression, start, end, optional step (seq).
    Others need data list.
    """
    o = (op or "").lower().strip()
    aliases = {
        "cumsum": "cumsum",
        "cum_sum": "cumsum",
        "sorta": "sort_a",
        "sort_asc": "sort_a",
        "sortd": "sort_d",
        "sort_desc": "sort_d",
        "deltalist": "delta",
        "delta_list": "delta",
        "Δlist": "delta",
    }
    o = aliases.get(o, o)

    if o == "seq":
        if expression is None or start is None or end is None:
            raise CalcError(
                "invalid_data",
                "seq requires expression, start, end",
                "seq(expr,x,begin,end[,step]).",
            )
        a, b, st = float(start), float(end), float(step)
        if st == 0:
            raise CalcError("invalid_data", "step must be non-zero", "Pass step ≠ 0.")
        if (b - a) * st < 0:
            raise CalcError("invalid_data", "step must move toward end", "Fix step sign.")
        est = int(abs((b - a) / st)) + 2
        if est > 100_000:
            raise CalcError(
                "overflow",
                "seq too long",
                "Increase step or shrink range (max 100000 points).",
            )
        out: list[float] = []
        x = a
        guard = 0
        while (st > 0 and x <= b + 1e-12) or (st < 0 and x >= b - 1e-12):
            out.append(eval_at(expression, x, angle_mode))
            x += st
            guard += 1
            if guard > 100_000:
                raise CalcError("overflow", "seq too long", "Increase step or shrink range.")
        return ok(op="seq", result=out, expression=expression, start=a, end=b, step=st)

    if data is None:
        raise CalcError("invalid_data", f"{o} requires data", "Pass a list of numbers.")
    xs = _data(data)

    if o == "cumsum":
        total = 0.0
        out = []
        for v in xs:
            total += v
            out.append(total)
        return ok(op="cumsum", result=out)

    if o in ("sort_a", "sorta"):
        return ok(op="sort_a", result=sorted(xs))

    if o in ("sort_d", "sortd"):
        return ok(op="sort_d", result=sorted(xs, reverse=True))

    if o == "delta":
        if len(xs) < 2:
            raise CalcError("invalid_data", "delta needs at least 2 elements", "Pass a longer list.")
        return ok(op="delta", result=[xs[i + 1] - xs[i] for i in range(len(xs) - 1)])

    raise CalcError(
        "invalid_data",
        f"Unknown list_op {op!r}",
        "Set op to seq, cumsum, sort_a, sort_d, or delta.",
        example="op='cumsum', data=[1,2,3]",
    )


def finance_tvm(
    solve_for: str,
    *,
    N: float | None = None,
    I: float | None = None,
    PV: float | None = None,
    PMT: float | None = None,
    FV: float | None = None,
    P_Y: float = 1.0,
    C_Y: float | None = None,
    begin: bool = False,
) -> dict[str, Any]:
    """
    TVM: solve for one of N, I, PV, PMT, FV.
    I is annual percent rate. P_Y payments/year, C_Y compounds/year (default = P_Y).
    begin=True → begin-mode payments (BGN); False → END.
    Convention: outflow negative / inflow positive as on typical TVM when consistent.
    Equation (END): PV*(1+i)^N + PMT*(1+i*g)*((1+i)^N-1)/i + FV = 0
    where i = (I/100)/(C_Y), N = N, g=1 if begin else 0; and payment period uses i_eff.
    Simplified calculator-compatible: i = (I/100)/P_Y, periods = N.
    """
    key = (solve_for or "").upper().strip().replace("%", "")
    if key in ("I%", "I"):
        key = "I"
    cy = float(C_Y) if C_Y is not None else float(P_Y)
    py = float(P_Y)
    if py <= 0 or cy <= 0:
        raise CalcError(
            "domain_error",
            "P_Y and C_Y must be > 0",
            "Pass positive payments-per-year P_Y and compounds-per-year C_Y (C_Y defaults to P_Y).",
            example="P_Y=12, C_Y=12",
        )

    vals = {"N": N, "I": I, "PV": PV, "PMT": PMT, "FV": FV}
    if key not in vals:
        raise CalcError(
            "invalid_data",
            f"solve_for must be N, I, PV, PMT, or FV; got {solve_for!r}",
            "Set solve_for to the unknown variable; provide numeric values for the other four.",
            example="solve_for='PMT', N=12, I=6, PV=-1000, FV=0",
        )
    known = {k: float(v) for k, v in vals.items() if k != key and v is not None}
    if len(known) != 4:
        raise CalcError(
            "invalid_data",
            "Provide the other four of N,I,PV,PMT,FV",
            "Leave only the unknown unset (or omit it) and set solve_for to that unknown. "
            f"Currently known: {sorted(known.keys())}; solve_for={key}.",
            example="solve_for='FV', N=10, I=5, PV=-100, PMT=0",
        )

    g = 1.0 if begin else 0.0

    def i_from_I(I_pct: float) -> float:
        # effective rate per payment: ((1+I/100/C_Y)^(C_Y/P_Y)-1)
        return (1 + I_pct / 100.0 / cy) ** (cy / py) - 1

    def balance(Nn: float, Ii: float, pv: float, pmt: float, fv: float) -> float:
        i = i_from_I(Ii)
        if abs(i) < 1e-14:
            return pv + pmt * Nn + fv
        factor = (1 + i) ** Nn
        return pv * factor + pmt * (1 + i * g) * (factor - 1) / i + fv

    if key == "FV":
        Nn, Ii, pv, pmt = known["N"], known["I"], known["PV"], known["PMT"]
        i = i_from_I(Ii)
        if abs(i) < 1e-14:
            fv = -(pv + pmt * Nn)
        else:
            factor = (1 + i) ** Nn
            fv = -(pv * factor + pmt * (1 + i * g) * (factor - 1) / i)
        return ok(solve_for="FV", FV=fv, N=Nn, I=Ii, PV=pv, PMT=pmt, P_Y=py, C_Y=cy, begin=begin)

    if key == "PV":
        Nn, Ii, pmt, fv = known["N"], known["I"], known["PMT"], known["FV"]
        i = i_from_I(Ii)
        if abs(i) < 1e-14:
            pv = -(fv + pmt * Nn)
        else:
            factor = (1 + i) ** Nn
            pv = -(fv + pmt * (1 + i * g) * (factor - 1) / i) / factor
        return ok(solve_for="PV", PV=pv, N=Nn, I=Ii, PMT=pmt, FV=fv, P_Y=py, C_Y=cy, begin=begin)

    if key == "PMT":
        Nn, Ii, pv, fv = known["N"], known["I"], known["PV"], known["FV"]
        i = i_from_I(Ii)
        if abs(i) < 1e-14:
            pmt = -(pv + fv) / Nn
        else:
            factor = (1 + i) ** Nn
            pmt = -(pv * factor + fv) / ((1 + i * g) * (factor - 1) / i)
        return ok(solve_for="PMT", PMT=pmt, N=Nn, I=Ii, PV=pv, FV=fv, P_Y=py, C_Y=cy, begin=begin)

    if key == "N":
        Ii, pv, pmt, fv = known["I"], known["PV"], known["PMT"], known["FV"]
        i = i_from_I(Ii)
        if abs(i) < 1e-14:
            if abs(pmt) < 1e-15:
                raise CalcError("domain_error", "Cannot solve N", "PMT≈0 with I≈0.")
            Nn = -(pv + fv) / pmt
        else:
            # PV*(1+i)^N + PMT*(1+i*g)*((1+i)^N-1)/i + FV = 0
            a = pv + pmt * (1 + i * g) / i
            b = fv - pmt * (1 + i * g) / i
            if a == 0 or -b / a <= 0:
                raise CalcError("domain_error", "Cannot solve N for these cash flows", "Check signs.")
            Nn = math.log(-b / a) / math.log(1 + i)
        return ok(solve_for="N", N=Nn, I=Ii, PV=pv, PMT=pmt, FV=fv, P_Y=py, C_Y=cy, begin=begin)

    # key == I — numeric solve
    Nn, pv, pmt, fv = known["N"], known["PV"], known["PMT"], known["FV"]

    def f(I_pct: float) -> float:
        return balance(Nn, I_pct, pv, pmt, fv)

    lo, hi = -99.0, 1000.0
    flo, fhi = f(lo), f(hi)
    # expand if needed
    for _ in range(40):
        if flo * fhi <= 0:
            break
        lo -= 50
        hi += 200
        flo, fhi = f(lo), f(hi)
    else:
        raise CalcError("no_root", "Cannot find interest rate", "Check cash-flow signs.")
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < 1e-10 or abs(hi - lo) < 1e-10:
            return ok(
                solve_for="I",
                I=mid,
                N=Nn,
                PV=pv,
                PMT=pmt,
                FV=fv,
                P_Y=py,
                C_Y=cy,
                begin=begin,
            )
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    raise CalcError("convergence_failed", "I% solve did not converge", "Retry with different guesses.")
