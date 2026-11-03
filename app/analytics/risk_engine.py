from __future__ import annotations

import os

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ============================================================
# RISK SETTINGS
# ============================================================

@dataclass(
    frozen=True
)
class RiskSettings:
    """
    Settings used by the initial risk-scoring model.
    """

    minimum_deviation_percent: float

    minimum_value_gap: float

    deviation_cap_percent: float

    peer_count_cap: int

    high_risk_threshold: float

    medium_risk_threshold: float

    model_version: str


    @classmethod
    def from_environment(
        cls
    ) -> "RiskSettings":
        """
        Read risk settings from the .env file.
        """

        settings = cls(
            minimum_deviation_percent=float(
                os.getenv(
                    "RISK_MINIMUM_DEVIATION_PERCENT",
                    "10"
                )
            ),

            minimum_value_gap=float(
                os.getenv(
                    "RISK_MINIMUM_VALUE_GAP",
                    "1000"
                )
            ),

            deviation_cap_percent=float(
                os.getenv(
                    "RISK_DEVIATION_CAP_PERCENT",
                    "50"
                )
            ),

            peer_count_cap=int(
                os.getenv(
                    "RISK_PEER_COUNT_CAP",
                    "100"
                )
            ),

            high_risk_threshold=float(
                os.getenv(
                    "RISK_HIGH_THRESHOLD",
                    "70"
                )
            ),

            medium_risk_threshold=float(
                os.getenv(
                    "RISK_MEDIUM_THRESHOLD",
                    "45"
                )
            ),

            model_version=os.getenv(
                "RISK_MODEL_VERSION",
                "UVP_SQL_V1"
            ).strip()
        )

        settings.validate()

        return settings


    def validate(
        self
    ) -> None:
        """
        Validate the risk settings.
        """

        if self.minimum_deviation_percent < 0:

            raise ValueError(
                "RISK_MINIMUM_DEVIATION_PERCENT "
                "cannot be negative."
            )

        if self.minimum_value_gap < 0:

            raise ValueError(
                "RISK_MINIMUM_VALUE_GAP "
                "cannot be negative."
            )

        if self.deviation_cap_percent <= 0:

            raise ValueError(
                "RISK_DEVIATION_CAP_PERCENT "
                "must be greater than zero."
            )

        if self.peer_count_cap < 1:

            raise ValueError(
                "RISK_PEER_COUNT_CAP must "
                "be at least 1."
            )

        if not (
            0
            <= self.medium_risk_threshold
            <= 100
        ):

            raise ValueError(
                "RISK_MEDIUM_THRESHOLD must "
                "be between 0 and 100."
            )

        if not (
            0
            <= self.high_risk_threshold
            <= 100
        ):

            raise ValueError(
                "RISK_HIGH_THRESHOLD must "
                "be between 0 and 100."
            )

        if (
            self.high_risk_threshold
            <= self.medium_risk_threshold
        ):

            raise ValueError(
                "RISK_HIGH_THRESHOLD must be "
                "greater than RISK_MEDIUM_THRESHOLD."
            )

        if not self.model_version:

            raise ValueError(
                "RISK_MODEL_VERSION cannot be empty."
            )


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_risk_input(
    dataframe: pd.DataFrame
) -> None:
    """
    Confirm that clustering output contains the fields required
    by the risk engine.
    """

    required_columns = {
        "PreparedDeclarationId",
        "YearQuarter",
        "Traders",
        "Lib_Traders",
        "HS",
        "FOBValue",
        "SelectedQuantity",
        "SelectedUnit",
        "UnitValue",
        "PeerKey",
        "PeerCount",
        "OriginalQ1",
        "OriginalMedian",
        "OriginalQ3",
        "IsBenchmarkEligible",
        "ClusterApplied",
        "ClusterEligible",
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
            "Risk input is missing required columns: "
            + ", ".join(
                missing_columns
            )
        )


# ============================================================
# NUMERIC CONVERSION
# ============================================================

def convert_risk_numeric_columns(
    dataframe: pd.DataFrame
) -> pd.DataFrame:
    """
    Convert risk-related fields into numeric columns.
    """

    output = dataframe.copy()

    numeric_columns = [
        "FOBValue",
        "SelectedQuantity",
        "UnitValue",
        "PeerCount",
        "OriginalQ1",
        "OriginalMedian",
        "OriginalQ3",
        "ClusterPeerCount",
        "ClusterQ1",
        "ClusterMedian",
        "ClusterQ3",
        "ClusterSilhouetteScore"
    ]

    for column_name in numeric_columns:

        output[column_name] = pd.to_numeric(
            output[column_name],
            errors="coerce"
        )

    return output


# ============================================================
# ORIGINAL BENCHMARK INDICATORS
# ============================================================

