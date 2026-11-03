from __future__ import annotations

import html
import re

from config.settings import (
    PipelineSettings
)


# ============================================================
# SQL-LITERAL HELPERS
# ============================================================

def escape_sql_literal(
    value: str
) -> str:
    """
    Escape a controlled string value for use in generated SQL.

    Runtime user input must still be supplied through SQL
    parameters rather than inserted into SQL text.
    """

    return value.replace(
        "'",
        "''"
    )


def build_unicode_sql_literal(
    value: str
) -> str:
    """
    Convert a controlled Python string into an escaped
    SQL Server Unicode literal.

    Example:
        Imports

    becomes:
        N'Imports'
    """

    escaped_value = escape_sql_literal(
        value
    )

    return (
        f"N'{escaped_value}'"
    )


def build_sql_literal_list(
    values: tuple[str, ...]
) -> str:
    """
    Convert a tuple into a comma-separated SQL literal list.

    Example:
        ("G", "2")

    becomes:
        N'G', N'2'
    """

    return ", ".join(
        build_unicode_sql_literal(
            value
        )
        for value in values
    )


# ============================================================
# BUILD FULL PREPARATION SQL
# ============================================================

def build_full_preparation_sql(
    settings: PipelineSettings
) -> str:
    """
    Build the SQL used to perform a complete preparation of
    the customs declarations.

    The operation:

    1. truncates analytics.PreparedDeclarations;
    2. filters relevant imports;
    3. standardises source fields;
    4. selects the analytical quantity;
    5. calculates unit values;
    6. classifies valid and invalid rows;
    7. returns preparation counts.
    """

    settings.validate()

    source_table = (
        settings.source_full_name
    )

    prepared_table = (
        settings.prepared_full_name
    )

    import_flow_literal = (
        build_unicode_sql_literal(
            settings.import_flow_value
        )
    )

    merchandise_trade_literals = (
        build_sql_literal_list(
            settings.merchandise_trade_values
        )
    )

    maximum_unit_value_case = ""

    maximum_unit_value_reason = ""

    if (
        settings.maximum_unit_value
    is not None
    ):

        maximum_unit_value = float(
            settings.maximum_unit_value
        )

        maximum_unit_value_case = (
            "\n"
            "            WHEN key_prepared.UnitValue > "
            f"{maximum_unit_value}\n"
            "            THEN 0\n"
        )

        maximum_unit_value_reason = (
            "\n"
            "            WHEN key_prepared.UnitValue > "
            f"{maximum_unit_value}\n"
            "            THEN "
            "'UNIT_VALUE_ABOVE_LIMIT'\n"
        )

    return f"""
SET NOCOUNT ON;
SET XACT_ABORT ON;


-- ===========================================================
-- CLEAR THE EXISTING PREPARED TABLE
-- ===========================================================

TRUNCATE TABLE {prepared_table};


-- ===========================================================
-- PREPARE SOURCE DECLARATIONS
-- ===========================================================

;WITH SourcePrepared AS
(
    SELECT
        TRY_CONVERT(
            smallint,
            source_data.[Year]
        ) AS [Year],

        TRY_CONVERT(
            tinyint,
            source_data.[Period]
        ) AS [Period],

        TRY_CONVERT(
            tinyint,
            source_data.[Day]
        ) AS [Day],


        -- ---------------------------------------------------
        -- CREATE A VALID REGISTRATION DATE
        -- ---------------------------------------------------

        TRY_CONVERT(
            date,

            CONCAT(
                TRY_CONVERT(
                    varchar(4),
                    source_data.[Year]
                ),

                '-',

                RIGHT(
                    '0'
                    + TRY_CONVERT(
                        varchar(2),
                        source_data.[Period]
                    ),
                    2
                ),

                '-',

                RIGHT(
                    '0'
                    + TRY_CONVERT(
                        varchar(2),
                        source_data.[Day]
                    ),
                    2
                )
            )
        ) AS RegistrationDate,


        -- ---------------------------------------------------
        -- OFFICE AND DECLARATION IDENTIFIERS
        -- ---------------------------------------------------

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(30),
                        source_data.[Office]
                    )
                )
            ),
            ''
        ) AS Office,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        nvarchar(255),
                        source_data.[Lib_Office]
                    )
                )
            ),
            ''
        ) AS Lib_Office,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(20),
                        source_data.[DecType]
                    )
                )
            ),
            ''
        ) AS DecType,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(60),
                        source_data.[FormNumber]
                    )
                )
            ),
            ''
        ) AS FormNumber,


        -- ---------------------------------------------------
        -- TRADER IDENTIFIERS
        -- ---------------------------------------------------

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(60),
                        source_data.[Traders]
                    )
                )
            ),
            ''
        ) AS Traders,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        nvarchar(255),
                        source_data.[Lib_Traders]
                    )
                )
            ),
            ''
        ) AS Lib_Traders,


        -- ---------------------------------------------------
        -- TRANSPORT AND PROCEDURES
        -- ---------------------------------------------------

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(30),
                        source_data.[Transport]
                    )
                )
            ),
            ''
        ) AS Transport,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        nvarchar(255),
                        source_data.[Lib_Transport]
                    )
                )
            ),
            ''
        ) AS Lib_Transport,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(20),
                        source_data.[EPC]
                    )
                )
            ),
            ''
        ) AS EPC,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(20),
                        source_data.[APC]
                    )
                )
            ),
            ''
        ) AS APC,


        -- ---------------------------------------------------
        -- TRADE CLASSIFICATION
        -- ---------------------------------------------------

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(20),
                        source_data.[TRS_Trade]
                    )
                )
            ),
            ''
        ) AS TRS_Trade,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(20),
                        source_data.[TRS_Flow]
                    )
                )
            ),
            ''
        ) AS TRS_Flow,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(30),
                        source_data.[Flows]
                    )
                )
            ),
            ''
        ) AS Flows,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(20),
                        source_data.[SACU]
                    )
                )
            ),
            ''
        ) AS SACU,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(20),
                        source_data.[SADC]
                    )
                )
            ),
            ''
        ) AS SADC,


        -- ---------------------------------------------------
        -- PRODUCT CLASSIFICATION
        -- ---------------------------------------------------

        NULLIF(
            RIGHT(
                '00'
                + LTRIM(
                    RTRIM(
                        TRY_CONVERT(
                            varchar(10),
                            source_data.[HS_Chapter]
                        )
                    )
                ),
                2
            ),
            ''
        ) AS HS_Chapter,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        nvarchar(255),
                        source_data.[Lib_HS_Chapter]
                    )
                )
            ),
            ''
        ) AS Lib_HS_Chapter,

        NULLIF(
            RIGHT(
                '0000'
                + LTRIM(
                    RTRIM(
                        TRY_CONVERT(
                            varchar(12),
                            source_data.[HS_Heading]
                        )
                    )
                ),
                4
            ),
            ''
        ) AS HS_Heading,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        nvarchar(255),
                        source_data.[Lib_HS_Heading]
                    )
                )
            ),
            ''
        ) AS Lib_HS_Heading,

        NULLIF(
            RIGHT(
                '00000000'
                + LTRIM(
                    RTRIM(
                        TRY_CONVERT(
                            varchar(20),
                            source_data.[HS]
                        )
                    )
                ),
                8
            ),
            ''
        ) AS HS,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        nvarchar(500),
                        source_data.[Lib_HS8]
                    )
                )
            ),
            ''
        ) AS Lib_HS8,


        -- ---------------------------------------------------
        -- PARTNER
        -- ---------------------------------------------------

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        varchar(20),
                        source_data.[Partner]
                    )
                )
            ),
            ''
        ) AS Partner,

        NULLIF(
            LTRIM(
                RTRIM(
                    TRY_CONVERT(
                        nvarchar(255),
                        source_data.[Lib_Partner]
                    )
                )
            ),
            ''
        ) AS Lib_Partner,


        -- ---------------------------------------------------
        -- DECLARED VALUES
        -- ---------------------------------------------------

        TRY_CONVERT(
            decimal(28, 4),
            source_data.[FOBValue]
        ) AS FOBValue,

        TRY_CONVERT(
            decimal(28, 4),
            source_data.[CIFValue]
        ) AS CIFValue,

        TRY_CONVERT(
            decimal(28, 4),
            source_data.[SZLValue]
        ) AS SZLValue,

        TRY_CONVERT(
            decimal(28, 4),
            source_data.[USDValue]
        ) AS USDValue,


        -- ---------------------------------------------------
        -- TAX VALUES
        -- ---------------------------------------------------

        TRY_CONVERT(
            decimal(28, 4),
            source_data.[VAT]
        ) AS VAT,

        TRY_CONVERT(
            decimal(28, 4),
            source_data.[CDGVal]
        ) AS CDGVal,

        TRY_CONVERT(
            decimal(28, 4),
            source_data.[ATLVal]
        ) AS ATLVal,

        TRY_CONVERT(
            decimal(28, 4),
            source_data.[MVLVal]
        ) AS MVLVal,

        TRY_CONVERT(
            decimal(28, 4),
            source_data.[EDAVal]
        ) AS EDAVal,


        -- ---------------------------------------------------
        -- SOURCE QUANTITIES
        -- ---------------------------------------------------

        TRY_CONVERT(
            decimal(28, 6),
            source_data.[NetWeight]
        ) AS NetWeight,

        TRY_CONVERT(
            decimal(28, 6),
            source_data.[QTY]
        ) AS QTY,

        NULLIF(
            UPPER(
                LTRIM(
                    RTRIM(
                        TRY_CONVERT(
                            varchar(30),
                            source_data.[SU]
                        )
                    )
                )
            ),
            ''
        ) AS SU

    FROM {source_table}
        AS source_data

    WHERE
        LTRIM(
            RTRIM(
                TRY_CONVERT(
                    varchar(20),
                    source_data.[TRS_Trade]
                )
            )
        )
        IN
        (
            {merchandise_trade_literals}
        )

        AND
        (
            UPPER(
                LTRIM(
                    RTRIM(
                        TRY_CONVERT(
                            varchar(30),
                            source_data.[Flows]
                        )
                    )
                )
            )
            = UPPER(
                {import_flow_literal}
            )

            OR

            UPPER(
                LTRIM(
                    RTRIM(
                        TRY_CONVERT(
                            varchar(30),
                            source_data.[TRS_Flow]
                        )
                    )
                )
            )
            = UPPER(
                {import_flow_literal}
            )
        )
),


-- ===========================================================
-- CREATE PERIOD VARIABLES
-- ===========================================================

PeriodPrepared AS
(
    SELECT
        source_prepared.*,

        CASE
            WHEN
                source_prepared.RegistrationDate
                IS NOT NULL
            THEN
                CONVERT(
                    char(7),
                    source_prepared.RegistrationDate,
                    120
                )

            ELSE NULL
        END AS YearMonth,

        CASE
            WHEN
                source_prepared.RegistrationDate
                IS NOT NULL
            THEN
                CONCAT(
                    DATEPART(
                        year,
                        source_prepared.RegistrationDate
                    ),

                    '-Q',

                    DATEPART(
                        quarter,
                        source_prepared.RegistrationDate
                    )
                )

            ELSE NULL
        END AS YearQuarter

    FROM SourcePrepared
        AS source_prepared
),


-- ===========================================================
-- SELECT THE COMPARABLE QUANTITY
-- ===========================================================

QuantityPrepared AS
(
    SELECT
        period_prepared.*,

        CASE
            WHEN
                period_prepared.QTY > 0
                AND period_prepared.SU
                    IS NOT NULL
            THEN period_prepared.QTY

            WHEN
                period_prepared.NetWeight > 0
            THEN period_prepared.NetWeight

            ELSE NULL
        END AS SelectedQuantity,

        CASE
            WHEN
                period_prepared.QTY > 0
                AND period_prepared.SU
                    IS NOT NULL
            THEN period_prepared.SU

            WHEN
                period_prepared.NetWeight > 0
            THEN 'KGM'

            ELSE NULL
        END AS SelectedUnit

    FROM PeriodPrepared
        AS period_prepared
),


-- ===========================================================
-- CALCULATE UNIT VALUE
-- ===========================================================

UnitValuePrepared AS
(
    SELECT
        quantity_prepared.*,

        CASE
            WHEN
                quantity_prepared.FOBValue
                    IS NOT NULL

                AND quantity_prepared.FOBValue >= 0

                AND quantity_prepared.SelectedQuantity > 0
            THEN TRY_CONVERT(
                decimal(28, 8),

                quantity_prepared.FOBValue
                /
                NULLIF(
                    quantity_prepared.SelectedQuantity,
                    0
                )
            )

            ELSE NULL
        END AS UnitValue

    FROM QuantityPrepared
        AS quantity_prepared
),


-- ===========================================================
-- CREATE ANALYTICAL KEYS
-- ===========================================================

KeyPrepared AS
(
    SELECT
        unit_value_prepared.*,

        CASE
            WHEN
                unit_value_prepared.HS
                    IS NOT NULL

                AND unit_value_prepared.YearQuarter
                    IS NOT NULL
            THEN CONCAT(
                unit_value_prepared.HS,
                '_',
                unit_value_prepared.YearQuarter
            )

            ELSE NULL
        END AS HSQuarter,

        CASE
            WHEN
                unit_value_prepared.HS
                    IS NOT NULL

                AND unit_value_prepared.YearQuarter
                    IS NOT NULL

                AND unit_value_prepared.SelectedUnit
                    IS NOT NULL
            THEN CONCAT(
                unit_value_prepared.HS,
                '|',
                unit_value_prepared.YearQuarter,
                '|',
                unit_value_prepared.SelectedUnit
            )

            ELSE NULL
        END AS PeerKey

    FROM UnitValuePrepared
        AS unit_value_prepared
),


-- ===========================================================
-- ASSESS ANALYTICAL VALIDITY
-- ===========================================================

ValidityPrepared AS
(
    SELECT
        key_prepared.*,

        CASE
            WHEN RegistrationDate IS NULL
            THEN 0

            WHEN HS IS NULL
            THEN 0

            WHEN FOBValue IS NULL
            THEN 0

            WHEN FOBValue < 0
            THEN 0

            WHEN SelectedQuantity IS NULL
            THEN 0

            WHEN SelectedQuantity <= 0
            THEN 0

            WHEN SelectedUnit IS NULL
            THEN 0

            WHEN UnitValue IS NULL
            THEN 0

            WHEN UnitValue < 0
            THEN 0

            {maximum_unit_value_case}

            ELSE 1
        END AS IsAnalyticallyValid,

        CASE
            WHEN RegistrationDate IS NULL
            THEN 'INVALID_REGISTRATION_DATE'

            WHEN HS IS NULL
            THEN 'MISSING_HS'

            WHEN FOBValue IS NULL
            THEN 'MISSING_FOB_VALUE'

            WHEN FOBValue < 0
            THEN 'NEGATIVE_FOB_VALUE'

            WHEN SelectedQuantity IS NULL
            THEN 'MISSING_ANALYTICAL_QUANTITY'

            WHEN SelectedQuantity <= 0
            THEN 'NON_POSITIVE_ANALYTICAL_QUANTITY'

            WHEN SelectedUnit IS NULL
            THEN 'MISSING_ANALYTICAL_UNIT'

            WHEN UnitValue IS NULL
            THEN 'MISSING_UNIT_VALUE'

            WHEN UnitValue < 0
            THEN 'NEGATIVE_UNIT_VALUE'

            {maximum_unit_value_reason}

            ELSE NULL
        END AS InvalidReason

    FROM KeyPrepared
        AS key_prepared
)


-- ===========================================================
-- LOAD THE PREPARED TABLE
-- ===========================================================

INSERT INTO {prepared_table}
(
    [Year],
    [Period],
    [Day],
    RegistrationDate,
    YearMonth,
    YearQuarter,

    Office,
    Lib_Office,
    DecType,
    FormNumber,

    Traders,
    Lib_Traders,

    Transport,
    Lib_Transport,
    EPC,
    APC,

    TRS_Trade,
    TRS_Flow,
    Flows,
    SACU,
    SADC,

    HS_Chapter,
    Lib_HS_Chapter,
    HS_Heading,
    Lib_HS_Heading,
    HS,
    Lib_HS8,

    Partner,
    Lib_Partner,

    FOBValue,
    CIFValue,
    SZLValue,
    USDValue,

    VAT,
    CDGVal,
    ATLVal,
    MVLVal,
    EDAVal,

    NetWeight,
    QTY,
    SU,

    SelectedQuantity,
    SelectedUnit,

    UnitValue,
    HSQuarter,
    PeerKey,

    IsAnalyticallyValid,
    InvalidReason
)
SELECT
    [Year],
    [Period],
    [Day],
    RegistrationDate,
    YearMonth,
    YearQuarter,

    Office,
    Lib_Office,
    DecType,
    FormNumber,

    Traders,
    Lib_Traders,

    Transport,
    Lib_Transport,
    EPC,
    APC,

    TRS_Trade,
    TRS_Flow,
    Flows,
    SACU,
    SADC,

    HS_Chapter,
    Lib_HS_Chapter,
    HS_Heading,
    Lib_HS_Heading,
    HS,
    Lib_HS8,

    Partner,
    Lib_Partner,

    FOBValue,
    CIFValue,
    SZLValue,
    USDValue,

    VAT,
    CDGVal,
    ATLVal,
    MVLVal,
    EDAVal,

    NetWeight,
    QTY,
    SU,

    SelectedQuantity,
    SelectedUnit,

    UnitValue,
    HSQuarter,
    PeerKey,

    IsAnalyticallyValid,
    InvalidReason

FROM ValidityPrepared;


-- ===========================================================
-- RETURN LOAD STATISTICS
-- ===========================================================

SELECT
    COUNT_BIG(*)
        AS PreparedRows,

    SUM(
        CASE
            WHEN IsAnalyticallyValid = 1
            THEN CONVERT(
                bigint,
                1
            )
            ELSE CONVERT(
                bigint,
                0
            )
        END
    )
        AS ValidRows,

    SUM(
        CASE
            WHEN IsAnalyticallyValid = 0
            THEN CONVERT(
                bigint,
                1
            )
            ELSE CONVERT(
                bigint,
                0
            )
        END
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
        AS ValidPeerGroups

FROM {prepared_table};
"""


# ============================================================
# BUILD QUALITY-SUMMARY SQL
# ============================================================

def build_preparation_quality_sql(
    settings: PipelineSettings
) -> str:
    """
    Return quality statistics from PreparedDeclarations.
    """

    prepared_table = (
        settings.prepared_full_name
    )

    return f"""
SET NOCOUNT ON;


-- ===========================================================
-- OVERALL PREPARATION SUMMARY
-- ===========================================================

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

FROM {prepared_table};


-- ===========================================================
-- INVALID-REASON SUMMARY
-- ===========================================================

SELECT
    COALESCE(
        InvalidReason,
        'VALID'
    ) AS PreparationStatus,

    COUNT_BIG(*)
        AS Rows

FROM {prepared_table}

GROUP BY
    COALESCE(
        InvalidReason,
        'VALID'
    )

ORDER BY
    Rows DESC;
"""