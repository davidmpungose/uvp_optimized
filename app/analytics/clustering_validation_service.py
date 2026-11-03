from __future__ import annotations

import os

from pathlib import Path

import pandas as pd


# ============================================================
# GET CLUSTER OUTPUT PATH
# ============================================================

def get_cluster_output_path(
    year_quarter: str
) -> Path:
    """
    Return the expected quarter clustering output path.
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

    safe_quarter = year_quarter.replace(
        "/",
        "-"
    )

    return (
        project_root
        / configured_directory
        / f"clustered_{safe_quarter}.parquet"
    )


# ============================================================
# VALIDATE CLUSTER OUTPUT
# ============================================================

def validate_cluster_output(
    year_quarter: str
) -> dict[str, object]:
    """
    Validate the saved quarter clustering output.
    """

    output_path = (
        get_cluster_output_path(
            year_quarter
        )
    )

    if not output_path.exists():

        raise FileNotFoundError(
            f"Cluster output does not exist: "
            f"{output_path}"
        )

    dataframe = pd.read_parquet(
        output_path
    )

    required_columns = {
        "PreparedDeclarationId",
        "YearQuarter",
        "HS",
        "SelectedUnit",
        "UnitValue",
        "PeerKey",
        "OriginalQ1",
        "OriginalMedian",
        "OriginalQ3",
        "ClusterApplied",
        "ClusterEligible",
        "ClusterEligibilityReason",
        "ClusterCount",
        "ClusterId",
        "ClusterPriceTier",
        "ClusterSilhouetteScore",
        "ClusterPeerCount",
        "ClusterQ1",
        "ClusterMedian",
        "ClusterQ3"
    }

    missing_columns = sorted(
        required_columns
        - set(
            dataframe.columns
        )
    )

    if missing_columns:

        raise RuntimeError(
            "Cluster output is missing required "
            "columns: "
            + ", ".join(
                missing_columns
            )
        )

    clustered_rows_mask = (
        dataframe[
            "ClusterApplied"
        ]
        .fillna(False)
        .astype(bool)
    )

    clustered_data = dataframe.loc[
        clustered_rows_mask
    ]

    invalid_cluster_quartiles = int(
        (
            (
                clustered_data[
                    "ClusterQ1"
                ]
                >
                clustered_data[
                    "ClusterMedian"
                ]
            )
            |
            (
                clustered_data[
                    "ClusterMedian"
                ]
                >
                clustered_data[
                    "ClusterQ3"
                ]
            )
        )
        .sum()
    )

    summary = {
        "output_path":
            output_path,

        "rows":
            len(
                dataframe
            ),

        "peer_groups":
            int(
                dataframe[
                    "PeerKey"
                ]
                .nunique(
                    dropna=True
                )
            ),

        "cluster_eligible_groups":
            int(
                dataframe.loc[
                    dataframe[
                        "ClusterEligible"
                    ],
                    "PeerKey"
                ]
                .nunique(
                    dropna=True
                )
            ),

        "clustered_groups":
            int(
                clustered_data[
                    "PeerKey"
                ]
                .nunique(
                    dropna=True
                )
            ),

        "clustered_rows":
            int(
                clustered_rows_mask.sum()
            ),

        "unclustered_rows":
            int(
                (
                    ~clustered_rows_mask
                )
                .sum()
            ),

        "minimum_silhouette":
            (
                float(
                    clustered_data[
                        "ClusterSilhouetteScore"
                    ]
                    .min()
                )
                if not clustered_data.empty
                else None
            ),

        "average_silhouette":
            (
                float(
                    clustered_data[
                        "ClusterSilhouetteScore"
                    ]
                    .mean()
                )
                if not clustered_data.empty
                else None
            ),

        "invalid_cluster_quartiles":
            invalid_cluster_quartiles,

        "duplicate_prepared_ids":
            int(
                dataframe[
                    "PreparedDeclarationId"
                ]
                .duplicated()
                .sum()
            )
    }

    reason_summary = (
        dataframe[
            [
                "PeerKey",
                "ClusterEligibilityReason"
            ]
        ]
        .drop_duplicates(
            subset=[
                "PeerKey"
            ]
        )
        .groupby(
            "ClusterEligibilityReason",
            dropna=False
        )
        .size()
        .sort_values(
            ascending=False
        )
    )

    summary[
        "reason_summary"
    ] = [
        {
            "reason":
                str(
                    reason
                ),

            "groups":
                int(
                    group_count
                )
        }
        for reason, group_count
        in reason_summary.items()
    ]

    return summary


# ============================================================
# PRINT CLUSTER VALIDATION
# ============================================================

def print_cluster_validation(
    year_quarter: str,
    summary: dict[str, object]
) -> None:
    """
    Display cluster-output validation.
    """

    print(
        "=" * 70
    )

    print(
        "CLUSTERING OUTPUT VALIDATION"
    )

    print(
        "=" * 70
    )

    print(
        "Quarter:",
        year_quarter
    )

    print(
        "Rows:",
        f"{summary['rows']:,}"
    )

    print(
        "Peer groups:",
        f"{summary['peer_groups']:,}"
    )

    print(
        "Cluster-eligible groups:",
        f"{summary['cluster_eligible_groups']:,}"
    )

    print(
        "Successfully clustered groups:",
        f"{summary['clustered_groups']:,}"
    )

    print(
        "Clustered rows:",
        f"{summary['clustered_rows']:,}"
    )

    print(
        "Unclustered rows:",
        f"{summary['unclustered_rows']:,}"
    )

    print(
        "Minimum silhouette:",
        (
            f"{summary['minimum_silhouette']:.4f}"
            if summary[
                "minimum_silhouette"
            ]
            is not None
            else "Not available"
        )
    )

    print(
        "Average silhouette:",
        (
            f"{summary['average_silhouette']:.4f}"
            if summary[
                "average_silhouette"
            ]
            is not None
            else "Not available"
        )
    )

    print(
        "Invalid cluster quartiles:",
        f"{summary['invalid_cluster_quartiles']:,}"
    )

    print(
        "Duplicate declaration IDs:",
        f"{summary['duplicate_prepared_ids']:,}"
    )

    print()

    print(
        "Cluster decisions:"
    )

    for record in summary[
        "reason_summary"
    ]:

        print(
            "  ",
            record["reason"],
            ":",
            f"{record['groups']:,}",
            "groups"
        )

    print()

    print(
        "Output:",
        summary["output_path"]
    )

    print(
        "=" * 70
    )