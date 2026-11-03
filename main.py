from __future__ import annotations

import argparse
import sys
import traceback

import pyodbc

from app.database.connection import (
    database_connection
)

from app.services.analytics_input_service import (
    list_analytical_quarters,
    load_analytical_quarter
)

from app.services.analytics_input_validation_service import (
    print_analytical_input_validation,
    validate_analytical_input
)

from app.services.benchmark_service import (
    build_original_benchmarks
)

from app.services.benchmark_validation_service import (
    get_benchmark_summary,
    get_ineligible_benchmark_summary,
    print_benchmark_validation
)

from app.analytics.clustering_service import (
    cluster_analytical_quarter
)

from app.analytics.clustering_validation_service import (
    print_cluster_validation,
    validate_cluster_output
)

from app.services.preparation_service import (
    prepare_all_declarations
)

from app.services.preparation_validation_service import (
    get_invalid_reason_summary,
    get_preparation_summary,
    print_preparation_validation
)

from app.services.schema_service import (
    create_analytics_schema,
    print_schema_verification,
    verify_analytics_schema
)

from app.services.risk_service import (
    score_clustered_quarter
)

from app.services.performance_test_service import (
    run_all_quarters_performance_test
)

from app.services.risk_validation_service import (
    print_risk_validation,
    validate_risk_output
)

from config.settings import (
    DatabaseSettings,
    PipelineSettings
)


# ============================================================
# ARGUMENT PARSER
# ============================================================

