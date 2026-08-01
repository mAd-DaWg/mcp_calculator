"""Matrix and vector operations (pure Python, safety-capped)."""

from __future__ import annotations

import math
from typing import Any

from mcp_calculator.errors import CalcError, ok

MAX_DIM = 32


Matrix = list[list[float]]
Vector = list[float]


def _check_matrix(m: Any, name: str = "matrix") -> Matrix:
    if not isinstance(m, list) or not m:
        raise CalcError(
            "invalid_data",
            f"{name} must be a non-empty nested list",
            "Pass e.g. [[1,2],[3,4]].",
        )
    if not isinstance(m[0], list):
        raise CalcError(
            "invalid_data",
            f"{name} must be a 2D list of rows",
            "Pass nested lists: [[1,2],[3,4]].",
        )
    rows, cols = len(m), len(m[0])
    if rows > MAX_DIM or cols > MAX_DIM:
        raise CalcError(
            "overflow",
            f"Matrix exceeds max dimension {MAX_DIM}",
            f"Use matrices with rows/cols <= {MAX_DIM}.",
        )
    out: Matrix = []
    for i, row in enumerate(m):
        if not isinstance(row, list) or len(row) != cols:
            raise CalcError(
                "dimension_error",
                f"Row {i} has inconsistent length",
                "All rows must have the same number of columns.",
            )
        out.append([float(x) for x in row])
    return out


def _check_vector(v: Any, name: str = "vector") -> Vector:
    if not isinstance(v, list) or not v:
        raise CalcError(
            "invalid_data",
            f"{name} must be a non-empty list",
            "Pass e.g. [1,2,3].",
        )
    if len(v) > MAX_DIM:
        raise CalcError(
            "overflow",
            f"Vector exceeds max length {MAX_DIM}",
            f"Use length <= {MAX_DIM}.",
        )
    if any(isinstance(x, list) for x in v):
        raise CalcError(
            "invalid_data",
            f"{name} must be 1D",
            "Pass a flat list of numbers.",
        )
    return [float(x) for x in v]


