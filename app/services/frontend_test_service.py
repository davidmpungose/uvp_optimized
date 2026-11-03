from __future__ import annotations

import argparse
import json
import os

from datetime import date
from datetime import datetime

from decimal import Decimal

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

FRONTEND_DIRECTORY = (
    PROJECT_ROOT
    / "frontend"
)

FRONTEND_DATA_DIRECTORY = (
    FRONTEND_DIRECTORY
    / "data"
)

DEFAULT_OUTPUT_FILE = (
    FRONTEND_DATA_DIRECTORY
    / "test_dashboard_data.json"
)


# ============================================================
# PATH HELPERS
# ============================================================

def get_risk_output_directory() -> Path:
    """
    Return the configured risk-output directory.
    """

    configured_directory = os.getenv(
        "RISK_OUTPUT_DIRECTORY",
        "output/risk"
    ).strip()

    return (
        PROJECT_ROOT
        / configured_directory
    )


def get_risk_result_path(
    year_quarter: str
) -> Path:
    """
    Return the expected risk-result file for one quarter.

    Example:

        output/risk/risk_results_2024-Q1.parquet
    """

    safe_quarter = year_quarter.replace(
        "/",
        "-"
    )

    return (
        get_risk_output_directory()
        / f"risk_results_{safe_quarter}.parquet"
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def first_available_column(
    dataframe: pd.DataFrame,
    candidates: list[str]
) -> str | None:
    """
    Return the first available column from a candidate list.
    """

    for column_name in candidates:

        if column_name in dataframe.columns:

            return column_name

    return None


def safe_numeric_series(
    dataframe: pd.DataFrame,
    column_name: str | None,
    default: float = 0
) -> pd.Series:
    """
    Return a numeric pandas Series.

    If the requested column does not exist, return a Series
    containing the default value.
    """

    if (
        column_name is None
        or column_name not in dataframe.columns
    ):

        return pd.Series(
            default,
            index=dataframe.index,
            dtype="float64"
        )

    return (
        pd.to_numeric(
            dataframe[column_name],
            errors="coerce"
        )
        .fillna(default)
    )


def safe_text_series(
    dataframe: pd.DataFrame,
    column_name: str | None,
    default: str = ""
) -> pd.Series:
    """
    Return a text pandas Series.

    Missing values are converted into the supplied default.
    """

    if (
        column_name is None
        or column_name not in dataframe.columns
    ):

        return pd.Series(
            default,
            index=dataframe.index,
            dtype="object"
        )

    return (
        dataframe[column_name]
        .fillna(default)
        .astype(str)
    )


def safe_boolean_series(
    dataframe: pd.DataFrame,
    column_name: str | None,
    default: bool = False
) -> pd.Series:
    """
    Return a boolean pandas Series.
    """

    if (
        column_name is None
        or column_name not in dataframe.columns
    ):

        return pd.Series(
            default,
            index=dataframe.index,
            dtype="bool"
        )

    series = dataframe[
        column_name
    ]

    if pd.api.types.is_bool_dtype(
        series
    ):

        return (
            series
            .fillna(default)
            .astype(bool)
        )

    normalized = (
        series
        .fillna(default)
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return normalized.isin(
        {
            "1",
            "true",
            "yes",
            "y"
        }
    )


def normalize_datetime_value(
    value: object
) -> str | None:
    """
    Convert a date-like value into an ISO formatted string.
    """

    if value is None:

        return None

    if pd.isna(value):

        return None

    if isinstance(
        value,
        pd.Timestamp
    ):

        return value.isoformat()

    if isinstance(
        value,
        (
            datetime,
            date
        )
    ):

        return value.isoformat()

    return str(value)


def json_safe_value(
    value: object
) -> object:
    """
    Convert pandas, NumPy, Decimal and date values into values
    supported by Python's JSON encoder.
    """

    if value is None:

        return None

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
            date
        )
    ):

        return value.isoformat()

    if isinstance(
        value,
        Decimal
    ):

        return float(value)

    if isinstance(
        value,
        np.integer
    ):

        return int(value)

    if isinstance(
        value,
        np.floating
    ):

        if np.isnan(value):

            return None

        if np.isinf(value):

            return None

        return float(value)

    if isinstance(
        value,
        np.bool_
    ):

        return bool(value)

    try:

        if pd.isna(value):

            return None

    except (
        TypeError,
        ValueError
    ):

        pass

    return value


