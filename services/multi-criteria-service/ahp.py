"""AHP — principal eigenvector weights with Saaty validation.

Weights are derived from the dominant (largest-magnitude real) eigenvector
of the pairwise comparison matrix; consistency is computed from λ_max
exactly as in Saaty (1980). Alternatives are scored by vector-normalising
their raw values per criterion (with benefit/cost orientation) and then
applying the weighted sum.
"""
from __future__ import annotations

import logging
from typing import Sequence

import numpy as np

from schemas import AHPInput, AHPResult

logger = logging.getLogger(__name__)

RANDOM_INDEX = {
    1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90,
    5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41,
    9: 1.45, 10: 1.49,
}

SAATY_VALUES = {1 / 9, 1 / 8, 1 / 7, 1 / 6, 1 / 5, 1 / 4, 1 / 3, 1 / 2,
                1, 2, 3, 4, 5, 6, 7, 8, 9}


class AHPValidationError(ValueError):
    """Raised when a comparison matrix violates Saaty's preconditions."""


def _validate_saaty_matrix(matrix: np.ndarray) -> None:
    n = matrix.shape[0]
    if matrix.shape != (n, n):
        raise AHPValidationError("Comparison matrix must be square")
    for i in range(n):
        if not np.isclose(matrix[i, i], 1.0):
            raise AHPValidationError(
                f"Diagonal element [{i},{i}] must equal 1.0, got {matrix[i, i]}"
            )
        for j in range(i + 1, n):
            if matrix[i, j] <= 0 or matrix[j, i] <= 0:
                raise AHPValidationError(
                    f"Comparison [{i},{j}] and reciprocal must be positive"
                )
            if not _within_saaty_scale(matrix[i, j]):
                raise AHPValidationError(
                    f"Value at [{i},{j}]={matrix[i, j]:.4f} not on Saaty 1–9 scale"
                )
            if not np.isclose(matrix[i, j] * matrix[j, i], 1.0, atol=1e-3):
                raise AHPValidationError(
                    f"Reciprocity violated: M[{i},{j}] * M[{j},{i}] != 1"
                )


def _within_saaty_scale(value: float) -> bool:
    return any(np.isclose(value, ref, atol=1e-3) for ref in SAATY_VALUES)


def _principal_eigenvector(matrix: np.ndarray) -> tuple[np.ndarray, float]:
    """Return (weights, lambda_max) using the dominant real eigenpair."""
    eigvals, eigvecs = np.linalg.eig(matrix)
    real_mask = np.isclose(eigvals.imag, 0.0, atol=1e-6)
    if not real_mask.any():
        raise AHPValidationError("Matrix has no real principal eigenvalue")
    real_vals = eigvals[real_mask].real
    real_vecs = eigvecs[:, real_mask].real
    idx = int(np.argmax(real_vals))
    lambda_max = float(real_vals[idx])
    vec = np.abs(real_vecs[:, idx])
    total = vec.sum()
    if total == 0:
        raise AHPValidationError("Principal eigenvector is degenerate")
    return vec / total, lambda_max


def _normalise_alternative_scores(
    raw_scores: np.ndarray,
    is_benefit: Sequence[bool],
) -> np.ndarray:
    """Vector-normalise per criterion and flip cost criteria so higher = better."""
    norms = np.sqrt((raw_scores ** 2).sum(axis=0))
    norms = np.where(norms == 0, 1.0, norms)
    normalised = raw_scores / norms
    for j, benefit in enumerate(is_benefit):
        if not benefit:
            col_max = normalised[:, j].max()
            if col_max > 0:
                normalised[:, j] = col_max - normalised[:, j]
    return normalised


def calculate_ahp(data: AHPInput) -> AHPResult:
    n = len(data.criteria)
    matrix = np.array(data.comparison_matrix, dtype=float)
    if matrix.shape != (n, n):
        raise AHPValidationError(
            "Comparison matrix dimensions do not match number of criteria"
        )
    _validate_saaty_matrix(matrix)

    weights, lambda_max = _principal_eigenvector(matrix)

    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = RANDOM_INDEX.get(n, 1.49)
    cr = float(ci / ri) if ri > 0 else 0.0
    is_consistent = cr < 0.1
    if not is_consistent:
        logger.warning(
            "AHP CR=%.4f >= 0.1 — pairwise judgements are inconsistent", cr
        )

    is_benefit = data.is_benefit or [True] * n
    if len(is_benefit) != n:
        raise AHPValidationError(
            "is_benefit length must match number of criteria"
        )

    raw = np.array(
        [[float(alt.get(c, 0.0)) for c in data.criteria] for alt in data.alternatives],
        dtype=float,
    )
    normalised = _normalise_alternative_scores(raw, is_benefit)
    weighted_scores = normalised @ weights

    ranking = []
    for i, alt in enumerate(data.alternatives):
        ranking.append({
            "name": alt["name"],
            "score": round(float(weighted_scores[i]), 6),
            "scores_per_criterion": {
                c: round(float(raw[i, j]), 4) for j, c in enumerate(data.criteria)
            },
        })
    ranking.sort(key=lambda r: r["score"], reverse=True)
    for rank, item in enumerate(ranking, start=1):
        item["rank"] = rank

    return AHPResult(
        criteria=list(data.criteria),
        weights=[round(float(w), 6) for w in weights],
        consistency_ratio=round(cr, 6),
        is_consistent=is_consistent,
        lambda_max=round(lambda_max, 6),
        ranking=ranking,
    )
