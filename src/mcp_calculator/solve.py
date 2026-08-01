"""Linear systems, numeric roots (Brent/Newton), low-degree polynomials."""

from __future__ import annotations

import cmath
import math
from typing import Any

from mcp_calculator.errors import CalcError, ok
from mcp_calculator.infix import eval_at

MAX_DIM = 32


def solve_linear(
    coefficients: list[list[float]] | None = None,
    A: list[list[float]] | None = None,
    b: list[float] | None = None,
) -> dict[str, Any]:
    """Solve Ax=b. Pass augmented matrix as coefficients, or A and b separately."""
    if coefficients is not None:
        aug = [list(map(float, row)) for row in coefficients]
        if not aug or not aug[0]:
            raise CalcError("invalid_data", "Empty system", "Pass a non-empty augmented matrix.")
        n = len(aug)
        m = len(aug[0])
        if m != n + 1:
            raise CalcError(
                "dimension_error",
                f"Augmented matrix should be n×(n+1); got {n}×{m}",
                "Each row is [a_i1,...,a_in,b_i].",
            )
        mat = [row[:-1] for row in aug]
        rhs = [row[-1] for row in aug]
    else:
        if A is None or b is None:
            raise CalcError(
                "invalid_data",
                "Provide coefficients (augmented) or A and b",
                "Example: A=[[2,1],[1,3]], b=[1,2].",
            )
        mat = [list(map(float, row)) for row in A]
        rhs = list(map(float, b))
        n = len(mat)
        if n == 0 or len(mat[0]) != n or len(rhs) != n:
            raise CalcError(
                "dimension_error",
                "A must be square and match b length",
                "Ensure A is n×n and b has length n.",
            )

    if n > MAX_DIM:
        raise CalcError(
            "overflow",
            f"System exceeds max dimension {MAX_DIM}",
            f"Use at most {MAX_DIM} equations (n <= {MAX_DIM}).",
        )

    # Gaussian elimination with partial pivoting
    a = [mat[i][:] + [rhs[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-14:
            # Check inconsistency vs infinite
            for r in range(col, n):
                if abs(a[r][n]) > 1e-10:
                    raise CalcError(
                        "no_unique_solution",
                        "System is inconsistent (no solution)",
                        "Check equations for contradictions.",
                    )
            raise CalcError(
                "no_unique_solution",
                "System has infinitely many solutions (or is singular)",
                "Provide a full-rank coefficient matrix for a unique solution.",
            )
        a[col], a[pivot] = a[pivot], a[col]
        piv = a[col][col]
        for r in range(col + 1, n):
            factor = a[r][col] / piv
            for c in range(col, n + 1):
                a[r][c] -= factor * a[col][c]

    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        if abs(a[i][i]) < 1e-14:
            raise CalcError(
                "no_unique_solution",
                "Singular system during back-substitution",
                "Check for dependent rows.",
            )
        s = a[i][n] - sum(a[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / a[i][i]

    residual = [
        sum(mat[i][j] * x[j] for j in range(n)) - rhs[i] for i in range(n)
    ]
    return ok(solution=x, residual=residual, status="unique")


def _brent(f, a: float, b: float, tol: float = 2e-12, maxiter: int = 200) -> tuple[float, int]:
    """Bracketed root finder (bisection with secant steps when safe)."""
    fa, fb = f(a), f(b)
    if not (math.isfinite(fa) and math.isfinite(fb)):
        raise CalcError(
            "domain_error",
            "f(a) or f(b) is not finite",
            "Choose a bracket where the expression is defined.",
        )
    if fa == 0:
        return a, 0
    if fb == 0:
        return b, 0
    if fa * fb > 0:
        raise CalcError(
            "no_root",
            "No sign change on bracket",
            "Widen bracket so f(a) and f(b) have opposite signs, or supply a better guess.",
            example='solve_root("x sq 2 -", bracket=[0,2])',
        )

    lo, hi = (a, b) if a < b else (b, a)
    flo, fhi = (fa, fb) if a < b else (fb, fa)
    # keep flo <= 0 <= fhi by swapping if needed
    if flo > 0:
        lo, hi, flo, fhi = hi, lo, fhi, flo

    for it in range(1, maxiter + 1):
        # try secant point if useful
        if fhi != flo:
            mid = lo - flo * (hi - lo) / (fhi - flo)
            if not (lo < mid < hi):
                mid = 0.5 * (lo + hi)
        else:
            mid = 0.5 * (lo + hi)
        # fall back to bisection every few iterations for guarantee
        if it % 4 == 0:
            mid = 0.5 * (lo + hi)

        fmid = f(mid)
        if fmid == 0 or abs(hi - lo) < tol * (1 + abs(mid)):
            return mid, it
        if fmid < 0:
            lo, flo = mid, fmid
        else:
            hi, fhi = mid, fmid

    return 0.5 * (lo + hi), maxiter


def _newton(f, x0: float, tol: float = 1e-10, maxiter: int = 100) -> tuple[float, int]:
    x = x0
    h = max(1e-8, abs(x0) * 1e-6)
    for it in range(1, maxiter + 1):
        fx = f(x)
        if abs(fx) < tol:
            return x, it
        fph = f(x + h)
        fmh = f(x - h)
        df = (fph - fmh) / (2 * h)
        if abs(df) < 1e-16:
            raise CalcError(
                "convergence_failed",
                "Newton derivative ~0",
                "Provide a bracket=[a,b] with a sign change for Brent instead.",
            )
        step = fx / df
        x_new = x - step
        if abs(step) < tol * (1 + abs(x)):
            return x_new, it
        x = x_new
    raise CalcError(
        "convergence_failed",
        "Newton did not converge",
        "Provide bracket=[a,b] with opposite signs, or a better guess.",
    )


def solve_root(
    expression: str,
    variable: str = "x",
    guess: float | None = None,
    bracket: list[float] | None = None,
    angle_mode: str = "rad",
) -> dict[str, Any]:
    if variable != "x":
        # rewrite not supported — require x for safety/simplicity
        raise CalcError(
            "invalid_data",
            "Only variable name 'x' is supported",
            "Write the RPN expression using token x.",
        )

    def f(t: float) -> float:
        return eval_at(expression, t, angle_mode=angle_mode)

    if bracket is not None:
        if len(bracket) != 2:
            raise CalcError(
                "invalid_data",
                "bracket must be [a,b]",
                "Pass two numbers with a sign change.",
            )
        root, iters = _brent(f, float(bracket[0]), float(bracket[1]))
        method = "brent"
    elif guess is not None:
        root, iters = _newton(f, float(guess))
        method = "newton"
    else:
        raise CalcError(
            "invalid_data",
            "Provide bracket or guess",
            'Example: bracket=[0,2] for "x sq 2 -".',
            example='solve_root("x sq 2 -", bracket=[0, 2])',
        )

    return ok(
        root=root,
        abs_f=abs(f(root)),
        iterations=iters,
        method=method,
        expression=expression,
        angle_mode=angle_mode,
    )


def solve_polynomial(coefficients: list[float]) -> dict[str, Any]:
    """Roots of a0 + a1 x + ... + an x^n = 0. coefficients = [a0, a1, ..., an]."""
    if not coefficients:
        raise CalcError("invalid_data", "Empty coefficient list", "Pass [a0,a1,...,an].")
    coeffs = [complex(c) for c in coefficients]
    while len(coeffs) > 1 and abs(coeffs[-1]) < 1e-18:
        coeffs.pop()
    deg = len(coeffs) - 1
    if deg == 0:
        raise CalcError(
            "invalid_data",
            "Constant polynomial has no roots (or infinitely many if zero)",
            "Provide degree >= 1.",
        )
    if deg > 4:
        raise CalcError(
            "overflow",
            "Only degrees 1–4 supported",
            "Factor into lower-degree polynomials or use solve_root for one real root.",
        )

    a = coeffs
    roots: list[complex] = []

    if deg == 1:
        roots = [-a[0] / a[1]]
    elif deg == 2:
        c, b, aa = a[0], a[1], a[2]
        disc = b * b - 4 * aa * c
        sqrt_d = cmath.sqrt(disc)
        roots = [(-b + sqrt_d) / (2 * aa), (-b - sqrt_d) / (2 * aa)]
    elif deg == 3:
        c0, c1, c2, c3 = a[0], a[1], a[2], a[3]
        A, B, C = c2 / c3, c1 / c3, c0 / c3
        p = B - A * A / 3
        q = C + (2 * A * A * A - 9 * A * B) / 27
        disc = (q / 2) ** 2 + (p / 3) ** 3
        shift = -A / 3
        if abs(disc.imag) < 1e-14 and disc.real >= 0:
            sd = math.sqrt(disc.real)
            u = math.copysign(abs(-q.real / 2 + sd) ** (1 / 3), -q.real / 2 + sd)
            v = math.copysign(abs(-q.real / 2 - sd) ** (1 / 3), -q.real / 2 - sd)
            roots = [
                complex(u + v + shift.real if isinstance(shift, complex) else u + v + shift),
                complex(-0.5 * (u + v) + float(shift.real if isinstance(shift, complex) else shift),
                        (u - v) * math.sqrt(3) / 2),
                complex(-0.5 * (u + v) + float(shift.real if isinstance(shift, complex) else shift),
                        -(u - v) * math.sqrt(3) / 2),
            ]
        else:
            sd = cmath.sqrt(disc)
            u = (-q / 2 + sd) ** (1 / 3)
            v = (-q / 2 - sd) ** (1 / 3)
            w = complex(-0.5, math.sqrt(3) / 2)
            roots = [u + v + shift, w * u + (w * w) * v + shift, (w * w) * u + w * v + shift]
    else:
        # Durand–Kerner for monic degree 4
        lead = a[-1]
        monic = [c / lead for c in a]
        n = deg
        roots = [cmath.exp(2j * math.pi * (i + 0.5) / n) * (0.4 + 0.9j) for i in range(n)]
        for _ in range(300):
            new_roots: list[complex] = []
            max_delta = 0.0
            for i in range(n):
                xi = roots[i]
                pval = monic[-1]
                for c in reversed(monic[:-1]):
                    pval = pval * xi + c
                denom = 1 + 0j
                for j in range(n):
                    if i != j:
                        denom *= xi - roots[j]
                if abs(denom) < 1e-30:
                    denom = 1e-30 + 0j
                xi2 = xi - pval / denom
                max_delta = max(max_delta, abs(xi2 - xi))
                new_roots.append(xi2)
            roots = new_roots
            if max_delta < 1e-14:
                break

    def ser(z: complex) -> Any:
        if abs(z.imag) < 1e-10:
            return float(z.real)
        return {"re": float(z.real), "im": float(z.imag)}

    return ok(
        degree=deg,
        roots=[ser(r) for r in roots],
        coefficients=[
            float(c.real) if abs(c.imag) < 1e-15 else {"re": c.real, "im": c.imag} for c in a
        ],
    )
