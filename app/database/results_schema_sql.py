from __future__ import annotations

from dataclasses import dataclass
import os

from config.settings import PipelineSettings, quote_sql_identifier


@dataclass(frozen=True)
class ResultStorageSettings:
    cluster_results_table: str
    case_results_table: str
    insert_batch_size: int

    @classmethod
    def from_environment(cls) -> "ResultStorageSettings":
        settings = cls(
            cluster_results_table=os.getenv(
                "CLUSTER_RESULTS_TABLE", "ClusterResults"
            ).strip(),
            case_results_table=os.getenv(
                "CASE_RESULTS_TABLE", "CaseResults"
            ).strip(),
            insert_batch_size=int(os.getenv(
                "RESULT_INSERT_BATCH_SIZE", "5000"
            )),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.cluster_results_table:
            raise ValueError("CLUSTER_RESULTS_TABLE cannot be empty.")
        if not self.case_results_table:
            raise ValueError("CASE_RESULTS_TABLE cannot be empty.")
        if self.insert_batch_size < 1:
            raise ValueError("RESULT_INSERT_BATCH_SIZE must be at least 1.")

    def quoted_name(self, pipeline: PipelineSettings, table: str) -> str:
        return (
            f"{quote_sql_identifier(pipeline.analytics_schema)}."
            f"{quote_sql_identifier(table)}"
        )

    def object_name(self, pipeline: PipelineSettings, table: str) -> str:
        return f"{pipeline.analytics_schema}.{table}"

    @property
    def cluster_table(self) -> str:
        return self.cluster_results_table

    @property
    def case_table(self) -> str:
        return self.case_results_table


def build_results_schema_sql(
    pipeline: PipelineSettings,
    results: ResultStorageSettings | None = None,
) -> str:
    if results is None:
        results = ResultStorageSettings.from_environment()

    pipeline.validate()
    results.validate()

    cluster_full = results.quoted_name(pipeline, results.cluster_table)
    cluster_object = results.object_name(pipeline, results.cluster_table)
    case_full = results.quoted_name(pipeline, results.case_table)
    case_object = results.object_name(pipeline, results.case_table)

    return f"""
SET NOCOUNT ON;
SET XACT_ABORT ON;

IF OBJECT_ID(N'{cluster_object}', N'U') IS NULL
BEGIN
    CREATE TABLE {cluster_full}
    (
        PreparedDeclarationId bigint NOT NULL,
        YearQuarter char(7) NOT NULL,
        PeerKey varchar(100) NULL,
        ClusterApplied bit NOT NULL,
        ClusterEligible bit NOT NULL,
        ClusterEligibilityReason varchar(100) NULL,
        ClusterModel varchar(50) NULL,
        ClusterCount int NULL,
        ClusterId int NULL,
        ClusterPriceTier varchar(30) NULL,
        ClusterSilhouetteScore decimal(18,8) NULL,
        ClusterPeerCount bigint NULL,
        ClusterQ1 decimal(28,8) NULL,
        ClusterMedian decimal(28,8) NULL,
        ClusterQ3 decimal(28,8) NULL,
        ClusterMinimumUnitValue decimal(28,8) NULL,
        ClusterMaximumUnitValue decimal(28,8) NULL,
        ClusterAverageUnitValue decimal(28,8) NULL,
        ClusterInterquartileRange decimal(28,8) NULL,
        ModelVersion varchar(100) NULL,
        LoadedAt datetime2(0) NOT NULL
            CONSTRAINT [DF_{results.cluster_table}_LoadedAt]
            DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_{results.cluster_table}]
            PRIMARY KEY CLUSTERED (PreparedDeclarationId)
    );
END;

IF NOT EXISTS
(
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'{cluster_object}')
      AND name = N'IX_{results.cluster_table}_Quarter'
)
BEGIN
    CREATE NONCLUSTERED INDEX [IX_{results.cluster_table}_Quarter]
    ON {cluster_full} (YearQuarter, ClusterApplied)
    INCLUDE
    (
        PeerKey, ClusterId, ClusterPriceTier,
        ClusterQ1, ClusterMedian, ClusterQ3
    );
END;

IF NOT EXISTS
(
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'{cluster_object}')
      AND name = N'IX_{results.cluster_table}_Peer'
)
BEGIN
    CREATE NONCLUSTERED INDEX [IX_{results.cluster_table}_Peer]
    ON {cluster_full} (YearQuarter, PeerKey)
    INCLUDE
    (
        ClusterApplied, ClusterId, ClusterPeerCount,
        ClusterQ1, ClusterMedian, ClusterQ3
    );
END;

IF OBJECT_ID(N'{case_object}', N'U') IS NULL
BEGIN
    CREATE TABLE {case_full}
    (
        CaseResultId bigint IDENTITY(1,1) NOT NULL,
        PreparedDeclarationId bigint NOT NULL,
        YearQuarter char(7) NOT NULL,
        RegistrationDate date NULL,
        FormNumber varchar(60) NULL,
        Traders varchar(60) NULL,
        Lib_Traders nvarchar(255) NULL,
        HS varchar(20) NULL,
        Lib_HS8 nvarchar(500) NULL,
        SelectedQuantity decimal(28,6) NULL,
        SelectedUnit varchar(30) NULL,
        FOBValue decimal(28,4) NULL,
        UnitValue decimal(28,8) NULL,
        PeerCount bigint NULL,
        OriginalQ1 decimal(28,8) NULL,
        OriginalMedian decimal(28,8) NULL,
        OriginalQ3 decimal(28,8) NULL,
        ClusterApplied bit NOT NULL,
        ClusterId int NULL,
        ClusterPriceTier varchar(30) NULL,
        ClusterPeerCount bigint NULL,
        ClusterQ1 decimal(28,8) NULL,
        ClusterMedian decimal(28,8) NULL,
        ClusterQ3 decimal(28,8) NULL,
        OriginalFlag bit NOT NULL,
        ClusterFlag bit NOT NULL,
        FinalBenchmarkMethod varchar(30) NULL,
        FinalBenchmarkQ1 decimal(28,8) NULL,
        FinalDeviationPercent decimal(18,6) NULL,
        PotentialValueGap decimal(28,4) NULL,
        ModelAgreement varchar(50) NULL,
        DeviationRiskComponent decimal(10,4) NULL,
        ValueGapRiskComponent decimal(10,4) NULL,
        PeerSupportRiskComponent decimal(10,4) NULL,
        ModelAgreementRiskComponent decimal(10,4) NULL,
        TransactionValueRiskComponent decimal(10,4) NULL,
        CaseRiskScore decimal(10,4) NULL,
        CaseRiskLevel varchar(30) NULL,
        IsPotentialCase bit NOT NULL,
        CaseReason nvarchar(1000) NULL,
        ModelVersion varchar(100) NULL,
        LoadedAt datetime2(0) NOT NULL
            CONSTRAINT [DF_{results.case_table}_LoadedAt]
            DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [PK_{results.case_table}]
            PRIMARY KEY CLUSTERED (CaseResultId),
        CONSTRAINT [UQ_{results.case_table}_Prepared]
            UNIQUE (PreparedDeclarationId)
    );
END;

IF NOT EXISTS
(
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'{case_object}')
      AND name = N'IX_{results.case_table}_QuarterRisk'
)
BEGIN
    CREATE NONCLUSTERED INDEX [IX_{results.case_table}_QuarterRisk]
    ON {case_full} (YearQuarter, IsPotentialCase, CaseRiskLevel)
    INCLUDE
    (
        PreparedDeclarationId, Traders, HS,
        CaseRiskScore, PotentialValueGap,
        FinalBenchmarkMethod
    );
END;

IF NOT EXISTS
(
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'{case_object}')
      AND name = N'IX_{results.case_table}_Trader'
)
BEGIN
    CREATE NONCLUSTERED INDEX [IX_{results.case_table}_Trader]
    ON {case_full} (Traders, YearQuarter)
    INCLUDE
    (
        FormNumber, HS, CaseRiskScore, CaseRiskLevel,
        PotentialValueGap, IsPotentialCase
    );
END;

IF NOT EXISTS
(
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'{case_object}')
      AND name = N'IX_{results.case_table}_HS'
)
BEGIN
    CREATE NONCLUSTERED INDEX [IX_{results.case_table}_HS]
    ON {case_full} (HS, YearQuarter)
    INCLUDE
    (
        Traders, FormNumber, UnitValue, FinalBenchmarkQ1,
        FinalDeviationPercent, PotentialValueGap,
        CaseRiskScore, CaseRiskLevel
    );
END;
"""
