from __future__ import annotations

import argparse
import sys
import traceback

import pyodbc

from app.database.connection import (
    database_connection
)

from app.database.reporting_sql import (
    build_reporting_indexes_sql,
    build_reporting_view_batches
)

from app.database.results_schema_sql import (
    ResultStorageSettings
)

from config.settings import (
    DatabaseSettings,
    PipelineSettings
)


# ============================================================
# REPORTING VIEW DEFINITIONS
# ============================================================

REPORTING_VIEWS = [
    "vw_CaseDashboard",
    "vw_QuarterRiskSummary",
    "vw_HSRiskSummary",
    "vw_TraderRiskSummary",
    "vw_TraderCaseHistory",
    "vw_ClusterQualitySummary"
]


# ============================================================
# CREATE REPORTING LAYER
# ============================================================

def create_reporting_layer(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings,
    results: ResultStorageSettings
) -> None:
    """
    Create each reporting view in its own SQL execution batch.

    This is required because SQL Server requires CREATE VIEW
    and CREATE OR ALTER VIEW to be the first statement in a
    query batch.
    """

    cursor = connection.cursor()

    try:

        print(
            "=" * 70
        )

        print(
            "CREATING SQL REPORTING LAYER"
        )

        print(
            "=" * 70
        )

        view_batches = (
            build_reporting_view_batches(
                pipeline=pipeline,
                results=results
            )
        )

        for view_number, view_sql in enumerate(
            view_batches,
            start=1
        ):

            view_name = (
                REPORTING_VIEWS[
                    view_number - 1
                ]
            )

            print(
                "Creating view",
                f"{view_number:,}",
                "of",
                f"{len(view_batches):,}",
                ":",
                view_name
            )

            # Each view is executed separately.
            cursor.execute(
                view_sql
            )

        print(
            "Creating reporting indexes..."
        )

        cursor.execute(
            build_reporting_indexes_sql(
                pipeline=pipeline,
                results=results
            )
        )

        connection.commit()

        print()

        print(
            "Reporting views and supporting "
            "indexes are ready."
        )

        print(
            "=" * 70
        )

    except Exception:

        connection.rollback()

        print()

        print(
            "Reporting-layer creation failed."
        )

        print(
            "The transaction was rolled back."
        )

        raise

    finally:

        cursor.close()


# ============================================================
# VALIDATE REPORTING LAYER
# ============================================================

def validate_reporting_layer(
    connection: pyodbc.Connection,
    pipeline: PipelineSettings
) -> None:
    """
    Confirm that every view exists and return summary totals.
    """

    cursor = connection.cursor()

    try:

        print(
            "=" * 70
        )

        print(
            "REPORTING LAYER VALIDATION"
        )

        print(
            "=" * 70
        )

        all_views_exist = True

        for view_name in REPORTING_VIEWS:

            object_name = (
                f"{pipeline.analytics_schema}"
                f".{view_name}"
            )

            cursor.execute(
                """
                SELECT
                    OBJECT_ID(
                        ?,
                        'V'
                    );
                """,
                object_name
            )

            exists = (
                cursor.fetchone()[0]
                is not None
            )

            if not exists:

                all_views_exist = False

            print(
                view_name,
                ":",
                (
                    "YES"
                    if exists
                    else "NO"
                )
            )

        if not all_views_exist:

            raise RuntimeError(
                "One or more reporting views "
                "do not exist."
            )

        cursor.execute(
            f"""
            SELECT
                COUNT_BIG(*)
                    AS QuarterRows,

                COALESCE(
                    SUM(
                        PotentialCases
                    ),
                    0
                ) AS PotentialCases,

                COALESCE(
                    SUM(
                        TotalPotentialValueGap
                    ),
                    0
                ) AS PotentialValueGap

            FROM
                [{pipeline.analytics_schema}]
                .[vw_QuarterRiskSummary];
            """
        )

        row = cursor.fetchone()

        print()

        print(
            "Quarter summaries:",
            f"{int(row.QuarterRows or 0):,}"
        )

        print(
            "Potential cases:",
            f"{int(row.PotentialCases or 0):,}"
        )

        print(
            "Potential value gap:",
            f"E{float(row.PotentialValueGap or 0):,.2f}"
        )

        print(
            "=" * 70
        )

    finally:

        cursor.close()


# ============================================================
# COMMAND LINE
# ============================================================

def build_argument_parser() -> argparse.ArgumentParser:
    """
    Create the reporting command-line parser.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Stage 9 SQL reporting and "
            "trader-history layer."
        )
    )

    parser.add_argument(
        "operation",
        choices=[
            "create-reporting-layer",
            "validate-reporting-layer"
        ]
    )

    return parser


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    Create or validate the reporting layer.
    """

    parser = build_argument_parser()

    arguments = parser.parse_args()

    database_settings = (
        DatabaseSettings
        .from_environment()
    )

    pipeline_settings = (
        PipelineSettings
        .from_environment()
    )

    result_settings = (
        ResultStorageSettings
        .from_environment()
    )

    with database_connection(
        database_settings
    ) as connection:

        if (
            arguments.operation
            == "create-reporting-layer"
        ):

            create_reporting_layer(
                connection=connection,
                pipeline=pipeline_settings,
                results=result_settings
            )

            return

        validate_reporting_layer(
            connection=connection,
            pipeline=pipeline_settings
        )


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

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
            "APPLICATION ERROR"
        )

        print(
            error
        )

        traceback.print_exc()

        sys.exit(1)