def calculate_original_indicators(
    dataframe: pd.DataFrame
) -> pd.DataFrame:
    """
    Compare each declaration with the original Q1 benchmark.
    """

    output = dataframe.copy()

    benchmark_available = (
        output["OriginalQ1"].notna()
        & output["OriginalQ1"].gt(0)
        & output[
            "IsBenchmarkEligible"
        ].fillna(False).astype(bool)
    )

    output[
        "OriginalBenchmarkAvailable"
    ] = benchmark_available

    output[
        "OriginalUnitValueDifference"
    ] = np.where(
        benchmark_available,

        output["OriginalQ1"]
        - output["UnitValue"],

        np.nan
    )

    output[
        "OriginalDeviationPercent"
    ] = np.where(
        benchmark_available,

        (
            output["OriginalQ1"]
            - output["UnitValue"]
        )
        / output["OriginalQ1"]
        * 100,

        np.nan
    )

    output[
        "OriginalDeviationPercent"
    ] = (
        pd.to_numeric(
            output[
                "OriginalDeviationPercent"
            ],
            errors="coerce"
        )
        .clip(
            lower=0
        )
    )

    output[
        "OriginalValueGap"
    ] = np.where(
        benchmark_available,

        (
            output["OriginalQ1"]
            - output["UnitValue"]
        )
        * output["SelectedQuantity"],

        np.nan
    )

    output[
        "OriginalValueGap"
    ] = (
        pd.to_numeric(
            output[
                "OriginalValueGap"
            ],
            errors="coerce"
        )
        .clip(
            lower=0
        )
    )

    output["OriginalFlag"] = (
        benchmark_available
        & output[
            "UnitValue"
        ].lt(
            output[
                "OriginalQ1"
            ]
        )
    )

    return output


# ============================================================
# CLUSTER BENCHMARK INDICATORS
# ============================================================

def calculate_cluster_indicators(
    dataframe: pd.DataFrame
) -> pd.DataFrame:
    """
    Compare each declaration with its cluster-specific Q1.
    """

    output = dataframe.copy()

    cluster_applied = (
        output[
            "ClusterApplied"
        ]
        .fillna(False)
        .astype(bool)
    )

    benchmark_available = (
        cluster_applied
        & output["ClusterQ1"].notna()
        & output["ClusterQ1"].gt(0)
    )

    output[
        "ClusterBenchmarkAvailable"
    ] = benchmark_available

    output[
        "ClusterUnitValueDifference"
    ] = np.where(
        benchmark_available,

        output["ClusterQ1"]
        - output["UnitValue"],

        np.nan
    )

    output[
        "ClusterDeviationPercent"
    ] = np.where(
        benchmark_available,

        (
            output["ClusterQ1"]
            - output["UnitValue"]
        )
        / output["ClusterQ1"]
        * 100,

        np.nan
    )

    output[
        "ClusterDeviationPercent"
    ] = (
        pd.to_numeric(
            output[
                "ClusterDeviationPercent"
            ],
            errors="coerce"
        )
        .clip(
            lower=0
        )
    )

    output[
        "ClusterValueGap"
    ] = np.where(
        benchmark_available,

        (
            output["ClusterQ1"]
            - output["UnitValue"]
        )
        * output["SelectedQuantity"],

        np.nan
    )

    output[
        "ClusterValueGap"
    ] = (
        pd.to_numeric(
            output[
                "ClusterValueGap"
            ],
            errors="coerce"
        )
        .clip(
            lower=0
        )
    )

    output["ClusterFlag"] = (
        benchmark_available
        & output[
            "UnitValue"
        ].lt(
            output[
                "ClusterQ1"
            ]
        )
    )

    return output


# ============================================================
# SELECT FINAL BENCHMARK
# ============================================================

def select_final_benchmark(
    dataframe: pd.DataFrame
) -> pd.DataFrame:
    """
    Select the benchmark used for operational risk scoring.

    Cluster Q1 is used when clustering was successfully applied.
    Otherwise the original Q1 benchmark is used.
    """

    output = dataframe.copy()

    use_cluster_benchmark = (
        output[
            "ClusterBenchmarkAvailable"
        ]
        .fillna(False)
        .astype(bool)
    )

    output[
        "FinalBenchmarkMethod"
    ] = np.where(
        use_cluster_benchmark,
        "CLUSTER_Q1",
        "ORIGINAL_Q1"
    )

    output[
        "FinalBenchmarkQ1"
    ] = np.where(
        use_cluster_benchmark,

        output[
            "ClusterQ1"
        ],

        output[
            "OriginalQ1"
        ]
    )

    output[
        "FinalDeviationPercent"
    ] = np.where(
        use_cluster_benchmark,

        output[
            "ClusterDeviationPercent"
        ],

        output[
            "OriginalDeviationPercent"
        ]
    )

    output[
        "PotentialValueGap"
    ] = np.where(
        use_cluster_benchmark,

        output[
            "ClusterValueGap"
        ],

        output[
            "OriginalValueGap"
        ]
    )

    output[
        "PotentialValueGap"
    ] = (
        pd.to_numeric(
            output[
                "PotentialValueGap"
            ],
            errors="coerce"
        )
        .fillna(0)
        .clip(
            lower=0
        )
    )

    output[
        "FinalDeviationPercent"
    ] = (
        pd.to_numeric(
            output[
                "FinalDeviationPercent"
            ],
            errors="coerce"
        )
        .fillna(0)
        .clip(
            lower=0
        )
    )

    return output


