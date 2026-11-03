from __future__ import annotations

from config.settings import (
    PipelineSettings
)


# ============================================================
# BUILD ORIGINAL BENCHMARK SQL
# ============================================================

def build_original_benchmark_sql(
    settings: PipelineSettings
) -> str:
    """
    Build original peer-group benchmarks from valid prepared
    declarations.

    Peer group:

        HS
        + YearQuarter
        + SelectedUnit
    """

    settings.validate()

    prepared_table = (
        settings.prepared_full_name
    )

    benchmark_table = (
        settings.benchmark_full_name
    )

    minimum_peer_count = int(
        settings.minimum_peer_count
    )

    return f"""
SET NOCOUNT ON;
SET XACT_ABORT ON;


-- ===========================================================
-- CLEAR EXISTING BENCHMARKS
-- ===========================================================

TRUNCATE TABLE {benchmark_table};


-- ===========================================================
-- CALCULATE BENCHMARK DISTRIBUTIONS
-- ===========================================================

;WITH ValidPreparedRows AS
(
    SELECT
        HS,
        YearQuarter,
        SelectedUnit,
        PeerKey,
        UnitValue

    FROM {prepared_table}

    WHERE
        IsAnalyticallyValid = 1

        AND HS IS NOT NULL

        AND YearQuarter IS NOT NULL

        AND SelectedUnit IS NOT NULL

        AND PeerKey IS NOT NULL

        AND UnitValue IS NOT NULL

        AND UnitValue >= 0
),


-- ===========================================================
-- CALCULATE QUARTILES USING WINDOW FUNCTIONS
-- ===========================================================

BenchmarkWindows AS
(
    SELECT
        HS,
        YearQuarter,
        SelectedUnit,
        PeerKey,
        UnitValue,

        COUNT_BIG(*) OVER
        (
            PARTITION BY
                HS,
                YearQuarter,
                SelectedUnit
        ) AS PeerCount,

        PERCENTILE_CONT(
            0.25
        )
        WITHIN GROUP
        (
            ORDER BY UnitValue
        )
        OVER
        (
            PARTITION BY
                HS,
                YearQuarter,
                SelectedUnit
        ) AS OriginalQ1,

        PERCENTILE_CONT(
            0.50
        )
        WITHIN GROUP
        (
            ORDER BY UnitValue
        )
        OVER
        (
            PARTITION BY
                HS,
                YearQuarter,
                SelectedUnit
        ) AS OriginalMedian,

        PERCENTILE_CONT(
            0.75
        )
        WITHIN GROUP
        (
            ORDER BY UnitValue
        )
        OVER
        (
            PARTITION BY
                HS,
                YearQuarter,
                SelectedUnit
        ) AS OriginalQ3

    FROM ValidPreparedRows
),


-- ===========================================================
-- REDUCE EACH PEER GROUP TO ONE RECORD
-- ===========================================================

BenchmarkGroups AS
(
    SELECT
        HS,
        YearQuarter,
        SelectedUnit,
        PeerKey,

        MAX(
            PeerCount
        ) AS PeerCount,

        MAX(
            OriginalQ1
        ) AS OriginalQ1,

        MAX(
            OriginalMedian
        ) AS OriginalMedian,

        MAX(
            OriginalQ3
        ) AS OriginalQ3,

        MIN(
            UnitValue
        ) AS MinimumUnitValue,

        MAX(
            UnitValue
        ) AS MaximumUnitValue,

        AVG(
            UnitValue
        ) AS AverageUnitValue,

        STDEV(
            UnitValue
        ) AS UnitValueStdDev

    FROM BenchmarkWindows

    GROUP BY
        HS,
        YearQuarter,
        SelectedUnit,
        PeerKey
)


-- ===========================================================
-- LOAD ORIGINAL BENCHMARK TABLE
-- ===========================================================

INSERT INTO {benchmark_table}
(
    HS,
    YearQuarter,
    SelectedUnit,
    PeerKey,

    PeerCount,

    OriginalQ1,
    OriginalMedian,
    OriginalQ3,

    MinimumUnitValue,
    MaximumUnitValue,
    AverageUnitValue,
    UnitValueStdDev,
    InterquartileRange,

    IsBenchmarkEligible,
    IneligibilityReason
)

SELECT
    HS,
    YearQuarter,
    SelectedUnit,
    PeerKey,

    PeerCount,

    TRY_CONVERT(
        decimal(28, 8),
        OriginalQ1
    ),

    TRY_CONVERT(
        decimal(28, 8),
        OriginalMedian
    ),

    TRY_CONVERT(
        decimal(28, 8),
        OriginalQ3
    ),

    TRY_CONVERT(
        decimal(28, 8),
        MinimumUnitValue
    ),

    TRY_CONVERT(
        decimal(28, 8),
        MaximumUnitValue
    ),

    TRY_CONVERT(
        decimal(28, 8),
        AverageUnitValue
    ),

    TRY_CONVERT(
        decimal(28, 8),
        UnitValueStdDev
    ),

    TRY_CONVERT(
        decimal(28, 8),
        OriginalQ3 - OriginalQ1
    ),

    CONVERT(
        bit,
        CASE
            WHEN PeerCount >= {minimum_peer_count}
            THEN 1

            ELSE 0
        END
    ),

    CASE
        WHEN PeerCount < {minimum_peer_count}
        THEN 'INSUFFICIENT_PEER_COUNT'

        WHEN OriginalQ1 IS NULL
        THEN 'MISSING_Q1'

        WHEN OriginalMedian IS NULL
        THEN 'MISSING_MEDIAN'

        WHEN OriginalQ3 IS NULL
        THEN 'MISSING_Q3'

        ELSE NULL
    END

FROM BenchmarkGroups;


-- ===========================================================
-- RETURN BENCHMARK BUILD SUMMARY
-- ===========================================================

SELECT
    COUNT_BIG(*)
        AS BenchmarkGroups,

    COALESCE(
        SUM(
            CASE
                WHEN IsBenchmarkEligible = 1
                THEN CONVERT(bigint, 1)
                ELSE CONVERT(bigint, 0)
            END
        ),
        0
    ) AS EligibleGroups,

    COALESCE(
        SUM(
            CASE
                WHEN IsBenchmarkEligible = 0
                THEN CONVERT(bigint, 1)
                ELSE CONVERT(bigint, 0)
            END
        ),
        0
    ) AS IneligibleGroups,

    COALESCE(
        SUM(
            CASE
                WHEN IsBenchmarkEligible = 1
                THEN PeerCount
                ELSE CONVERT(bigint, 0)
            END
        ),
        0
    ) AS EligibleRows

FROM {benchmark_table};
"""