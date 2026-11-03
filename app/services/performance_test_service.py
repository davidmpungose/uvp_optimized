from __future__ import annotations

import gc
import os
import time

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.database.connection import (
    database_connection
)

from app.services.analytics_input_service import (
    list_analytical_quarters
)

from app.analytics.clustering_service import (
    cluster_analytical_quarter
)

from app.services.risk_service import (
    score_clustered_quarter
)

from config.settings import (
    DatabaseSettings,
    PipelineSettings
)


# ============================================================
# PERFORMANCE RESULT
# ============================================================

@dataclass(
    frozen=True
)
class QuarterPerformanceResult:
    """
    Performance results for one analytical quarter.
    """

    quarter: str

    clustering_seconds: float

    scoring_seconds: float

    total_seconds: float

    clustering_rows: int

    cases_generated: int

    potential_value_gap: float


# ============================================================
# OUTPUT PATH
# ============================================================

def get_performance_output_directory() -> Path:
    """
    Return the performance-results directory.
    """

    project_root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
        .parent
    )

    output_directory = (
        project_root
        / "output"
        / "performance"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return output_directory


# ============================================================
# FORMAT ELAPSED TIME
# ============================================================

def format_elapsed_time(
    seconds: float
) -> str:
    """
    Convert seconds into readable hours, minutes and seconds.
    """

    total_seconds = int(
        round(
            seconds
        )
    )

    hours = (
        total_seconds
        // 3600
    )

    remaining_seconds = (
        total_seconds
        % 3600
    )

    minutes = (
        remaining_seconds
        // 60
    )

    seconds_remaining = (
        remaining_seconds
        % 60
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds_remaining:02d}"
    )


# ============================================================
# TEST ALL AVAILABLE QUARTERS
# ============================================================

