from fastapi import FastAPI, Depends
from fastapi.responses import Response
import schemas
import generator
import excel_generator
import auth

app = FastAPI(title="Report Service", root_path="/api/reports")


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
