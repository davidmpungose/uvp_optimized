from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import pyodbc

from app.database.connection import database_connection
from app.database.results_schema_sql import (
    ResultStorageSettings,
    build_results_schema_sql,
)
from app.services.results_loading_service import (
    load_cluster_results,
    load_case_results,
    load_quarter_results,
)
from app.services.results_validation_service import (
    validate_stored_results,
    print_results_validation,
)
from config.settings import DatabaseSettings, PipelineSettings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage 8 permanent storage for clustering and case results."
    )
    parser.add_argument(
        "operation",
        choices=[
            "create-results-schema",
            "load-clusters",
            "load-risk-results",
            "load-quarter-results",
            "validate-results",
            "load-all-results",
        ],
    )
    parser.add_argument("--quarter", required=False)
    return parser


def require_quarter(parser: argparse.ArgumentParser, quarter: str | None) -> str:
    if not quarter:
        parser.error("--quarter is required for this operation.")
    return quarter


def create_schema(connection, pipeline, results):
    cursor = connection.cursor()
    try:
        cursor.execute(build_results_schema_sql(pipeline, results))
        connection.commit()
        print("Permanent result tables are ready.")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def available_quarters() -> list[str]:
    project_root = Path(__file__).resolve().parent
    risk_dir = project_root / "output" / "risk"
    return sorted(
        path.stem.replace("risk_results_", "")
        for path in risk_dir.glob("risk_results_*.parquet")
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    db = DatabaseSettings.from_environment()
    pipeline = PipelineSettings.from_environment()
    results = ResultStorageSettings.from_environment()

    with database_connection(db) as connection:
        if args.operation == "create-results-schema":
            create_schema(connection, pipeline, results)
            return

        if args.operation == "load-all-results":
            quarters = available_quarters()
            if not quarters:
                raise RuntimeError("No risk-result quarter files were found.")
            for number, quarter in enumerate(quarters, start=1):
                print(f"\nQuarter {number} of {len(quarters)}: {quarter}")
                load_quarter_results(connection, quarter, pipeline, results)
                print_results_validation(
                    validate_stored_results(connection, quarter, pipeline, results)
                )
            return

        quarter = require_quarter(parser, args.quarter)

        if args.operation == "load-clusters":
            load_cluster_results(connection, quarter, pipeline, results)
        elif args.operation == "load-risk-results":
            load_case_results(connection, quarter, pipeline, results)
        elif args.operation == "load-quarter-results":
            summary = load_quarter_results(connection, quarter, pipeline, results)
            print(summary)
        elif args.operation == "validate-results":
            print_results_validation(
                validate_stored_results(connection, quarter, pipeline, results)
            )


if __name__ == "__main__":
    try:
        main()
    except pyodbc.Error as error:
        print("\nSQL SERVER ERROR")
        print(error)
        traceback.print_exc()
        sys.exit(1)
    except Exception as error:
        print("\nAPPLICATION ERROR")
        print(error)
        traceback.print_exc()
        sys.exit(1)