def run_all_quarters_performance_test() -> Path:
    """
    Run clustering and risk scoring for every available quarter
    and record the time taken by each stage.

    This does not rerun source preparation or SQL benchmark
    creation.

    It tests the performance of:

        SQL extraction
            +
        Python clustering
            +
        Python risk scoring
    """

    database_settings = (
        DatabaseSettings
        .from_environment()
    )

    pipeline_settings = (
        PipelineSettings
        .from_environment()
    )

    overall_started_at = (
        time.perf_counter()
    )

    run_started_at = (
        datetime.now()
    )

    print(
        "=" * 78
    )

    print(
        "FULL ANALYTICAL PERFORMANCE TEST"
    )

    print(
        "=" * 78
    )

    print(
        "Started:",
        run_started_at
    )

    print()


    with database_connection(
        database_settings
    ) as connection:

        quarters = (
            list_analytical_quarters(
                connection=connection,
                settings=pipeline_settings
            )
        )


    if not quarters:

        raise RuntimeError(
            "No analytical quarters are available."
        )


    print(
        "Quarters to process:",
        len(
            quarters
        )
    )

    print(
        "Quarter range:",
        quarters[0],
        "to",
        quarters[-1]
    )

    print()


    results: list[
        QuarterPerformanceResult
    ] = []


    for quarter_number, quarter in enumerate(
        quarters,
        start=1
    ):

        print()

        print(
            "=" * 78
        )

        print(
            f"PROCESSING {quarter}"
        )

        print(
            f"Quarter "
            f"{quarter_number:,} "
            f"of {len(quarters):,}"
        )

        print(
            "=" * 78
        )


        # ====================================================
        # CLUSTERING
        # ====================================================

        clustering_started_at = (
            time.perf_counter()
        )


        with database_connection(
            database_settings
        ) as connection:

            clustering_result = (
                cluster_analytical_quarter(
                    connection=connection,

                    year_quarter=quarter,

                    pipeline_settings=(
                        pipeline_settings
                    )
                )
            )


        clustering_seconds = (
            time.perf_counter()
            - clustering_started_at
        )


        # ====================================================
        # RISK SCORING
        # ====================================================

        scoring_started_at = (
            time.perf_counter()
        )


        risk_result = (
            score_clustered_quarter(
                year_quarter=quarter
            )
        )


        scoring_seconds = (
            time.perf_counter()
            - scoring_started_at
        )


        quarter_total_seconds = (
            clustering_seconds
            + scoring_seconds
        )


        quarter_result = (
            QuarterPerformanceResult(
                quarter=quarter,

                clustering_seconds=(
                    clustering_seconds
                ),

                scoring_seconds=(
                    scoring_seconds
                ),

                total_seconds=(
                    quarter_total_seconds
                ),

                clustering_rows=(
                    clustering_result.rows
                ),

                cases_generated=(
                    risk_result.potential_cases
                ),

                potential_value_gap=(
                    risk_result
                    .total_potential_value_gap
                )
            )
        )


        results.append(
            quarter_result
        )


        print()

        print(
            "Quarter performance:"
        )

        print(
            "  Clustering:",
            format_elapsed_time(
                clustering_seconds
            )
        )

        print(
            "  Risk scoring:",
            format_elapsed_time(
                scoring_seconds
            )
        )

        print(
            "  Quarter total:",
            format_elapsed_time(
                quarter_total_seconds
            )
        )

        print(
            "  Rows:",
            f"{clustering_result.rows:,}"
        )

        print(
            "  Cases:",
            f"{risk_result.potential_cases:,}"
        )


        # ====================================================
        # RELEASE MEMORY BEFORE NEXT QUARTER
        # ====================================================

        del clustering_result
        del risk_result

        gc.collect()


    # ========================================================
    # CREATE PERFORMANCE TABLE
    # ========================================================

    performance_dataframe = pd.DataFrame(
        [
            {
                "Quarter":
                    result.quarter,

                "ClusteringSeconds":
                    result.clustering_seconds,

                "RiskScoringSeconds":
                    result.scoring_seconds,

                "TotalSeconds":
                    result.total_seconds,

                "RowsProcessed":
                    result.clustering_rows,

                "PotentialCases":
                    result.cases_generated,

                "PotentialValueGap":
                    result.potential_value_gap
            }
            for result in results
        ]
    )


    output_directory = (
        get_performance_output_directory()
    )


    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


    output_path = (
        output_directory
        / (
            "full_analytical_performance_"
            f"{timestamp}.csv"
        )
    )


    performance_dataframe.to_csv(
        output_path,
        index=False
    )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    overall_seconds = (
        time.perf_counter()
        - overall_started_at
    )


    total_rows = int(
        performance_dataframe[
            "RowsProcessed"
        ]
        .sum()
    )


    total_cases = int(
        performance_dataframe[
            "PotentialCases"
        ]
        .sum()
    )


    total_clustering_seconds = float(
        performance_dataframe[
            "ClusteringSeconds"
        ]
        .sum()
    )


    total_scoring_seconds = float(
        performance_dataframe[
            "RiskScoringSeconds"
        ]
        .sum()
    )


    print()

    print(
        "=" * 78
    )

    print(
        "FULL PERFORMANCE TEST COMPLETE"
    )

    print(
        "=" * 78
    )

    print(
        "Quarters processed:",
        f"{len(results):,}"
    )

    print(
        "Rows processed:",
        f"{total_rows:,}"
    )

    print(
        "Potential cases:",
        f"{total_cases:,}"
    )

    print()

    print(
        "Clustering time:",
        format_elapsed_time(
            total_clustering_seconds
        )
    )

    print(
        "Risk scoring time:",
        format_elapsed_time(
            total_scoring_seconds
        )
    )

    print(
        "Total elapsed time:",
        format_elapsed_time(
            overall_seconds
        )
    )


    if overall_seconds > 0:

        print(
            "Average processing speed:",
            f"{total_rows / overall_seconds:,.0f}",
            "rows / second"
        )


    print()

    print(
        "Performance results:"
    )

    print(
        output_path
    )

    print(
        "=" * 78
    )


    return output_path