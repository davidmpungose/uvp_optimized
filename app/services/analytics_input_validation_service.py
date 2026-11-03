from __future__ import annotations

import pandas as pd


# ============================================================
# VALIDATE ANALYTICAL INPUT
# ============================================================

def validate_analytical_input(
    dataframe: pd.DataFrame
) -> dict[str, object]:
    """
    Validate the SQL-prepared DataFrame before clustering.
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
        "InterquartileRange",
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
            "Analytical input is missing "
            "required columns: "
            + ", ".join(
                missing_columns
            )
        )

    summary = {
        "rows":
            len(dataframe),

        "peer_groups":
            int(
                dataframe[
                    "PeerKey"
                ]
                .nunique(
                    dropna=True
                )
            ),

        "unique_hs":
            int(
                dataframe[
                    "HS"
                ]
                .nunique(
                    dropna=True
                )
            ),

        "unique_traders":
            int(
                dataframe[
                    "Traders"
                ]
                .nunique(
                    dropna=True
                )
            ),

        "missing_unit_values":
            int(
                dataframe[
                    "UnitValue"
                ]
                .isna()
                .sum()
            ),

        "missing_q1":
            int(
                dataframe[
                    "OriginalQ1"
                ]
                .isna()
                .sum()
            ),

        "missing_median":
            int(
                dataframe[
                    "OriginalMedian"
                ]
                .isna()
                .sum()
            ),

        "missing_q3":
            int(
                dataframe[
                    "OriginalQ3"
                ]
                .isna()
                .sum()
            ),

        "ineligible_rows":
            int(
                (
                    dataframe[
                        "IsBenchmarkEligible"
                    ]
                    != 1
                )
                .sum()
            )
    }

    return summary


# ============================================================
# PRINT VALIDATION
# ============================================================

def print_analytical_input_validation(
    year_quarter: str,
    summary: dict[str, object]
) -> None:
    """
    Print the quarter-level input validation.
    """

    print()

    print(
        "=" * 70
    )

    print(
        "ANALYTICAL INPUT VALIDATION"
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
        "Unique HS codes:",
        f"{summary['unique_hs']:,}"
    )

    print(
        "Unique traders:",
        f"{summary['unique_traders']:,}"
    )

    print(
        "Missing unit values:",
        f"{summary['missing_unit_values']:,}"
    )

    print(
        "Missing Q1:",
        f"{summary['missing_q1']:,}"
    )

    print(
        "Missing median:",
        f"{summary['missing_median']:,}"
    )

    print(
        "Missing Q3:",
        f"{summary['missing_q3']:,}"
    )

    print(
        "Ineligible rows:",
        f"{summary['ineligible_rows']:,}"
    )

    print(
        "=" * 70
    )