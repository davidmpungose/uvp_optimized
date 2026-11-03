from __future__ import annotations

import argparse
import json
import os
import re
import time

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

QUARTER_DATA_DIRECTORY = (
    FRONTEND_DATA_DIRECTORY
    / "quarters"
)

MANIFEST_PATH = (
    FRONTEND_DATA_DIRECTORY
    / "dashboard_manifest.json"
)


# ============================================================
# RISK-RESULT DIRECTORY
# ============================================================

def get_risk_output_directory() -> Path:
    """
    Return the directory containing quarterly risk Parquet files.
    """

    configured_directory = os.getenv(
        "RISK_OUTPUT_DIRECTORY",
        "output/risk"
    ).strip()

    return (
        PROJECT_ROOT
        / configured_directory
    )


# ============================================================
# QUARTER HELPERS
# ============================================================

def extract_quarter_from_filename(
    file_path: Path
) -> str:
    """
    Extract YYYY-QN from a risk-result filename.

    Expected example:
        risk_results_2024-Q1.parquet
    """

    match = re.search(
        r"risk_results_(\d{4}-Q[1-4])\.parquet$",
        file_path.name,
        flags=re.IGNORECASE
    )

    if not match:

        raise ValueError(
            "Could not identify a quarter from: "
            f"{file_path.name}"
        )

    return match.group(1).upper()


def quarter_sort_key(
    year_quarter: str
) -> tuple[int, int]:
    """
    Convert YYYY-QN into a sortable tuple.
    """

    match = re.fullmatch(
        r"(\d{4})-Q([1-4])",
        year_quarter
    )

    if not match:

        return (
            0,
            0
        )

    return (
        int(
            match.group(1)
        ),
        int(
            match.group(2)
        )
    )


# ============================================================
# SAFE DATA CONVERSION
# ============================================================

def json_safe_value(
    value: object
) -> object:
    """
    Convert pandas, NumPy, Decimal and date values into JSON.
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

        if (
            np.isnan(value)
            or np.isinf(value)
        ):

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
    Convert DataFrame records into JSON-safe dictionaries.
    """

    raw_records = dataframe.to_dict(
        orient="records"
    )

    return [
        {
            key:
                json_safe_value(
                    value
                )
            for key, value
            in record.items()
        }
        for record in raw_records
    ]


def first_available_column(
    dataframe: pd.DataFrame,
    candidates: list[str]
) -> str | None:
    """
    Return the first available column name.
    """

    for column_name in candidates:

        if column_name in dataframe.columns:

            return column_name

    return None


def safe_text_series(
    dataframe: pd.DataFrame,
    column_name: str | None
) -> pd.Series:
    """
    Return a safe text Series.
    """

    if (
        column_name is None
        or column_name not in dataframe.columns
    ):

        return pd.Series(
            "",
            index=dataframe.index,
            dtype="object"
        )

    return (
        dataframe[column_name]
        .fillna("")
        .astype(str)
    )


def safe_numeric_series(
    dataframe: pd.DataFrame,
    column_name: str | None
) -> pd.Series:
    """
    Return a safe numeric Series.
    """

    if (
        column_name is None
        or column_name not in dataframe.columns
    ):

        return pd.Series(
            0,
            index=dataframe.index,
            dtype="float64"
        )

    return (
        pd.to_numeric(
            dataframe[column_name],
            errors="coerce"
        )
        .fillna(0)
    )


def safe_boolean_series(
    dataframe: pd.DataFrame,
    column_name: str
) -> pd.Series:
    """
    Return a safe boolean Series.
    """

    if column_name not in dataframe.columns:

        return pd.Series(
            False,
            index=dataframe.index,
            dtype="bool"
        )

    series = dataframe[column_name]

    if pd.api.types.is_bool_dtype(
        series
    ):

        return (
            series
            .fillna(False)
            .astype(bool)
        )

    return (
        series
        .fillna(False)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(
            {
                "1",
                "true",
                "yes",
                "y"
            }
        )
    )


def normalize_date_value(
    value: object
) -> str | None:
    """
    Convert date-like values into ISO strings.
    """

    if value is None:

        return None

    try:

        if pd.isna(value):

            return None

    except (
        TypeError,
        ValueError
    ):

        pass

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
            date
        )
    ):

        return value.isoformat()

    return str(value)


