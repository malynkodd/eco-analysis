"""TOPSIS — Hwang & Yoon's distance-to-ideal method."""
from __future__ import annotations

import numpy as np

from schemas import TOPSISInput, TOPSISResult


class TOPSISValidationError(ValueError):
    """Raised when TOPSIS inputs are inconsistent."""


def _build_decision_matrix(
    alternatives: list[dict], criteria: list[str]
) -> tuple[np.ndarray, list[str]]:
    names: list[str] = []
    rows: list[list[float]] = []
    for alt in alternatives:
        if "name" not in alt:
            raise TOPSISValidationError("Alternative is missing 'name'")
        names.append(alt["name"])
        row = []
        for c in criteria:
            if c not in alt:
                raise TOPSISValidationError(
                    f"Alternative '{alt['name']}' is missing criterion '{c}'"
                )
            row.append(float(alt[c]))
        rows.append(row)
    return np.array(rows, dtype=float), names


def calculate_topsis(data: TOPSISInput) -> TOPSISResult:
    n_crit = len(data.criteria)
    if len(data.weights) != n_crit:
        raise TOPSISValidationError(
            "Number of weights must match number of criteria"
        )
    if len(data.is_benefit) != n_crit:
        raise TOPSISValidationError(
            "Number of benefit flags must match number of criteria"
        )
    if not data.alternatives:
        raise TOPSISValidationError("At least one alternative is required")

    weights = np.asarray(data.weights, dtype=float)
    if weights.sum() <= 0:
        raise TOPSISValidationError("Weight sum must be positive")
    weights = weights / weights.sum()

    matrix, names = _build_decision_matrix(data.alternatives, list(data.criteria))
    n_alt = matrix.shape[0]

    norms = np.sqrt((matrix ** 2).sum(axis=0))
    norms = np.where(norms == 0, 1.0, norms)
    normalised = matrix / norms

    weighted = normalised * weights

    ideal_best = np.empty(n_crit)
    ideal_worst = np.empty(n_crit)
    for j, benefit in enumerate(data.is_benefit):
        col = weighted[:, j]
        ideal_best[j] = col.max() if benefit else col.min()
        ideal_worst[j] = col.min() if benefit else col.max()

    dist_best = np.sqrt(((weighted - ideal_best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((weighted - ideal_worst) ** 2).sum(axis=1))
    denominators = dist_best + dist_worst
    closeness = np.where(denominators == 0, 0.0, dist_worst / denominators)

    ranking = [
        {
            "name": names[i],
            "closeness_coefficient": round(float(closeness[i]), 6),
            "distance_to_ideal": round(float(dist_best[i]), 6),
            "distance_to_anti_ideal": round(float(dist_worst[i]), 6),
        }
        for i in range(n_alt)
    ]
    ranking.sort(key=lambda r: r["closeness_coefficient"], reverse=True)
    for rank, item in enumerate(ranking, start=1):
        item["rank"] = rank

    return TOPSISResult(
        criteria=list(data.criteria),
        weights=[round(float(w), 6) for w in weights],
        ranking=ranking,
    )
