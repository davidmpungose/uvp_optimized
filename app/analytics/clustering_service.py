from __future__ import annotations

import os

from dataclasses import dataclass

from datetime import datetime

from pathlib import Path

import pandas as pd
import pyodbc

from app.analytics.clustering_engine import (
    ClusteringSettings,
    run_clustering
)

from app.services.analytics_input_service import (
    load_analytical_quarter
)

from config.settings import (
    PipelineSettings
)


# ============================================================
# CLUSTERING RESULT
# ============================================================

@dataclass(
    frozen=True
)
class QuarterClusteringResult:
    """
    Summary of one quarter's clustering run.
    """

    year_quarter: str

    rows: int

    peer_groups: int

    eligible_groups: int

    clustered_groups: int

    clustered_rows: int

    output_path: Path

    elapsed_seconds: float


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

def get_clustering_output_directory() -> Path:
    """
    Return the configured clustering output directory.
    """

    project_root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
        .parent
    )

    configured_directory = os.getenv(
        "CLUSTER_OUTPUT_DIRECTORY",
        "output/clustering"
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


# ============================================================
# RUN QUARTER CLUSTERING
# ============================================================

def cluster_analytical_quarter(
    connection: pyodbc.Connection,
    year_quarter: str,
    pipeline_settings: PipelineSettings | None = None,
    clustering_settings: ClusteringSettings | None = None
) -> QuarterClusteringResult:
    """
    Load, cluster and save one complete analytical quarter.
    """

    if pipeline_settings is None:

        pipeline_settings = (
            PipelineSettings
            .from_environment()
        )

    if clustering_settings is None:

        clustering_settings = (
            ClusteringSettings
            .from_environment()
        )

    started_at = datetime.now()

    print(
        "=" * 70
    )

    print(
        "RUNNING PRICE-SEGMENT CLUSTERING"
    )

    print(
        "=" * 70
    )

    print(
        "Quarter:",
        year_quarter
    )

    print()

    analytical_input = (
        load_analytical_quarter(
            connection=connection,
            year_quarter=year_quarter,
            settings=pipeline_settings
        )
    )

    if analytical_input.empty:

        raise RuntimeError(
            f"No benchmark-eligible rows were found "
            f"for quarter {year_quarter}."
        )

    clustered_results = (
        run_clustering(
            dataframe=analytical_input,
            settings=clustering_settings
        )
    )

    output_directory = (
        get_clustering_output_directory()
    )

    safe_quarter = (
        year_quarter.replace(
            "/",
            "-"
        )
    )

    output_path = (
        output_directory
        / f"clustered_{safe_quarter}.parquet"
    )

    clustered_results.to_parquet(
        output_path,
        index=False
    )

    peer_groups = int(
        clustered_results[
            "PeerKey"
        ]
        .nunique(
            dropna=True
        )
    )

    eligible_groups = int(
        clustered_results.loc[
            clustered_results[
                "ClusterEligible"
            ],
            "PeerKey"
        ]
        .nunique(
            dropna=True
        )
    )

    clustered_groups = int(
        clustered_results.loc[
            clustered_results[
                "ClusterApplied"
            ],
            "PeerKey"
        ]
        .nunique(
            dropna=True
        )
    )

    clustered_rows = int(
        clustered_results[
            "ClusterApplied"
        ]
        .sum()
    )

    elapsed_seconds = (
        datetime.now()
        - started_at
    ).total_seconds()

    print()

    print(
        "Quarter clustering completed."
    )

    print(
        "Rows:",
        f"{len(clustered_results):,}"
    )

    print(
        "Peer groups:",
        f"{peer_groups:,}"
    )

    print(
        "Cluster-eligible groups:",
        f"{eligible_groups:,}"
    )

    print(
        "Successfully clustered groups:",
        f"{clustered_groups:,}"
    )

    print(
        "Clustered rows:",
        f"{clustered_rows:,}"
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

    del analytical_input
    del clustered_results

    return QuarterClusteringResult(
        year_quarter=year_quarter,
        rows=len(
            pd.read_parquet(
                output_path,
                columns=[
                    "PreparedDeclarationId"
                ]
            )
        ),
        peer_groups=peer_groups,
        eligible_groups=eligible_groups,
        clustered_groups=clustered_groups,
        clustered_rows=clustered_rows,
        output_path=output_path,
        elapsed_seconds=elapsed_seconds
    )