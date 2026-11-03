from __future__ import annotations

import sys
import traceback

import pyodbc

from app.database.connection import (
    database_connection
)

from app.services.schema_service import (
    deploy_analytical_schema
)

from config.settings import (
    DatabaseSettings,
    PipelineSettings
)


# ============================================================
# EXPECTED TABLES
# ============================================================

def expected_analytical_tables(
    settings: PipelineSettings) -> list:
    """
    Return the expected analytical table names.
     """

    return [
        settings.run_log_table,
        settings.prepared_table,
        settings.original_benchmark_table,
        settings.cluster_benchmark_table,
        settings.case_results_table,
        settings.period_summary_table,
        settings.hs_summary_table,
        settings.trader_summary_table
    ]


# ============================================================
# DEPLOY AND TEST SCHEMA
# ============================================================

def create_and_test_schema() -> None:
    """
    Create the analytical schema and verify every table.
    """

    database_settings = (
        DatabaseSettings
        .from_environment()
    )

    pipeline_settings = (
        PipelineSettings
        .from_environment()
    )

    print(
        "=" * 70
    )

    print(
        "ANALYTICAL SCHEMA DEPLOYMENT"
    )

    print(
        "=" * 70
    )

    print(
        "Server:",
        database_settings.server
    )

    print(
        "Database:",
        database_settings.database
    )

    print(
        "Analytical schema:",
        pipeline_settings.analytics_schema
    )

    print()

    with database_connection(
        database_settings
    ) as connection:

        deployment_result = (
            deploy_analytical_schema(
                connection,
                pipeline_settings
            )
        )

        print()

        print(
            "Deployment steps completed:"
        )

        for object_name in (
            deployment_result
            .objects_processed
        ):

            print(
                "  -",
                object_name
            )

        cursor = connection.cursor()

        # ----------------------------------------------------
        # VERIFY SCHEMA
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                SCHEMA_ID(
                    ?
                ) AS SchemaId;
            """,
            pipeline_settings.analytics_schema
        )

        schema_id = (
            cursor.fetchone()
            .SchemaId
        )

        if schema_id is None:

            raise RuntimeError(
                "The analytics schema was not created."
            )

        print()

        print(
            "Analytics schema exists:",
            "YES"
        )

        # ----------------------------------------------------
        # VERIFY TABLES
        # ----------------------------------------------------

        expected_tables = (
            expected_analytical_tables(
                pipeline_settings
            )
        )

        cursor.execute(
            """
            SELECT
                t.name
                    AS TableName
            FROM sys.tables AS t
            INNER JOIN sys.schemas AS s
                ON t.schema_id = s.schema_id
            WHERE s.name = ?
            ORDER BY
                t.name;
            """,
            pipeline_settings.analytics_schema
        )

        actual_tables = {
            row.TableName
            for row in cursor.fetchall()
        }

        missing_tables = [
            table_name
            for table_name in expected_tables
            if table_name not in actual_tables
        ]

        print()

        print(
            "Expected tables:"
        )

        for table_name in expected_tables:

            status = (
                "FOUND"
                if table_name in actual_tables
                else "MISSING"
            )

            print(
                f"  {table_name}: "
                f"{status}"
            )

        if missing_tables:

            raise RuntimeError(
                "The following analytical tables "
                "were not created: "
                + ", ".join(
                    missing_tables
                )
            )

        # ----------------------------------------------------
        # VERIFY TABLE ROW COUNTS
        # ----------------------------------------------------

        print()

        print(
            "Initial table row counts:"
        )

        for table_name in expected_tables:

            full_table_name = (
                pipeline_settings
                .analytical_table_name(
                    table_name
                )
            )

            cursor.execute(
                f"""
                SELECT
                    COUNT_BIG(*)
                FROM {full_table_name};
                """
            )

            row_count = (
                cursor.fetchone()[0]
            )

            print(
                f"  {full_table_name}: "
                f"{row_count:,}"
            )

        cursor.close()

    print()

    print(
        "=" * 70
    )

    print(
        "ANALYTICAL SCHEMA CREATED SUCCESSFULLY"
    )

    print(
        "=" * 70
    )


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        create_and_test_schema()

    except pyodbc.Error as error:

        print()

        print(
            "SQL SERVER ERROR"
        )

        print(
            error
        )

        traceback.print_exc()

        sys.exit(1)

    except Exception as error:

        print()

        print(
            "SCHEMA DEPLOYMENT FAILED"
        )

        print(
            error
        )

        traceback.print_exc()

        sys.exit(1)