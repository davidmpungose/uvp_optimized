from __future__ import annotations

import pandas as pd
import pyodbc

from app.database.analytics_repository import (
    get_available_quarters,
    get_quarter_record_count,
    load_quarter_with_benchmarks
)

from config.settings import (
    PipelineSettings
)


# ============================================================
# GET AVAILABLE QUARTERS
# ============================================================

def list_analytical_quarters(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> list[str]:
    """
    Return quarters available for downstream Python analytics.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    return get_available_quarters(
        connection=connection,
        settings=settings
    )


# ============================================================
# LOAD QUARTER
# ============================================================

def load_analytical_quarter(
    connection: pyodbc.Connection,
    year_quarter: str,
    settings: PipelineSettings | None = None
) -> pd.DataFrame:
    """
    Load one quarter prepared for clustering.

    Only benchmark-eligible groups are returned.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    quarter_rows = (
        get_quarter_record_count(
            connection=connection,
            year_quarter=year_quarter,
            settings=settings
        )
    )

    print(
        "Quarter:",
        year_quarter
    )

    print(
        "Valid prepared records:",
        f"{quarter_rows:,}"
    )

    dataframe = (
        load_quarter_with_benchmarks(
            connection=connection,
            year_quarter=year_quarter,
            settings=settings,
            eligible_benchmarks_only=True
        )
    )

    print(
        "Benchmark-eligible rows loaded:",
        f"{len(dataframe):,}"
    )

    return dataframe