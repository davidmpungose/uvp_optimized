from __future__ import annotations

from typing import Any

import pyodbc

from config.settings import PipelineSettings


def _row_to_dict(cursor: pyodbc.Cursor, row: pyodbc.Row) -> dict[str, Any]:
    columns = [description[0] for description in cursor.description]
    return dict(zip(columns, row))


def _fetch_all(cursor: pyodbc.Cursor) -> list[dict[str, Any]]:
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _view(pipeline: PipelineSettings, name: str) -> str:
    return f"[{pipeline.analytics_schema}].[{name}]"


def _list_filter(values: list[str], column: str) -> tuple[str, list[Any]]:
    if not values:
        return "1 = 1", []
    placeholders = ", ".join("?" for _ in values)
    return f"{column} IN ({placeholders})", list(values)


def _global_filters(
    quarters: list[str],
    risk_levels: list[str],
    quarter_column: str = "YearQuarter",
    risk_column: str = "CaseRiskLevel",
) -> tuple[str, list[Any]]:
    quarter_sql, quarter_parameters = _list_filter(quarters, quarter_column)
    risk_sql, risk_parameters = _list_filter(risk_levels, risk_column)
    return (
        f"({quarter_sql}) AND ({risk_sql})",
        quarter_parameters + risk_parameters,
    )


def _case_where(
    quarters: list[str],
    risk_levels: list[str],
    benchmark_method: str | None = None,
    model_agreement: str | None = None,
    hs: str | None = None,
    trader: str | None = None,
    search: str | None = None,
    minimum_score: float = 0,
) -> tuple[str, list[Any]]:
    global_sql, parameters = _global_filters(quarters, risk_levels)
    filters = [global_sql, "IsPotentialCase = 1", "CaseRiskScore >= ?"]
    parameters.append(minimum_score)

    optional_filters = [
        (benchmark_method, "FinalBenchmarkMethod = ?"),
        (model_agreement, "ModelAgreement = ?"),
        (hs, "HS = ?"),
        (trader, "Traders = ?"),
    ]
    for value, sql in optional_filters:
        if value:
            filters.append(sql)
            parameters.append(value)

    if search:
        filters.append(
            "(Traders LIKE ? OR Lib_Traders LIKE ? OR HS LIKE ? "
            "OR Lib_HS8 LIKE ? OR FormNumber LIKE ?)"
        )
        pattern = f"%{search}%"
        parameters.extend([pattern] * 5)

    return " AND ".join(filters), parameters


def get_available_quarters(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings,
) -> list[dict[str, Any]]:
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""
            SELECT
                YearQuarter, PotentialCases, HighRiskCases,
                MediumRiskCases, LowRiskCases, UniqueTraders, UniqueHS,
                TotalPotentialValueGap, AverageRiskScore, MaximumRiskScore
            FROM {_view(pipeline, 'vw_QuarterRiskSummary')}
            ORDER BY YearQuarter DESC;
            """
        )
        return _fetch_all(cursor)
    finally:
        cursor.close()


def get_dashboard_summary(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings,
    quarters: list[str],
    risk_levels: list[str],
) -> dict[str, Any]:
    where_sql, parameters = _global_filters(quarters, risk_levels)
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""
            SELECT
                COUNT_BIG(*) AS PotentialCases,
                SUM(CASE WHEN CaseRiskLevel = 'High Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS HighRiskCases,
                SUM(CASE WHEN CaseRiskLevel = 'Medium Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS MediumRiskCases,
                SUM(CASE WHEN CaseRiskLevel = 'Low Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS LowRiskCases,
                COUNT(DISTINCT Traders) AS UniqueTraders,
                COUNT(DISTINCT HS) AS UniqueHS,
                COALESCE(SUM(PotentialValueGap),0) AS TotalPotentialValueGap,
                COALESCE(AVG(CaseRiskScore),0) AS AverageRiskScore,
                COALESCE(MAX(CaseRiskScore),0) AS MaximumRiskScore,
                MIN(YearQuarter) AS MinimumQuarter,
                MAX(YearQuarter) AS MaximumQuarter,
                COUNT(DISTINCT YearQuarter) AS QuarterCount
            FROM {_view(pipeline, 'vw_CaseDashboard')}
            WHERE {where_sql}
              AND IsPotentialCase = 1;
            """,
            *parameters,
        )
        result = _row_to_dict(cursor, cursor.fetchone())

        # Cluster quality is a property of the selected quarters, not of a
        # case risk level. It therefore respects quarters but not risk levels.
        quarter_sql, quarter_parameters = _list_filter(quarters, "YearQuarter")
        cursor.execute(
            f"""
            SELECT
                COALESCE(SUM(AnalyticalRows),0) AS AnalyticalRows,
                COALESCE(SUM(ClusteredRows),0) AS ClusteredRows,
                COALESCE(SUM(ClusteredGroups),0) AS ClusteredGroups,
                COALESCE(AVG(AverageSilhouetteScore),0) AS AverageSilhouetteScore,
                COALESCE(MIN(MinimumSilhouetteScore),0) AS MinimumSilhouetteScore,
                COALESCE(SUM(UnclusteredRows),0) AS UnclusteredRows
            FROM {_view(pipeline, 'vw_ClusterQualitySummary')}
            WHERE {quarter_sql};
            """,
            *quarter_parameters,
        )
        result.update(_row_to_dict(cursor, cursor.fetchone()))
        return result
    finally:
        cursor.close()


