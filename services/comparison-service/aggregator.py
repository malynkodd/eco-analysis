"""Aggregate persisted results from sibling services into a single
``ComparisonInput`` keyed by measure name.

The merge rule is: take the latest financial result per measure name,
the latest eco result per measure name, and the latest AHP/TOPSIS scores
(if present) — then emit one ``MeasureData`` per measure.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from schemas import MeasureData


def _latest_by_name(results: List[dict], name_path: List[str]) -> Dict[str, dict]:
    """Pick the most recent (first by id desc) result per measure name."""
    latest: Dict[str, dict] = {}
    for row in results:
        payload = row.get("result", {})
        name = payload.get(name_path[0])
        if name is None:
            continue
        if name not in latest:
            latest[name] = payload
    return latest


def _index_alternative_scores(rows: List[dict]) -> Dict[str, float]:
    """Collect the most recent AHP/TOPSIS score per alternative name."""
    scores: Dict[str, float] = {}
    for row in rows:
        ranking = row.get("result", {}).get("ranking", [])
        for entry in ranking:
            name = entry.get("name") or entry.get("alternative")
            if not name or name in scores:
                continue
            score = entry.get("score") or entry.get("closeness") or entry.get("weight")
            if score is None:
                continue
            scores[name] = float(score)
    return scores


def build_measures(
    *,
    financial_results: List[dict],
    eco_results: List[dict],
    ahp_results: Optional[List[dict]] = None,
    topsis_results: Optional[List[dict]] = None,
) -> List[MeasureData]:
    fin_by_name = _latest_by_name(financial_results, ["name"])
    eco_by_name = _latest_by_name(eco_results, ["name"])
    ahp_scores = _index_alternative_scores(ahp_results or [])
    topsis_scores = _index_alternative_scores(topsis_results or [])

    measures: List[MeasureData] = []
    common = sorted(set(fin_by_name) & set(eco_by_name))
    for name in common:
        fin = fin_by_name[name]
        eco = eco_by_name[name]
        measures.append(
            MeasureData(
                name=name,
                npv=float(fin["npv"]),
                irr=_irr_value(fin.get("irr")),
                bcr=fin.get("bcr"),
                simple_payback=fin.get("simple_payback"),
                co2_reduction=float(eco["co2_reduction_tons_per_year"]),
                ahp_score=ahp_scores.get(name),
                topsis_score=topsis_scores.get(name),
            )
        )
    return measures


def _irr_value(irr) -> Optional[float]:
    """Accept both the new IRRResult dict and the legacy bare float."""
    if irr is None:
        return None
    if isinstance(irr, dict):
        value = irr.get("value")
        return float(value) if value is not None else None
    try:
        return float(irr)
    except (TypeError, ValueError):
        return None