# ============================================================
# MODEL AGREEMENT
# ============================================================

def classify_model_agreement(
    dataframe: pd.DataFrame
) -> pd.DataFrame:
    """
    Describe whether the original and cluster methods agree.
    """

    output = dataframe.copy()

    original_flag = (
        output[
            "OriginalFlag"
        ]
        .fillna(False)
        .astype(bool)
    )

    cluster_flag = (
        output[
            "ClusterFlag"
        ]
        .fillna(False)
        .astype(bool)
    )

    cluster_available = (
        output[
            "ClusterBenchmarkAvailable"
        ]
        .fillna(False)
        .astype(bool)
    )

    output[
        "ModelAgreement"
    ] = np.select(
        [
            original_flag
            & cluster_flag,

            original_flag
            & cluster_available
            & ~cluster_flag,

            ~original_flag
            & cluster_flag,

            original_flag
            & ~cluster_available
        ],

        [
            "FLAGGED_BY_BOTH",
            "ORIGINAL_ONLY",
            "CLUSTER_ONLY",
            "ORIGINAL_ONLY_NO_CLUSTER"
        ],

        default="NOT_FLAGGED"
    )

    return output


# ============================================================
# CALCULATE RISK COMPONENTS
# ============================================================

def calculate_risk_components(
    dataframe: pd.DataFrame,
    settings: RiskSettings
) -> pd.DataFrame:
    """
    Calculate the initial operational risk components.

    Maximum score:

        Deviation component       40
        Value-gap component       25
        Peer-support component    15
        Model-agreement component 10
        Transaction-value component 10

        Total                     100
    """

    output = dataframe.copy()

    # --------------------------------------------------------
    # DEVIATION COMPONENT: 40 POINTS
    # --------------------------------------------------------

    output[
        "DeviationRiskComponent"
    ] = (
        output[
            "FinalDeviationPercent"
        ]
        .div(
            settings.deviation_cap_percent
        )
        .clip(
            lower=0,
            upper=1
        )
        .mul(40)
    )


    # --------------------------------------------------------
    # VALUE-GAP COMPONENT: 25 POINTS
    #
    # Each declaration is ranked against other declarations
    # within the same quarter.
    # --------------------------------------------------------

    output[
        "ValueGapPercentile"
    ] = (
        output[
            "PotentialValueGap"
        ]
        .rank(
            method="average",
            pct=True
        )
        .fillna(0)
    )

    output[
        "ValueGapRiskComponent"
    ] = (
        output[
            "ValueGapPercentile"
        ]
        .mul(25)
    )


    # --------------------------------------------------------
    # PEER-SUPPORT COMPONENT: 15 POINTS
    # --------------------------------------------------------

    cluster_peer_count = pd.to_numeric(
        output[
            "ClusterPeerCount"
        ],
        errors="coerce"
    )

    original_peer_count = pd.to_numeric(
        output[
            "PeerCount"
        ],
        errors="coerce"
    )

    output[
        "FinalPeerCount"
    ] = np.where(
        output[
            "ClusterBenchmarkAvailable"
        ]
        .fillna(False)
        .astype(bool),

        cluster_peer_count,

        original_peer_count
    )

    output[
        "FinalPeerCount"
    ] = (
        pd.to_numeric(
            output[
                "FinalPeerCount"
            ],
            errors="coerce"
        )
        .fillna(0)
    )

    output[
        "PeerSupportRiskComponent"
    ] = (
        output[
            "FinalPeerCount"
        ]
        .div(
            settings.peer_count_cap
        )
        .clip(
            lower=0,
            upper=1
        )
        .mul(15)
    )


    # --------------------------------------------------------
    # MODEL-AGREEMENT COMPONENT: 10 POINTS
    # --------------------------------------------------------

    agreement_points = {
        "FLAGGED_BY_BOTH": 10,
        "CLUSTER_ONLY": 8,
        "ORIGINAL_ONLY_NO_CLUSTER": 6,
        "ORIGINAL_ONLY": 4,
        "NOT_FLAGGED": 0
    }

    output[
        "ModelAgreementRiskComponent"
    ] = (
        output[
            "ModelAgreement"
        ]
        .map(
            agreement_points
        )
        .fillna(0)
        .astype(float)
    )


    # --------------------------------------------------------
    # TRANSACTION-VALUE COMPONENT: 10 POINTS
    # --------------------------------------------------------

    output[
        "FOBValueNumeric"
    ] = (
        pd.to_numeric(
            output[
                "FOBValue"
            ],
            errors="coerce"
        )
        .fillna(0)
        .clip(
            lower=0
        )
    )

    output[
        "FOBValuePercentile"
    ] = (
        output[
            "FOBValueNumeric"
        ]
        .rank(
            method="average",
            pct=True
        )
        .fillna(0)
    )

    output[
        "TransactionValueRiskComponent"
    ] = (
        output[
            "FOBValuePercentile"
        ]
        .mul(10)
    )

    return output


