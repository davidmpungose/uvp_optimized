from __future__ import annotations

import os

from dataclasses import dataclass

import numpy as np
import pandas as pd

from sklearn.cluster import (
    KMeans,
    MiniBatchKMeans
)

from sklearn.metrics import (
    silhouette_score
)


# ============================================================
# CLUSTERING SETTINGS
# ============================================================

@dataclass(
    frozen=True
)
class ClusteringSettings:
    """
    Configuration for the price-segment clustering engine.
    """

    minimum_group_size: int

    minimum_unique_values: int

    minimum_clusters: int

    maximum_clusters: int

    minimum_silhouette: float

    silhouette_sample_size: int

    minimum_spread_ratio: float

    minibatch_threshold: int

    minibatch_size: int

    random_state: int

    @classmethod
    def from_environment(
        cls
    ) -> "ClusteringSettings":
        """
        Load clustering settings from environment variables.
        """

        settings = cls(
            minimum_group_size=int(
                os.getenv(
                    "CLUSTER_MINIMUM_GROUP_SIZE",
                    "20"
                )
            ),

            minimum_unique_values=int(
                os.getenv(
                    "CLUSTER_MINIMUM_UNIQUE_VALUES",
                    "3"
                )
            ),

            minimum_clusters=int(
                os.getenv(
                    "CLUSTER_MINIMUM_K",
                    "2"
                )
            ),

            maximum_clusters=int(
                os.getenv(
                    "CLUSTER_MAXIMUM_K",
                    "3"
                )
            ),

            minimum_silhouette=float(
                os.getenv(
                    "CLUSTER_MINIMUM_SILHOUETTE",
                    "0.25"
                )
            ),

            silhouette_sample_size=int(
                os.getenv(
                    "CLUSTER_SILHOUETTE_SAMPLE_SIZE",
                    "5000"
                )
            ),

            minimum_spread_ratio=float(
                os.getenv(
                    "CLUSTER_MINIMUM_SPREAD_RATIO",
                    "0.10"
                )
            ),

            minibatch_threshold=int(
                os.getenv(
                    "CLUSTER_MINIBATCH_THRESHOLD",
                    "20000"
                )
            ),

            minibatch_size=int(
                os.getenv(
                    "CLUSTER_BATCH_SIZE",
                    "2048"
                )
            ),

            random_state=int(
                os.getenv(
                    "CLUSTER_RANDOM_STATE",
                    "42"
                )
            )
        )

        settings.validate()

        return settings

    def validate(
        self
    ) -> None:
        """
        Validate clustering configuration.
        """

        if self.minimum_group_size < 2:

            raise ValueError(
                "CLUSTER_MINIMUM_GROUP_SIZE must "
                "be at least 2."
            )

        if self.minimum_unique_values < 2:

            raise ValueError(
                "CLUSTER_MINIMUM_UNIQUE_VALUES must "
                "be at least 2."
            )

        if self.minimum_clusters < 2:

            raise ValueError(
                "CLUSTER_MINIMUM_K must be "
                "at least 2."
            )

        if (
            self.maximum_clusters
            < self.minimum_clusters
        ):

            raise ValueError(
                "CLUSTER_MAXIMUM_K cannot be less "
                "than CLUSTER_MINIMUM_K."
            )

        if not (
            0
            <= self.minimum_silhouette
            <= 1
        ):

            raise ValueError(
                "CLUSTER_MINIMUM_SILHOUETTE must "
                "be between 0 and 1."
            )

        if self.silhouette_sample_size < 2:

            raise ValueError(
                "CLUSTER_SILHOUETTE_SAMPLE_SIZE "
                "must be at least 2."
            )

        if self.minimum_spread_ratio < 0:

            raise ValueError(
                "CLUSTER_MINIMUM_SPREAD_RATIO cannot "
                "be negative."
            )


# ============================================================
# OUTPUT COLUMN DEFINITIONS
# ============================================================

