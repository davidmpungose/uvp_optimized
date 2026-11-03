from __future__ import annotations

import pyodbc

from config.settings import (
    PipelineSettings
)


# ============================================================
# BENCHMARK SUMMARY
# ============================================================

def get_benchmark_summary(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> dict[str, object]:
    """
    Return the main benchmark statistics.
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
                        PeerCount
                    ),
                    0
                ) AS TotalRowsRepresented,

                COALESCE(
                    SUM(
                        CASE
                            WHEN IsBenchmarkEligible = 1
                            THEN PeerCount
                            ELSE CONVERT(bigint, 0)
                        END
                    ),
                    0
                ) AS EligibleRowsRepresented,

                MIN(
                    YearQuarter
                ) AS MinimumQuarter,

                MAX(
                    YearQuarter
                ) AS MaximumQuarter,

                MIN(
                    PeerCount
                ) AS MinimumPeerCount,

                MAX(
                    PeerCount
                ) AS MaximumPeerCount,

                AVG(
                    CONVERT(
                        decimal(28, 4),
                        PeerCount
                    )
                ) AS AveragePeerCount,

                SUM(
                    CASE
                        WHEN OriginalQ1 > OriginalMedian
                        THEN CONVERT(bigint, 1)

                        WHEN OriginalMedian > OriginalQ3
                        THEN CONVERT(bigint, 1)

                        ELSE CONVERT(bigint, 0)
                    END
                ) AS InvalidQuartileOrderGroups

            FROM {
                settings.benchmark_full_name
            };
            """
        )

        row = cursor.fetchone()

        return {
            "benchmark_groups":
                int(
                    row.BenchmarkGroups
                    or 0
                ),

            "eligible_groups":
                int(
                    row.EligibleGroups
                    or 0
                ),

            "ineligible_groups":
                int(
                    row.IneligibleGroups
                    or 0
                ),

            "total_rows_represented":
                int(
                    row.TotalRowsRepresented
                    or 0
                ),

            "eligible_rows_represented":
                int(
                    row.EligibleRowsRepresented
                    or 0
                ),

            "minimum_quarter":
                row.MinimumQuarter,

            "maximum_quarter":
                row.MaximumQuarter,

            "minimum_peer_count":
                int(
                    row.MinimumPeerCount
                    or 0
                ),

            "maximum_peer_count":
                int(
                    row.MaximumPeerCount
                    or 0
                ),

            "average_peer_count":
                float(
                    row.AveragePeerCount
                    or 0
                ),

            "invalid_quartile_order_groups":
                int(
                    row.InvalidQuartileOrderGroups
                    or 0
                )
        }

    finally:

        cursor.close()


# ============================================================
# INELIGIBILITY SUMMARY
# ============================================================

def get_ineligible_benchmark_summary(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> list[dict[str, object]]:
    """
    Return benchmark counts by eligibility status or reason.
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
                CASE
                    WHEN IsBenchmarkEligible = 1
                    THEN 'ELIGIBLE'

                    ELSE COALESCE(
                        IneligibilityReason,
                        'INELIGIBLE'
                    )
                END AS BenchmarkStatus,

                COUNT_BIG(*)
                    AS BenchmarkGroups,

                SUM(
                    PeerCount
                ) AS RowsRepresented

            FROM {
                settings.benchmark_full_name
            }

            GROUP BY
                CASE
                    WHEN IsBenchmarkEligible = 1
                    THEN 'ELIGIBLE'

                    ELSE COALESCE(
                        IneligibilityReason,
                        'INELIGIBLE'
                    )
                END

            ORDER BY
                BenchmarkGroups DESC;
            """
        )

        return [
            {
                "status":
                    row.BenchmarkStatus,

                "benchmark_groups":
                    int(
                        row.BenchmarkGroups
                    ),

                "rows_represented":
                    int(
                        row.RowsRepresented
                        or 0
                    )
            }
            for row in cursor.fetchall()
        ]

    finally:

        cursor.close()


# ============================================================
# PRINT BENCHMARK VALIDATION
# ============================================================

def print_benchmark_validation(
    summary: dict[str, object],
    ineligible_summary: list[
        dict[str, object]
    ]
) -> None:
    """
    Print benchmark-validation results.
    """

    print(
        "=" * 70
    )

    print(
        "ORIGINAL BENCHMARK VALIDATION"
    )

    print(
        "=" * 70
    )

    print(
        "Benchmark groups:",
        f"{summary['benchmark_groups']:,}"
    )

    print(
        "Eligible groups:",
        f"{summary['eligible_groups']:,}"
    )

    print(
        "Ineligible groups:",
        f"{summary['ineligible_groups']:,}"
    )

    print(
        "Total rows represented:",
        f"{summary['total_rows_represented']:,}"
    )

    print(
        "Eligible rows represented:",
        f"{summary['eligible_rows_represented']:,}"
    )

    print(
        "Quarter coverage:",
        summary["minimum_quarter"],
        "to",
        summary["maximum_quarter"]
    )

    print(
        "Minimum peer count:",
        f"{summary['minimum_peer_count']:,}"
    )

    print(
        "Maximum peer count:",
        f"{summary['maximum_peer_count']:,}"
    )

    print(
        "Average peer count:",
        f"{summary['average_peer_count']:,.2f}"
    )

    print(
        "Invalid quartile ordering:",
        f"{summary['invalid_quartile_order_groups']:,}"
    )

    print()

    print(
        "Benchmark status:"
    )

    for record in ineligible_summary:

        print(
            "  ",
            record["status"],
            ":",
            f"{record['benchmark_groups']:,}",
            "groups |",
            f"{record['rows_represented']:,}",
            "rows"
        )

    print(
        "=" * 70
    )