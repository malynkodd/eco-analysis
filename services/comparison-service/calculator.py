import logging
from typing import List, Optional
from schemas import MeasureData, RankingRow, ParetoItem, ComparisonResult

logger = logging.getLogger(__name__)

# Sentinel value: -1.0 означає "показник відсутній / не окупається"
_SENTINEL = -1.0

# Замінники sentinel для коректного ранжування
_WORST_PAYBACK = float('inf')   # найгірший payback = нескінченність (менше = краще)
_WORST_IRR = -999.0             # найгірший IRR (більше = краще, тому від'ємний)


def _safe_payback(v: float) -> float:
    """Замінює sentinel -1.0 (не окупається) на нескінченність для ранжування."""
    return _WORST_PAYBACK if v <= _SENTINEL else v


def _safe_irr(v: float) -> float:
    """Замінює sentinel -1.0 (IRR відсутній) на дуже погане значення."""
    return _WORST_IRR if v <= _SENTINEL else v


def rank_list(values: List[float], reverse: bool = True) -> List[int]:
    """
    Повертає ранги для списку значень.
    reverse=True — більше значення = кращий ранг (для NPV, IRR, BCR, CO2)
    reverse=False — менше значення = кращий ранг (для Payback)
    Значення float('inf') або -999.0 отримують найгірший ранг автоматично.
    """
    sorted_vals = sorted(enumerate(values), key=lambda x: x[1], reverse=reverse)
    ranks = [0] * len(values)
    for rank, (idx, _) in enumerate(sorted_vals, start=1):
        ranks[idx] = rank
    return ranks


def calculate_pareto(measures: List[MeasureData]) -> List[ParetoItem]:
    """
    Pareto-аналіз: захід є Pareto-оптимальним якщо
    жоден інший захід не перевершує його одночасно
    за NPV і CO2.
    """
    items = []
    for m in measures:
        # Перевіряємо чи домінується цей захід
        is_dominated = False
        for other in measures:
            if other.name == m.name:
                continue
            # other домінує m якщо він кращий або рівний по обох критеріях
            # і строго кращий хоча б по одному
            if (other.npv >= m.npv and other.co2_reduction >= m.co2_reduction and
                    (other.npv > m.npv or other.co2_reduction > m.co2_reduction)):
                is_dominated = True
                break

        items.append(ParetoItem(
            name=m.name,
            npv=m.npv,
            co2_reduction=m.co2_reduction,
            is_pareto_optimal=not is_dominated
        ))

    return items


def compare_measures(measures: List[MeasureData]) -> ComparisonResult:
    """Головна функція порівняльного аналізу"""

    # ─── Ранжування по кожному методу ─────────────────────────────
    npv_ranks = rank_list([m.npv for m in measures], reverse=True)
    irr_ranks = rank_list([_safe_irr(m.irr) for m in measures], reverse=True)
    bcr_ranks = rank_list([m.bcr for m in measures], reverse=True)
    # Payback — менше краще; sentinel -1.0 → нескінченність (гірше за будь-який реальний)
    pb_ranks = rank_list([_safe_payback(m.simple_payback) for m in measures], reverse=False)
    co2_ranks = rank_list([m.co2_reduction for m in measures], reverse=True)

    ahp_ranks = None
    topsis_ranks = None
    if any(m.ahp_score is not None for m in measures):
        ahp_scores = [m.ahp_score or 0 for m in measures]
        ahp_ranks = rank_list(ahp_scores, reverse=True)
    if any(m.topsis_score is not None for m in measures):
        topsis_scores = [m.topsis_score or 0 for m in measures]
        topsis_ranks = rank_list(topsis_scores, reverse=True)

    # ─── Консенсусний рейтинг ─────────────────────────────────────
    # Середнє арифметичне всіх рангів (менше = краще)
    ranking_table = []
    for i, m in enumerate(measures):
        ranks_to_avg = [
            npv_ranks[i], irr_ranks[i], bcr_ranks[i],
            pb_ranks[i], co2_ranks[i]
        ]
        if ahp_ranks:
            ranks_to_avg.append(ahp_ranks[i])
        if topsis_ranks:
            ranks_to_avg.append(topsis_ranks[i])

        consensus_score = round(sum(ranks_to_avg) / len(ranks_to_avg), 3)

        ranking_table.append(RankingRow(
            name=m.name,
            rank_npv=npv_ranks[i],
            rank_irr=irr_ranks[i],
            rank_bcr=bcr_ranks[i],
            rank_payback=pb_ranks[i],
            rank_co2=co2_ranks[i],
            rank_ahp=ahp_ranks[i] if ahp_ranks else None,
            rank_topsis=topsis_ranks[i] if topsis_ranks else None,
            consensus_score=consensus_score,
            consensus_rank=0  # заповнимо нижче
        ))

    # Сортуємо за консенсусним балом (менше = краще)
    ranking_table.sort(key=lambda x: x.consensus_score)
    for i, row in enumerate(ranking_table):
        row.consensus_rank = i + 1

    # ─── Pareto-аналіз ────────────────────────────────────────────
    pareto_front = calculate_pareto(measures)

    # ─── Визначаємо переможців ────────────────────────────────────
    best_financial = measures[npv_ranks.index(1)].name
    best_ecological = measures[co2_ranks.index(1)].name
    best_consensus = ranking_table[0].name

    # ─── Суперечливі заходи ───────────────────────────────────────
    # Захід суперечливий якщо різниця між найкращим і найгіршим
    # рангом серед методів > половини кількості альтернатив
    n = len(measures)
    conflicting = []
    for row in ranking_table:
        ranks = [row.rank_npv, row.rank_irr, row.rank_bcr,
                 row.rank_payback, row.rank_co2]
        if row.rank_ahp:
            ranks.append(row.rank_ahp)
        if row.rank_topsis:
            ranks.append(row.rank_topsis)
        if max(ranks) - min(ranks) > n // 2:
            conflicting.append(row.name)

    logger.info(
        "Comparison done: %d measures, best_consensus='%s', conflicting=%s",
        n, best_consensus, conflicting
    )

    return ComparisonResult(
        ranking_table=ranking_table,
        pareto_front=pareto_front,
        best_financial=best_financial,
        best_ecological=best_ecological,
        best_consensus=best_consensus,
        conflicting=conflicting
    )
