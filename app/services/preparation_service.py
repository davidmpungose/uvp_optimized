from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pyodbc

from app.database import preparation_sql
from app.database.preparation_sql import (
    build_full_preparation_sql
)

from config.settings import (
    PipelineSettings
)


# ============================================================
# PREPARATION RESULT
# ============================================================

@dataclass(
    frozen=True
)
class PreparationResult:
    """
    Summary returned after preparing the declarations.
    """

    run_id: int

    prepared_rows: int

    valid_rows: int

    invalid_rows: int

    valid_peer_groups: int

    elapsed_seconds: float


# ============================================================
# CREATE RUN-LOG RECORD
# ============================================================

def start_pipeline_run(
    connection: pyodbc.Connection,
    settings: PipelineSettings,
    operation: str
) -> int:
    """
    Create a RUNNING entry in PipelineRunLog.

    This record is committed before the main data operation
    begins so a failed operation remains visible in the log.
    """

    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            INSERT INTO {
                settings.run_log_full_name
            }
            (
                Operation,
                Status
            )
            OUTPUT
                INSERTED.RunId
            VALUES
            (
                ?,
                'RUNNING'
            );
            """,
            operation
        )

        run_id = int(
            cursor.fetchone()[0]
        )

        connection.commit()

        return run_id

    finally:

        cursor.close()


# ============================================================
# COMPLETE SUCCESSFUL RUN
# ============================================================

def complete_pipeline_run(
    connection: pyodbc.Connection,
    settings: PipelineSettings,
    run_id: int,
    prepared_rows: int,
    valid_rows: int,
    invalid_rows: int
) -> None:
    """
    Mark the pipeline run as successful.
    """

    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            UPDATE {
                settings.run_log_full_name
            }
            SET
                CompletedAt =
                    SYSUTCDATETIME(),

                Status =
                    'SUCCEEDED',

                PreparedRows =
                    ?,

                ValidRows =
                    ?,

                InvalidRows =
                    ?,

                ErrorMessage =
                    NULL

            WHERE RunId =
                ?;
            """,
            prepared_rows,
            valid_rows,
            invalid_rows,
            run_id
        )

        connection.commit()

    finally:

        cursor.close()


# ============================================================
# RECORD FAILED RUN
# ============================================================

def fail_pipeline_run(
    connection: pyodbc.Connection,
    settings: PipelineSettings,
    run_id: int,
    error_message: str
) -> None:
    """
    Mark the pipeline run as failed.
    """

    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            UPDATE {
                settings.run_log_full_name
            }
            SET
                CompletedAt =
                    SYSUTCDATETIME(),

                Status =
                    'FAILED',

                ErrorMessage =
                    ?

            WHERE RunId =
                ?;
            """,
            error_message[:4000],
            run_id
        )

        connection.commit()

    finally:

        cursor.close()


# ============================================================
# RUN FULL PREPARATION
# ============================================================

def prepare_all_declarations(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> PreparationResult:
    """
    Perform a complete rebuild of PreparedDeclarations.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    settings.validate()

    run_id = start_pipeline_run(
        connection=connection,
        settings=settings,
        operation="PREPARE_FULL"
    )

    started_at = datetime.now()

    cursor = connection.cursor()

    try:

        print(
            "=" * 70
        )

        print(
            "PREPARING DECLARATIONS IN SQL SERVER"
        )

        print(
            "=" * 70
        )

        print(
            "Source table:",
            settings.source_full_name
        )

        print(
            "Prepared table:",
            settings.prepared_full_name
        )

        print(
            "Import flow:",
            settings.import_flow_value
        )

        print(
            "Merchandise trade values:",
            ", ".join(
                settings.merchandise_trade_values
            )
        )

        print()

        preparation_sql = (
              build_full_preparation_sql(
        settings
        )
    )


# ============================================================
# SAVE THE GENERATED SQL FOR DEBUGGING
# ============================================================

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
            / "generated_preparation.sql"
        )

        debug_sql_path.parent.mkdir(
            parents=True,
            exist_ok=True
            )

        debug_sql_path.write_text(
            preparation_sql,
            encoding="utf-8"
            )

        print(
        "Generated SQL saved to:"
        )

        print(
        debug_sql_path
        )

        print()


# ============================================================
# EXECUTE THE GENERATED SQL
# ============================================================

        cursor.execute(
        preparation_sql
        )

        

        result_row = cursor.fetchone()

        if result_row is None:

            raise RuntimeError(
                "The preparation query did not return "
                "its expected summary result."
            )

        prepared_rows = int(
            result_row.PreparedRows
            or 0
        )

        valid_rows = int(
            result_row.ValidRows
            or 0
        )

        invalid_rows = int(
            result_row.InvalidRows
            or 0
        )

        valid_peer_groups = int(
            result_row.ValidPeerGroups
            or 0
        )

        connection.commit()

        elapsed_seconds = (
            datetime.now()
            - started_at
        ).total_seconds()

        complete_pipeline_run(
            connection=connection,
            settings=settings,
            run_id=run_id,
            prepared_rows=prepared_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows
        )

        print(
            "Declaration preparation completed."
        )

        print(
            "Prepared rows:",
            f"{prepared_rows:,}"
        )

        print(
            "Valid analytical rows:",
            f"{valid_rows:,}"
        )

        print(
            "Invalid analytical rows:",
            f"{invalid_rows:,}"
        )

        print(
            "Valid peer groups:",
            f"{valid_peer_groups:,}"
        )

        print(
            "Elapsed seconds:",
            f"{elapsed_seconds:,.1f}"
        )

        return PreparationResult(
            run_id=run_id,
            prepared_rows=prepared_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            valid_peer_groups=valid_peer_groups,
            elapsed_seconds=elapsed_seconds
        )

    except Exception as error:

        connection.rollback()

        try:

            fail_pipeline_run(
                connection=connection,
                settings=settings,
                run_id=run_id,
                error_message=str(error)
            )

        except Exception as logging_error:

            print(
                "The failed run could not be "
                "recorded in PipelineRunLog:"
            )

            print(
                logging_error
            )

        raise

    finally:

        cursor.close()