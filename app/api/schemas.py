from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
import re

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from app.services.api_settings import ApiSettings


QUARTER_PATTERN = re.compile(r"^\d{4}-Q[1-4]$")
ALLOWED_RISK_LEVELS = ("High Risk", "Medium Risk", "Low Risk")


def api_safe(value: Any) -> Any:
    """Convert database-returned values into JSON-safe values."""
    return jsonable_encoder(
        value,
        custom_encoder={
            Decimal: float,
            datetime: lambda item: item.isoformat(),
            date: lambda item: item.isoformat(),
        },
    )


def _unique_csv_values(raw_value: str | None) -> list[str]:
    if raw_value is None or not raw_value.strip():
        return []
    values: list[str] = []
    seen: set[str] = set()
    for item in raw_value.split(","):
        value = item.strip()
        if value and value not in seen:
            seen.add(value)
            values.append(value)
    return values


def parse_quarters(raw_quarters: str | None) -> list[str]:
    """Parse optional comma-separated quarters. Empty means all quarters."""
    values = [item.upper() for item in _unique_csv_values(raw_quarters)]
    for quarter in values:
        if not QUARTER_PATTERN.fullmatch(quarter):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid quarter '{quarter}'. Use YYYY-QN, "
                    "for example 2024-Q1."
                ),
            )

    maximum = ApiSettings.from_environment().maximum_selected_quarters
    if len(values) > maximum:
        raise HTTPException(
            status_code=422,
            detail=f"A maximum of {maximum} quarters may be selected.",
        )
    return values


def parse_risk_levels(raw_risk_levels: str | None) -> list[str]:
    """
    Parse optional comma-separated risk levels.

    Empty means all risk levels. Values are matched case-insensitively and
    returned using the canonical labels stored in SQL Server.
    """
    lookup = {value.casefold(): value for value in ALLOWED_RISK_LEVELS}
    parsed: list[str] = []
    for value in _unique_csv_values(raw_risk_levels):
        canonical = lookup.get(value.casefold())
        if canonical is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid risk level '{value}'. Allowed values are: "
                    + ", ".join(ALLOWED_RISK_LEVELS)
                ),
            )
        if canonical not in parsed:
            parsed.append(canonical)
    return parsed