def records_to_json_safe(
    dataframe: pd.DataFrame
) -> list[dict[str, object]]:
    """
    Convert a DataFrame into JSON-safe records.
    """

    records = dataframe.to_dict(
        orient="records"
    )

    clean_records = []

    for record in records:

        clean_record = {
            key:
                json_safe_value(
                    value
                )
            for key, value
            in record.items()
        }

        clean_records.append(
            clean_record
        )

    return clean_records


# ============================================================
# PREPARE STANDARD DASHBOARD COLUMNS
# ============================================================

def standardize_dashboard_columns(
    dataframe: pd.DataFrame,
    year_quarter: str
) -> pd.DataFrame:
    """
    Create a consistent set of frontend columns from the
    quarter risk-result file.
    """

    output = dataframe.copy()

    registration_date_column = (
        first_available_column(
            output,
            [
                "RegistrationDate",
                "DATE",
                "DeclarationDate"
            ]
        )
    )

    declaration_reference_column = (
        first_available_column(
            output,
            [
                "FormNumber",
                "DECLARATION_REFERENCE",
                "DeclarationReference"
            ]
        )
    )

    trader_tin_column = (
        first_available_column(
            output,
            [
                "Traders",
                "TIN",
                "TraderTin"
            ]
        )
    )

    trader_name_column = (
        first_available_column(
            output,
            [
                "Lib_Traders",
                "TRADER_NAME",
                "TraderName"
            ]
        )
    )

    hs_column = first_available_column(
        output,
        [
            "HS",
            "HSCode"
        ]
    )

    hs_description_column = (
        first_available_column(
            output,
            [
                "Lib_HS8",
                "HSDescription",
                "LIB_HS8"
            ]
        )
    )

    selected_quantity_column = (
        first_available_column(
            output,
            [
                "SelectedQuantity",
                "SELECTED_QUANTITY"
            ]
        )
    )

    selected_unit_column = (
        first_available_column(
            output,
            [
                "SelectedUnit",
                "SU",
                "SELECTED_UNIT"
            ]
        )
    )

    output[
        "DashboardQuarter"
    ] = year_quarter

    if registration_date_column:

        output[
            "DashboardDate"
        ] = output[
            registration_date_column
        ].map(
            normalize_datetime_value
        )

    else:

        output[
            "DashboardDate"
        ] = None

    output[
        "DashboardDeclarationReference"
    ] = safe_text_series(
        output,
        declaration_reference_column,
        default=""
    )

    output[
        "DashboardTraderTin"
    ] = safe_text_series(
        output,
        trader_tin_column,
        default=""
    )

    output[
        "DashboardTraderName"
    ] = safe_text_series(
        output,
        trader_name_column,
        default=""
    )

    output[
        "DashboardHS"
    ] = safe_text_series(
        output,
        hs_column,
        default=""
    )

    output[
        "DashboardHSDescription"
    ] = safe_text_series(
        output,
        hs_description_column,
        default=""
    )

    output[
        "DashboardSelectedQuantity"
    ] = safe_numeric_series(
        output,
        selected_quantity_column
    )

    output[
        "DashboardSelectedUnit"
    ] = safe_text_series(
        output,
        selected_unit_column,
        default=""
    )

    numeric_columns = [
        "FOBValue",
        "UnitValue",
        "OriginalQ1",
        "OriginalMedian",
        "OriginalQ3",
        "ClusterQ1",
        "ClusterMedian",
        "ClusterQ3",
        "FinalBenchmarkQ1",
        "FinalDeviationPercent",
        "PotentialValueGap",
        "CaseRiskScore",
        "PeerCount",
        "ClusterPeerCount",
        "ClusterSilhouetteScore"
    ]

    for column_name in numeric_columns:

        if column_name not in output.columns:

            output[column_name] = 0

        output[column_name] = (
            pd.to_numeric(
                output[column_name],
                errors="coerce"
            )
            .fillna(0)
        )

    text_columns = [
        "FinalBenchmarkMethod",
        "ModelAgreement",
        "CaseRiskLevel",
        "CaseReason",
        "ClusterPriceTier",
        "ClusterEligibilityReason",
        "ModelVersion",
        "PeerKey"
    ]

    for column_name in text_columns:

        if column_name not in output.columns:

            output[column_name] = ""

        output[column_name] = (
            output[column_name]
            .fillna("")
            .astype(str)
        )

    output[
        "IsPotentialCase"
    ] = safe_boolean_series(
        output,
        "IsPotentialCase"
    )

    output[
        "ClusterApplied"
    ] = safe_boolean_series(
        output,
        "ClusterApplied"
    )

    output[
        "OriginalFlag"
    ] = safe_boolean_series(
        output,
        "OriginalFlag"
    )

    output[
        "ClusterFlag"
    ] = safe_boolean_series(
        output,
        "ClusterFlag"
    )

    return output


