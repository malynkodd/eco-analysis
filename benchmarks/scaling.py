"""In-process scaling benchmark for the compute-heavy calculators.

Runs locally — no services required. Exercises AHP + TOPSIS with growing
alternative counts and the sensitivity engine with growing step counts, then
prints p50 / p95 / max latency per scenario.

Usage:
    python benchmarks/scaling.py

Why in-process: the TS asks for a performance evaluation of the analytic
core; HTTP / TLS / JSON overhead swamps the calculators themselves at small
input sizes, so measuring the pure algorithm gives a stable, reproducible
number for capacity planning.
"""

from __future__ import annotations

import importlib.util
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load(prefix: str, service_dir: str, module: str):
    path = ROOT / "services" / service_dir / f"{module}.py"
    spec = importlib.util.spec_from_file_location(f"{prefix}_{module}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"{prefix}_{module}"] = mod
    if module == "schemas":
        sys.modules["schemas"] = mod
    spec.loader.exec_module(mod)
    return mod


def _percentile(samples: list[float], pct: float) -> float:
    if not samples:
        return 0.0
    k = max(0, min(len(samples) - 1, int(round((pct / 100) * (len(samples) - 1)))))
    return sorted(samples)[k]


def _report(name: str, samples: list[float]) -> None:
    p50 = _percentile(samples, 50) * 1000
    p95 = _percentile(samples, 95) * 1000
    mx = max(samples) * 1000
    mean = statistics.mean(samples) * 1000
    print(f"  {name:<40} mean={mean:7.2f}ms  p50={p50:7.2f}ms  p95={p95:7.2f}ms  max={mx:7.2f}ms")


def bench_multi_criteria(ahp_mod, topsis_mod, schemas_mod) -> None:
    print("\n[multi-criteria] AHP + TOPSIS — scaling with alternatives")
    criteria = ["npv", "irr", "co2", "payback"]
    is_benefit = [True, True, True, False]
    matrix = [
        [1, 2, 2, 3],
        [1 / 2, 1, 1, 2],
        [1 / 2, 1, 1, 2],
        [1 / 3, 1 / 2, 1 / 2, 1],
    ]

    for n_alts in (10, 50, 100, 500, 1000):
        alternatives = [
            {
                "name": f"m{i}",
                "npv": 100_000 + i * 37,
                "irr": 10 + (i % 20),
                "co2": 5 + (i % 15),
                "payback": 2 + (i % 10),
            }
            for i in range(n_alts)
        ]
        ahp_samples: list[float] = []
        topsis_samples: list[float] = []
        for _ in range(10):
            t = time.perf_counter()
            ahp_res = ahp_mod.calculate_ahp(
                schemas_mod.AHPInput(
                    criteria=criteria,
                    comparison_matrix=matrix,
                    alternatives=alternatives,
                    is_benefit=is_benefit,
                )
            )
            ahp_samples.append(time.perf_counter() - t)

            t = time.perf_counter()
            topsis_mod.calculate_topsis(
                schemas_mod.TOPSISInput(
                    criteria=criteria,
                    weights=ahp_res.weights,
                    is_benefit=is_benefit,
                    alternatives=alternatives,
                )
            )
            topsis_samples.append(time.perf_counter() - t)

        _report(f"AHP   n_alts={n_alts}", ahp_samples)
        _report(f"TOPSIS n_alts={n_alts}", topsis_samples)


def bench_sensitivity(calc_mod, schemas_mod) -> None:
    print("\n[scenario] sensitivity — scaling with step count")
    base = schemas_mod.BaseScenario(
        name="benchmark",
        initial_investment=500_000,
        operational_cost=10_000,
        expected_savings=80_000,
        lifetime_years=15,
        discount_rate=0.1,
    )
    for steps in (5, 10, 25, 50):
        samples: list[float] = []
        for _ in range(10):
            t = time.perf_counter()
            calc_mod.run_sensitivity(
                schemas_mod.SensitivityInput(base=base, variation_percent=30.0, steps=steps)
            )
            samples.append(time.perf_counter() - t)
        _report(f"sensitivity steps={steps}", samples)


def bench_breakeven(calc_mod, schemas_mod) -> None:
    print("\n[scenario] break-even — solver latency")
    base = schemas_mod.BaseScenario(
        name="benchmark",
        initial_investment=500_000,
        operational_cost=10_000,
        expected_savings=80_000,
        lifetime_years=15,
        discount_rate=0.1,
    )
    samples: list[float] = []
    for _ in range(50):
        t = time.perf_counter()
        calc_mod.run_breakeven(schemas_mod.BreakEvenInput(base=base))
        samples.append(time.perf_counter() - t)
    _report("break-even (4 params)", samples)


def main() -> None:
    mc_schemas = _load("mc", "multi-criteria-service", "schemas")
    ahp = _load("mc", "multi-criteria-service", "ahp")
    topsis = _load("mc", "multi-criteria-service", "topsis")

    bench_multi_criteria(ahp, topsis, mc_schemas)

    sc_schemas = _load("sc", "scenario-service", "schemas")
    sc_calc = _load("sc", "scenario-service", "calculator")
    bench_sensitivity(sc_calc, sc_schemas)
    bench_breakeven(sc_calc, sc_schemas)

    print("\nBenchmark complete.")


if __name__ == "__main__":
    main()
