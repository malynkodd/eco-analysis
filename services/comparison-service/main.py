from fastapi import FastAPI, Depends
import schemas
import calculator
import auth

app = FastAPI(title="Comparison Service", root_path="/api/comparison")


@app.get("/health")
def health():
    return {"status": "ok", "service": "comparison-service"}


@app.post("/compare", response_model=schemas.ComparisonResult)
def compare(
    data: schemas.ComparisonInput,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Порівняльний аналіз заходів за всіма методами.
    Будує зведену таблицю рангів, консенсусний рейтинг
    та Pareto-фронт (NPV vs CO2).
    """
    return calculator.compare_measures(data.measures)