CLUSTER_OUTPUT_COLUMNS = [
    "ClusterApplied",
    "ClusterEligible",
    "ClusterEligibilityReason",
    "ClusterModel",
    "ClusterCount",
    "ClusterId",
    "ClusterPriceTier",
    "ClusterSilhouetteScore",
    "ClusterPeerCount",
    "ClusterQ1",
    "ClusterMedian",
    "ClusterQ3",
    "ClusterMinimumUnitValue",
    "ClusterMaximumUnitValue",
    "ClusterAverageUnitValue",
    "ClusterInterquartileRange"
]


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_clustering_input(
    dataframe: pd.DataFrame
) -> None:
    """
    Confirm that the SQL-prepared DataFrame contains the
    columns required by the clustering engine.
    """

    required_columns = {
        "PreparedDeclarationId",
        "YearQuarter",
        "HS",
        "SelectedUnit",
        "UnitValue",
        "PeerKey",
        "PeerCount",
        "OriginalQ1",
        "OriginalMedian",
        "OriginalQ3",
        "IsBenchmarkEligible"
    }

    missing_columns = sorted(
        required_columns
        - set(
            dataframe.columns
        )
    )

    if missing_columns:

        raise RuntimeError(
            "Clustering input is missing required "
            "columns: "
            + ", ".join(
                missing_columns
            )
        )


# ============================================================
# CREATE EMPTY CLUSTER OUTPUTS
# ============================================================

def initialise_cluster_columns(
    dataframe: pd.DataFrame
) -> pd.DataFrame:
    """
    Add clustering result columns with safe initial values.
    """

    output = dataframe.copy()

    output["ClusterApplied"] = False

    output["ClusterEligible"] = False

    output[
        "ClusterEligibilityReason"
    ] = ""

    output["ClusterModel"] = ""

    output["ClusterCount"] = 0

    output["ClusterId"] = pd.Series(
        pd.NA,
        index=output.index,
        dtype="Int64"
    )

    output["ClusterPriceTier"] = ""

    output[
        "ClusterSilhouetteScore"
    ] = np.nan

    output["ClusterPeerCount"] = pd.Series(
        pd.NA,
        index=output.index,
        dtype="Int64"
    )

    output["ClusterQ1"] = np.nan

    output["ClusterMedian"] = np.nan

    output["ClusterQ3"] = np.nan

    output[
        "ClusterMinimumUnitValue"
    ] = np.nan

    output[
        "ClusterMaximumUnitValue"
    ] = np.nan

    output[
        "ClusterAverageUnitValue"
    ] = np.nan

    output[
        "ClusterInterquartileRange"
    ] = np.nan

    return output


# ============================================================
# GROUP ELIGIBILITY
# ============================================================

def evaluate_group_eligibility(
    group: pd.DataFrame,
    settings: ClusteringSettings
) -> tuple[
    bool,
    str
]:
    """
    Determine whether a peer group should be clustered.
    """

    group_size = len(
        group
    )

    if group_size < settings.minimum_group_size:

        return (
            False,
            "INSUFFICIENT_GROUP_SIZE"
        )

    unit_values = pd.to_numeric(
        group["UnitValue"],
        errors="coerce"
    )

    unit_values = unit_values.replace(
        [
            np.inf,
            -np.inf
        ],
        np.nan
    ).dropna()

    if len(unit_values) < settings.minimum_group_size:

        return (
            False,
            "INSUFFICIENT_VALID_UNIT_VALUES"
        )

    unique_value_count = int(
        unit_values.nunique()
    )

    if (
        unique_value_count
        < settings.minimum_unique_values
    ):

        return (
            False,
            "INSUFFICIENT_UNIQUE_VALUES"
        )

    median_value = float(
        unit_values.median()
    )

    q1_value = float(
        unit_values.quantile(
            0.25
        )
    )

    q3_value = float(
        unit_values.quantile(
            0.75
        )
    )

    interquartile_range = (
        q3_value
        - q1_value
    )

    denominator = max(
        abs(
            median_value
        ),
        1e-12
    )

    spread_ratio = (
        interquartile_range
        / denominator
    )

    if (
        spread_ratio
        < settings.minimum_spread_ratio
    ):

        return (
            False,
            "INSUFFICIENT_PRICE_SPREAD"
        )

    if (
        group[
            "IsBenchmarkEligible"
        ]
        .fillna(0)
        .astype(int)
        .max()
        != 1
    ):

        return (
            False,
            "ORIGINAL_BENCHMARK_INELIGIBLE"
        )

    return (
        True,
        "ELIGIBLE"
    )