# ============================================================
# KPI CREATION
# ============================================================

def create_dashboard_kpis(
    dataframe: pd.DataFrame
) -> dict[str, object]:
    """
    Create the main dashboard summary indicators.
    """

    potential_case_mask = (
        dataframe[
            "IsPotentialCase"
        ]
        .fillna(False)
        .astype(bool)
    )

    potential_cases = dataframe.loc[
        potential_case_mask
    ]

    risk_level_counts = (
        potential_cases[
            "CaseRiskLevel"
        ]
        .value_counts()
    )

    clustered_groups = (
        dataframe.loc[
            dataframe[
                "ClusterApplied"
            ],
            "PeerKey"
        ]
        .nunique(
            dropna=True
        )
    )

    total_peer_groups = (
        dataframe[
            "PeerKey"
        ]
        .nunique(
            dropna=True
        )
    )

    return {
        "rowsScored":
            int(
                len(
                    dataframe
                )
            ),

        "potentialCases":
            int(
                len(
                    potential_cases
                )
            ),

        "highRiskCases":
            int(
                risk_level_counts.get(
                    "High Risk",
                    0
                )
            ),

        "mediumRiskCases":
            int(
                risk_level_counts.get(
                    "Medium Risk",
                    0
                )
            ),

        "lowRiskCases":
            int(
                risk_level_counts.get(
                    "Low Risk",
                    0
                )
            ),

        "totalPotentialValueGap":
            float(
                potential_cases[
                    "PotentialValueGap"
                ]
                .sum()
            ),

        "averageRiskScore":
            (
                float(
                    potential_cases[
                        "CaseRiskScore"
                    ]
                    .mean()
                )
                if not potential_cases.empty
                else 0
            ),

        "maximumRiskScore":
            float(
                dataframe[
                    "CaseRiskScore"
                ]
                .max()
            ),

        "uniqueTraders":
            int(
                potential_cases[
                    "DashboardTraderTin"
                ]
                .replace(
                    "",
                    np.nan
                )
                .nunique(
                    dropna=True
                )
            ),

        "uniqueHS":
            int(
                potential_cases[
                    "DashboardHS"
                ]
                .replace(
                    "",
                    np.nan
                )
                .nunique(
                    dropna=True
                )
            ),

        "peerGroups":
            int(
                total_peer_groups
            ),

        "clusteredGroups":
            int(
                clustered_groups
            )
    }


