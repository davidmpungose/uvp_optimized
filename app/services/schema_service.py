from __future__ import annotations

import pyodbc

from app.database.schema_sql import (
    build_complete_schema_sql
)

from config.settings import (
    PipelineSettings
)


# ============================================================
# CREATE ANALYTICS SCHEMA OBJECTS
# ============================================================

def create_analytics_schema(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> None:
    """
    Create all currently defined analytics schema objects.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    deployment_sql = (
        build_complete_schema_sql(
            settings
        )
    )

    cursor = connection.cursor()

    try:

        print(
            "=" * 70
        )

        print(
            "CREATING ANALYTICS SCHEMA"
        )

        print(
            "=" * 70
        )

        print(
            "Analytics schema:",
            settings.analytics_schema
        )

        print(
            "Run-log table:",
            settings.run_log_full_name
        )

        print(
            "Prepared table:",
            settings.prepared_full_name
        )

        print(
            "Benchmark table:",
            settings.benchmark_full_name
        )

        print()

        cursor.execute(
            deployment_sql
        )

        connection.commit()

        print(
            "Analytics schema objects created successfully."
        )

    except Exception:

        connection.rollback()

        print()

        print(
            "Schema creation failed."
        )

        print(
            "The active transaction was rolled back."
        )

        raise

    finally:

        cursor.close()


# ============================================================
# VERIFY ANALYTICS SCHEMA
# ============================================================

def verify_analytics_schema(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> dict[str, object]:
    """
    Verify the analytics schema, prepared table and benchmark
    table.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                SCHEMA_ID(
                    ?
                ) AS SchemaId,

                OBJECT_ID(
                    ?,
                    'U'
                ) AS RunLogObjectId,

                OBJECT_ID(
                    ?,
                    'U'
                ) AS PreparedObjectId,

                OBJECT_ID(
                    ?,
                    'U'
                ) AS BenchmarkObjectId;
            """,
            settings.analytics_schema,
            settings.run_log_object_name,
            settings.prepared_object_name,
            settings.benchmark_object_name
        )

        row = cursor.fetchone()

        verification = {
            "schema_exists":
                row.SchemaId is not None,

            "run_log_table_exists":
                row.RunLogObjectId is not None,

            "prepared_table_exists":
                row.PreparedObjectId is not None,

            "benchmark_table_exists":
                row.BenchmarkObjectId is not None,

            "schema_id":
                row.SchemaId,

            "run_log_object_id":
                row.RunLogObjectId,

            "prepared_object_id":
                row.PreparedObjectId,

            "benchmark_object_id":
                row.BenchmarkObjectId,

            "prepared_column_count":
                0,

            "prepared_index_count":
                0,

            "prepared_row_count":
                0,

            "benchmark_column_count":
                0,

            "benchmark_index_count":
                0,

            "benchmark_row_count":
                0
        }

        if row.PreparedObjectId is not None:

            cursor.execute(
                """
                SELECT
                    COUNT_BIG(*)
                FROM sys.columns
                WHERE object_id = ?;
                """,
                row.PreparedObjectId
            )

            verification[
                "prepared_column_count"
            ] = int(
                cursor.fetchone()[0]
            )

            cursor.execute(
                """
                SELECT
                    COUNT_BIG(*)
                FROM sys.indexes
                WHERE object_id = ?
                  AND name IS NOT NULL;
                """,
                row.PreparedObjectId
            )

            verification[
                "prepared_index_count"
            ] = int(
                cursor.fetchone()[0]
            )

            cursor.execute(
                f"""
                SELECT
                    COUNT_BIG(*)
                FROM {
                    settings.prepared_full_name
                };
                """
            )

            verification[
                "prepared_row_count"
            ] = int(
                cursor.fetchone()[0]
            )

        if row.BenchmarkObjectId is not None:

            cursor.execute(
            """
            SELECT
                COUNT_BIG(*)
                FROM sys.columns
            WHERE object_id = ?;
            """,
            row.BenchmarkObjectId
        )

            verification[
        "benchmark_column_count"
        ] = int(
            cursor.fetchone()[0]
        )

            cursor.execute(
            """
            SELECT
                COUNT_BIG(*)
            FROM sys.columns
            WHERE object_id = ?
            AND name IN
            (
              'HS',
              'YearQuarter',
              'SelectedUnit',
              'PeerKey',
              'PeerCount',
              'OriginalQ1',
              'OriginalMedian',
              'OriginalQ3',
              'MinimumUnitValue',
              'MaximumUnitValue',
              'AverageUnitValue',
              'UnitValueStdDev',
              'InterquartileRange',
              'IsBenchmarkEligible',
              'IneligibilityReason',
              'CalculatedAt'
          );
        """,
        row.BenchmarkObjectId
    )

            verification[
        "required_benchmark_columns"
            ] = int(
                cursor.fetchone()[0]
            )

            cursor.execute(
                f"""
                SELECT
            COUNT_BIG(*)
        FROM {
            settings.benchmark_full_name
        };
        """
            )

            verification[
            "benchmark_row_count"
        ] = int(
            cursor.fetchone()[0]
            )

        else:

            verification[
        "benchmark_column_count"
            ] = 0

            verification[
        "required_benchmark_columns"
            ] = 0

            verification[
        "benchmark_row_count"
    ] = 0
        
        return verification

    finally:

        cursor.close()


# ============================================================
# PRINT SCHEMA VERIFICATION
# ============================================================

def print_schema_verification(
    verification: dict[str, object]
) -> None:
    """
    Print schema verification results.
    """

    print()

    print(
        "Schema exists:",
        (
            "YES"
            if verification[
                "schema_exists"
            ]
            else "NO"
        )
    )

    print(
        "Run-log table exists:",
        (
            "YES"
            if verification[
                "run_log_table_exists"
            ]
            else "NO"
        )
    )

    print(
        "Prepared table exists:",
        (
            "YES"
            if verification[
                "prepared_table_exists"
            ]
            else "NO"
        )
    )

    print(
        "Benchmark table exists:",
        (
            "YES"
            if verification[
                "benchmark_table_exists"
            ]
            else "NO"
        )
    )

    print(
        "Prepared-table columns:",
        f"{verification['prepared_column_count']:,}"
    )

    print(
        "Prepared-table indexes:",
        f"{verification['prepared_index_count']:,}"
    )

    print(
        "Prepared-table rows:",
        f"{verification['prepared_row_count']:,}"
    )

    print(
        "Benchmark-table columns:",
        f"{verification['benchmark_column_count']:,}"
    )

    print(
        "Benchmark-table indexes:",
        f"{verification['benchmark_index_count']:,}"
    )

    print(
        "Benchmark-table rows:",
        f"{verification['benchmark_row_count']:,}"
    )

    print(
    "Benchmark-table columns:",
    f"{verification.get(
        'benchmark_column_count',
        0
    ):,}"
)

    print(
    "Required benchmark columns:",
    f"{verification.get(
        'required_benchmark_columns',
        0
    ):,}",
    "of 16"
)

    print(
    "Benchmark-table rows:",
    f"{verification.get(
        'benchmark_row_count',
        0
    ):,}"
)