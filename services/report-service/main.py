"""Report service — PDF + Excel reports.

Two endpoint families:
  * Legacy: ``/generate`` and ``/generate/excel`` accept a full
    ``ReportInput`` body (kept for clients that build the payload
    themselves). Will be removed once the frontend migrates.
  * Project-scoped: ``/projects/{id}/pdf`` and ``/projects/{id}/excel``
    take only ``project_id`` and assemble the payload by calling sibling
    services through ``eco_common.internal``.
"""
from __future__ import annotations

import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import auth
import builder
import excel_generator
import generator
import schemas


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _cors_origins() -> List[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="Report Service",
    root_path="/api/v1/reports",
    docs_url=None if _is_production() else "/docs",
    redoc_url=None if _is_production() else "/redoc",
    openapi_url=None if _is_production() else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "report-service"}


# ─── Legacy body-driven generation ───────────────────────────────────────────


@app.post("/generate")
def generate_report(
    data: schemas.ReportInput,
    current_user: dict = Depends(auth.get_current_user),
):
    pdf_bytes = generator.generate_pdf(data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=eco_analysis_report.pdf"},
    )


@app.post("/generate/excel")
def generate_excel_report(
    data: schemas.ReportInput,
    current_user: dict = Depends(auth.get_current_user),
):
    excel_bytes = excel_generator.generate_excel(data)
    return Response(
        content=excel_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": "attachment; filename=eco_report.xlsx"},
    )


# ─── Project-scoped (project_id only) ────────────────────────────────────────


def _analyst_name(current_user: dict) -> str:
    return current_user.get("username") or "Analyst"


@app.post("/projects/{project_id}/pdf")
async def project_pdf(
    project_id: int,
    recommendation: str = Query(default=""),
    current_user: dict = Depends(auth.get_current_user),
):
    try:
        report_input = await builder.build_report_input(
            project_id,
            token=current_user["token"],
            analyst_name=_analyst_name(current_user),
            recommendation=recommendation,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    pdf_bytes = generator.generate_pdf(report_input)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=eco_report_project_{project_id}.pdf"
            )
        },
    )


@app.post("/projects/{project_id}/excel")
async def project_excel(
    project_id: int,
    recommendation: str = Query(default=""),
    current_user: dict = Depends(auth.get_current_user),
):
    try:
        report_input = await builder.build_report_input(
            project_id,
            token=current_user["token"],
            analyst_name=_analyst_name(current_user),
            recommendation=recommendation,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    excel_bytes = excel_generator.generate_excel(report_input)
    return Response(
        content=excel_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f"attachment; filename=eco_report_project_{project_id}.xlsx"
            )
        },
    )
