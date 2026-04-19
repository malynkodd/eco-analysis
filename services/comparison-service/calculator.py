"""Cross-method ranking + Pareto front for a project's measures.

Inputs may carry ``None`` for IRR/BCR/payback (the financial service now
returns those values when no real solution exists). Missing values are
ranked last in their respective category; payback ``None`` is treated as
``+inf`` (lower is better) and the others as ``-inf`` (higher is better).
"""
from __future__ import annotations

import logging
import math
from typing import List, Optional

from schemas import ComparisonResult, MeasureData, ParetoItem, RankingRow

logger = logging.getLogger(__name__)


def _safe_higher_better(v: Optional[float]) -> float:
    """Map ``None`` to -inf so it always ranks last when higher is better."""
    return -math.inf if v is None else float(v)


def _safe_lower_better(v: Optional[float]) -> float:
    """Map ``None`` to +inf so it always ranks last when lower is better."""
    return math.inf if v is None else float(v)


def rank_list(values: List[float], reverse: bool = True) -> List[int]:
    sorted_vals = sorted(enumerate(values), key=lambda x: x[1], reverse=reverse)
    ranks = [0] * len(values)
    for rank, (idx, _) in enumerate(sorted_vals, start=1):
        ranks[idx] = rank
    return ranks


def calculate_pareto(measures: List[MeasureData]) -> List[ParetoItem]:
    items = []
    for m in measures:
        is_dominated = False
        for other in measures:
            if other.name == m.name:
                continue
            if (
                other.npv >= m.npv
                and other.co2_reduction >= m.co2_reduction
                and (other.npv > m.npv or other.co2_reduction > m.co2_reduction)
            ):
                is_dominated = True
                break
        items.append(ParetoItem(
            name=m.name,
            npv=m.npv,
            co2_reduction=m.co2_reduction,
            is_pareto_optimal=not is_dominated,
        ))
    return items


def compare_measures(measures: List[MeasureData]) -> ComparisonResult:
    if not measures:
        raise ValueError("At least one measure is required for comparison")

    npv_ranks = rank_list([m.npv for m in measures], reverse=True)
    irr_ranks = rank_list([_safe_higher_better(m.irr) for m in measures], reverse=True)
    bcr_ranks = rank_list([_safe_higher_better(m.bcr) for m in measures], reverse=True)
    pb_ranks = rank_list(
        [_safe_lower_better(m.simple_payback) for m in measures], reverse=False
    )
    co2_ranks = rank_list([m.co2_reduction for m in measures], reverse=True)

    ahp_ranks: Optional[List[int]] = None
    topsis_ranks: Optional[List[int]] = None
    if any(m.ahp_score is not None for m in measures):
        ahp_ranks = rank_list(
            [_safe_higher_better(m.ahp_score) for m in measures], reverse=True
        )
    if any(m.topsis_score is not None for m in measures):
        topsis_ranks = rank_list(
            [_safe_higher_better(m.topsis_score) for m in measures], reverse=True
        )

    ranking_table: List[RankingRow] = []
    for i, m in enumerate(measures):
        ranks_to_avg = [npv_ranks[i], irr_ranks[i], bcr_ranks[i], pb_ranks[i], co2_ranks[i]]
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
            consensus_rank=0,
        ))

    ranking_table.sort(key=lambda x: x.consensus_score)
    for i, row in enumerate(ranking_table):
        row.consensus_rank = i + 1

    pareto_front = calculate_pareto(measures)

    best_financial = measures[npv_ranks.index(1)].name
    best_ecological = measures[co2_ranks.index(1)].name
    best_consensus = ranking_table[0].name

    n = len(measures)
    conflicting: List[str] = []
    for row in ranking_table:
        ranks = [row.rank_npv, row.rank_irr, row.rank_bcr, row.rank_payback, row.rank_co2]
        if row.rank_ahp:
            ranks.append(row.rank_ahp)
        if row.rank_topsis:
            ranks.append(row.rank_topsis)
        if max(ranks) - min(ranks) > n // 2:
            conflicting.append(row.name)

    logger.info(
        "Comparison done: %d measures, best_consensus='%s', conflicting=%s",
        n, best_consensus, conflicting,
    )

    return ComparisonResult(
        ranking_table=ranking_table,
        pareto_front=pareto_front,
        best_financial=best_financial,
        best_ecological=best_ecological,
        best_consensus=best_consensus,
        conflicting=conflicting,
    )
