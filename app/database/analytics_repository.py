from __future__ import annotations

import pandas as pd
import pyodbc

from config.settings import (
    PipelineSettings
)


# ============================================================
# GET AVAILABLE ANALYTICAL QUARTERS
# ============================================================

def get_available_quarters(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> list[str]:
    """
    Return all available analytical quarters.

    Example:
        [
            "2023-Q1",
            "2023-Q2",
            "2023-Q3"
        ]
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            SELECT DISTINCT
                YearQuarter

            FROM {
                settings.prepared_full_name
            }

            WHERE
                YearQuarter IS NOT NULL

            ORDER BY
                YearQuarter;
            """
        )

        quarters = [
            row.YearQuarter
            for row in cursor.fetchall()
        ]

        return quarters

    finally:

        cursor.close()


# ============================================================
# COUNT QUARTER RECORDS
# ============================================================

def get_quarter_record_count(
    connection: pyodbc.Connection,
    year_quarter: str,
    settings: PipelineSettings | None = None
) -> int:
    """
    Count analytically valid records for one quarter.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            SELECT
                COUNT_BIG(*)

            FROM {
                settings.prepared_full_name
            }

            WHERE
                YearQuarter = ?

                AND
                IsAnalyticallyValid = 1;
            """,
            year_quarter
        )

        return int(
            cursor.fetchone()[0]
        )

    finally:

        cursor.close()


# ============================================================
# LOAD ONE QUARTER WITH ORIGINAL BENCHMARKS
# ============================================================

def load_quarter_with_benchmarks(
    connection: pyodbc.Connection,
    year_quarter: str,
    settings: PipelineSettings | None = None,
    eligible_benchmarks_only: bool = False
) -> pd.DataFrame:
    """
    Load one complete quarter of analytically valid declarations
    together with their original benchmark statistics.

    Loading by complete quarter ensures that HS-quarter peer
    populations remain together when Python performs clustering.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    eligibility_filter = ""

    if eligible_benchmarks_only:

        eligibility_filter = """
        AND benchmark.IsBenchmarkEligible = 1
        """

    sql = f"""
    SELECT
        -- ===================================================
        -- INTERNAL ID
        -- ===================================================

        prepared.PreparedDeclarationId,


        -- ===================================================
        -- PERIOD
        -- ===================================================

        prepared.[Year],

        prepared.[Period],

        prepared.[Day],

        prepared.RegistrationDate,

        prepared.YearMonth,

        prepared.YearQuarter,


        -- ===================================================
        -- DECLARATION DETAILS
        -- ===================================================

        prepared.Office,

        prepared.DecType,

        prepared.FormNumber,


        -- ===================================================
        -- TRADER DETAILS
        -- ===================================================

        prepared.Traders,

        prepared.Lib_Traders,


        -- ===================================================
        -- TRANSPORT AND PROCEDURES
        -- ===================================================

        prepared.Transport,

        prepared.EPC,

        prepared.APC,


        -- ===================================================
        -- TRADE CLASSIFICATION
        -- ===================================================

        prepared.TRS_Trade,

        prepared.TRS_Flow,

        prepared.Flows,

        prepared.SACU,

        prepared.SADC,


        -- ===================================================
        -- PRODUCT DETAILS
        -- ===================================================

        prepared.HS_Chapter,

        prepared.HS_Heading,

        prepared.HS,

        prepared.Lib_HS8,


        -- ===================================================
        -- PARTNER
        -- ===================================================

        prepared.Partner,

        prepared.Lib_Partner,


        -- ===================================================
        -- VALUES
        -- ===================================================

        prepared.FOBValue,

        prepared.CIFValue,

        prepared.SZLValue,

        prepared.USDValue,


        -- ===================================================
        -- TAXES
        -- ===================================================

        prepared.VAT,

        prepared.CDGVal,

        prepared.ATLVal,

        prepared.MVLVal,

        prepared.EDAVal,


        -- ===================================================
        -- SOURCE QUANTITY
        -- ===================================================

        prepared.NetWeight,

        prepared.QTY,

        prepared.SU,


        -- ===================================================
        -- ANALYTICAL QUANTITY
        -- ===================================================

        prepared.SelectedQuantity,

        prepared.SelectedUnit,

        prepared.UnitValue,

        prepared.HSQuarter,

        prepared.PeerKey,


        -- ===================================================
        -- ORIGINAL BENCHMARK
        -- ===================================================

        benchmark.PeerCount,

        benchmark.OriginalQ1,

        benchmark.OriginalMedian,

        benchmark.OriginalQ3,

        benchmark.MinimumUnitValue,

        benchmark.MaximumUnitValue,

        benchmark.AverageUnitValue,

        benchmark.UnitValueStdDev,

        benchmark.InterquartileRange,

        benchmark.IsBenchmarkEligible,

        benchmark.IneligibilityReason

    FROM {
        settings.prepared_full_name
    } AS prepared

    INNER JOIN {
        settings.benchmark_full_name
    } AS benchmark

        ON
            benchmark.HS =
                prepared.HS

        AND
            benchmark.YearQuarter =
                prepared.YearQuarter

        AND
            benchmark.SelectedUnit =
                prepared.SelectedUnit

    WHERE
        prepared.YearQuarter = ?

        AND
        prepared.IsAnalyticallyValid = 1

        {eligibility_filter}

    ORDER BY
        prepared.HS,
        prepared.SelectedUnit,
        prepared.PreparedDeclarationId;
    """

    dataframe = pd.read_sql_query(
        sql,
        connection,
        params=[
            year_quarter
        ]
    )

    return dataframe