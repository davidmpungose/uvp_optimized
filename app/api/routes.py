from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
import pyodbc

from app.api.schemas import api_safe, parse_quarters, parse_risk_levels
from app.database.connection import database_connection
from app.database.reporting_repository import (
    get_available_quarters,
    get_case_detail,
    get_case_page,
    get_dashboard_summary,
    get_distributions,
    get_top_hs,
    get_top_traders,
    get_trader_history,
)
from app.services.api_settings import ApiSettings
from config.settings import DatabaseSettings, PipelineSettings

router = APIRouter(prefix="/api/v1")


def get_connection():
    settings = DatabaseSettings.from_environment()
    with database_connection(settings) as connection:
        yield connection


def pipeline_settings() -> PipelineSettings:
    return PipelineSettings.from_environment()


def effective_page_size(page_size: int | None) -> int:
    settings = ApiSettings.from_environment()
    size = page_size or settings.default_page_size
    if size > settings.maximum_page_size:
        raise HTTPException(
            status_code=400,
            detail=f"page_size cannot exceed {settings.maximum_page_size}.",
        )
    return size


@router.get("/health")
def health(connection: pyodbc.Connection = Depends(get_connection)):
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        return {"status": "ok", "database": "connected"}
    finally:
        cursor.close()


@router.get("/quarters")
def quarters(connection: pyodbc.Connection = Depends(get_connection)):
    return api_safe(get_available_quarters(connection, pipeline_settings()))


@router.get("/dashboard/summary")
def dashboard_summary(
    quarters: str | None = Query(None),
    risk_levels: str | None = Query(None),
    connection: pyodbc.Connection = Depends(get_connection),
):
    selected_quarters = parse_quarters(quarters)
    selected_risks = parse_risk_levels(risk_levels)
    result = get_dashboard_summary(
        connection, pipeline_settings(), selected_quarters, selected_risks
    )
    return api_safe({
        "selected_quarters": selected_quarters,
        "selected_risk_levels": selected_risks,
        "all_quarters_selected": not bool(selected_quarters),
        "all_risk_levels_selected": not bool(selected_risks),
        "summary": result,
    })


@router.get("/dashboard/distributions")
def dashboard_distributions(
    quarters: str | None = Query(None),
    risk_levels: str | None = Query(None),
    connection: pyodbc.Connection = Depends(get_connection),
):
    selected_quarters = parse_quarters(quarters)
    selected_risks = parse_risk_levels(risk_levels)
    return api_safe({
        "selected_quarters": selected_quarters,
        "selected_risk_levels": selected_risks,
        "all_quarters_selected": not bool(selected_quarters),
        "all_risk_levels_selected": not bool(selected_risks),
        "distributions": get_distributions(
            connection, pipeline_settings(), selected_quarters, selected_risks
        ),
    })


@router.get("/cases")
def cases(
    quarters: str | None = Query(None),
    risk_levels: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1),
    benchmark_method: str | None = None,
    model_agreement: str | None = None,
    hs: str | None = None,
    trader: str | None = None,
    search: str | None = Query(None, max_length=100),
    minimum_score: float = Query(0, ge=0, le=100),
    connection: pyodbc.Connection = Depends(get_connection),
):
    selected_quarters = parse_quarters(quarters)
    selected_risks = parse_risk_levels(risk_levels)
    return api_safe(get_case_page(
        connection=connection,
        pipeline=pipeline_settings(),
        quarters=selected_quarters,
        risk_levels=selected_risks,
        page=page,
        page_size=effective_page_size(page_size),
        benchmark_method=benchmark_method,
        model_agreement=model_agreement,
        hs=hs,
        trader=trader,
        search=search,
        minimum_score=minimum_score,
    ))


@router.get("/cases/{case_result_id}")
def case_detail(
    case_result_id: int,
    connection: pyodbc.Connection = Depends(get_connection),
):
    result = get_case_detail(connection, pipeline_settings(), case_result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Case was not found.")
    return api_safe(result)


@router.get("/top-hs")
def top_hs(
    quarters: str | None = Query(None),
    risk_levels: str | None = Query(None),
    limit: int = Query(15, ge=1, le=100),
    connection: pyodbc.Connection = Depends(get_connection),
):
    selected_quarters = parse_quarters(quarters)
    selected_risks = parse_risk_levels(risk_levels)
    return api_safe({
        "selected_quarters": selected_quarters,
        "selected_risk_levels": selected_risks,
        "rows": get_top_hs(
            connection, pipeline_settings(), selected_quarters,
            selected_risks, limit
        ),
    })


@router.get("/top-traders")
def top_traders(
    quarters: str | None = Query(None),
    risk_levels: str | None = Query(None),
    limit: int = Query(15, ge=1, le=100),
    connection: pyodbc.Connection = Depends(get_connection),
):
    selected_quarters = parse_quarters(quarters)
    selected_risks = parse_risk_levels(risk_levels)
    return api_safe({
        "selected_quarters": selected_quarters,
        "selected_risk_levels": selected_risks,
        "rows": get_top_traders(
            connection, pipeline_settings(), selected_quarters,
            selected_risks, limit
        ),
    })


@router.get("/traders/{trader}/history")
def trader_history(
    trader: str,
    quarters: str | None = Query(None),
    risk_levels: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1),
    connection: pyodbc.Connection = Depends(get_connection),
):
    selected_quarters = parse_quarters(quarters)
    selected_risks = parse_risk_levels(risk_levels)
    result = get_trader_history(
        connection=connection,
        pipeline=pipeline_settings(),
        trader=trader,
        quarters=selected_quarters,
        risk_levels=selected_risks,
        page=page,
        page_size=effective_page_size(page_size),
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Trader history was not found for the selected filters.",
        )
    return api_safe(result)
