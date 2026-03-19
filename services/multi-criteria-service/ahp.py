import logging
import numpy as np
from typing import List
from schemas import AHPInput, AHPResult

logger = logging.getLogger(__name__)

# Індекси узгодженості для матриць розміром 1-10 (таблиця Сааті)
RANDOM_INDEX = {
    1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90,
    5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41,
    9: 1.45, 10: 1.49
}


def calculate_ahp(data: AHPInput) -> AHPResult:
    n = len(data.criteria)
    matrix = np.array(data.comparison_matrix, dtype=float)

    # ─── Крок 0: Виправлення оберненої симетрії матриці ───────────
    # AHP вимагає A[i][j] * A[j][i] = 1 (обернена симетрія).
    # Якщо клієнт передав неузгоджену матрицю — виправляємо автоматично:
    # верхній трикутник лишаємо як є, нижній примусово = 1 / верхній.
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] <= 0:
                logger.warning(
                    "AHP matrix[%d][%d] = %f is non-positive, resetting to 1",
                    i, j, matrix[i][j]
                )
                matrix[i][j] = 1.0
            # Enforce A[j][i] = 1 / A[i][j]
            matrix[j][i] = 1.0 / matrix[i][j]
        # Diagonal must be 1
        matrix[i][i] = 1.0

    logger.debug("AHP matrix after symmetry correction:\n%s", matrix)

    # ─── Крок 1: Нормалізація матриці ─────────────────────────────
    # Ділимо кожен елемент на суму стовпця
    col_sums = matrix.sum(axis=0)
    normalized = matrix / col_sums

    # ─── Крок 2: Вектор пріоритетів (ваги критеріїв) ──────────────
    # Середнє по рядках нормалізованої матриці
    weights = normalized.mean(axis=1)

    # ─── Крок 3: Перевірка узгодженості (CR) ──────────────────────
    # Знаходимо λ_max
    weighted_sum = matrix @ weights
    lambda_values = weighted_sum / weights
    lambda_max = lambda_values.mean()

    # Consistency Index (CI)
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0

    # Random Index (RI) з таблиці Сааті
    ri = RANDOM_INDEX.get(n, 1.49)

    # Consistency Ratio (CR) — має бути < 0.1
    cr = ci / ri if ri > 0 else 0.0

    if cr >= 0.1:
        logger.warning(
            "AHP consistency ratio CR=%.4f >= 0.1 — matrix is inconsistent", cr
        )

    # ─── Крок 4: Ранжування альтернатив ───────────────────────────
    ranking = []
    for alt in data.alternatives:
        name = alt["name"]
        scores = [alt.get(criterion, 0) for criterion in data.criteria]

        # Зважена сума оцінок
        weighted_score = sum(
            score * weight
            for score, weight in zip(scores, weights)
        )
        ranking.append({
            "name": name,
            "score": round(float(weighted_score), 4),
            "scores_per_criterion": {
                c: round(s, 3)
                for c, s in zip(data.criteria, scores)
            }
        })

    # Сортуємо за зваженою оцінкою (більше = краще)
    ranking.sort(key=lambda x: x["score"], reverse=True)
    for i, item in enumerate(ranking):
        item["rank"] = i + 1

    return AHPResult(
        criteria=data.criteria,
        weights=[round(float(w), 4) for w in weights],
        consistency_ratio=round(float(cr), 4),
        is_consistent=bool(cr < 0.1),
        ranking=ranking
    )
