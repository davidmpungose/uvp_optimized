from __future__ import annotations

from config.settings import (
    PipelineSettings
)

from app.database.results_schema_sql import (
    ResultStorageSettings
)


# ============================================================
# CASE DASHBOARD VIEW
# ============================================================

def build_case_dashboard_view_sql(
    pipeline: PipelineSettings,
    results: ResultStorageSettings
) -> str:
    """
    Create the detailed operational case-dashboard view.
    """

    cases_table = (
        results.quoted_name(
            pipeline,
            results.case_table
        )
    )

    analytics_schema = (
        f"[{pipeline.analytics_schema}]"
    )

    return f"""
CREATE OR ALTER VIEW
    {analytics_schema}.[vw_CaseDashboard]
AS

SELECT
    case_result.CaseResultId,

    case_result.PreparedDeclarationId,

    case_result.YearQuarter,

    case_result.RegistrationDate,

    case_result.FormNumber,

    case_result.Traders,

    case_result.Lib_Traders,

    case_result.HS,

    case_result.Lib_HS8,

    case_result.SelectedQuantity,

    case_result.SelectedUnit,

    case_result.FOBValue,

    case_result.UnitValue,

    case_result.PeerCount,

    case_result.OriginalQ1,

    case_result.OriginalMedian,

    case_result.OriginalQ3,

    case_result.ClusterApplied,

    case_result.ClusterId,

    case_result.ClusterPriceTier,

    case_result.ClusterPeerCount,

    case_result.ClusterQ1,

    case_result.ClusterMedian,

    case_result.ClusterQ3,

    case_result.OriginalFlag,

    case_result.ClusterFlag,

    case_result.FinalBenchmarkMethod,

    case_result.FinalBenchmarkQ1,

    case_result.FinalDeviationPercent,

    case_result.PotentialValueGap,

    case_result.ModelAgreement,

    case_result.CaseRiskScore,

    case_result.CaseRiskLevel,

    case_result.IsPotentialCase,

    case_result.CaseReason,

    case_result.ModelVersion,

    case_result.LoadedAt

FROM {cases_table}
    AS case_result;
"""


# ============================================================
# QUARTER RISK SUMMARY VIEW
# ============================================================

def build_quarter_risk_summary_view_sql(
    pipeline: PipelineSettings,
    results: ResultStorageSettings
) -> str:
    """
    Create one management-summary record per quarter.
    """

    cases_table = (
        results.quoted_name(
            pipeline,
            results.case_table
        )
    )

    analytics_schema = (
        f"[{pipeline.analytics_schema}]"
    )

    return f"""
CREATE OR ALTER VIEW
    {analytics_schema}.[vw_QuarterRiskSummary]
AS

SELECT
    YearQuarter,

    COUNT_BIG(*)
        AS PotentialCases,

    SUM(
        CASE
            WHEN CaseRiskLevel = 'High Risk'
            THEN CONVERT(bigint, 1)
            ELSE CONVERT(bigint, 0)
        END
    ) AS HighRiskCases,

    SUM(
        CASE
            WHEN CaseRiskLevel = 'Medium Risk'
            THEN CONVERT(bigint, 1)
            ELSE CONVERT(bigint, 0)
        END
    ) AS MediumRiskCases,

    SUM(
        CASE
            WHEN CaseRiskLevel = 'Low Risk'
            THEN CONVERT(bigint, 1)
            ELSE CONVERT(bigint, 0)
        END
    ) AS LowRiskCases,

    COUNT(
        DISTINCT Traders
    ) AS UniqueTraders,

    COUNT(
        DISTINCT HS
    ) AS UniqueHS,

    SUM(
        PotentialValueGap
    ) AS TotalPotentialValueGap,

    AVG(
        CaseRiskScore
    ) AS AverageRiskScore,

    MAX(
        CaseRiskScore
    ) AS MaximumRiskScore

FROM {cases_table}

WHERE IsPotentialCase = 1

GROUP BY
    YearQuarter;
"""


# ============================================================
# HS RISK SUMMARY VIEW
# ============================================================