# ============================================================
# STANDARDISE DASHBOARD COLUMNS
# ============================================================

def standardize_dashboard_columns(
    dataframe: pd.DataFrame,
    year_quarter: str
) -> pd.DataFrame:
    """
    Create consistent frontend column names.
    """

    output = dataframe.copy()

    date_column = first_available_column(
        output,
        [
            "RegistrationDate",
            "DeclarationDate",
            "DATE"
        ]
    )

    declaration_column = first_available_column(
        output,
        [
            "FormNumber",
            "DeclarationReference",
            "DECLARATION_REFERENCE"
        ]
    )

    trader_tin_column = first_available_column(
        output,
        [
            "Traders",
            "TIN",
            "TraderTin"
        ]
    )

    trader_name_column = first_available_column(
        output,
        [
            "Lib_Traders",
            "TraderName",
            "TRADER_NAME"
        ]
    )

    hs_column = first_available_column(
        output,
        [
            "HS",
            "HSCode"
        ]
    )

    hs_description_column = first_available_column(
        output,
        [
            "Lib_HS8",
            "HSDescription",
            "LIB_HS8"
        ]
    )

    quantity_column = first_available_column(
        output,
        [
            "SelectedQuantity",
            "SELECTED_QUANTITY"
        ]
    )

    unit_column = first_available_column(
        output,
        [
            "SelectedUnit",
            "SU",
            "SELECTED_UNIT"
        ]
    )

    output[
        "DashboardQuarter"
    ] = year_quarter

    if date_column:

        output[
            "DashboardDate"
        ] = output[
            date_column
        ].map(
            normalize_date_value
        )

    else:

        output[
            "DashboardDate"
        ] = None

    output[
        "DashboardDeclarationReference"
    ] = safe_text_series(
        output,
        declaration_column
    )

    output[
        "DashboardTraderTin"
    ] = safe_text_series(
        output,
        trader_tin_column
    )

    output[
        "DashboardTraderName"
    ] = safe_text_series(
        output,
        trader_name_column
    )

    output[
        "DashboardHS"
    ] = safe_text_series(
        output,
        hs_column
    )

    output[
        "DashboardHSDescription"
    ] = safe_text_series(
        output,
        hs_description_column
    )

    output[
        "DashboardSelectedQuantity"
    ] = safe_numeric_series(
        output,
        quantity_column
    )

    output[
        "DashboardSelectedUnit"
    ] = safe_text_series(
        output,
        unit_column
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

    boolean_columns = [
        "IsPotentialCase",
        "ClusterApplied",
        "OriginalFlag",
        "ClusterFlag"
    ]

    for column_name in boolean_columns:

        output[column_name] = (
            safe_boolean_series(
                output,
                column_name
            )
        )

    return output


# ============================================================
# KPI AND DISTRIBUTION HELPERS
# ============================================================

def create_count_distribution(
    dataframe: pd.DataFrame,
    column_name: str
) -> list[dict[str, object]]:
    """
    Count records by category.
    """

    if column_name not in dataframe.columns:

        return []

    counts = (
        dataframe[column_name]
        .fillna("Unknown")
        .replace(
            "",
            "Unknown"
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


def create_quarter_kpis(
    dataframe: pd.DataFrame
) -> dict[str, object]:
    """
    Create quarterly headline figures.
    """

    cases = dataframe.loc[
        dataframe[
            "IsPotentialCase"
        ]
    ]

    risk_counts = (
        cases[
            "CaseRiskLevel"
        ]
        .value_counts()
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
                    cases
                )
            ),

        "highRiskCases":
            int(
                risk_counts.get(
                    "High Risk",
                    0
                )
            ),

        "mediumRiskCases":
            int(
                risk_counts.get(
                    "Medium Risk",
                    0
                )
            ),

        "lowRiskCases":
            int(
                risk_counts.get(
                    "Low Risk",
                    0
                )
            ),

        "totalPotentialValueGap":
            float(
                cases[
                    "PotentialValueGap"
                ]
                .sum()
            ),

        "averageRiskScore":
            (
                float(
                    cases[
                        "CaseRiskScore"
                    ]
                    .mean()
                )
                if not cases.empty
                else 0
            ),

        "maximumRiskScore":
            float(
                dataframe[
                    "CaseRiskScore"
                ]
                .max()
            )
    }


# ============================================================
# TOP CASES
# ============================================================

def create_top_cases(
    dataframe: pd.DataFrame,
    maximum_cases: int
) -> list[dict[str, object]]:
    """
    Return the highest-priority cases for browser display.
    """

    cases = dataframe.loc[
        dataframe[
            "IsPotentialCase"
        ]
    ].copy()

    cases.sort_values(
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

    cases = cases.head(
        maximum_cases
    ).copy()

    cases[
        "DashboardRank"
    ] = range(
        1,
        len(
            cases
        )
        + 1
    )

    requested_columns = [
        "DashboardRank",
        "PreparedDeclarationId",
        "DashboardQuarter",
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
        for column_name in requested_columns
        if column_name in cases.columns
    ]

    return records_to_json_safe(
        cases[
            available_columns
        ]
    )


# ============================================================
# TOP HS SUMMARY
# ============================================================

def create_top_hs_summary(
    dataframe: pd.DataFrame,
    maximum_rows: int = 15
) -> list[dict[str, object]]:
    """
    Summarise quarterly potential cases by HS code.
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
    Summarise quarterly potential cases by trader.
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
# FILTER OPTIONS
# ============================================================

def create_filter_options(
    dataframe: pd.DataFrame
) -> dict[str, list[str]]:
    """
    Return filter values for one quarter.
    """

    cases = dataframe.loc[
        dataframe[
            "IsPotentialCase"
        ]
    ]

    def unique_values(
        column_name: str
    ) -> list[str]:

        if column_name not in cases.columns:

            return []

        return sorted(
            value
            for value in (
                cases[column_name]
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
# BUILD ONE QUARTER JSON
# ============================================================

def build_quarter_dashboard_file(
    risk_file: Path,
    maximum_cases: int
) -> dict[str, object]:
    """
    Create one quarter-specific frontend JSON file.
    """

    started_at = time.perf_counter()

    year_quarter = (
        extract_quarter_from_filename(
            risk_file
        )
    )

    print(
        "Processing:",
        year_quarter
    )

    raw_data = pd.read_parquet(
        risk_file
    )

    dashboard_data = (
        standardize_dashboard_columns(
            dataframe=raw_data,
            year_quarter=year_quarter
        )
    )

    cases = dashboard_data.loc[
        dashboard_data[
            "IsPotentialCase"
        ]
    ]

    payload = {
        "metadata": {
            "title":
                "Undervaluation Risk Intelligence",

            "quarter":
                year_quarter,

            "generatedAt":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "casesAvailable":
                int(
                    len(
                        cases
                    )
                ),

            "maximumCasesIncluded":
                int(
                    maximum_cases
                )
        },

        "kpis":
            create_quarter_kpis(
                dashboard_data
            ),

        "riskDistribution":
            create_count_distribution(
                cases,
                "CaseRiskLevel"
            ),

        "modelAgreementDistribution":
            create_count_distribution(
                cases,
                "ModelAgreement"
            ),

        "benchmarkMethodDistribution":
            create_count_distribution(
                cases,
                "FinalBenchmarkMethod"
            ),

        "topCases":
            create_top_cases(
                dashboard_data,
                maximum_cases
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

    QUARTER_DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        QUARTER_DATA_DIRECTORY
        / f"dashboard_{year_quarter}.json"
    )

    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    elapsed_seconds = (
        time.perf_counter()
        - started_at
    )

    file_size_bytes = (
        output_path.stat().st_size
    )

    print(
        "  Rows scored:",
        f"{len(dashboard_data):,}"
    )

    print(
        "  Potential cases:",
        f"{len(cases):,}"
    )

    print(
        "  Browser cases:",
        f"{len(payload['topCases']):,}"
    )

    print(
        "  File size:",
        f"{file_size_bytes / 1_048_576:,.2f}",
        "MB"
    )

    print(
        "  Build seconds:",
        f"{elapsed_seconds:,.2f}"
    )

    return {
        "quarter":
            year_quarter,

        "dataUrl":
            (
                "./data/quarters/"
                f"dashboard_{year_quarter}.json"
            ),

        "rowsScored":
            int(
                payload[
                    "kpis"
                ][
                    "rowsScored"
                ]
            ),

        "potentialCases":
            int(
                payload[
                    "kpis"
                ][
                    "potentialCases"
                ]
            ),

        "highRiskCases":
            int(
                payload[
                    "kpis"
                ][
                    "highRiskCases"
                ]
            ),

        "mediumRiskCases":
            int(
                payload[
                    "kpis"
                ][
                    "mediumRiskCases"
                ]
            ),

        "lowRiskCases":
            int(
                payload[
                    "kpis"
                ][
                    "lowRiskCases"
                ]
            ),

        "totalPotentialValueGap":
            float(
                payload[
                    "kpis"
                ][
                    "totalPotentialValueGap"
                ]
            ),

        "casesIncluded":
            int(
                len(
                    payload[
                        "topCases"
                    ]
                )
            ),

        "fileSizeBytes":
            int(
                file_size_bytes
            ),

        "buildSeconds":
            float(
                elapsed_seconds
            )
    }


# ============================================================
# BUILD ALL QUARTERS
# ============================================================

def build_all_quarters_dashboard_data(
    maximum_cases: int = 5000
) -> Path:
    """
    Create the manifest and all quarter frontend files.
    """

    risk_directory = (
        get_risk_output_directory()
    )

    risk_files = list(
        risk_directory.glob(
            "risk_results_*.parquet"
        )
    )

    risk_files = sorted(
        risk_files,
        key=lambda file_path: (
            quarter_sort_key(
                extract_quarter_from_filename(
                    file_path
                )
            )
        )
    )

    if not risk_files:

        raise FileNotFoundError(
            "No risk-result files were found in:\n"
            f"{risk_directory}"
        )

    started_at = time.perf_counter()

    print(
        "=" * 78
    )

    print(
        "BUILDING ALL-QUARTERS FRONTEND DATA"
    )

    print(
        "=" * 78
    )

    print(
        "Quarter files:",
        f"{len(risk_files):,}"
    )

    print(
        "Maximum browser cases per quarter:",
        f"{maximum_cases:,}"
    )

    print()

    quarter_results = []

    for risk_file in risk_files:

        result = (
            build_quarter_dashboard_file(
                risk_file=risk_file,
                maximum_cases=maximum_cases
            )
        )

        quarter_results.append(
            result
        )

        print()

    latest_quarter = max(
        (
            result[
                "quarter"
            ]
            for result in quarter_results
        ),
        key=quarter_sort_key
    )

    total_build_seconds = (
        time.perf_counter()
        - started_at
    )

    manifest = {
        "metadata": {
            "title":
                "Undervaluation Risk Intelligence",

            "generatedAt":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "quarterCount":
                int(
                    len(
                        quarter_results
                    )
                ),

            "defaultQuarter":
                latest_quarter,

            "maximumCasesPerQuarter":
                int(
                    maximum_cases
                ),

            "totalBuildSeconds":
                float(
                    total_build_seconds
                )
        },

        "quarters":
            quarter_results
    }

    FRONTEND_DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(
        "=" * 78
    )

    print(
        "FRONTEND QUARTER FILES CREATED"
    )

    print(
        "=" * 78
    )

    print(
        "Manifest:",
        MANIFEST_PATH
    )

    print(
        "Total build seconds:",
        f"{total_build_seconds:,.2f}"
    )

    print(
        "=" * 78
    )

    return MANIFEST_PATH


# ============================================================
# COMMAND LINE
# ============================================================

def main() -> None:
    """
    Build all quarterly frontend files.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Build frontend data for all quarterly "
            "risk-result files."
        )
    )

    parser.add_argument(
        "--maximum-cases",
        type=int,
        default=5000
    )

    arguments = parser.parse_args()

    build_all_quarters_dashboard_data(
        maximum_cases=(
            arguments.maximum_cases
        )
    )


if __name__ == "__main__":

    main()