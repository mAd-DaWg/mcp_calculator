# mcp_calculator

stdio MCP server that gives LLMs a **scientific calculator with normal infix maths** (e.g. `90+(40-30)`, `sin(30)`, `x^2-2`). Expressions are parsed safely, converted internally to Reverse Polish Notation, and evaluated by a stack machine over allowlisted operators and constants — **no Python `eval`/`exec`** — so agents can verify numeric work without inventing answers.

**Runtime:** Python ≥3.10, dependency `mcp≥1.0`. Numerics use IEEE-754 `float` / `complex` via the standard `math` and `cmath` libraries (no SymPy, NumPy, or mpmath).

## Table of contents

- [Install / use](#install--use-cursor--claude-desktop)
- [How the calculator works](#how-the-calculator-works)
- [MCP request and response conventions](#mcp-request-and-response-conventions)
- [Tools reference](#tools-reference)
- [Operator / function reference](#operator--function-reference)
- [Constants reference](#constants-reference)
- [Unit conversions](#unit-conversions)
- [Precision](#precision)
- [Limitations and safety](#limitations-and-safety)
- [Tests](#tests)

---

## Install / use (Cursor / Claude Desktop)

From GitHub:

```json
{
  "mcpServers": {
    "mcp_calculator": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/mAd-DaWg/mcp_calculator", "mcp-calculator"]
    }
  }
}
```

Local clone:

```bash
pip install -e ".[dev]"
```

```json
{
  "mcpServers": {
    "mcp_calculator": {
      "command": "python",
      "args": ["-m", "mcp_calculator"],
      "cwd": "/path/to/mcp_calculator"
    }
  }
}
```

Entry points: console script `mcp-calculator`, or `python -m mcp_calculator`. Transport is **stdio** only (no HTTP port or env-based precision flags).

---

## How the calculator works

```
MCP client (stdio JSON-RPC)
  → mcp-calculator tool handler
  → catch_calc (never raises to the client)
  → infix parser → RPN stack engine (or matrix / solve / …)
  → JSON object serialized as a string
```

### Infix evaluation (`evaluate`)

1. Validate non-empty expression (length ≤ 100 000 characters) and `angle_mode` ∈ `{rad, deg, grad}`.
2. Lex infix into numbers, names, operators, parentheses, commas, and `!`.
3. Insert implicit multiplication where needed (`2pi`, `2(3+4)`, `2x`).
4. Convert to RPN with the shunting-yard algorithm (precedence, unary minus, function calls).
5. Evaluate the RPN token list on the allowlisted stack machine.
6. Return the result plus the original `expression` and the internal `rpn` string.

**Infix syntax**

| Construct | Example |
| --- | --- |
| Arithmetic | `90+(40-30)`, `2+3*4` |
| Powers | `2^10`, `2**3` (same as `^`) |
| Unary minus | `-5`, `2*-3`; `-2^2` → `-4` |
| Functions | `sin(30)`, `sqrt(9)`, `abs(x)` |
| Multi-arg | `atan2(y,x)`, `log(10,100)`, `cmplx(3,4)`, `min(a,b)` |
| Factorial | `5!` |
| Constants | `pi/6`, `qe` |
| Variable | `x` (calculus / roots) |
| Implicit `*` | `2pi`, `2(3+4)`, `(1+2)(3)`, `2x` |

**Precedence (tightest last):** `+` `-` → `*` `/` `%` → unary `-` → `^` → postfix `!`. `^` is right-associative.

**Angle mode** affects circular trig (`sin`, `cos`, `tan`, inverses, `sec`/`csc`/`cot`, `atan2`, `arg`). Hyperbolic functions ignore angle mode. Pass `angle_mode` on the tool call (mid-expression `RAD`/`DEG`/`GRAD` tokens are not part of the infix grammar).

Higher-level tools (matrix, stats, solve, BASE-N, units) use dedicated algorithms; `differentiate`, `integrate`, and `solve_root` evaluate **infix** expressions in `x`.

---

## MCP request and response conventions

Every tool returns a **JSON string**. The MCP layer delivers that string as tool-result text. Agents should `JSON.parse` it.

### Success shape

```json
{"ok": true, "...": "tool-specific fields"}
```

### Failure shape

```json
{
  "ok": false,
  "error": "<code>",
  "message": "human-readable explanation",
  "hint": "how to fix the call",
  "example": "optional",
  "did_you_mean": "optional"
}
```

On `ok: false`, read **`message`** and **`hint`** before retrying. Discovery tools (`list_operations`, `list_constants`, `list_unit_conversions`) help recover from unknown tokens.

### Illustrative MCP `tools/call` envelope

Clients send JSON-RPC over stdio. Example call for `evaluate`:

**Request**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "evaluate",
    "arguments": {
      "expression": "90+(40-30)",
      "angle_mode": "rad"
    }
  }
}
```

**Decoded tool payload** (the string inside the tool result content):

```json
{
  "ok": true,
  "result": 100.0,
  "expression": "90+(40-30)",
  "angle_mode": "rad",
  "rpn": "90 40 30 - +"
}
```

Below, examples show the **arguments object** and the **parsed JSON response** — what agents reason over after the MCP wrapper.

---

## Tools reference

When this server is connected over MCP, the model sees each tool’s **description** (from the Python docstrings in `server.py`) plus the server **instructions** — not this README. Keep those in sync when changing behaviour.

| Tool | Purpose |
| --- | --- |
| `evaluate` | Main calculator: evaluate ordinary maths expressions |
| `list_operations` | Discover available operators and function names |
| `list_constants` | Discover math/physics constant names and values |
| `list_unit_conversions` | Discover supported unit conversion ids |
| `matrix_op` | Matrix and vector algebra (det, inverse, dot, …) |
| `stats_1var` | Summary statistics for one list of numbers |
| `stats_2var` | Two-variable stats and linear regression |
| `solve_linear` | Solve a system of linear equations |
| `solve_root` | Find a numeric root of f(x) = 0 |
| `solve_polynomial` | Find roots of a polynomial (degree 1–4) |
| `base_convert` | Convert integers between binary/octal/decimal/hex |
| `base_arith` | Integer arithmetic and bitwise ops in a chosen base |
| `differentiate` | Approximate the derivative of f(x) at a point |
| `integrate` | Approximate a definite integral of f(x) |
| `convert_unit` | Convert a value between listed measurement units |

### `evaluate`

The primary tool for checking arithmetic and scientific expressions. Pass ordinary infix maths (parentheses, precedence, functions, constants). The server converts to RPN internally and returns the numeric result plus the internal `rpn` form for transparency.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `expression` | string | required | Infix expression |
| `angle_mode` | string | `"rad"` | `rad`, `deg`, or `grad` |

**Arguments**

```json
{"expression": "90+(40-30)", "angle_mode": "rad"}
```

**Response**

```json
{
  "ok": true,
  "result": 100.0,
  "expression": "90+(40-30)",
  "angle_mode": "rad",
  "rpn": "90 40 30 - +"
}
```

**Degrees / grads**

```json
{"expression": "sin(30)", "angle_mode": "deg"}
```

```json
{
  "ok": true,
  "result": 0.49999999999999994,
  "expression": "sin(30)",
  "angle_mode": "deg",
  "rpn": "30 sin"
}
```

(`sin(50)` with `angle_mode=grad` likewise yields ~0.5.)

**Complex**

```json
{"expression": "abs(cmplx(3,4))"}
```

```json
{
  "ok": true,
  "result": 5.0,
  "expression": "abs(cmplx(3,4))",
  "angle_mode": "rad",
  "rpn": "3 4 cmplx abs"
}
```

A non-real complex result looks like `"result": {"re": 1.0, "im": 2.0}`.

**Constants**

```json
{"expression": "sin(pi/6)"}
```

```json
{
  "ok": true,
  "result": 0.49999999999999994,
  "expression": "sin(pi/6)",
  "angle_mode": "rad",
  "rpn": "pi 6 / sin"
}
```

**Error example**

```json
{"expression": "foo"}
```

```json
{
  "ok": false,
  "error": "unknown_token",
  "message": "Unknown name 'foo' at position 0",
  "hint": "Use a constant (list_constants), variable x, or function call like sin(x).",
  "example": "pi/2",
  "did_you_mean": "F",
  "token": "foo",
  "position": 0
}
```

### `list_operations` / `list_constants` / `list_unit_conversions`

Discovery helpers so agents do not guess names. Call these when unsure which operators, physics constants, or unit conversions exist. Each takes no parameters and returns `ok: true` plus an array:

- `list_operations` → `operations[]` with `name`, `arity`, `description`, `angle_sensitive`
- `list_constants` → `constants[]` with `name`, `value`, `unit`, `note`, `codata_year`, optional `casio_index`
- `list_unit_conversions` → `conversions[]` with `id`, `from`, `to`, plus `factor` or `note` for temperature

See the [operator](#operator--function-reference), [constants](#constants-reference), and [units](#unit-conversions) catalogs below for the full inventories.

### `matrix_op`

Linear algebra on small dense matrices and vectors: add/subtract/multiply, transpose, determinant, inverse, reduced row echelon form (RREF), identity matrices, and vector operations (dot product, 3D cross product, Euclidean norm, angle between vectors). Maximum dimension is **32**.

| Parameter | Type | Description |
| --- | --- | --- |
| `op` | string | `add`, `sub`, `mul`, `transpose`, `det`, `inv`, `identity`, `rref`, `dot`, `cross`, `norm`, `angle` |
| `matrices` | list | One or two matrices, or two vectors for vector ops |
| `vector` | list of float | Single vector (e.g. for `norm`) |
| `n` | int | Size for `identity` |

**Determinant**

```json
{"op": "det", "matrices": [[[1, 2], [3, 4]]]}
```

```json
{"ok": true, "op": "det", "result": -2.0}
```

**Vector norm**

```json
{"op": "norm", "vector": [3, 4]}
```

```json
{"ok": true, "op": "norm", "result": 5.0}
```

**Angle** (radians; includes `"unit": "rad"`)

```json
{"op": "angle", "matrices": [[1, 0], [0, 1]]}
```

```json
{"ok": true, "op": "angle", "result": 1.5707963267948966, "unit": "rad"}
```

**Cross product** (requires 3-vectors)

```json
{"op": "cross", "matrices": [[1, 0, 0], [0, 1, 0]]}
```

```json
{"ok": true, "op": "cross", "result": [0.0, 0.0, 1.0]}
```

**Identity** (requires `n`)

```json
{"op": "identity", "n": 2}
```

```json
{"ok": true, "op": "identity", "result": [[1.0, 0.0], [0.0, 1.0]]}
```

### `stats_1var`

One-variable descriptive statistics for a list of numbers: count, mean, sum, sum of squares, min/max, median, and population/sample variance and standard deviation. Use when summarizing a single sample (max 100 000 points).

| Parameter | Type | Description |
| --- | --- | --- |
| `data` | list of float | Non-empty; max 100 000 points |

```json
{"data": [1, 2, 3, 4]}
```

```json
{
  "ok": true,
  "n": 4,
  "mean": 2.5,
  "sum": 10.0,
  "sumsq": 30.0,
  "min": 1.0,
  "max": 4.0,
  "median": 2.5,
  "var_pop": 1.25,
  "var_sample": 1.6666666666666667,
  "std_pop": 1.118033988749895,
  "std_sample": 1.2909944487358056
}
```

### `stats_2var`

Two-variable statistics and ordinary least-squares linear regression. Fits **y = a + b·x**, returns slope `b`, intercept `a`, correlation `r`, and means. Needs at least two points and equal-length `x` / `y` lists.

```json
{"x": [1, 2, 3], "y": [2, 4, 6]}
```

```json
{
  "ok": true,
  "n": 3,
  "a": 0.0,
  "b": 2.0,
  "r": 1.0,
  "mean_x": 2.0,
  "mean_y": 4.0,
  "predict_at_mean": 4.0,
  "equation": "y = a + b*x"
}
```

### `solve_linear`

Solves a square system of linear equations **Ax = b** (unique solution when A is invertible). Pass either an augmented matrix or separate coefficient matrix `A` and right-hand side `b`. Uses Gaussian elimination with partial pivoting. Maximum size **n = 32**.

Pass either:

- `coefficients` — augmented matrix `n×(n+1)`, each row `[a_i1, …, a_in, b_i]`, or
- `A` (n×n) and `b` (length n)

```json
{"A": [[2, 1], [1, 3]], "b": [1, 2]}
```

```json
{
  "ok": true,
  "solution": [0.2, 0.6],
  "residual": [0.0, -2.220446049250313e-16],
  "status": "unique"
}
```

### `solve_root`

Finds a real number **x** where an infix expression **f(x) equals zero** (for example √2 from `x^2-2`). Prefer a bracketing interval `[a, b]` (Brent’s method); if you only have a starting guess, Newton’s method is used instead.

| Parameter | Type | Default |
| --- | --- | --- |
| `expression` | string | required — infix in `x` |
| `bracket` | `[a, b]` | preferred |
| `guess` | float | for Newton |
| `angle_mode` | string | `"rad"` |

```json
{"expression": "x^2-2", "bracket": [0, 2]}
```

```json
{
  "ok": true,
  "root": 1.414213562373095,
  "abs_f": 4.440892098500626e-16,
  "iterations": 19,
  "method": "brent",
  "expression": "x^2-2",
  "angle_mode": "rad"
}
```

### `solve_polynomial`

Finds all roots of a polynomial **a₀ + a₁x + … + aₙxⁿ**. Pass coefficients as `[a0, …, an]` (constant term first). **Degree 1–4 only** (closed form for degrees 1–3; Durand–Kerner iteration for degree 4). Roots may be complex (`{re, im}`).

```json
{"coefficients": [-2, 0, 1]}
```

```json
{
  "ok": true,
  "degree": 2,
  "roots": [1.4142135623730951, -1.4142135623730951],
  "coefficients": [-2.0, 0.0, 1.0]
}
```

### `base_convert`

Converts an integer string from one base to another among **2, 8, 10, and 16**, using **32-bit** two’s complement. Useful for hex/binary checks. Pass unsigned-style digit patterns for negatives (e.g. `FFFFFFFF` for −1).

```json
{"value": "FF", "from_base": 16, "to_base": 10}
```

```json
{
  "ok": true,
  "value": "255",
  "decimal": 255,
  "decimal_unsigned": 255,
  "from_base": 16,
  "to_base": 10,
  "bits": 32
}
```

### `base_arith`

Performs integer arithmetic and bitwise operations on values written in a chosen base (2/8/10/16), still in **32-bit** two’s complement. Supports `add`, `sub`, `mul`, `div`, `and`, `or`, `xor`, and unary `not`. Results wrap at 32 bits; `div` uses signed interpretation.

| Parameter | Type | Default |
| --- | --- | --- |
| `op` | string | `add`, `sub`, `mul`, `div`, `and`, `or`, `xor`, `not` |
| `a` | string | required |
| `b` | string | required except for `not` |
| `base` | int | `10` |

```json
{"op": "add", "a": "A", "b": "5", "base": 16}
```

```json
{"ok": true, "op": "add", "result": "F", "decimal_unsigned": 15, "base": 16}
```

### `differentiate`

Approximates the derivative **df/dx** of an infix function of `x` at a given point, using a central finite difference. Use for checking calculus results numerically (not symbolic differentiation). Optional `h` overrides the automatic step size; `truncation_est` is a rough error hint.

| Parameter | Type | Default |
| --- | --- | --- |
| `expression` | string | required — infix in `x` |
| `at` | float | required — point of evaluation |
| `angle_mode` | string | `"rad"` |
| `h` | float | auto: `(1+|x|)·(1e-16)^(1/3)` |

```json
{"expression": "x^3", "at": 2}
```

```json
{
  "ok": true,
  "derivative": 12.000000000147326,
  "at": 2.0,
  "h": 1.3924766500838347e-05,
  "truncation_est": 3.8779838599604476e-10,
  "expression": "x^3",
  "angle_mode": "rad"
}
```

### `integrate`

Approximates the definite integral of an infix function of `x` from `lower` to `upper` using adaptive Simpson quadrature. Use to check ∫f(x) dx numerically. Optional `tol` tightens or loosens the accuracy target; the response includes `error_est` and how many times `f` was evaluated.

| Parameter | Type | Default |
| --- | --- | --- |
| `expression` | string | required — infix in `x` |
| `lower`, `upper` | float | required — integration limits |
| `angle_mode` | string | `"rad"` |
| `tol` | float | `1e-10` |

```json
{"expression": "x^2", "lower": 0, "upper": 1}
```

```json
{
  "ok": true,
  "integral": 0.3333333333333333,
  "lower": 0.0,
  "upper": 1.0,
  "error_est": 0.0,
  "evaluations": 5,
  "expression": "x^2",
  "angle_mode": "rad"
}
```

Caps: recursion depth 40, ≤ 100 000 function evaluations.

### `convert_unit`

Converts a numeric value between common measurement units (length, area, volume, mass, pressure, force, energy, power, and temperature). Only pairs listed by `list_unit_conversions` are supported — there is no free-form dimensional analysis. Pass either a `conversion_id` **or** `from_unit` + `to_unit`. Full id list: [Unit conversions](#unit-conversions).

```json
{"value": 1, "conversion_id": "mile_to_km"}
```

```json
{
  "ok": true,
  "value": 1.609344,
  "from_unit": "mile",
  "to_unit": "km",
  "conversion_id": "mile_to_km"
}
```

Temperature example (`100 °C → °F`):

```json
{"value": 100, "conversion_id": "C_to_F"}
```

```json
{"ok": true, "value": 212.0, "from_unit": "C", "to_unit": "F", "conversion_id": "C_to_F"}
```

---

## Operator / function reference

74 operators/functions from the allowlist. In infix, use binary symbols (`+`, `^`, …) or **function-call** form `name(args)` matching arity. `angle_sensitive` means circular-trig / mode behavior. Call `list_operations` at runtime for the same data.

### Arithmetic and powers

| Name | Arity | Angle | Description |
| --- | --- | --- | --- |
| `+` | 2 | | Addition |
| `-` | 2 | | Subtraction |
| `*` | 2 | | Multiplication |
| `/` | 2 | | Division |
| `^` | 2 | | Power `a^b` — infix `a^b` or `a**b`; also `pow(a,b)` |
| `pow` | 2 | | Alias for `^` |
| `%` | 2 | | Remainder (fmod); also `mod(a,b)` |
| `mod` | 2 | | Modulo |
| `nroot` | 2 | | `nroot(x,y)` → `y^(1/x)` |
| `neg` | 1 | | Negate (infix unary `-`) |
| `abs` | 1 | | Absolute value / modulus — `abs(x)` |
| `inv` | 1 | | Reciprocal `1/x` — `inv(x)` |
| `sqrt` | 1 | | Square root — `sqrt(x)` |
| `cbrt` | 1 | | Cube root — `cbrt(x)` |
| `sq` | 1 | | Square — `sq(x)` or prefer `x^2` |
| `cube` | 1 | | Cube — `cube(x)` or prefer `x^3` |
| `pct` | 2 | | `x * y / 100` |
| `pct1` | 1 | | `x / 100` |
| `min` | 2 | | Minimum |
| `max` | 2 | | Maximum |
| `hypot` | 2 | | Hypotenuse |
| `sgn` | 1 | | Sign (−1, 0, 1) |

### Exponentials and logarithms

| Name | Arity | Description |
| --- | --- | --- |
| `exp` | 1 | `e^x` |
| `exp10` | 1 | `10^x` |
| `ln` | 1 | Natural log |
| `log10` | 1 | Log base 10 |
| `log2` | 1 | Log base 2 |
| `log` | 2 | `log(b,a)` → log base b of a |

### Circular trigonometry (angle mode)

| Name | Arity | Description |
| --- | --- | --- |
| `sin` / `cos` / `tan` | 1 | Forward trig |
| `asin` / `acos` / `atan` | 1 | Inverse → angle mode |
| `atan2` | 2 | `atan2(y,x)`: `y x atan2` |
| `sec` / `csc` / `cot` | 1 | Reciprocal trig |

### Hyperbolic (ignore angle mode)

| Name | Arity | Description |
| --- | --- | --- |
| `sinh` / `cosh` / `tanh` | 1 | Hyperbolic |
| `asinh` / `acosh` / `atanh` | 1 | Inverse hyperbolic |
| `sech` / `csch` / `coth` | 1 | Reciprocal hyperbolic |

### Angle conversion helpers

| Name | Arity | Description |
| --- | --- | --- |
| `d2r` / `r2d` | 1 | Degrees ↔ radians |
| `g2r` / `r2g` | 1 | Grads ↔ radians |
| `d2g` / `g2d` | 1 | Degrees ↔ grads |

### Rounding and integers

| Name | Arity | Description |
| --- | --- | --- |
| `floor` / `ceil` / `round` | 1 | Floor / ceiling / nearest |
| `trunc` | 1 | Truncate toward zero |
| `frac` | 1 | Fractional part |
| `int` | 1 | Integer part (floor) |
| `fact` | 1 | Factorial `n!` (n ≤ 170) — infix `n!` or `fact(n)` |
| `nPr` / `nCr` | 2 | Permutations / combinations — `nPr(n,r)`, `nCr(n,r)` (n ≤ 1000) |
| `gcd` / `lcm` | 2 | GCD / LCM |

### Random

| Name | Arity | Description |
| --- | --- | --- |
| `rand` | 0 | Uniform float in `[0, 1)` — `rand()` |
| `randint` | 2 | Random int inclusive — `randint(a,b)` |

### Complex

| Name | Arity | Angle | Description |
| --- | --- | --- | --- |
| `cmplx` | 2 | | Pack re, im → complex — `cmplx(re,im)` |
| `re` / `im` | 1 | | Real / imaginary part — `re(z)`, `im(z)` |
| `conj` | 1 | | Conjugate — `conj(z)` |
| `arg` | 1 | yes | Argument (angle mode) — `arg(z)` |

### Mode switches

`RAD` / `DEG` / `GRAD` exist in the internal op table (arity 0) but are **not** part of the infix grammar. Set `angle_mode` on the tool instead.

Function/operator names are matched case-insensitively.

---

## Constants reference

Physics values follow **NIST CODATA 2022** (exact SI values where applicable). Use them as names in infix, e.g. `c*qe`.

**Naming pitfalls**

- Elementary charge is **`qe`** (or `echarge`). Token **`e`** is Euler’s number.
- Classical electron radius is **`r_e`**. Token **`re`** is the real-part operator.
- Case-insensitive lookup is disabled for ambiguous pairs that collide when lowercased (e.g. `muN` vs `mun`). Prefer the exact spelling from this table or `list_constants`.

| Token | Value | Unit | Note |
| --- | --- | --- | --- |
| `pi` | 3.141592653589793 | 1 | Archimedes' constant |
| `e` | 2.718281828459045 | 1 | Euler's number |
| `euler` | (alias of `e`) | 1 | Alias for `e` |
| `tau` | 6.283185307179586 | 1 | `2*pi` |
| `phi` | 1.618033988749895 | 1 | Golden ratio |
| `inf` | +∞ | 1 | Positive infinity (ops that produce non-finite results still raise `overflow` on output) |
| `mp` | 1.67262192595e-27 | kg | proton mass |
| `mn` | 1.67492750056e-27 | kg | neutron mass |
| `me` | 9.1093837139e-31 | kg | electron mass |
| `mmu` | 1.883531627e-28 | kg | muon mass |
| `a0` | 5.29177210544e-11 | m | Bohr radius |
| `h` | 6.62607015e-34 | J s | Planck constant (exact) |
| `muN` | 5.0507837393e-27 | J T⁻¹ | nuclear magneton |
| `muB` | 9.2740100657e-24 | J T⁻¹ | Bohr magneton |
| `hbar` | 1.0545718176461565e-34 | J s | reduced Planck constant |
| `alpha` | 7.2973525643e-3 | 1 | fine-structure constant |
| `r_e` | 2.8179403205e-15 | m | classical electron radius |
| `lambdaC` | 2.42631023538e-12 | m | Compton wavelength |
| `gammap` | 2.6752218708e8 | s⁻¹ T⁻¹ | proton gyromagnetic ratio |
| `lambdaCp` | 1.32140985539e-15 | m | proton Compton wavelength |
| `lambdaCn` | 1.31959090382e-15 | m | neutron Compton wavelength |
| `Rinf` | 10973731.568157 | m⁻¹ | Rydberg constant |
| `u` | 1.66053906892e-27 | kg | atomic mass unit |
| `mup` | 1.41060679545e-26 | J T⁻¹ | proton magnetic moment |
| `mue` | −9.2847646917e-24 | J T⁻¹ | electron magnetic moment |
| `mun` | −9.6623653e-27 | J T⁻¹ | neutron magnetic moment |
| `mumu` | −4.49044830e-26 | J T⁻¹ | muon magnetic moment |
| `F` | 96485.3321 | C mol⁻¹ | Faraday constant |
| `qe` | 1.602176634e-19 | C | elementary charge (exact) |
| `echarge` | (alias of `qe`) | C | Alias for `qe` |
| `NA` | 6.02214076e23 | mol⁻¹ | Avogadro constant (exact) |
| `k` | 1.380649e-23 | J K⁻¹ | Boltzmann constant (exact) |
| `k_B` | (alias of `k`) | J K⁻¹ | Alias for `k` |
| `Vm` | 0.02271095464 | m³ mol⁻¹ | molar volume ideal gas (273.15 K, 100 kPa) |
| `R` | 8.314462618 | J mol⁻¹ K⁻¹ | molar gas constant |
| `c` | 299792458 | m s⁻¹ | speed of light (exact) |
| `c1` | 3.741771852e-16 | W m² | first radiation constant |
| `c2` | 1.438776877e-2 | m K | second radiation constant |
| `sigma` | 5.670374419e-8 | W m⁻² K⁻⁴ | Stefan–Boltzmann constant |
| `eps0` | 8.8541878188e-12 | F m⁻¹ | vacuum permittivity |
| `epsilon0` | (alias of `eps0`) | F m⁻¹ | Alias for `eps0` |
| `mu0` | 1.25663706127e-6 | N A⁻² | vacuum permeability |
| `Phi0` | 2.067833848e-15 | Wb | magnetic flux quantum |
| `g` | 9.80665 | m s⁻² | standard gravity |
| `G0` | 7.748091729e-5 | S | conductance quantum |
| `Z0` | 376.730313412 | ohm | vacuum impedance |
| `t0C` | 273.15 | K | 0 °C in kelvin |
| `G` | 6.67430e-11 | m³ kg⁻¹ s⁻² | Newtonian gravitation |
| `atm` | 101325 | Pa | standard atmosphere |

---

## Unit conversions

Linear conversions multiply by a fixed factor. Temperature (`C`/`F`/`K`) uses affine conversion via kelvin.

| Id | From | To | Factor / note |
| --- | --- | --- | --- |
| `in_to_cm` / `cm_to_in` | in ↔ cm | | 2.54 |
| `ft_to_m` / `m_to_ft` | ft ↔ m | | 0.3048 |
| `yd_to_m` / `m_to_yd` | yd ↔ m | | 0.9144 |
| `mile_to_km` / `km_to_mile` | mile ↔ km | | 1.609344 |
| `nmi_to_m` / `m_to_nmi` | nmi ↔ m | | 1852 |
| `pc_to_km` / `km_to_pc` | pc ↔ km | | 3.085677581e13 |
| `acre_to_m2` / `m2_to_acre` | acre ↔ m2 | | 4046.8564224 |
| `ha_to_m2` / `m2_to_ha` | ha ↔ m2 | | 10000 |
| `gal_to_L` / `L_to_gal` | gal ↔ L | | 3.785411784 |
| `floz_to_mL` / `mL_to_floz` | floz ↔ mL | | 29.5735295625 |
| `oz_to_g` / `g_to_oz` | oz ↔ g | | 28.349523125 |
| `lb_to_kg` / `kg_to_lb` | lb ↔ kg | | 0.45359237 |
| `atm_to_Pa` / `Pa_to_atm` | atm ↔ Pa | | 101325 |
| `mmHg_to_Pa` / `Pa_to_mmHg` | mmHg ↔ Pa | | 133.322387415 |
| `lbf_to_N` / `N_to_lbf` | lbf ↔ N | | 4.4482216152605 |
| `kgf_to_N` / `N_to_kgf` | kgf ↔ N | | 9.80665 |
| `cal_to_J` / `J_to_cal` | cal ↔ J | | 4.184 |
| `hp_to_W` / `W_to_hp` | hp ↔ W | | 745.6998715822702 |
| `C_to_F` / `F_to_C` | C ↔ F | | affine temperature |
| `C_to_K` / `K_to_C` | C ↔ K | | affine temperature |
| `F_to_K` / `K_to_F` | F ↔ K | | affine temperature |

There is no free-form dimensional analysis — only this table.

---

## Precision

All numeric work uses **IEEE-754 double** (`float`) and Python `complex`. There is no arbitrary-precision mode and no Decimal/mpmath backend.

| Mechanism | Threshold / default | Role |
| --- | --- | --- |
| Integer-ish check | `1e-12` | `fact`, `nPr`, `gcd`, etc. |
| Imag → real | imag &lt; `1e-15` | Treat as real in serialization / real-only ops |
| Differentiate step `h` | `(1+\|x\|)·(1e-16)^(1/3)` | Default central-difference step |
| Integrate `tol` | `1e-10` | Adaptive Simpson tolerance (tool arg) |
| Brent root | `tol=2e-12`, max 200 iters | Bracketed root |
| Newton root | `tol=1e-10`, max 100 iters | Guess-based root |
| Linear pivot | ~`1e-14` | Singularity / no unique solution |
| JSON | `allow_nan=False` | Non-finite values are not emitted; ops raise `overflow` instead |

**Practical accuracy:** well-conditioned real arithmetic and trig typically agree with reference values to roughly **1e-9–1e-12** relative. Numerical differentiation, integration, and root-finding are weaker and depend on conditioning, step size, and tolerance — use the returned `truncation_est`, `error_est`, and `abs_f` fields as guidance, not guarantees.

Trig in degrees can show classic float artifacts (e.g. `sin(30°)` → `0.49999999999999994` rather than exact `0.5`).

---

## Limitations and safety

### Hard limits

| Limit | Value |
| --- | --- |
| Expression length | 100 000 characters |
| Token count | 10 000 |
| Factorial | n ≤ 170 |
| nPr / nCr | n ≤ 1000 |
| Matrix / vector / linear system dimension | 32 |
| Stats sample size | 100 000 |
| Polynomial degree | 1–4 |
| BASE-N | bases 2, 8, 10, 16 only; 32-bit two’s complement |
| Integration | depth ≤ 40; ≤ 100 000 evaluations |
| Calculus / root variable | only `x` |
| Calculus | numerical only (not symbolic) |
| Units | fixed conversion table only |

### Scope boundaries

- Agents write **infix**; RPN is an internal implementation detail (also returned as `rpn` on `evaluate` for transparency).
- Not a CAS: no symbolic simplify, expand, or algebraic rearrange.
- Not arbitrary precision.
- Hyperbolic functions ignore `angle_mode`.
- Mid-expression `RAD`/`DEG`/`GRAD` tokens are not supported in infix — use the `angle_mode` parameter.
- BASE-N does not accept leading `-`; use 32-bit patterns for negatives.
- Responses never include NaN/Inf JSON numbers; overflow becomes an error object.

### Error codes

| Code | Typical cause |
| --- | --- |
| `empty_expression` | Blank expression |
| `invalid_angle_mode` | Not `rad`/`deg`/`grad` |
| `unknown_token` | Bad name, character, function, or matrix/base op |
| `stack_underflow` | Internal evaluation needed more operands |
| `leftover_stack` | Internal evaluation left multiple values |
| `division_by_zero` | `/`, `inv`, base `div`, etc. |
| `domain_error` | Out-of-domain real/complex input |
| `overflow` | Non-finite result, size/bit/token limits |
| `invalid_factorial` / `invalid_combinatorics` / `invalid_integer` | Integer domain violations |
| `invalid_data` | Bad syntax, arity, lists, missing args, bad `h`/`tol` |
| `dimension_error` | Matrix/system shape mismatch |
| `singular_matrix` | Non-invertible matrix |
| `no_unique_solution` | Linear system under/over-determined |
| `no_root` / `convergence_failed` | Root finder failed |
| `invalid_base` | Unsupported base or digits |
| `unknown_conversion` | Bad unit id/pair |
| `internal_error` | Unexpected exception at tool boundary |

### Safety

Expressions are lexed and dispatched through fixed operator and constant registries. There is no Python `eval`/`exec` of user input, and no subprocess invocation for calculation.

---

## Tests

```bash
pip install -e ".[dev]"
pytest --cov=mcp_calculator --cov-report=term-missing
```
