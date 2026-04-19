# Benchmarks

Performance sanity-checks for the compute core. These run in-process against
the calculator modules without touching HTTP, FastAPI, or Postgres, so they
measure the algorithm itself rather than request overhead.

## Running

```bash
python benchmarks/scaling.py
```

Requires the project's runtime deps (`numpy`, `scipy`, `pydantic`).

## Scenarios

- **Multi-criteria (AHP + TOPSIS)** — sweeps `n_alternatives ∈ {10, 50, 100,
  500, 1000}` over the default 4-criterion Saaty matrix.
- **Sensitivity** — sweeps `steps ∈ {5, 10, 25, 50}` against a typical
  15-year portfolio scenario with `variation_percent = 30%`.
- **Break-even** — 4-parameter solver latency (Brent).

## Expected order of magnitude

On a commodity dev laptop (x86_64, single thread):

| Scenario | Typical p95 |
|----------|-------------|
| AHP n_alts=100 | < 5 ms |
| AHP n_alts=1000 | < 40 ms |
| TOPSIS n_alts=1000 | < 30 ms |
| Sensitivity steps=50 | < 15 ms |
| Break-even (4 params) | < 50 ms |

Deviations above 5× the numbers above warrant investigation (likely an O(n²)
regression in normalisation or a mis-bracketed Brent search).
