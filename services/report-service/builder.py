"""Build a ``ReportInput`` from data persisted by sibling services.

Hits project-service, financial-service, eco-impact-service,
comparison-service, multi-criteria-service, and scenario-service via the
shared ``InternalAPI`` and assembles the merged payload the existing
PDF/Excel generators expect.
"""

from __future__ import annotations

from typing import Optional

from schemas import (
    AHPData,
    EcoData,
    FinancialData,
    RankingData,
    ReportInput,
    SensitivityData,
    TOPSISData,
)

from eco_common.exceptions import InternalServiceError
from eco_common.internal import InternalAPI


def _latest_per_name(rows):
    seen = {}
    for r in rows:
        payload = r.get("result", {})
        name = payload.get("name")
        if name and name not in seen:
            seen[name] = payload
    return seen


def _coerce_irr(value) -> float:
    """Map IRRResult dict / None / legacy float into a single float.

    -1.0 is preserved as the "no real IRR" sentinel because the existing
    PDF/Excel renderers already use ``>= 0`` to mean "render as a number".
    """
    if value is None:
        return -1.0
    if isinstance(value, dict):
        v = value.get("value")
        return float(v) if v is not None else -1.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def _coerce_optional(value, fallback: float = -1.0) -> float:
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _financial_data(rows) -> list[FinancialData]:
    return [
        FinancialData(
            name=p["name"],
            npv=p["npv"],
            irr=_coerce_irr(p.get("irr")),
            bcr=_coerce_optional(p.get("bcr"), 0.0),
            simple_payback=_coerce_optional(p.get("simple_payback")),
            discounted_payback=_coerce_optional(p.get("discounted_payback")),
            lcca=p.get("lcca", 0.0),
            yearly_details=p.get("yearly_details"),
        )
        for p in _latest_per_name(rows).values()
    ]


def _eco_data(rows) -> list[EcoData]:
    return [
        EcoData(
            name=p["name"],
            co2_reduction_tons_per_year=p["co2_reduction_tons_per_year"],
            averted_damage_uah=p["averted_damage_uah"],
            total_co2_value_usd=p["total_co2_value_usd"],
        )
        for p in _latest_per_name(rows).values()
    ]


def _ranking(comparison_rows) -> tuple[list[RankingData], str]:
    if not comparison_rows:
        return [], ""
    latest = comparison_rows[0].get("result", {})
    rows = [
        RankingData(
            name=r["name"],
            consensus_rank=r["consensus_rank"],
            rank_npv=r["rank_npv"],
            rank_co2=r["rank_co2"],
            rank_ahp=r.get("rank_ahp"),
            rank_topsis=r.get("rank_topsis"),
        )
        for r in latest.get("ranking_table", [])
    ]
    return rows, latest.get("best_consensus", "")


def _ahp_data(rows) -> Optional[AHPData]:
    if not rows:
        return None
    p = rows[0]["result"]
    return AHPData(
        criteria=p["criteria"],
        weights=p["weights"],
        consistency_ratio=p["consistency_ratio"],
        ranking=p.get("ranking", []),
    )


def _topsis_data(rows) -> Optional[TOPSISData]:
    if not rows:
        return None
    p = rows[0]["result"]
    return TOPSISData(criteria=p["criteria"], ranking=p.get("ranking", []))


def _sensitivity_data(rows) -> Optional[list[SensitivityData]]:
    for r in rows:
        if r.get("kind") != "sensitivity":
            continue
        payload = r.get("result", {})
        items = payload.get("results", [])
        return [
            SensitivityData(
                parameter=item["parameter"],
                impact_absolute=float(item.get("impact_absolute", item.get("impact_percent", 0.0))),
                impact_percent=float(item.get("impact_percent", 0.0)),
            )
            for item in items
        ]
    return None


async def build_report_input(
    project_id: int,
    *,
    token: str,
    analyst_name: str,
    recommendation: str,
    api: Optional[InternalAPI] = None,
) -> ReportInput:
    api = api or InternalAPI()
    try:
        project = await api.get_project(project_id, token)
        financial = await api.get_financial_results(project_id, token)
        eco = await api.get_eco_results(project_id, token)
        ahp = await api.get_ahp_results(project_id, token)
        topsis = await api.get_topsis_results(project_id, token)
        scenarios = await api.get_scenario_results(project_id, token)
        comparisons = await api.get_comparison_results(project_id, token)
    except InternalServiceError as exc:
        raise RuntimeError(str(exc)) from exc

    ranking_rows, best = _ranking(comparisons)

    return ReportInput(
        project_name=project.get("name", f"Project {project_id}"),
        project_description=project.get("description") or "",
        analyst_name=analyst_name,
        financial_results=_financial_data(financial),
        eco_results=_eco_data(eco),
        ranking=ranking_rows,
        best_measure=best,
        recommendation=recommendation,
        ahp_data=_ahp_data(ahp),
        topsis_data=_topsis_data(topsis),
        sensitivity_data=_sensitivity_data(scenarios),
    )