# ============================================================
# MODEL CREATION
# ============================================================

def create_cluster_model(
    number_of_clusters: int,
    group_size: int,
    settings: ClusteringSettings
):
    """
    Choose KMeans or MiniBatchKMeans based on group size.
    """

    if (
        group_size
        >= settings.minibatch_threshold
    ):

        model = MiniBatchKMeans(
            n_clusters=number_of_clusters,

            random_state=(
                settings.random_state
            ),

            batch_size=(
                settings.minibatch_size
            ),

            n_init=10
        )

        model_name = (
            "MiniBatchKMeans"
        )

    else:

        model = KMeans(
            n_clusters=number_of_clusters,

            random_state=(
                settings.random_state
            ),

            n_init=10
        )

        model_name = "KMeans"

    return (
        model,
        model_name
    )


# ============================================================
# SILHOUETTE SCORING
# ============================================================

def calculate_silhouette(
    transformed_values: np.ndarray,
    labels: np.ndarray,
    settings: ClusteringSettings
) -> float:
    """
    Calculate silhouette score using a controlled sample
    when a group is large.
    """

    unique_labels = np.unique(
        labels
    )

    if len(unique_labels) < 2:

        return -1.0

    sample_size = min(
        settings.silhouette_sample_size,
        len(
            transformed_values
        )
    )

    if sample_size < len(
        transformed_values
    ):

        random_generator = (
            np.random.default_rng(
                settings.random_state
            )
        )

        sample_indices = (
            random_generator.choice(
                len(
                    transformed_values
                ),

                size=sample_size,

                replace=False
            )
        )

        sample_values = (
            transformed_values[
                sample_indices
            ]
        )

        sample_labels = labels[
            sample_indices
        ]

    else:

        sample_values = (
            transformed_values
        )

        sample_labels = labels

    if (
        len(
            np.unique(
                sample_labels
            )
        )
        < 2
    ):

        return -1.0

    return float(
        silhouette_score(
            sample_values,
            sample_labels
        )
    )


# ============================================================
# SELECT BEST MODEL
# ============================================================

def select_best_cluster_model(
    unit_values: np.ndarray,
    settings: ClusteringSettings
) -> dict[str, object] | None:
    """
    Test candidate cluster counts and return the model with
    the highest acceptable silhouette score.

    Unit values are transformed using log1p because customs
    unit-value distributions are commonly right-skewed.
    """

    transformed_values = np.log1p(
        unit_values
    ).reshape(
        -1,
        1
    )

    unique_value_count = len(
        np.unique(
            transformed_values
        )
    )

    maximum_possible_clusters = min(
        settings.maximum_clusters,

        unique_value_count,

        len(
            transformed_values
        ) - 1
    )

    if (
        maximum_possible_clusters
        < settings.minimum_clusters
    ):

        return None

    best_result = None

    for number_of_clusters in range(
        settings.minimum_clusters,
        maximum_possible_clusters + 1
    ):

        model, model_name = (
            create_cluster_model(
                number_of_clusters=(
                    number_of_clusters
                ),

                group_size=len(
                    transformed_values
                ),

                settings=settings
            )
        )

        labels = model.fit_predict(
            transformed_values
        )

        if (
            len(
                np.unique(
                    labels
                )
            )
            < 2
        ):

            continue

        silhouette_value = (
            calculate_silhouette(
                transformed_values=(
                    transformed_values
                ),

                labels=labels,

                settings=settings
            )
        )

        if (
            best_result is None
            or silhouette_value
            > best_result[
                "silhouette_score"
            ]
        ):

            best_result = {
                "model":
                    model,

                "model_name":
                    model_name,

                "cluster_count":
                    number_of_clusters,

                "labels":
                    labels,

                "silhouette_score":
                    silhouette_value
            }

    if best_result is None:

        return None

    if (
        best_result[
            "silhouette_score"
        ]
        < settings.minimum_silhouette
    ):

        return None

    return best_result


