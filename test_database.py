from __future__ import annotations

import sys
import traceback

import pyodbc

from app.database.connection import (
    database_connection
)

from config.settings import (
    DatabaseSettings,
    PipelineSettings
)


# ============================================================
# DATABASE CONNECTION TEST
# ============================================================

def test_database_connection() -> None:
    """
    Test the SQL Server connection and source table.

    This function does not change any database data.
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
        "DATABASE CONNECTION TEST"
    )

    print(
        "=" * 70
    )

    print(
        "Configured server:",
        database_settings.server
    )

    print(
        "Configured database:",
        database_settings.database
    )

    print(
        "Configured driver:",
        database_settings.driver
    )

    print(
        "Source table:",
        pipeline_settings.source_full_name
    )

    print()

    with database_connection(
        database_settings
    ) as connection:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # SQL SERVER INFORMATION
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                @@SERVERNAME
                    AS ServerName,

                DB_NAME()
                    AS DatabaseName,

                SUSER_SNAME()
                    AS LoginName,

                @@VERSION
                    AS SQLServerVersion;
            """
        )

        server_information = (
            cursor.fetchone()
        )

        print(
            "Connected server:",
            server_information.ServerName
        )

        print(
            "Connected database:",
            server_information.DatabaseName
        )

        print(
            "Connected login:",
            server_information.LoginName
        )

        print()

        # ----------------------------------------------------
        # CHECK SOURCE TABLE
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                OBJECT_ID(
                    ?,
                    'U'
                ) AS ObjectId;
            """,
            (
                f"{pipeline_settings.source_schema}"
                f"."
                f"{pipeline_settings.source_table}"
            )
        )

        object_id = (
            cursor.fetchone()
            .ObjectId
        )

        if object_id is None:

            raise RuntimeError(
                "The configured source table "
                f"{pipeline_settings.source_full_name} "
                "does not exist in database "
                f"{server_information.DatabaseName}."
            )

        print(
            "Source table exists:",
            "YES"
        )

        # ----------------------------------------------------
        # COUNT SOURCE ROWS
        # ----------------------------------------------------

        count_sql = (
            "SELECT COUNT_BIG(*) "
            f"FROM "
            f"{pipeline_settings.source_full_name};"
        )

        cursor.execute(
            count_sql
        )

        source_row_count = (
            cursor.fetchone()[0]
        )

        print(
            "Source rows:",
            f"{source_row_count:,}"
        )

        # ----------------------------------------------------
        # CHECK SOURCE COLUMNS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
                AS c
            WHERE c.TABLE_SCHEMA = ?
              AND c.TABLE_NAME = ?
            ORDER BY
                c.ORDINAL_POSITION;
            """,
            pipeline_settings.source_schema,
            pipeline_settings.source_table
        )

        source_columns = (
            cursor.fetchall()
        )

        print(
            "Source columns:",
            f"{len(source_columns):,}"
        )

        print()

        print(
            "First 10 columns:"
        )

        for column in source_columns[:10]:

            print(
                "  ",
                column.COLUMN_NAME,
                "|",
                column.DATA_TYPE,
                "| nullable:",
                column.IS_NULLABLE
            )

        # ----------------------------------------------------
        # REQUIRED COLUMN CHECK
        # ----------------------------------------------------

        available_column_names = {
            column.COLUMN_NAME
            for column in source_columns
        }

        required_columns = {
            "Year",
            "Period",
            "Day",
            "FormNumber",
            "Traders",
            "Lib_Traders",
            "TRS_Trade",
            "Flows",
            "HS",
            "Lib_HS8",
            "FOBValue",
            "VAT",
            "NetWeight",
            "QTY",
            "SU"
        }

        missing_columns = sorted(
            required_columns
            - available_column_names
        )

        print()

        if missing_columns:

            print(
                "Missing required columns:"
            )

            for column_name in missing_columns:

                print(
                    "  -",
                    column_name
                )

            raise RuntimeError(
                "The source table is missing "
                "one or more required columns."
            )

        print(
            "Required columns available:",
            "YES"
        )

        print()

        print(
            "=" * 70
        )

        print(
            "DATABASE TEST COMPLETED SUCCESSFULLY"
        )

        print(
            "=" * 70
        )


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        test_database_connection()

    except pyodbc.Error as error:

        print()

        print(
            "SQL SERVER CONNECTION ERROR"
        )

        print(
            error
        )

        sys.exit(1)

    except Exception as error:

        print()

        print(
            "DATABASE TEST FAILED"
        )

        print(
            error
        )

        traceback.print_exc()

        sys.exit(1)