from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.services.risk_service import (
    get_risk_output_path
)


# ============================================================
# VALIDATE RISK OUTPUT
# ============================================================

def validate_risk_output(
    year_quarter: str
) -> dict[str, object]:
    """
    Validate a saved quarter risk-result file.
    """

    output_path = get_risk_output_path(
        year_quarter
    )

    if not output_path.exists():

        raise FileNotFoundError(
            f"Risk output does not exist: "
            f"{output_path}"
        )

    dataframe = pd.read_parquet(
        output_path
    )

    required_columns = {
        "PreparedDeclarationId",
        "YearQuarter",
        "Traders",
        "HS",
        "SelectedQuantity",
        "UnitValue",
        "OriginalQ1",
        "ClusterQ1",
        "OriginalFlag",
        "ClusterFlag",
        "FinalBenchmarkMethod",
        "FinalBenchmarkQ1",
        "FinalDeviationPercent",
        "PotentialValueGap",
        "ModelAgreement",
        "CaseRiskScore",
        "CaseRiskLevel",
        "IsPotentialCase",
        "CaseReason",
        "ModelVersion"
    }

    missing_columns = sorted(
        required_columns
        - set(
            dataframe.columns
        )
    )

    if missing_columns:

        raise RuntimeError(
            "Risk output is missing required columns: "
            + ", ".join(
                missing_columns
            )
        )

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

    invalid_scores = int(
        (
            dataframe[
                "CaseRiskScore"
            ].lt(0)
            |
            dataframe[
                "CaseRiskScore"
            ].gt(100)
        )
        .sum()
    )

    flagged_below_minimum_deviation = int(
        (
            potential_cases[
                "FinalDeviationPercent"
            ]
            .lt(0)
        )
        .sum()
    )

    negative_value_gaps = int(
        dataframe[
            "PotentialValueGap"
        ]
        .lt(0)
        .sum()
    )

    duplicate_ids = int(
        dataframe[
            "PreparedDeclarationId"
        ]
        .duplicated()
        .sum()
    )

    risk_levels = (
        potential_cases[
            "CaseRiskLevel"
        ]
        .value_counts()
    )

    model_agreement = (
        potential_cases[
            "ModelAgreement"
        ]
        .value_counts()
    )

    benchmark_methods = (
        potential_cases[
            "FinalBenchmarkMethod"
        ]
        .value_counts()
    )

    return {
        "output_path":
            output_path,

        "rows":
            len(
                dataframe
            ),

        "potential_cases":
            len(
                potential_cases
            ),

        "high_risk_cases":
            int(
                risk_levels.get(
                    "High Risk",
                    0
                )
            ),

        "medium_risk_cases":
            int(
                risk_levels.get(
                    "Medium Risk",
                    0
                )
            ),

        "low_risk_cases":
            int(
                risk_levels.get(
                    "Low Risk",
                    0
                )
            ),

        "total_potential_value_gap":
            float(
                potential_cases[
                    "PotentialValueGap"
                ]
                .fillna(0)
                .sum()
            ),

        "maximum_risk_score":
            float(
                dataframe[
                    "CaseRiskScore"
                ]
                .fillna(0)
                .max()
            ),

        "average_case_score":
            (
                float(
                    potential_cases[
                        "CaseRiskScore"
                    ]
                    .mean()
                )
                if not potential_cases.empty
                else 0.0
            ),

        "duplicate_prepared_ids":
            duplicate_ids,

        "invalid_scores":
            invalid_scores,

        "negative_value_gaps":
            negative_value_gaps,

        "flagged_below_minimum_deviation":
            (
                flagged_below_minimum_deviation
            ),

        "agreement_summary":
            {
                str(key):
                    int(value)
                for key, value
                in model_agreement.items()
            },

        "benchmark_method_summary":
            {
                str(key):
                    int(value)
                for key, value
                in benchmark_methods.items()
            }
    }


# ============================================================
# PRINT VALIDATION
# ============================================================

def print_risk_validation(
    year_quarter: str,
    summary: dict[str, object]
) -> None:
    """
    Print quarter risk-result validation.
    """

    print(
        "=" * 70
    )

    print(
        "RISK OUTPUT VALIDATION"
    )

    print(
        "=" * 70
    )

    print(
        "Quarter:",
        year_quarter
    )

    print(
        "Rows scored:",
        f"{summary['rows']:,}"
    )

    print(
        "Potential cases:",
        f"{summary['potential_cases']:,}"
    )

    print(
        "High-risk cases:",
        f"{summary['high_risk_cases']:,}"
    )

    print(
        "Medium-risk cases:",
        f"{summary['medium_risk_cases']:,}"
    )

    print(
        "Low-risk cases:",
        f"{summary['low_risk_cases']:,}"
    )

    print(
        "Potential value gap:",
        f"E{summary['total_potential_value_gap']:,.2f}"
    )

    print(
        "Maximum risk score:",
        f"{summary['maximum_risk_score']:,.2f}"
    )

    print(
        "Average potential-case score:",
        f"{summary['average_case_score']:,.2f}"
    )

    print()

    print(
        "Quality checks:"
    )

    print(
        "  Duplicate declaration IDs:",
        f"{summary['duplicate_prepared_ids']:,}"
    )

    print(
        "  Scores outside 0 to 100:",
        f"{summary['invalid_scores']:,}"
    )

    print(
        "  Negative value gaps:",
        f"{summary['negative_value_gaps']:,}"
    )

    print()

    print(
        "Model agreement:"
    )

    for (
        agreement,
        case_count
    ) in summary[
        "agreement_summary"
    ].items():

        print(
            "  ",
            agreement,
            ":",
            f"{case_count:,}"
        )

    print()

    print(
        "Final benchmark method:"
    )

    for (
        benchmark_method,
        case_count
    ) in summary[
        "benchmark_method_summary"
    ].items():

        print(
            "  ",
            benchmark_method,
            ":",
            f"{case_count:,}"
        )

    print()

    print(
        "Output:",
        summary["output_path"]
    )

    print(
        "=" * 70
    )