def build_argument_parser() -> argparse.ArgumentParser:
    """
    Create the command-line interface.

    Some operations work on the complete database, while
    quarter-level operations require --quarter.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Optimized Customs Valuation "
            "Analytics Platform"
        )
    )

    parser.add_argument(
        "--operation",
        choices=[
            "create-schema",
            "verify-schema",
            "prepare-full",
            "validate-preparation",
            "build-benchmarks",
            "validate-benchmarks",
            "list-quarters",
            "validate-analytical-input",
            "cluster-quarter",
            "validate-clustering",
            "score-quarter",
            "validate-risk",
            "performance-test"
        ],
        required=True,
        help=(
            "Select the pipeline operation to run."
        )
    )

    parser.add_argument(
        "--quarter",
        required=False,
        help=(
            "Quarter required by quarter-level operations. "
            "Use the format YYYY-QN, for example 2024-Q1."
        )
    )

    return parser


# ============================================================
# LOAD PROJECT SETTINGS
# ============================================================

def load_project_settings() -> tuple[
    DatabaseSettings,
    PipelineSettings
]:
    """
    Load the database and pipeline settings from .env.
    """

    database_settings = (
        DatabaseSettings
        .from_environment()
    )

    pipeline_settings = (
        PipelineSettings
        .from_environment()
    )

    pipeline_settings.validate()

    return (
        database_settings,
        pipeline_settings
    )


# ============================================================
# CREATE SCHEMA
# ============================================================

def run_create_schema() -> None:
    """
    Create and verify the analytical schema objects.
    """

    (
        database_settings,
        pipeline_settings
    ) = load_project_settings()

    with database_connection(
        database_settings
    ) as connection:

        create_analytics_schema(
            connection=connection,
            settings=pipeline_settings
        )

        verification = (
            verify_analytics_schema(
                connection=connection,
                settings=pipeline_settings
            )
        )

        print_schema_verification(
            verification
        )

        required_checks = [
            verification.get(
                "schema_exists",
                False
            ),

            verification.get(
                "run_log_table_exists",
                False
            ),

            verification.get(
                "prepared_table_exists",
                False
            ),

            verification.get(
                "benchmark_table_exists",
                False
            ),

            (
                verification.get(
                    "prepared_column_count",
                    0
                )
                >= 50
            ),

            (
                verification.get(
                    "prepared_index_count",
                    0
                )
                >= 1
            ),

            (
                verification.get(
                    "required_benchmark_columns",
                    0
                )
                == 16
            ),

            (
                verification.get(
                    "benchmark_index_count",
                    0
                )
                >= 1
            )
        ]

        if not all(
            required_checks
        ):

            failed_checks = []

            if not verification.get(
                "schema_exists",
                False
            ):
                failed_checks.append(
                    "analytics schema"
                )

            if not verification.get(
                "run_log_table_exists",
                False
            ):
                failed_checks.append(
                    "PipelineRunLog"
                )

            if not verification.get(
                "prepared_table_exists",
                False
            ):
                failed_checks.append(
                    "PreparedDeclarations"
                )

            if not verification.get(
                "benchmark_table_exists",
                False
            ):
                failed_checks.append(
                    "OriginalBenchmarks"
                )

            if (
                verification.get(
                    "prepared_column_count",
                    0
                )
                < 50
            ):
                failed_checks.append(
                    "PreparedDeclarations columns"
                )

            if (
                verification.get(
                    "prepared_index_count",
                    0
                )
                < 1
            ):
                failed_checks.append(
                    "PreparedDeclarations indexes"
                )

            if (
                verification.get(
                    "required_benchmark_columns",
                    0
                )
                != 16
            ):
                failed_checks.append(
                    "OriginalBenchmarks columns"
                )

            if (
                verification.get(
                    "benchmark_index_count",
                    0
                )
                < 1
            ):
                failed_checks.append(
                    "OriginalBenchmarks indexes"
                )

            raise RuntimeError(
                "Schema verification failed for: "
                + ", ".join(
                    failed_checks
                )
            )

        print()

        print(
            "=" * 70
        )

        print(
            "SCHEMA CREATION COMPLETED SUCCESSFULLY"
        )

        print(
            "=" * 70
        )


# ============================================================
# VERIFY SCHEMA
# ============================================================

def run_verify_schema() -> None:
    """
    Verify the analytical schema without changing it.
    """

    (
        database_settings,
        pipeline_settings
    ) = load_project_settings()

    with database_connection(
        database_settings
    ) as connection:

        verification = (
            verify_analytics_schema(
                connection=connection,
                settings=pipeline_settings
            )
        )

        print(
            "=" * 70
        )

        print(
            "VERIFYING ANALYTICS SCHEMA"
        )

        print(
            "=" * 70
        )

        print_schema_verification(
            verification
        )


# ============================================================
# PREPARE ALL DECLARATIONS
# ============================================================

def run_prepare_full() -> None:
    """
    Rebuild PreparedDeclarations from the complete source table.
    """

    (
        database_settings,
        pipeline_settings
    ) = load_project_settings()

    with database_connection(
        database_settings
    ) as connection:

        verification = (
            verify_analytics_schema(
                connection=connection,
                settings=pipeline_settings
            )
        )

        if not verification.get(
            "prepared_table_exists",
            False
        ):

            raise RuntimeError(
                "PreparedDeclarations does not exist. "
                "Run this command first:\n\n"
                "py main.py --operation create-schema"
            )

        prepare_all_declarations(
            connection=connection,
            settings=pipeline_settings
        )

        summary = (
            get_preparation_summary(
                connection=connection,
                settings=pipeline_settings
            )
        )

        invalid_reasons = (
            get_invalid_reason_summary(
                connection=connection,
                settings=pipeline_settings
            )
        )

        print()

        print_preparation_validation(
            summary=summary,
            invalid_reasons=invalid_reasons
        )

        if (
            summary.get(
                "prepared_rows",
                0
            )
            == 0
        ):

            raise RuntimeError(
                "No declarations were loaded into "
                "PreparedDeclarations."
            )


# ============================================================
# VALIDATE PREPARATION
# ============================================================

def run_validate_preparation() -> None:
    """
    Display preparation results without rebuilding the data.
    """

    (
        database_settings,
        pipeline_settings
    ) = load_project_settings()

    with database_connection(
        database_settings
    ) as connection:

        summary = (
            get_preparation_summary(
                connection=connection,
                settings=pipeline_settings
            )
        )

        invalid_reasons = (
            get_invalid_reason_summary(
                connection=connection,
                settings=pipeline_settings
            )
        )

        print_preparation_validation(
            summary=summary,
            invalid_reasons=invalid_reasons
        )


# ============================================================
# BUILD ORIGINAL BENCHMARKS
# ============================================================

def run_build_benchmarks() -> None:
    """
    Build original unit-value benchmarks from valid prepared
    declaration records.
    """

    (
        database_settings,
        pipeline_settings
    ) = load_project_settings()

    with database_connection(
        database_settings
    ) as connection:

        verification = (
            verify_analytics_schema(
                connection=connection,
                settings=pipeline_settings
            )
        )

        if not verification.get(
            "prepared_table_exists",
            False
        ):

            raise RuntimeError(
                "PreparedDeclarations does not exist. "
                "Run create-schema first."
            )

        if not verification.get(
            "benchmark_table_exists",
            False
        ):

            raise RuntimeError(
                "OriginalBenchmarks does not exist. "
                "Run create-schema first."
            )

        preparation_summary = (
            get_preparation_summary(
                connection=connection,
                settings=pipeline_settings
            )
        )

        valid_rows = int(
            preparation_summary.get(
                "valid_rows",
                0
            )
            or 0
        )

        if valid_rows == 0:

            raise RuntimeError(
                "There are no valid prepared rows. "
                "Run prepare-full and inspect the "
                "preparation validation results."
            )

        print(
            "=" * 70
        )

        print(
            "BUILDING ORIGINAL UNIT-VALUE BENCHMARKS"
        )

        print(
            "=" * 70
        )

        print(
            "Prepared table:",
            pipeline_settings.prepared_full_name
        )

        print(
            "Benchmark table:",
            pipeline_settings.benchmark_full_name
        )

        print(
            "Valid prepared rows:",
            f"{valid_rows:,}"
        )

        print(
            "Minimum peer count:",
            f"{pipeline_settings.minimum_peer_count:,}"
        )

        print()

        benchmark_result = (
            build_original_benchmarks(
                connection=connection,
                settings=pipeline_settings
            )
        )

        print(
            "Benchmark groups:",
            f"{benchmark_result.benchmark_groups:,}"
        )

        print(
            "Eligible groups:",
            f"{benchmark_result.eligible_groups:,}"
        )

        print(
            "Ineligible groups:",
            f"{benchmark_result.ineligible_groups:,}"
        )

        print(
            "Rows covered by eligible groups:",
            f"{benchmark_result.eligible_rows:,}"
        )

        print(
            "Elapsed seconds:",
            f"{benchmark_result.elapsed_seconds:,.1f}"
        )

        benchmark_summary = (
            get_benchmark_summary(
                connection=connection,
                settings=pipeline_settings
            )
        )

        ineligible_summary = (
            get_ineligible_benchmark_summary(
                connection=connection,
                settings=pipeline_settings
            )
        )

        print()

        print_benchmark_validation(
            summary=benchmark_summary,
            ineligible_summary=(
                ineligible_summary
            )
        )

        if (
            benchmark_summary.get(
                "benchmark_groups",
                0
            )
            == 0
        ):

            raise RuntimeError(
                "No benchmark groups were created."
            )

        print()

        print(
            "=" * 70
        )

        print(
            "BENCHMARK BUILD COMPLETED SUCCESSFULLY"
        )

        print(
            "=" * 70
        )


# ============================================================
# VALIDATE ORIGINAL BENCHMARKS
# ============================================================

def run_validate_benchmarks() -> None:
    """
    Display benchmark results without rebuilding them.
    """

    (
        database_settings,
        pipeline_settings
    ) = load_project_settings()

    with database_connection(
        database_settings
    ) as connection:

        verification = (
            verify_analytics_schema(
                connection=connection,
                settings=pipeline_settings
            )
        )

        if not verification.get(
            "benchmark_table_exists",
            False
        ):

            raise RuntimeError(
                "OriginalBenchmarks does not exist. "
                "Run create-schema first."
            )

        benchmark_summary = (
            get_benchmark_summary(
                connection=connection,
                settings=pipeline_settings
            )
        )

        ineligible_summary = (
            get_ineligible_benchmark_summary(
                connection=connection,
                settings=pipeline_settings
            )
        )

        print_benchmark_validation(
            summary=benchmark_summary,
            ineligible_summary=(
                ineligible_summary
            )
        )

        if (
            benchmark_summary.get(
                "benchmark_groups",
                0
            )
            == 0
        ):

            print()

            print(
                "No benchmark groups are currently stored."
            )

            print(
                "Run:"
            )

            print(
                "py main.py --operation build-benchmarks"
            )


# ============================================================
# LIST AVAILABLE QUARTERS
# ============================================================

def run_list_quarters() -> None:
    """
    Display quarters available for Python analytics.
    """

    (
        database_settings,
        pipeline_settings
    ) = load_project_settings()

    with database_connection(
        database_settings
    ) as connection:

        quarters = (
            list_analytical_quarters(
                connection=connection,
                settings=pipeline_settings
            )
        )

        print(
            "=" * 70
        )

        print(
            "AVAILABLE ANALYTICAL QUARTERS"
        )

        print(
            "=" * 70
        )

        for quarter in quarters:

            print(
                quarter
            )

        print()

        print(
            "Total quarters:",
            len(quarters)
        )

        print(
            "=" * 70
        )


# ============================================================
# VALIDATE QUARTER ANALYTICAL INPUT
# ============================================================

def run_validate_analytical_input(
    year_quarter: str
) -> None:
    """
    Load and validate benchmark-enriched data for one quarter.
    """

    (
        database_settings,
        pipeline_settings
    ) = load_project_settings()

    with database_connection(
        database_settings
    ) as connection:

        dataframe = (
            load_analytical_quarter(
                connection=connection,
                year_quarter=year_quarter,
                settings=pipeline_settings
            )
        )

        summary = (
            validate_analytical_input(
                dataframe
            )
        )

        print_analytical_input_validation(
            year_quarter=year_quarter,
            summary=summary
        )

        del dataframe


# ============================================================
# CLUSTER ONE QUARTER
# ============================================================

def run_cluster_quarter(
    year_quarter: str
) -> None:
    """
    Run price-segment clustering for one complete quarter.
    """

    (
        database_settings,
        pipeline_settings
    ) = load_project_settings()

    with database_connection(
        database_settings
    ) as connection:

        clustering_result = (
            cluster_analytical_quarter(
                connection=connection,
                year_quarter=year_quarter,
                pipeline_settings=(
                    pipeline_settings
                )
            )
        )

    validation = (
        validate_cluster_output(
            year_quarter
        )
    )

    print()

    print_cluster_validation(
        year_quarter=year_quarter,
        summary=validation
    )

    if (
        validation.get(
            "duplicate_prepared_ids",
            0
        )
        > 0
    ):

        raise RuntimeError(
            "Clustering output contains duplicate "
            "PreparedDeclarationId values."
        )

    if (
        validation.get(
            "invalid_cluster_quartiles",
            0
        )
        > 0
    ):

        raise RuntimeError(
            "One or more cluster quartiles are "
            "not logically ordered."
        )

    print()

    print(
        "Clustering file created:"
    )

    print(
        clustering_result.output_path
    )


# ============================================================
# VALIDATE CLUSTERING OUTPUT
# ============================================================

def run_validate_clustering(
    year_quarter: str
) -> None:
    """
    Validate an existing quarter-level clustering output file.
    """

    validation = (
        validate_cluster_output(
            year_quarter
        )
    )

    print_cluster_validation(
        year_quarter=year_quarter,
        summary=validation
    )

    if (
        validation.get(
            "duplicate_prepared_ids",
            0
        )
        > 0
    ):

        raise RuntimeError(
            "Clustering output contains duplicate "
            "PreparedDeclarationId values."
        )

    if (
        validation.get(
            "invalid_cluster_quartiles",
            0
        )
        > 0
    ):

        raise RuntimeError(
            "One or more cluster quartiles are "
            "not logically ordered."
        )


# ============================================================
# SCORE ONE QUARTER
# ============================================================

def run_score_quarter(
    year_quarter: str
) -> None:
    """
    Run risk scoring for a previously clustered quarter.
    """

    result = score_clustered_quarter(
        year_quarter=year_quarter
    )

    validation = validate_risk_output(
        year_quarter=year_quarter
    )

    print()

    print_risk_validation(
        year_quarter=year_quarter,
        summary=validation
    )

    if (
        validation[
            "duplicate_prepared_ids"
        ]
        > 0
    ):

        raise RuntimeError(
            "Risk output contains duplicate "
            "PreparedDeclarationId values."
        )

    if (
        validation[
            "invalid_scores"
        ]
        > 0
    ):

        raise RuntimeError(
            "Risk output contains scores outside "
            "the permitted 0 to 100 range."
        )

    if (
        validation[
            "negative_value_gaps"
        ]
        > 0
    ):

        raise RuntimeError(
            "Risk output contains negative "
            "potential value gaps."
        )

    print()

    print(
        "Risk-result file created:"
    )

    print(
        result.output_path
    )


# ============================================================
# VALIDATE QUARTER RISK OUTPUT
# ============================================================

def run_validate_risk(
    year_quarter: str
) -> None:
    """
    Validate an existing risk-result file without rerunning
    the scoring process.
    """

    validation = validate_risk_output(
        year_quarter=year_quarter
    )

    print_risk_validation(
        year_quarter=year_quarter,
        summary=validation
    )


# ============================================================
# FULL ANALYTICAL PERFORMANCE TEST
# ============================================================

def run_performance_test() -> None:
    """
    Test clustering and risk-scoring performance across all
    available quarters.
    """

    run_all_quarters_performance_test()
# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

def main() -> None:
    """
    Read the selected command and run the correct operation.

    Quarter-level operations are handled first because they
    require the additional --quarter argument.
    """

    parser = build_argument_parser()

    arguments = parser.parse_args()

    # ========================================================
    # OPERATIONS THAT REQUIRE --quarter
    # ========================================================

    quarter_operations = {
        "validate-analytical-input",
        "cluster-quarter",
        "validate-clustering",
        "score-quarter",
        "validate-risk"
    }

    if (
        arguments.operation
        in quarter_operations
    ):

        if not arguments.quarter:

            parser.error(
                "--quarter is required when using "
                f"--operation {arguments.operation}. "
                "Example: --quarter 2024-Q1"
            )

    if (
        arguments.operation
        == "validate-analytical-input"
    ):

        run_validate_analytical_input(
            year_quarter=arguments.quarter
        )

        return

    if (
        arguments.operation
        == "cluster-quarter"
    ):

        run_cluster_quarter(
            year_quarter=arguments.quarter
        )

        return

    if (
        arguments.operation
        == "validate-clustering"
    ):

        run_validate_clustering(
            year_quarter=arguments.quarter
        )

        return

    if (
        arguments.operation
        == "score-quarter"
    ):

        run_score_quarter(
            year_quarter=arguments.quarter
        )

        return

    if (
        arguments.operation
        == "validate-risk"
    ):

        run_validate_risk (
            year_quarter=arguments.quarter
        )

        return

    # ========================================================
    # OPERATIONS THAT DO NOT REQUIRE --quarter
    # ========================================================

    operation_handlers = {
        "create-schema":
            run_create_schema,

        "verify-schema":
            run_verify_schema,

        "prepare-full":
            run_prepare_full,

        "validate-preparation":
            run_validate_preparation,

        "build-benchmarks":
            run_build_benchmarks,

        "validate-benchmarks":
            run_validate_benchmarks,

        "list-quarters":
            run_list_quarters,

        "performance-test":
    run_performance_test
    }

    operation_handler = (
        operation_handlers.get(
            arguments.operation
        )
    )

    if operation_handler is None:

        raise ValueError(
            "No operation handler has been defined for: "
            f"{arguments.operation}"
        )

    operation_handler()


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

    except KeyboardInterrupt:

        print()

        print(
            "Operation cancelled by the user."
        )

        sys.exit(130)

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