# ============================================================
# DISTRIBUTION CREATORS
# ============================================================

def create_count_distribution(
    dataframe: pd.DataFrame,
    column_name: str,
    default_label: str = "Unknown"
) -> list[dict[str, object]]:
    """
    Create a simple category and count distribution.
    """

    if column_name not in dataframe.columns:

        return []

    counts = (
        dataframe[
            column_name
        ]
        .fillna(
            default_label
        )
        .replace(
            "",
            default_label
        )
        .astype(str)
        .value_counts()
    )

    return [
        {
            "label":
                str(
                    label
                ),

            "value":
                int(
                    value
                )
        }
        for label, value
        in counts.items()
    ]


def create_value_distribution(
    dataframe: pd.DataFrame,
    category_column: str,
    value_column: str,
    default_label: str = "Unknown"
) -> list[dict[str, object]]:
    """
    Sum a numeric value by a category.
    """

    if (
        category_column not in dataframe.columns
        or value_column not in dataframe.columns
    ):

        return []

    grouped = (
        dataframe.assign(
            _category=(
                dataframe[
                    category_column
                ]
                .fillna(
                    default_label
                )
                .replace(
                    "",
                    default_label
                )
                .astype(str)
            ),

            _value=pd.to_numeric(
                dataframe[
                    value_column
                ],
                errors="coerce"
            ).fillna(0)
        )
        .groupby(
            "_category",
            dropna=False
        )["_value"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    return [
        {
            "label":
                str(
                    label
                ),

            "value":
                float(
                    value
                )
        }
        for label, value
        in grouped.items()
    ]


# ============================================================
# TOP CASES
# ============================================================

def create_top_cases(
    dataframe: pd.DataFrame,
    maximum_cases: int
) -> list[dict[str, object]]:
    """
    Create the potential-case table shown in the browser.
    """

    potential_cases = dataframe.loc[
        dataframe[
            "IsPotentialCase"
        ]
    ].copy()

    potential_cases.sort_values(
        by=[
            "CaseRiskScore",
            "PotentialValueGap"
        ],
        ascending=[
            False,
            False
        ],
        inplace=True
    )

    potential_cases = (
        potential_cases
        .head(
            maximum_cases
        )
        .copy()
    )

    potential_cases[
        "DashboardRank"
    ] = range(
        1,
        len(
            potential_cases
        )
        + 1
    )

    case_columns = [
        "DashboardRank",
        "PreparedDeclarationId",
        "DashboardDate",
        "DashboardDeclarationReference",
        "DashboardTraderTin",
        "DashboardTraderName",
        "DashboardHS",
        "DashboardHSDescription",
        "DashboardSelectedQuantity",
        "DashboardSelectedUnit",
        "FOBValue",
        "UnitValue",
        "OriginalQ1",
        "OriginalMedian",
        "OriginalQ3",
        "ClusterQ1",
        "ClusterMedian",
        "ClusterQ3",
        "FinalBenchmarkQ1",
        "FinalBenchmarkMethod",
        "FinalDeviationPercent",
        "PotentialValueGap",
        "CaseRiskScore",
        "CaseRiskLevel",
        "ModelAgreement",
        "CaseReason",
        "PeerKey",
        "PeerCount",
        "ClusterApplied",
        "ClusterPriceTier",
        "ClusterPeerCount",
        "ClusterSilhouetteScore",
        "ClusterEligibilityReason",
        "OriginalFlag",
        "ClusterFlag",
        "ModelVersion"
    ]

    available_columns = [
        column_name
        for column_name in case_columns
        if column_name in potential_cases.columns
    ]

    return records_to_json_safe(
        potential_cases[
            available_columns
        ]
    )


# ============================================================
# FILTER OPTIONS
# ============================================================

def create_filter_options(
    dataframe: pd.DataFrame
) -> dict[str, list[str]]:
    """
    Create the dropdown values required by the frontend.
    """

    potential_cases = dataframe.loc[
        dataframe[
            "IsPotentialCase"
        ]
    ]

    def unique_values(
        column_name: str
    ) -> list[str]:

        if column_name not in potential_cases.columns:

            return []

        return sorted(
            value
            for value in (
                potential_cases[
                    column_name
                ]
                .fillna("")
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )
            if value
        )

    return {
        "riskLevels":
            unique_values(
                "CaseRiskLevel"
            ),

        "benchmarkMethods":
            unique_values(
                "FinalBenchmarkMethod"
            ),

        "modelAgreements":
            unique_values(
                "ModelAgreement"
            ),

        "hsCodes":
            unique_values(
                "DashboardHS"
            )
    }


# ============================================================
# TOP HS SUMMARY
# ============================================================

def create_top_hs_summary(
    dataframe: pd.DataFrame,
    maximum_rows: int = 15
) -> list[dict[str, object]]:
    """
    Create an HS-level case summary.
    """

    cases = dataframe.loc[
        dataframe[
            "IsPotentialCase"
        ]
    ].copy()

    if cases.empty:

        return []

    summary = (
        cases.groupby(
            [
                "DashboardHS",
                "DashboardHSDescription"
            ],
            dropna=False
        )
        .agg(
            PotentialCases=(
                "PreparedDeclarationId",
                "count"
            ),

            TotalPotentialValueGap=(
                "PotentialValueGap",
                "sum"
            ),

            AverageRiskScore=(
                "CaseRiskScore",
                "mean"
            ),

            MaximumRiskScore=(
                "CaseRiskScore",
                "max"
            )
        )
        .reset_index()
        .sort_values(
            by=[
                "TotalPotentialValueGap",
                "PotentialCases"
            ],
            ascending=[
                False,
                False
            ]
        )
        .head(
            maximum_rows
        )
    )

    return records_to_json_safe(
        summary
    )


# ============================================================
# TOP TRADER SUMMARY
# ============================================================

def create_top_trader_summary(
    dataframe: pd.DataFrame,
    maximum_rows: int = 15
) -> list[dict[str, object]]:
    """
    Create a trader-level case summary.
    """

    cases = dataframe.loc[
        dataframe[
            "IsPotentialCase"
        ]
    ].copy()

    if cases.empty:

        return []

    summary = (
        cases.groupby(
            [
                "DashboardTraderTin",
                "DashboardTraderName"
            ],
            dropna=False
        )
        .agg(
            PotentialCases=(
                "PreparedDeclarationId",
                "count"
            ),

            UniqueHS=(
                "DashboardHS",
                "nunique"
            ),

            TotalPotentialValueGap=(
                "PotentialValueGap",
                "sum"
            ),

            AverageRiskScore=(
                "CaseRiskScore",
                "mean"
            ),

            MaximumRiskScore=(
                "CaseRiskScore",
                "max"
            )
        )
        .reset_index()
        .sort_values(
            by=[
                "TotalPotentialValueGap",
                "PotentialCases"
            ],
            ascending=[
                False,
                False
            ]
        )
        .head(
            maximum_rows
        )
    )

    return records_to_json_safe(
        summary
    )


# ============================================================
# BUILD DASHBOARD DATA
# ============================================================

def build_frontend_test_data(
    year_quarter: str,
    maximum_cases: int = 5000,
    output_path: Path | None = None
) -> Path:
    """
    Build the complete JSON file used by the test frontend.
    """

    if maximum_cases < 1:

        raise ValueError(
            "maximum_cases must be at least 1."
        )

    risk_result_path = (
        get_risk_result_path(
            year_quarter
        )
    )

    if not risk_result_path.exists():

        raise FileNotFoundError(
            "The risk-result file does not exist:\n"
            f"{risk_result_path}\n\n"
            "Run the following commands first:\n\n"
            "py main.py --operation cluster-quarter "
            f"--quarter {year_quarter}\n\n"
            "py main.py --operation score-quarter "
            f"--quarter {year_quarter}"
        )

    print(
        "=" * 70
    )

    print(
        "BUILDING FRONTEND TEST DATA"
    )

    print(
        "=" * 70
    )

    print(
        "Quarter:",
        year_quarter
    )

    print(
        "Risk-result file:",
        risk_result_path
    )

    print()

    risk_results = pd.read_parquet(
        risk_result_path
    )

    required_columns = {
        "PreparedDeclarationId",
        "IsPotentialCase",
        "CaseRiskScore",
        "CaseRiskLevel",
        "PotentialValueGap"
    }

    missing_columns = sorted(
        required_columns
        - set(
            risk_results.columns
        )
    )

    if missing_columns:

        raise RuntimeError(
            "The risk-result file is missing required "
            "columns: "
            + ", ".join(
                missing_columns
            )
        )

    dashboard_data = (
        standardize_dashboard_columns(
            dataframe=risk_results,
            year_quarter=year_quarter
        )
    )

    potential_cases = dashboard_data.loc[
        dashboard_data[
            "IsPotentialCase"
        ]
    ]

    dashboard_payload = {
        "metadata": {
            "title":
                "Undervaluation Risk Intelligence",

            "subtitle":
                "Model Results Validation",

            "quarter":
                year_quarter,

            "generatedAt":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "riskResultFile":
                str(
                    risk_result_path
                ),

            "maximumCasesIncluded":
                int(
                    maximum_cases
                ),

            "casesAvailable":
                int(
                    len(
                        potential_cases
                    )
                )
        },

        "kpis":
            create_dashboard_kpis(
                dashboard_data
            ),

        "riskDistribution":
            create_count_distribution(
                potential_cases,
                "CaseRiskLevel"
            ),

        "modelAgreementDistribution":
            create_count_distribution(
                potential_cases,
                "ModelAgreement"
            ),

        "benchmarkMethodDistribution":
            create_count_distribution(
                potential_cases,
                "FinalBenchmarkMethod"
            ),

        "riskValueGapDistribution":
            create_value_distribution(
                potential_cases,
                "CaseRiskLevel",
                "PotentialValueGap"
            ),

        "topCases":
            create_top_cases(
                dashboard_data,
                maximum_cases=maximum_cases
            ),

        "topHS":
            create_top_hs_summary(
                dashboard_data
            ),

        "topTraders":
            create_top_trader_summary(
                dashboard_data
            ),

        "filters":
            create_filter_options(
                dashboard_data
            )
    }

    if output_path is None:

        output_path = (
            DEFAULT_OUTPUT_FILE
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        json.dumps(
            dashboard_payload,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(
        "Rows scored:",
        f"{len(dashboard_data):,}"
    )

    print(
        "Potential cases:",
        f"{len(potential_cases):,}"
    )

    print(
        "Cases written to JSON:",
        f"{len(dashboard_payload['topCases']):,}"
    )

    print(
        "Dashboard data created:"
    )

    print(
        output_path
    )

    print(
        "=" * 70
    )

    return output_path


# ============================================================
# COMMAND LINE
# ============================================================

def build_argument_parser() -> argparse.ArgumentParser:
    """
    Create the standalone command-line parser.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Build the model-results frontend test data."
        )
    )

    parser.add_argument(
        "--quarter",
        required=True,
        help=(
            "Quarter to build, for example 2024-Q1."
        )
    )

    parser.add_argument(
        "--maximum-cases",
        type=int,
        default=5000,
        help=(
            "Maximum potential cases included in the JSON file."
        )
    )

    return parser


def main() -> None:
    """
    Build the frontend test data.
    """

    parser = build_argument_parser()

    arguments = parser.parse_args()

    build_frontend_test_data(
        year_quarter=arguments.quarter,
        maximum_cases=arguments.maximum_cases
    )


if __name__ == "__main__":

    main()