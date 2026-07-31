# mcp_calculator

Provides a reverse Polish Notation scientific calculator MCP server for LLMs. Verifies numeric work safely (stack machine + allowlists — **no `eval`**) to reduce hallucinated maths answers.

## Install / use (Cursor / Claude Desktop)

From GitHub (replace owner/repo):

```json
{
  "mcpServers": {
    "mcp_calculator": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/<owner>/mcp_calculator", "mcp-calculator"]
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

## Tools

| Tool | Purpose |
| --- | --- |
| `rpn_eval` | RPN expression, `angle_mode` = `rad` \| `deg` \| `grad` |
| `list_operations` / `list_constants` / `list_unit_conversions` | Discovery |
| `matrix_op` | Matrix/vector ops |
| `stats_1var` / `stats_2var` | Statistics / regression |
| `solve_linear` / `solve_root` / `solve_polynomial` | Equation solving |
| `base_convert` / `base_arith` | BASE-N |
| `differentiate` / `integrate` | Numerical calculus on RPN `f(x)` |
| `convert_unit` | Metric conversions |

On `ok: false`, read **`message`** and **`hint`** before retrying.

### RPN examples

- `3 4 +` → `7`
- `30 sin` with `angle_mode=deg` → `0.5`
- `50 sin` with `angle_mode=grad` → `0.5`
- `3 4 cmplx abs` → `5`
- `pi 6 / sin` (rad) → `0.5`

Constants use CODATA 2022 values (NIST). Elementary charge is `qe` (Euler’s number is `e`). Classical electron radius is `r_e` (`re` is the real-part operator).

## Tests

```bash
pip install -e ".[dev]"
pytest --cov=mcp_calculator --cov-report=term-missing
```

## Safety

Expressions are tokenized and dispatched through fixed operator/constant registries. There is no Python `eval`/`exec` of user input.