def build_hs_risk_summary_view_sql(
    pipeline: PipelineSettings,
    results: ResultStorageSettings
) -> str:
    """
    Create quarterly risk summaries by HS code.
    """

    cases_table = (
        results.quoted_name(
            pipeline,
            results.case_table
        )
    )

    analytics_schema = (
        f"[{pipeline.analytics_schema}]"
    )

    return f"""
CREATE OR ALTER VIEW
    {analytics_schema}.[vw_HSRiskSummary]
AS

SELECT
    YearQuarter,

    HS,

    MAX(
        Lib_HS8
    ) AS Lib_HS8,

    COUNT_BIG(*)
        AS PotentialCases,

    COUNT(
        DISTINCT Traders
    ) AS UniqueTraders,

    SUM(
        FOBValue
    ) AS TotalFOBValue,

    SUM(
        PotentialValueGap
    ) AS TotalPotentialValueGap,

    AVG(
        CaseRiskScore
    ) AS AverageRiskScore,

    MAX(
        CaseRiskScore
    ) AS MaximumRiskScore,

    SUM(
        CASE
            WHEN CaseRiskLevel = 'High Risk'
            THEN CONVERT(bigint, 1)
            ELSE CONVERT(bigint, 0)
        END
    ) AS HighRiskCases

FROM {cases_table}

WHERE IsPotentialCase = 1

GROUP BY
    YearQuarter,
    HS;
"""


# ============================================================
# TRADER RISK SUMMARY VIEW
# ============================================================

def build_trader_risk_summary_view_sql(
    pipeline: PipelineSettings,
    results: ResultStorageSettings
) -> str:
    """
    Create quarterly risk summaries by trader.
    """

    cases_table = (
        results.quoted_name(
            pipeline,
            results.case_table
        )
    )

    analytics_schema = (
        f"[{pipeline.analytics_schema}]"
    )

    return f"""
CREATE OR ALTER VIEW
    {analytics_schema}.[vw_TraderRiskSummary]
AS

SELECT
    YearQuarter,

    Traders,

    MAX(
        Lib_Traders
    ) AS Lib_Traders,

    COUNT_BIG(*)
        AS PotentialCases,

    COUNT(
        DISTINCT HS
    ) AS UniqueHS,

    SUM(
        FOBValue
    ) AS TotalFOBValue,

    SUM(
        PotentialValueGap
    ) AS TotalPotentialValueGap,

    AVG(
        CaseRiskScore
    ) AS AverageRiskScore,

    MAX(
        CaseRiskScore
    ) AS MaximumRiskScore,

    SUM(
        CASE
            WHEN CaseRiskLevel = 'High Risk'
            THEN CONVERT(bigint, 1)
            ELSE CONVERT(bigint, 0)
        END
    ) AS HighRiskCases

FROM {cases_table}

WHERE IsPotentialCase = 1

GROUP BY
    YearQuarter,
    Traders;
"""


# ============================================================
# TRADER CASE HISTORY VIEW
# ============================================================

def build_trader_case_history_view_sql(
    pipeline: PipelineSettings,
    results: ResultStorageSettings
) -> str:
    """
    Create a declaration-level trader-history view.

    Lifetime measures are calculated across all loaded quarters.
    """

    cases_table = (
        results.quoted_name(
            pipeline,
            results.case_table
        )
    )

    analytics_schema = (
        f"[{pipeline.analytics_schema}]"
    )

    return f"""
CREATE OR ALTER VIEW
    {analytics_schema}.[vw_TraderCaseHistory]
AS

SELECT
    case_result.PreparedDeclarationId,

    case_result.Traders,

    case_result.Lib_Traders,

    case_result.YearQuarter,

    case_result.RegistrationDate,

    case_result.FormNumber,

    case_result.HS,

    case_result.Lib_HS8,

    case_result.FOBValue,

    case_result.UnitValue,

    case_result.FinalBenchmarkMethod,

    case_result.FinalBenchmarkQ1,

    case_result.FinalDeviationPercent,

    case_result.PotentialValueGap,

    case_result.ModelAgreement,

    case_result.CaseRiskScore,

    case_result.CaseRiskLevel,

    case_result.CaseReason,

    COUNT_BIG(*)
        OVER
        (
            PARTITION BY
                case_result.Traders
        )
        AS TraderLifetimeCaseCount,

    SUM(
        case_result.PotentialValueGap
    )
        OVER
        (
            PARTITION BY
                case_result.Traders
        )
        AS TraderLifetimePotentialValueGap,

    MAX(
        case_result.CaseRiskScore
    )
        OVER
        (
            PARTITION BY
                case_result.Traders
        )
        AS TraderMaximumRiskScore,

    COUNT_BIG(*)
        OVER
        (
            PARTITION BY
                case_result.Traders,
                case_result.HS
        )
        AS TraderHSCaseCount

FROM {cases_table}
    AS case_result

WHERE
    case_result.IsPotentialCase = 1;
"""