def get_distributions(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings,
    quarters: list[str],
    risk_levels: list[str],
) -> dict[str, list[dict[str, Any]]]:
    allowed_columns = {
        "risk_levels": "CaseRiskLevel",
        "benchmark_methods": "FinalBenchmarkMethod",
        "model_agreement": "ModelAgreement",
        "cluster_tiers": "ClusterPriceTier",
    }
    where_sql, parameters = _global_filters(quarters, risk_levels)
    cursor = connection.cursor()
    try:
        result = {}
        for key, column in allowed_columns.items():
            cursor.execute(
                f"""
                SELECT
                    COALESCE(NULLIF([{column}], ''), 'Unknown') AS Label,
                    COUNT_BIG(*) AS Value,
                    COALESCE(SUM(PotentialValueGap),0) AS PotentialValueGap
                FROM {_view(pipeline, 'vw_CaseDashboard')}
                WHERE {where_sql}
                  AND IsPotentialCase = 1
                GROUP BY COALESCE(NULLIF([{column}], ''), 'Unknown')
                ORDER BY Value DESC;
                """,
                *parameters,
            )
            result[key] = _fetch_all(cursor)
        return result
    finally:
        cursor.close()


def get_case_page(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings,
    quarters: list[str],
    risk_levels: list[str],
    page: int,
    page_size: int,
    benchmark_method: str | None = None,
    model_agreement: str | None = None,
    hs: str | None = None,
    trader: str | None = None,
    search: str | None = None,
    minimum_score: float = 0,
) -> dict[str, Any]:
    where_sql, parameters = _case_where(
        quarters=quarters,
        risk_levels=risk_levels,
        benchmark_method=benchmark_method,
        model_agreement=model_agreement,
        hs=hs,
        trader=trader,
        search=search,
        minimum_score=minimum_score,
    )
    offset = (page - 1) * page_size
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT COUNT_BIG(*) FROM {_view(pipeline, 'vw_CaseDashboard')} WHERE {where_sql};",
            *parameters,
        )
        total_rows = int(cursor.fetchone()[0])
        cursor.execute(
            f"""
            SELECT
                CaseResultId, PreparedDeclarationId, YearQuarter,
                RegistrationDate, FormNumber, Traders, Lib_Traders,
                HS, Lib_HS8, SelectedQuantity, SelectedUnit, FOBValue,
                UnitValue, OriginalQ1, ClusterQ1, FinalBenchmarkMethod,
                FinalBenchmarkQ1, FinalDeviationPercent,
                PotentialValueGap, ModelAgreement, CaseRiskScore,
                CaseRiskLevel, CaseReason
            FROM {_view(pipeline, 'vw_CaseDashboard')}
            WHERE {where_sql}
            ORDER BY CaseRiskScore DESC, PotentialValueGap DESC, CaseResultId
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
            """,
            *(parameters + [offset, page_size]),
        )
        return {
            "selected_quarters": quarters,
            "selected_risk_levels": risk_levels,
            "all_quarters_selected": not bool(quarters),
            "all_risk_levels_selected": not bool(risk_levels),
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": max(1, (total_rows + page_size - 1) // page_size),
            "rows": _fetch_all(cursor),
        }
    finally:
        cursor.close()


def get_case_detail(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings,
    case_result_id: int,
) -> dict[str, Any] | None:
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT * FROM {_view(pipeline, 'vw_CaseDashboard')} WHERE CaseResultId = ?;",
            case_result_id,
        )
        row = cursor.fetchone()
        return None if row is None else _row_to_dict(cursor, row)
    finally:
        cursor.close()


