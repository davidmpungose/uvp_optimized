from __future__ import annotations

import pyodbc

from config.settings import (
    PipelineSettings
)


# ============================================================
# PREPARATION SUMMARY
# ============================================================

def get_preparation_summary(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> dict[str, object]:
    """
    Return the main PreparedDeclarations statistics.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            SELECT
                COUNT_BIG(*)
                    AS PreparedRows,

                SUM(
                    CONVERT(
                        bigint,
                        IsAnalyticallyValid
                    )
                )
                    AS ValidRows,

                COUNT_BIG(*)
                -
                SUM(
                    CONVERT(
                        bigint,
                        IsAnalyticallyValid
                    )
                )
                    AS InvalidRows,

                COUNT(
                    DISTINCT
                    CASE
                        WHEN IsAnalyticallyValid = 1
                        THEN PeerKey
                        ELSE NULL
                    END
                )
                    AS ValidPeerGroups,

                MIN(RegistrationDate)
                    AS MinimumRegistrationDate,

                MAX(RegistrationDate)
                    AS MaximumRegistrationDate

            FROM {
                settings.prepared_full_name
            };
            """
        )

        row = cursor.fetchone()

        return {
            "prepared_rows":
                int(
                    row.PreparedRows
                    or 0
                ),

            "valid_rows":
                int(
                    row.ValidRows
                    or 0
                ),

            "invalid_rows":
                int(
                    row.InvalidRows
                    or 0
                ),

            "valid_peer_groups":
                int(
                    row.ValidPeerGroups
                    or 0
                ),

            "minimum_registration_date":
                row.MinimumRegistrationDate,

            "maximum_registration_date":
                row.MaximumRegistrationDate
        }

    finally:

        cursor.close()


# ============================================================
# INVALID-REASON SUMMARY
# ============================================================

def get_invalid_reason_summary(
    connection: pyodbc.Connection,
    settings: PipelineSettings | None = None
) -> list[dict[str, object]]:
    """
    Return row counts by validity or invalidity reason.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    cursor = connection.cursor()

    try:

        cursor.execute(
            f"""
            SELECT
                COALESCE(
                    InvalidReason,
                    'VALID'
                ) AS PreparationStatus,

                COUNT_BIG(*)
                    AS Rows

            FROM {
                settings.prepared_full_name
            }

            GROUP BY
                COALESCE(
                    InvalidReason,
                    'VALID'
                )

            ORDER BY
                Rows DESC;
            """
        )

        return [
            {
                "status":
                    row.PreparationStatus,

                "rows":
                    int(
                        row.Rows
                    )
            }
            for row in cursor.fetchall()
        ]

    finally:

        cursor.close()


# ============================================================
# PRINT PREPARATION VALIDATION
# ============================================================

def print_preparation_validation(
    summary: dict[str, object],
    invalid_reasons: list[
        dict[str, object]
    ]
) -> None:
    """
    Print the preparation output in a readable form.
    """

    print(
        "=" * 70
    )

    print(
        "PREPARED DECLARATIONS VALIDATION"
    )

    print(
        "=" * 70
    )

    print(
        "Prepared rows:",
        f"{summary['prepared_rows']:,}"
    )

    print(
        "Valid analytical rows:",
        f"{summary['valid_rows']:,}"
    )

    print(
        "Invalid analytical rows:",
        f"{summary['invalid_rows']:,}"
    )

    print(
        "Valid peer groups:",
        f"{summary['valid_peer_groups']:,}"
    )

    print(
        "Minimum date:",
        summary[
            "minimum_registration_date"
        ]
    )

    print(
        "Maximum date:",
        summary[
            "maximum_registration_date"
        ]
    )

    print()

    print(
        "Preparation status:"
    )

    for record in invalid_reasons:

        print(
            "  ",
            record["status"],
            ":",
            f"{record['rows']:,}"
        )

    print(
        "=" * 70
    )