# ============================================================
# ORDER CLUSTERS INTO PRICE TIERS
# ============================================================

def create_ordered_cluster_mapping(
    unit_values: np.ndarray,
    raw_labels: np.ndarray
) -> tuple[
    dict[int, int],
    dict[int, str]
]:
    """
    Reorder arbitrary KMeans labels according to each cluster's
    median unit value.

    The lowest median receives ClusterId 1.
    """

    cluster_records = []

    for raw_label in np.unique(
        raw_labels
    ):

        cluster_values = unit_values[
            raw_labels
            == raw_label
        ]

        cluster_records.append(
            {
                "raw_label":
                    int(
                        raw_label
                    ),

                "median":
                    float(
                        np.median(
                            cluster_values
                        )
                    )
            }
        )

    cluster_records.sort(
        key=lambda record: (
            record["median"]
        )
    )

    ordered_mapping = {}

    price_tier_mapping = {}

    cluster_count = len(
        cluster_records
    )

    for position, record in enumerate(
        cluster_records,
        start=1
    ):

        raw_label = record[
            "raw_label"
        ]

        ordered_mapping[
            raw_label
        ] = position

        if position == 1:

            tier_name = (
                "LOW_PRICE"
            )

        elif (
            position
            == cluster_count
        ):

            tier_name = (
                "HIGH_PRICE"
            )

        else:

            tier_name = (
                "MID_PRICE"
            )

        price_tier_mapping[
            position
        ] = tier_name

    return (
        ordered_mapping,
        price_tier_mapping
    )


# ============================================================
# CALCULATE CLUSTER STATISTICS
# ============================================================

