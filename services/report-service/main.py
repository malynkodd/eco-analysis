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

import auth
import builder
import excel_generator
import generator
import schemas
from fastapi import Depends, HTTPException, Query
from fastapi.responses import Response

from eco_common.api_setup import create_app

OPENAPI_TAGS = [
    {"name": "legacy", "description": "Body-driven PDF/Excel generation."},
    {"name": "projects", "description": "Project-scoped PDF/Excel generation."},
    {"name": "system", "description": "Health and metadata."},
]

app = create_app(
    title="Report Service",
    description="PDF (ReportLab) and Excel (openpyxl) reports for projects.",
    root_path="/api/v1/reports",
    openapi_tags=OPENAPI_TAGS,
)


@app.get("/health", tags=["system"], summary="Liveness probe")
def health():
    return {"status": "ok", "service": "report-service"}


@app.post(
    "/generate",
    tags=["legacy"],
    summary="Generate a PDF report from a fully-assembled ReportInput",
    response_class=Response,
)
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


@app.post(
    "/generate/excel",
    tags=["legacy"],
    summary="Generate an Excel report from a fully-assembled ReportInput",
    response_class=Response,
)
def generate_excel_report(
    data: schemas.ReportInput,
    current_user: dict = Depends(auth.get_current_user),
):
    excel_bytes = excel_generator.generate_excel(data)
    return Response(
        content=excel_bytes,
        media_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        headers={"Content-Disposition": "attachment; filename=eco_report.xlsx"},
    )


def _analyst_name(current_user: dict) -> str:
    return current_user.get("username") or "Analyst"


@app.post(
    "/projects/{project_id}/pdf",
    tags=["projects"],
    summary="Build the report payload for a project and return a PDF",
    response_class=Response,
)
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
            "Content-Disposition": (f"attachment; filename=eco_report_project_{project_id}.pdf")
        },
    )


@app.post(
    "/projects/{project_id}/excel",
    tags=["projects"],
    summary="Build the report payload for a project and return an Excel workbook",
    response_class=Response,
)
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
        media_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        headers={
            "Content-Disposition": (f"attachment; filename=eco_report_project_{project_id}.xlsx")
        },
    )
