from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pyodbc

from app.database.benchmark_sql import (
    build_original_benchmark_sql
)

from config.settings import (
    PipelineSettings
)


# ============================================================
# BENCHMARK RESULT
# ============================================================

@dataclass(
    frozen=True
)
class BenchmarkResult:
    """
    Summary returned after building original benchmarks.
    """

    benchmark_groups: int

    eligible_groups: int

    ineligible_groups: int

    eligible_rows: int

    elapsed_seconds: float


# ============================================================
# BUILD ORIGINAL BENCHMARKS
# ============================================================

def build_original_benchmarks(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> BenchmarkResult:
    """
    Rebuild analytics.OriginalBenchmarks.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    settings.validate()

    benchmark_sql = (
        build_original_benchmark_sql(
            settings
        )
    )

    project_root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
        .parent
    )

    debug_sql_path = (
        project_root
        / "logs"
        / "generated_benchmarks.sql"
    )

    debug_sql_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    debug_sql_path.write_text(
        benchmark_sql,
        encoding="utf-8"
    )

    started_at = datetime.now()

    cursor = connection.cursor()

    try:

        cursor.execute(
            benchmark_sql
        )

        result_row = cursor.fetchone()

        if result_row is None:

            raise RuntimeError(
                "The benchmark query did not return "
                "its expected summary result."
            )

        connection.commit()

        elapsed_seconds = (
            datetime.now()
            - started_at
        ).total_seconds()

        return BenchmarkResult(
            benchmark_groups=int(
                result_row.BenchmarkGroups
                or 0
            ),

            eligible_groups=int(
                result_row.EligibleGroups
                or 0
            ),

            ineligible_groups=int(
                result_row.IneligibleGroups
                or 0
            ),

            eligible_rows=int(
                result_row.EligibleRows
                or 0
            ),

            elapsed_seconds=elapsed_seconds
        )

    except Exception:

        connection.rollback()

        raise

    finally:

        cursor.close()