def _add(a: Matrix, b: Matrix) -> Matrix:
    if len(a) != len(b) or len(a[0]) != len(b[0]):
        raise CalcError(
            "dimension_error",
            "Matrices must have the same shape to add",
            "Ensure both matrices are m×n.",
        )
    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def _sub(a: Matrix, b: Matrix) -> Matrix:
    if len(a) != len(b) or len(a[0]) != len(b[0]):
        raise CalcError(
            "dimension_error",
            "Matrices must have the same shape to subtract",
            "Ensure both matrices are m×n.",
        )
    return [[a[i][j] - b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def _mul(a: Matrix, b: Matrix) -> Matrix:
    if len(a[0]) != len(b):
        raise CalcError(
            "dimension_error",
            f"Cannot multiply {len(a)}×{len(a[0])} by {len(b)}×{len(b[0])}",
            "Inner dimensions must match (m×n)·(n×p).",
            example="[[1,2],[3,4]] * [[5,6],[7,8]]",
        )
    n, p = len(a), len(b[0])
    return [
        [sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(p)]
        for i in range(n)
    ]


def _transpose(a: Matrix) -> Matrix:
    return [[a[i][j] for i in range(len(a))] for j in range(len(a[0]))]


def _det(a: Matrix) -> float:
    n = len(a)
    if n != len(a[0]):
        raise CalcError(
            "dimension_error",
            "Determinant requires a square matrix",
            "Pass an n×n matrix.",
        )
    m = [row[:] for row in a]
    det = 1.0
    for i in range(n):
        pivot = i
        for r in range(i, n):
            if abs(m[r][i]) > abs(m[pivot][i]):
                pivot = r
        if abs(m[pivot][i]) < 1e-15:
            return 0.0
        if pivot != i:
            m[i], m[pivot] = m[pivot], m[i]
            det = -det
        det *= m[i][i]
        piv = m[i][i]
        for r in range(i + 1, n):
            factor = m[r][i] / piv
            for c in range(i, n):
                m[r][c] -= factor * m[i][c]
    return det


def _inv(a: Matrix) -> Matrix:
    n = len(a)
    if n != len(a[0]):
        raise CalcError(
            "dimension_error",
            "Inverse requires a square matrix",
            "Pass an n×n matrix.",
        )
    # Augment with identity
    m = [a[i][:] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for i in range(n):
        pivot = i
        for r in range(i, n):
            if abs(m[r][i]) > abs(m[pivot][i]):
                pivot = r
        if abs(m[pivot][i]) < 1e-12:
            raise CalcError(
                "singular_matrix",
                "Matrix is singular; inverse undefined",
                "Check det≠0, or use another op (e.g. det).",
            )
        m[i], m[pivot] = m[pivot], m[i]
        piv = m[i][i]
        m[i] = [x / piv for x in m[i]]
        for r in range(n):
            if r == i:
                continue
            factor = m[r][i]
            m[r] = [m[r][c] - factor * m[i][c] for c in range(2 * n)]
    return [row[n:] for row in m]


def _identity(n: int) -> Matrix:
    if n < 1 or n > MAX_DIM:
        raise CalcError(
            "overflow",
            f"identity size must be 1..{MAX_DIM}",
            f"Pass n between 1 and {MAX_DIM}.",
        )
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _mat_mul(a: Matrix, b: Matrix) -> Matrix:
    n, m, p = len(a), len(b), len(b[0])
    return [
        [sum(a[i][k] * b[k][j] for k in range(m)) for j in range(p)] for i in range(n)
    ]


def _qr(a: Matrix) -> tuple[Matrix, Matrix]:
    """Classic Gram–Schmidt QR (sufficient for small real eigen)."""
    n = len(a)
    q = [[0.0] * n for _ in range(n)]
    r = [[0.0] * n for _ in range(n)]
    at = _transpose(a)
    u: list[list[float]] = []
    for j in range(n):
        v = at[j][:]
        for i in range(j):
            r[i][j] = sum(u[i][k] * at[j][k] for k in range(n))
            v = [v[k] - r[i][j] * u[i][k] for k in range(n)]
        norm = math.sqrt(sum(x * x for x in v))
        if norm < 1e-15:
            raise CalcError("domain_error", "QR failed (singular column)", "Matrix may be defective.")
        r[j][j] = norm
        u.append([x / norm for x in v])
    q = _transpose(u)
    return q, r


def _eigen(a: Matrix, max_iter: int = 200) -> tuple[list[Any], Matrix]:
    """Real QR eigenvalue algorithm; returns eigenvalues and approximate eigenvectors (V)."""
    n = len(a)
    if n != len(a[0]):
        raise CalcError("dimension_error", "eigen needs a square matrix", "Pass n×n.")
    ak = [row[:] for row in a]
    v = _identity(n)
    for _ in range(max_iter):
        q, r = _qr(ak)
        ak = _mat_mul(r, q)
        v = _mat_mul(v, q)
        off = sum(abs(ak[i][j]) for i in range(n) for j in range(n) if i != j)
        if off < 1e-10 * (1 + sum(abs(ak[i][i]) for i in range(n))):
            break
    vals: list[Any] = []
    for i in range(n):
        # detect 2x2 complex blocks roughly
        if i + 1 < n and abs(ak[i + 1][i]) > 1e-8:
            # complex conjugate pair from 2x2 block
            a11, a12 = ak[i][i], ak[i][i + 1]
            a21, a22 = ak[i + 1][i], ak[i + 1][i + 1]
            tr = a11 + a22
            det = a11 * a22 - a12 * a21
            disc = tr * tr - 4 * det
            if disc < 0:
                re, im = tr / 2, math.sqrt(-disc) / 2
                vals.append({"re": re, "im": im})
                vals.append({"re": re, "im": -im})
                i += 1
                continue
        vals.append(float(ak[i][i]))
    return vals, v


def _ref(a: Matrix) -> Matrix:
    """Row echelon form (not reduced) — graphing-calculator ref( / CAS graphing models REF."""
    m = [row[:] for row in a]
    rows, cols = len(m), len(m[0])
    r = 0
    for c in range(cols):
        if r >= rows:
            break
        pivot = r
        for i in range(r, rows):
            if abs(m[i][c]) > abs(m[pivot][c]):
                pivot = i
        if abs(m[pivot][c]) < 1e-12:
            continue
        m[r], m[pivot] = m[pivot], m[r]
        piv = m[r][c]
        m[r] = [x / piv for x in m[r]]
        for i in range(r + 1, rows):
            factor = m[i][c]
            m[i] = [m[i][j] - factor * m[r][j] for j in range(cols)]
        r += 1
    return m


def _rref(a: Matrix) -> Matrix:
    """Reduced row echelon form — graphing-calculator rref( / CAS graphing models RREF."""
    m = [row[:] for row in a]
    rows, cols = len(m), len(m[0])
    r = 0
    for c in range(cols):
        if r >= rows:
            break
        pivot = r
        for i in range(r, rows):
            if abs(m[i][c]) > abs(m[pivot][c]):
                pivot = i
        if abs(m[pivot][c]) < 1e-12:
            continue
        m[r], m[pivot] = m[pivot], m[r]
        piv = m[r][c]
        m[r] = [x / piv for x in m[r]]
        for i in range(rows):
            if i == r:
                continue
            factor = m[i][c]
            m[i] = [m[i][j] - factor * m[r][j] for j in range(cols)]
        r += 1
    return m


def _dot(u: Vector, v: Vector) -> float:
    if len(u) != len(v):
        raise CalcError(
            "dimension_error",
            "Vectors must have the same length for dot",
            "Ensure both vectors have matching length.",
        )
    return sum(a * b for a, b in zip(u, v))


def _cross(u: Vector, v: Vector) -> Vector:
    if len(u) != 3 or len(v) != 3:
        raise CalcError(
            "dimension_error",
            "cross requires two 3D vectors",
            "Pass two length-3 vectors.",
        )
    return [
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    ]


def _norm(v: Vector) -> float:
    return math.sqrt(sum(x * x for x in v))


def _unit(v: Vector) -> Vector:
    n = _norm(v)
    if n == 0:
        raise CalcError(
            "domain_error",
            "Cannot unit-normalize a zero vector",
            "Pass a non-zero vector.",
        )
    return [x / n for x in v]


def _angle(u: Vector, v: Vector) -> float:
    nu, nv = _norm(u), _norm(v)
    if nu == 0 or nv == 0:
        raise CalcError(
            "domain_error",
            "Cannot compute angle with a zero vector",
            "Use non-zero vectors.",
        )
    c = max(-1.0, min(1.0, _dot(u, v) / (nu * nv)))
    return math.acos(c)


def _from_rad(radians: float, angle_mode: str) -> float:
    if angle_mode == "rad":
        return radians
    if angle_mode == "deg":
        return radians * 180.0 / math.pi
    if angle_mode == "grad":
        return radians * 200.0 / math.pi
    raise CalcError(
        "invalid_angle_mode",
        f"angle_mode must be rad, deg, or grad; got {angle_mode!r}",
        'Pass angle_mode="deg" (scientific calculator setup default is Degree).',
    )


def _two_vectors(
    op: str,
    matrices: list[Any],
    vector: Any | None,
) -> tuple[Vector, Vector | None]:
    if vector is not None and op in ("norm", "unit"):
        return _check_vector(vector), None
    if len(matrices) == 2 and all(
        isinstance(m, list) and m and not isinstance(m[0], list) for m in matrices
    ):
        return _check_vector(matrices[0]), _check_vector(matrices[1])
    if vector is not None and len(matrices) == 1 and not isinstance(matrices[0][0], list):
        return _check_vector(matrices[0]), _check_vector(vector)
    if op in ("norm", "unit"):
        if len(matrices) == 1 and not isinstance(matrices[0][0], list):
            return _check_vector(matrices[0]), None
        raise CalcError(
            "invalid_data",
            f"{op} needs one vector",
            "Pass vector=[...] or matrices=[[u...]].",
        )
    if len(matrices) != 2:
        raise CalcError(
            "invalid_data",
            f"{op} needs two vectors",
            "Pass matrices=[[u...],[v...]].",
        )
    return _check_vector(matrices[0]), _check_vector(matrices[1])


def matrix_op(
    op: str,
    matrices: list[Any] | None = None,
    vector: Any | None = None,
    n: int | None = None,
    angle_mode: str = "rad",
) -> dict[str, Any]:
    op = (op or "").lower().strip()
    matrices = matrices or []
    if angle_mode not in ("rad", "deg", "grad"):
        raise CalcError(
            "invalid_angle_mode",
            f"angle_mode must be rad, deg, or grad; got {angle_mode!r}",
            'Pass angle_mode="deg" or "rad" or "grad".',
        )

    if op == "identity":
        if n is None:
            raise CalcError(
                "invalid_data",
                "identity requires n",
                "Pass n=size, e.g. n=3.",
            )
        return ok(op=op, result=_identity(int(n)))

    if op in ("dot", "cross", "norm", "angle", "unit", "unit_vector"):
        if op == "unit_vector":
            op = "unit"
        u, v = _two_vectors(op, matrices, vector)
        if op == "norm":
            return ok(op=op, result=_norm(u))
        if op == "unit":
            return ok(op="unit", result=_unit(u))
        assert v is not None
        if op == "dot":
            return ok(op=op, result=_dot(u, v))
        if op == "cross":
            return ok(op=op, result=_cross(u, v))
        ang = _from_rad(_angle(u, v), angle_mode)
        return ok(op="angle", result=ang, unit=angle_mode, angle_mode=angle_mode)

    mats = [_check_matrix(m) for m in matrices]

    if op == "add":
        if len(mats) != 2:
            raise CalcError("invalid_data", "add needs two matrices", "Pass matrices=[A,B].")
        return ok(op=op, result=_add(mats[0], mats[1]))
    if op == "sub":
        if len(mats) != 2:
            raise CalcError("invalid_data", "sub needs two matrices", "Pass matrices=[A,B].")
        return ok(op=op, result=_sub(mats[0], mats[1]))
    if op == "mul":
        if len(mats) != 2:
            raise CalcError("invalid_data", "mul needs two matrices", "Pass matrices=[A,B].")
        return ok(op=op, result=_mul(mats[0], mats[1]))
    if op == "transpose":
        if len(mats) != 1:
            raise CalcError("invalid_data", "transpose needs one matrix", "Pass matrices=[A].")
        return ok(op=op, result=_transpose(mats[0]))
    if op == "det":
        if len(mats) != 1:
            raise CalcError("invalid_data", "det needs one matrix", "Pass matrices=[A].")
        return ok(op=op, result=_det(mats[0]))
    if op == "inv":
        if len(mats) != 1:
            raise CalcError("invalid_data", "inv needs one matrix", "Pass matrices=[A].")
        return ok(op=op, result=_inv(mats[0]))
    if op == "ref":
        if len(mats) != 1:
            raise CalcError("invalid_data", "ref needs one matrix", "Pass matrices=[A].")
        return ok(op=op, result=_ref(mats[0]))
    if op == "rref":
        if len(mats) != 1:
            raise CalcError("invalid_data", "rref needs one matrix", "Pass matrices=[A].")
        return ok(op=op, result=_rref(mats[0]))
    if op == "eigen":
        if len(mats) != 1:
            raise CalcError("invalid_data", "eigen needs one matrix", "Pass matrices=[A].")
        vals, vecs = _eigen(mats[0])
        return ok(op=op, eigenvalues=vals, eigenvectors=vecs)

    raise CalcError(
        "unknown_token",
        f"Unknown matrix op {op!r}",
        "Set op to add, sub, mul, transpose, det, inv, identity, ref, rref, eigen, "
        "dot, cross, norm, angle, or unit.",
        example="op='det', matrices=[[[1,2],[3,4]]]",
        token=op,
    )