# ============================================================
# FINAL SCORE AND CASE STATUS
# ============================================================

def calculate_final_case_score(
    dataframe: pd.DataFrame,
    settings: RiskSettings
) -> pd.DataFrame:
    """
    Calculate the final score, risk level and potential-case
    status.
    """

    output = dataframe.copy()

    component_columns = [
        "DeviationRiskComponent",
        "ValueGapRiskComponent",
        "PeerSupportRiskComponent",
        "ModelAgreementRiskComponent",
        "TransactionValueRiskComponent"
    ]

    output[
        "CaseRiskScore"
    ] = (
        output[
            component_columns
        ]
        .sum(
            axis=1
        )
        .clip(
            lower=0,
            upper=100
        )
        .round(2)
    )

    output[
        "CaseRiskLevel"
    ] = np.select(
        [
            output[
                "CaseRiskScore"
            ]
            .ge(
                settings.high_risk_threshold
            ),

            output[
                "CaseRiskScore"
            ]
            .ge(
                settings.medium_risk_threshold
            ),

            output[
                "CaseRiskScore"
            ]
            .gt(0)
        ],

        [
            "High Risk",
            "Medium Risk",
            "Low Risk"
        ],

        default="Not Flagged"
    )

    benchmark_flag = (
        output[
            "OriginalFlag"
        ]
        .fillna(False)
        .astype(bool)
        |
        output[
            "ClusterFlag"
        ]
        .fillna(False)
        .astype(bool)
    )

    output[
        "IsPotentialCase"
    ] = (
        benchmark_flag
        & output[
            "FinalDeviationPercent"
        ]
        .ge(
            settings.minimum_deviation_percent
        )
        & output[
            "PotentialValueGap"
        ]
        .ge(
            settings.minimum_value_gap
        )
    )

    output[
        "ModelVersion"
    ] = settings.model_version

    return output


# ============================================================
# CASE REASON
# ============================================================

def create_case_reason(
    dataframe: pd.DataFrame
) -> pd.DataFrame:
    """
    Create a simple operational explanation for each record.
    """

    output = dataframe.copy()

    output[
        "CaseReason"
    ] = np.where(
        output[
            "IsPotentialCase"
        ],

        (
            output[
                "FinalBenchmarkMethod"
            ]
            .fillna(
                "UNKNOWN"
            )
            .astype(str)
            + " benchmark; unit value "
            + output[
                "FinalDeviationPercent"
            ]
            .fillna(0)
            .round(2)
            .astype(str)
            + "% below Q1; possible value gap E"
            + output[
                "PotentialValueGap"
            ]
            .fillna(0)
            .round(2)
            .astype(str)
            + "; model result "
            + output[
                "ModelAgreement"
            ]
            .fillna(
                "UNKNOWN"
            )
            .astype(str)
        ),

        "Not selected as a potential case"
    )

    return output


# ============================================================
# RUN COMPLETE RISK ENGINE
# ============================================================

def run_risk_engine(
    dataframe: pd.DataFrame,
    settings: RiskSettings | None = None
) -> pd.DataFrame:
    """
    Run the complete quarter-level risk model.
    """

    if settings is None:

        settings = (
            RiskSettings
            .from_environment()
        )

    validate_risk_input(
        dataframe
    )

    output = convert_risk_numeric_columns(
        dataframe
    )

    output = calculate_original_indicators(
        output
    )

    output = calculate_cluster_indicators(
        output
    )

    output = select_final_benchmark(
        output
    )

    output = classify_model_agreement(
        output
    )

    output = calculate_risk_components(
        dataframe=output,
        settings=settings
    )

    output = calculate_final_case_score(
        dataframe=output,
        settings=settings
    )

    output = create_case_reason(
        output
    )

    output.sort_values(
        by=[
            "IsPotentialCase",
            "CaseRiskScore",
            "PotentialValueGap"
        ],
        ascending=[
            False,
            False,
            False
        ],
        inplace=True
    )

    output.reset_index(
        drop=True,
        inplace=True
    )

    return output