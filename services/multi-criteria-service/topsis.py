import numpy as np
from schemas import TOPSISInput, TOPSISResult


def calculate_topsis(data: TOPSISInput) -> TOPSISResult:
    n_alt = len(data.alternatives)
    n_crit = len(data.criteria)

    # ─── Крок 1: Будуємо матрицю рішень ───────────────────────────
    matrix = np.zeros((n_alt, n_crit))
    names = []
    for i, alt in enumerate(data.alternatives):
        names.append(alt["name"])
        for j, criterion in enumerate(data.criteria):
            matrix[i][j] = alt.get(criterion, 0)

    # ─── Крок 2: Нормалізація матриці ─────────────────────────────
    # Евклідова нормалізація: x_ij / sqrt(sum(x_ij^2))
    norms = np.sqrt((matrix ** 2).sum(axis=0))
    norms[norms == 0] = 1  # захист від ділення на 0
    normalized = matrix / norms

    # ─── Крок 3: Зважена нормалізація ─────────────────────────────
    weights = np.array(data.weights)
    weighted = normalized * weights

    # ─── Крок 4: Ідеальне та анти-ідеальне рішення ────────────────
    ideal_best = np.zeros(n_crit)
    ideal_worst = np.zeros(n_crit)

    for j in range(n_crit):
        if data.is_benefit[j]:
            # Вигідний критерій: ідеал = максимум
            ideal_best[j] = weighted[:, j].max()
            ideal_worst[j] = weighted[:, j].min()
        else:
            # Витратний критерій: ідеал = мінімум
            ideal_best[j] = weighted[:, j].min()
            ideal_worst[j] = weighted[:, j].max()

    # ─── Крок 5: Евклідові відстані до ідеалу ─────────────────────
    dist_best = np.sqrt(((weighted - ideal_best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((weighted - ideal_worst) ** 2).sum(axis=1))

    # ─── Крок 6: Коефіцієнт відносної близькості ──────────────────
    # C_i = d_worst / (d_best + d_worst), чим більше — тим краще
    denominators = dist_best + dist_worst
    closeness = np.where(
        denominators == 0,
        0,
        dist_worst / denominators
    )

    # ─── Крок 7: Ранжування ───────────────────────────────────────
    ranking = []
    for i in range(n_alt):
        ranking.append({
            "name": names[i],
            "closeness_coefficient": round(float(closeness[i]), 4),
            "distance_to_ideal": round(float(dist_best[i]), 4),
            "distance_to_anti_ideal": round(float(dist_worst[i]), 4)
        })

    ranking.sort(key=lambda x: x["closeness_coefficient"], reverse=True)
    for i, item in enumerate(ranking):
        item["rank"] = i + 1

    return TOPSISResult(
        criteria=data.criteria,
        weights=data.weights,
        ranking=ranking
    )