def calculate_cluster_statistics(
    group_result: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate cluster-specific benchmark statistics.
    """

    grouped_unit_values = (
        group_result.groupby(
            "ClusterId",
            observed=True
        )["UnitValue"]
    )

    statistics = grouped_unit_values.agg(
        ClusterPeerCount="count",

        ClusterMinimumUnitValue="min",

        ClusterMaximumUnitValue="max",

        ClusterAverageUnitValue="mean",

        ClusterMedian="median"
    )

    statistics[
        "ClusterQ1"
    ] = grouped_unit_values.quantile(
        0.25
    )

    statistics[
        "ClusterQ3"
    ] = grouped_unit_values.quantile(
        0.75
    )

    statistics[
        "ClusterInterquartileRange"
    ] = (
        statistics[
            "ClusterQ3"
        ]
        - statistics[
            "ClusterQ1"
        ]
    )

    return statistics.reset_index()


# ============================================================
# CLUSTER ONE PEER GROUP
# ============================================================

def cluster_peer_group(
    group: pd.DataFrame,
    settings: ClusteringSettings
) -> pd.DataFrame:
    """
    Apply clustering to one SQL-defined peer group.
    """

    group_result = (
        group.copy()
    )

    eligible, reason = (
        evaluate_group_eligibility(
            group=group_result,
            settings=settings
        )
    )

    group_result[
        "ClusterEligible"
    ] = eligible

    group_result[
        "ClusterEligibilityReason"
    ] = reason

    if not eligible:

        return group_result

    unit_values_series = pd.to_numeric(
        group_result["UnitValue"],
        errors="coerce"
    )

    valid_value_mask = (
        unit_values_series.notna()
        & np.isfinite(
            unit_values_series
        )
        & (
            unit_values_series
            >= 0
        )
    )

    if not valid_value_mask.all():

        group_result[
            "ClusterEligible"
        ] = False

        group_result[
            "ClusterEligibilityReason"
        ] = (
            "INVALID_UNIT_VALUES"
        )

        return group_result

    unit_values = (
        unit_values_series
        .to_numpy(
            dtype=float
        )
    )

    best_model = (
        select_best_cluster_model(
            unit_values=unit_values,
            settings=settings
        )
    )

    if best_model is None:

        group_result[
            "ClusterEligibilityReason"
        ] = (
            "NO_ACCEPTABLE_CLUSTER_SOLUTION"
        )

        return group_result

    raw_labels = best_model[
        "labels"
    ]

    (
        ordered_mapping,
        price_tier_mapping
    ) = create_ordered_cluster_mapping(
        unit_values=unit_values,
        raw_labels=raw_labels
    )

    ordered_labels = np.array(
        [
            ordered_mapping[
                int(
                    raw_label
                )
            ]
            for raw_label in raw_labels
        ],
        dtype=int
    )

    group_result[
        "ClusterApplied"
    ] = True

    group_result[
        "ClusterEligibilityReason"
    ] = "CLUSTERED"

    group_result[
        "ClusterModel"
    ] = best_model[
        "model_name"
    ]

    group_result[
        "ClusterCount"
    ] = best_model[
        "cluster_count"
    ]

    group_result[
        "ClusterId"
    ] = ordered_labels

    group_result[
        "ClusterPriceTier"
    ] = [
        price_tier_mapping[
            int(
                cluster_number
            )
        ]
        for cluster_number in ordered_labels
    ]

    group_result[
        "ClusterSilhouetteScore"
    ] = best_model[
        "silhouette_score"
    ]

    cluster_statistics = (
        calculate_cluster_statistics(
            group_result
        )
    )

    group_result = group_result.merge(
        cluster_statistics,

        on="ClusterId",

        how="left",

        validate="many_to_one",

        suffixes=(
            "",
            "_Calculated"
        )
    )

    calculated_columns = [
        "ClusterPeerCount",
        "ClusterQ1",
        "ClusterMedian",
        "ClusterQ3",
        "ClusterMinimumUnitValue",
        "ClusterMaximumUnitValue",
        "ClusterAverageUnitValue",
        "ClusterInterquartileRange"
    ]

    for column_name in calculated_columns:

        calculated_name = (
            column_name
            + "_Calculated"
        )

        if (
            calculated_name
            in group_result.columns
        ):

            group_result[
                column_name
            ] = group_result[
                calculated_name
            ]

            group_result.drop(
                columns=[
                    calculated_name
                ],
                inplace=True
            )

    group_result[
        "ClusterPeerCount"
    ] = (
        group_result[
            "ClusterPeerCount"
        ]
        .astype(
            "Int64"
        )
    )

    return group_result


# ============================================================
# RUN CLUSTERING ENGINE
# ============================================================

def run_clustering(
    dataframe: pd.DataFrame,
    settings: ClusteringSettings | None = None
) -> pd.DataFrame:
    """
    Run price-tier clustering for every SQL-defined peer group.

    The input should represent one complete quarter.
    """

    if settings is None:

        settings = (
            ClusteringSettings
            .from_environment()
        )

    validate_clustering_input(
        dataframe
    )

    output = initialise_cluster_columns(
        dataframe
    )

    if output.empty:

        return output

    output["UnitValue"] = pd.to_numeric(
        output["UnitValue"],
        errors="coerce"
    )

    peer_groups = output.groupby(
        "PeerKey",
        sort=False,
        observed=True,
        dropna=False
    )

    clustered_groups = []

    total_groups = peer_groups.ngroups

    for group_number, (
        peer_key,
        peer_group
    ) in enumerate(
        peer_groups,
        start=1
    ):

        clustered_group = (
            cluster_peer_group(
                group=peer_group,
                settings=settings
            )
        )

        clustered_groups.append(
            clustered_group
        )

        if (
            group_number % 500
            == 0
            or group_number
            == total_groups
        ):

            print(
                "Cluster groups processed:",
                f"{group_number:,}",
                "of",
                f"{total_groups:,}"
            )

    result = pd.concat(
        clustered_groups,
        axis=0,
        ignore_index=False
    )

    result.sort_values(
        by=[
            "PreparedDeclarationId"
        ],
        inplace=True
    )

    result.reset_index(
        drop=True,
        inplace=True
    )

    return result