# ============================================================
# CLUSTER QUALITY VIEW
# ============================================================

def build_cluster_quality_summary_view_sql(
    pipeline: PipelineSettings,
    results: ResultStorageSettings
) -> str:
    """
    Create quarterly clustering-quality statistics.
    """

    cluster_table = (
        results.quoted_name(
            pipeline,
            results.cluster_table
        )
    )

    analytics_schema = (
        f"[{pipeline.analytics_schema}]"
    )

    return f"""
CREATE OR ALTER VIEW
    {analytics_schema}.[vw_ClusterQualitySummary]
AS

SELECT
    YearQuarter,

    COUNT_BIG(*)
        AS AnalyticalRows,

    SUM(
        CASE
            WHEN ClusterApplied = 1
            THEN CONVERT(bigint, 1)
            ELSE CONVERT(bigint, 0)
        END
    ) AS ClusteredRows,

    COUNT(
        DISTINCT
        CASE
            WHEN ClusterApplied = 1
            THEN PeerKey
        END
    ) AS ClusteredGroups,

    AVG(
        CASE
            WHEN ClusterApplied = 1
            THEN ClusterSilhouetteScore
        END
    ) AS AverageSilhouetteScore,

    MIN(
        CASE
            WHEN ClusterApplied = 1
            THEN ClusterSilhouetteScore
        END
    ) AS MinimumSilhouetteScore,

    SUM(
        CASE
            WHEN ClusterApplied = 0
            THEN CONVERT(bigint, 1)
            ELSE CONVERT(bigint, 0)
        END
    ) AS UnclusteredRows

FROM {cluster_table}

GROUP BY
    YearQuarter;
"""


# ============================================================
# RETURN VIEWS AS SEPARATE BATCHES
# ============================================================

def build_reporting_view_batches(
    pipeline: PipelineSettings,
    results: ResultStorageSettings | None = None
) -> list[str]:
    """
    Return each CREATE OR ALTER VIEW statement separately.

    SQL Server requires CREATE VIEW to be the first statement
    in its execution batch. The reporting service must therefore
    execute these strings one at a time.
    """

    if results is None:

        results = (
            ResultStorageSettings
            .from_environment()
        )

    pipeline.validate()

    results.validate()

    return [
        build_case_dashboard_view_sql(
            pipeline,
            results
        ),

        build_quarter_risk_summary_view_sql(
            pipeline,
            results
        ),

        build_hs_risk_summary_view_sql(
            pipeline,
            results
        ),

        build_trader_risk_summary_view_sql(
            pipeline,
            results
        ),

        build_trader_case_history_view_sql(
            pipeline,
            results
        ),

        build_cluster_quality_summary_view_sql(
            pipeline,
            results
        )
    ]


# ============================================================
# REPORTING INDEXES
# ============================================================

def build_reporting_indexes_sql(
    pipeline: PipelineSettings,
    results: ResultStorageSettings | None = None
) -> str:
    """
    Create the additional index used by dashboard ordering.
    """

    if results is None:

        results = (
            ResultStorageSettings
            .from_environment()
        )

    cases_table = (
        results.quoted_name(
            pipeline,
            results.case_table
        )
    )

    case_object_name = (
        results.object_name(
            pipeline,
            results.case_table
        )
    )

    index_name = (
        f"IX_{results.case_table}_QuarterScore"
    )

    return f"""
IF NOT EXISTS
(
    SELECT
        1

    FROM sys.indexes

    WHERE object_id =
        OBJECT_ID(
            N'{case_object_name}'
        )

      AND name =
        N'{index_name}'
)
BEGIN

    CREATE NONCLUSTERED INDEX
        [{index_name}]

    ON {cases_table}
    (
        YearQuarter,
        CaseRiskScore DESC,
        PotentialValueGap DESC
    )

    INCLUDE
    (
        PreparedDeclarationId,
        RegistrationDate,
        FormNumber,
        Traders,
        Lib_Traders,
        HS,
        Lib_HS8,
        UnitValue,
        FinalBenchmarkQ1,
        FinalBenchmarkMethod,
        FinalDeviationPercent,
        CaseRiskLevel,
        ModelAgreement
    );

END;
"""