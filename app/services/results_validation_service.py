from __future__ import annotations

import pyodbc

from config.settings import PipelineSettings
from app.database.results_schema_sql import ResultStorageSettings


def validate_stored_results(
    connection: pyodbc.Connection,
    year_quarter: str,
    pipeline: PipelineSettings | None = None,
    results: ResultStorageSettings | None = None,
) -> dict[str, object]:
    pipeline = pipeline or PipelineSettings.from_environment()
    results = results or ResultStorageSettings.from_environment()
    cluster_table = results.quoted_name(pipeline, results.cluster_table)
    case_table = results.quoted_name(pipeline, results.case_table)

    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""
            SELECT
                COUNT_BIG(*) AS ClusterRows,
                SUM(CASE WHEN ClusterApplied = 1 THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS ClusteredRows,
                COUNT(DISTINCT CASE WHEN ClusterApplied = 1 THEN PeerKey END) AS ClusteredGroups,
                COUNT_BIG(DISTINCT PreparedDeclarationId) AS DistinctPreparedIds
            FROM {cluster_table}
            WHERE YearQuarter = ?;
            """,
            year_quarter,
        )
        c = cursor.fetchone()

        cursor.execute(
            f"""
            SELECT
                COUNT_BIG(*) AS CaseRows,
                SUM(CASE WHEN CaseRiskLevel = 'High Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS HighRisk,
                SUM(CASE WHEN CaseRiskLevel = 'Medium Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS MediumRisk,
                SUM(CASE WHEN CaseRiskLevel = 'Low Risk' THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS LowRisk,
                COALESCE(SUM(PotentialValueGap),0) AS PotentialValueGap,
                COUNT_BIG(DISTINCT PreparedDeclarationId) AS DistinctPreparedIds,
                SUM(CASE WHEN CaseRiskScore < 0 OR CaseRiskScore > 100 THEN CONVERT(bigint,1) ELSE CONVERT(bigint,0) END) AS InvalidScores
            FROM {case_table}
            WHERE YearQuarter = ?;
            """,
            year_quarter,
        )
        r = cursor.fetchone()

        return {
            "year_quarter": year_quarter,
            "cluster_rows": int(c.ClusterRows or 0),
            "clustered_rows": int(c.ClusteredRows or 0),
            "clustered_groups": int(c.ClusteredGroups or 0),
            "cluster_duplicate_ids": int((c.ClusterRows or 0) - (c.DistinctPreparedIds or 0)),
            "case_rows": int(r.CaseRows or 0),
            "high_risk": int(r.HighRisk or 0),
            "medium_risk": int(r.MediumRisk or 0),
            "low_risk": int(r.LowRisk or 0),
            "potential_value_gap": float(r.PotentialValueGap or 0),
            "case_duplicate_ids": int((r.CaseRows or 0) - (r.DistinctPreparedIds or 0)),
            "invalid_scores": int(r.InvalidScores or 0),
        }
    finally:
        cursor.close()


def print_results_validation(summary: dict[str, object]) -> None:
    print("=" * 70)
    print("PERMANENT RESULT STORAGE VALIDATION")
    print("=" * 70)
    print("Quarter:", summary["year_quarter"])
    print("Cluster rows:", f"{summary['cluster_rows']:,}")
    print("Clustered rows:", f"{summary['clustered_rows']:,}")
    print("Clustered groups:", f"{summary['clustered_groups']:,}")
    print("Cluster duplicate IDs:", f"{summary['cluster_duplicate_ids']:,}")
    print("Case rows:", f"{summary['case_rows']:,}")
    print("High risk:", f"{summary['high_risk']:,}")
    print("Medium risk:", f"{summary['medium_risk']:,}")
    print("Low risk:", f"{summary['low_risk']:,}")
    print("Potential value gap:", f"E{summary['potential_value_gap']:,.2f}")
    print("Case duplicate IDs:", f"{summary['case_duplicate_ids']:,}")
    print("Scores outside 0-100:", f"{summary['invalid_scores']:,}")
    print("=" * 70)
