from __future__ import annotations

import os

from dataclasses import dataclass

from datetime import datetime

from pathlib import Path

import pandas as pd

from app.analytics.risk_engine import (
    RiskSettings,
    run_risk_engine
)

from app.analytics.clustering_validation_service import (
    get_cluster_output_path
)


# ============================================================
# RESULT MODEL
# ============================================================

@dataclass(
    frozen=True
)
class QuarterRiskResult:
    """
    Summary of one quarter's risk-scoring operation.
    """

    year_quarter: str

    rows: int

    potential_cases: int

    high_risk_cases: int

    medium_risk_cases: int

    low_risk_cases: int

    total_potential_value_gap: float

    output_path: Path

    elapsed_seconds: float


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

def get_risk_output_directory() -> Path:
    """
    Return the risk-output directory.
    """

    project_root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
        .parent
    )

    configured_directory = os.getenv(
        "RISK_OUTPUT_DIRECTORY",
        "output/risk"
    ).strip()

    output_directory = (
        project_root
        / configured_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return output_directory


def get_risk_output_path(
    year_quarter: str
) -> Path:
    """
    Return the expected risk-result file path.
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
# SCORE ONE QUARTER
# ============================================================

def score_clustered_quarter(
    year_quarter: str,
    settings: RiskSettings | None = None
) -> QuarterRiskResult:
    """
    Load a clustered quarter, run risk scoring and save results.
    """

    if settings is None:

        settings = (
            RiskSettings
            .from_environment()
        )

    cluster_path = get_cluster_output_path(
        year_quarter
    )

    if not cluster_path.exists():

        raise FileNotFoundError(
            "The quarter has not been clustered. "
            f"Missing file: {cluster_path}"
        )

    started_at = datetime.now()

    print(
        "=" * 70
    )

    print(
        "RUNNING QUARTER RISK SCORING"
    )

    print(
        "=" * 70
    )

    print(
        "Quarter:",
        year_quarter
    )

    print(
        "Clustering input:",
        cluster_path
    )

    print()

    clustered_data = pd.read_parquet(
        cluster_path
    )

    risk_results = run_risk_engine(
        dataframe=clustered_data,
        settings=settings
    )

    output_path = get_risk_output_path(
        year_quarter
    )

    risk_results.to_parquet(
        output_path,
        index=False
    )

    potential_case_mask = (
        risk_results[
            "IsPotentialCase"
        ]
        .fillna(False)
        .astype(bool)
    )

    potential_cases = risk_results.loc[
        potential_case_mask
    ]

    risk_level_counts = (
        potential_cases[
            "CaseRiskLevel"
        ]
        .value_counts()
    )

    high_risk_cases = int(
        risk_level_counts.get(
            "High Risk",
            0
        )
    )

    medium_risk_cases = int(
        risk_level_counts.get(
            "Medium Risk",
            0
        )
    )

    low_risk_cases = int(
        risk_level_counts.get(
            "Low Risk",
            0
        )
    )

    total_value_gap = float(
        potential_cases[
            "PotentialValueGap"
        ]
        .fillna(0)
        .sum()
    )

    elapsed_seconds = (
        datetime.now()
        - started_at
    ).total_seconds()

    print(
        "Risk scoring completed."
    )

    print(
        "Rows scored:",
        f"{len(risk_results):,}"
    )

    print(
        "Potential cases:",
        f"{len(potential_cases):,}"
    )

    print(
        "High-risk cases:",
        f"{high_risk_cases:,}"
    )

    print(
        "Medium-risk cases:",
        f"{medium_risk_cases:,}"
    )

    print(
        "Low-risk cases:",
        f"{low_risk_cases:,}"
    )

    print(
        "Total potential value gap:",
        f"E{total_value_gap:,.2f}"
    )

    print(
        "Output:",
        output_path
    )

    print(
        "Elapsed seconds:",
        f"{elapsed_seconds:,.1f}"
    )

    print(
        "=" * 70
    )

    result = QuarterRiskResult(
        year_quarter=year_quarter,
        rows=len(
            risk_results
        ),
        potential_cases=len(
            potential_cases
        ),
        high_risk_cases=high_risk_cases,
        medium_risk_cases=(
            medium_risk_cases
        ),
        low_risk_cases=low_risk_cases,
        total_potential_value_gap=(
            total_value_gap
        ),
        output_path=output_path,
        elapsed_seconds=elapsed_seconds
    )

    del clustered_data
    del risk_results
    del potential_cases

    return result