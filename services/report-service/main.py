import os
from typing import List

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import auth
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


@app.post("/generate")
def generate_report(
    data: schemas.ReportInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """Генерує PDF звіт з результатами аналізу."""
    pdf_bytes = generator.generate_pdf(data)

    # Ім'я файлу — тільки ASCII, без кирилиці
    filename = "eco_analysis_report.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.post("/generate/excel")
def generate_excel_report(
    data: schemas.ReportInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """Генерує Excel звіт"""
    excel_bytes = excel_generator.generate_excel(data)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=eco_report.xlsx"}
    )