def get_top_hs(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings,
    quarters: list[str],
    risk_levels: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    where_sql, parameters = _global_filters(quarters, risk_levels)
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""
            SELECT TOP (?)
                HS, MAX(Lib_HS8) AS Lib_HS8,
                COUNT_BIG(*) AS PotentialCases,
                COUNT(DISTINCT Traders) AS UniqueTraders,
                SUM(FOBValue) AS TotalFOBValue,
                SUM(PotentialValueGap) AS TotalPotentialValueGap,
                AVG(CaseRiskScore) AS AverageRiskScore,
                MAX(CaseRiskScore) AS MaximumRiskScore,
                SUM(CASE WHEN CaseRiskLevel = 'High Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS HighRiskCases
            FROM {_view(pipeline, 'vw_CaseDashboard')}
            WHERE {where_sql} AND IsPotentialCase = 1
            GROUP BY HS
            ORDER BY TotalPotentialValueGap DESC, PotentialCases DESC;
            """,
            limit,
            *parameters,
        )
        return _fetch_all(cursor)
    finally:
        cursor.close()


def get_top_traders(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings,
    quarters: list[str],
    risk_levels: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    where_sql, parameters = _global_filters(quarters, risk_levels)
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""
            SELECT TOP (?)
                Traders, MAX(Lib_Traders) AS Lib_Traders,
                COUNT_BIG(*) AS PotentialCases,
                COUNT(DISTINCT HS) AS UniqueHS,
                SUM(FOBValue) AS TotalFOBValue,
                SUM(PotentialValueGap) AS TotalPotentialValueGap,
                AVG(CaseRiskScore) AS AverageRiskScore,
                MAX(CaseRiskScore) AS MaximumRiskScore,
                SUM(CASE WHEN CaseRiskLevel = 'High Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS HighRiskCases
            FROM {_view(pipeline, 'vw_CaseDashboard')}
            WHERE {where_sql} AND IsPotentialCase = 1
            GROUP BY Traders
            ORDER BY TotalPotentialValueGap DESC, PotentialCases DESC;
            """,
            limit,
            *parameters,
        )
        return _fetch_all(cursor)
    finally:
        cursor.close()


def get_trader_history(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings,
    trader: str,
    quarters: list[str],
    risk_levels: list[str],
    page: int,
    page_size: int,
) -> dict[str, Any] | None:
    global_sql, global_parameters = _global_filters(quarters, risk_levels)
    selected_where = f"Traders = ? AND ({global_sql})"
    selected_values: list[Any] = [trader] + global_parameters
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""
            SELECT
                COUNT_BIG(*) AS PotentialCases,
                COUNT(DISTINCT HS) AS UniqueHS,
                COALESCE(SUM(PotentialValueGap),0) AS TotalPotentialValueGap,
                COALESCE(AVG(CaseRiskScore),0) AS AverageRiskScore,
                COALESCE(MAX(CaseRiskScore),0) AS MaximumRiskScore,
                SUM(CASE WHEN CaseRiskLevel = 'High Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS HighRiskCases,
                MIN(YearQuarter) AS MinimumQuarter,
                MAX(YearQuarter) AS MaximumQuarter
            FROM {_view(pipeline, 'vw_CaseDashboard')}
            WHERE {selected_where} AND IsPotentialCase = 1;
            """,
            *selected_values,
        )
        selected_summary = _row_to_dict(cursor, cursor.fetchone())
        if int(selected_summary["PotentialCases"] or 0) == 0:
            return None

        # Lifetime remains deliberately unfiltered by period and risk level.
        cursor.execute(
            f"""
            SELECT
                COUNT_BIG(*) AS PotentialCases,
                COUNT(DISTINCT HS) AS UniqueHS,
                COALESCE(SUM(PotentialValueGap),0) AS TotalPotentialValueGap,
                COALESCE(AVG(CaseRiskScore),0) AS AverageRiskScore,
                COALESCE(MAX(CaseRiskScore),0) AS MaximumRiskScore,
                SUM(CASE WHEN CaseRiskLevel = 'High Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS HighRiskCases,
                MIN(YearQuarter) AS MinimumQuarter,
                MAX(YearQuarter) AS MaximumQuarter
            FROM {_view(pipeline, 'vw_CaseDashboard')}
            WHERE Traders = ? AND IsPotentialCase = 1;
            """,
            trader,
        )
        lifetime_summary = _row_to_dict(cursor, cursor.fetchone())

        total_rows = int(selected_summary["PotentialCases"] or 0)
        offset = (page - 1) * page_size
        cursor.execute(
            f"""
            SELECT
                PreparedDeclarationId, Traders, Lib_Traders, YearQuarter,
                RegistrationDate, FormNumber, HS, Lib_HS8, FOBValue,
                UnitValue, FinalBenchmarkMethod, FinalBenchmarkQ1,
                FinalDeviationPercent, PotentialValueGap, ModelAgreement,
                CaseRiskScore, CaseRiskLevel, CaseReason
            FROM {_view(pipeline, 'vw_TraderCaseHistory')}
            WHERE {selected_where}
            ORDER BY RegistrationDate DESC, CaseRiskScore DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
            """,
            *(selected_values + [offset, page_size]),
        )
        return {
            "trader": trader,
            "selected_quarters": quarters,
            "selected_risk_levels": risk_levels,
            "all_quarters_selected": not bool(quarters),
            "all_risk_levels_selected": not bool(risk_levels),
            "selected_period_summary": selected_summary,
            "lifetime_summary": lifetime_summary,
            "history": {
                "page": page,
                "page_size": page_size,
                "total_rows": total_rows,
                "total_pages": max(1, (total_rows + page_size - 1) // page_size),
                "rows": _fetch_all(cursor),
            },
        }
    finally:
        cursor.close()
