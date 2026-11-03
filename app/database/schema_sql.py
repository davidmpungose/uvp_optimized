from __future__ import annotations

from config.settings import (
    PipelineSettings
)

from app.database.benchmark_sql import (
    build_original_benchmark_sql
)


# ============================================================
# SQL IDENTIFIER HELPERS
# ============================================================

def quote_identifier(
    value: str
) -> str:
    """
    Safely quote a SQL Server identifier.

    Example:
        analytics

    becomes:
        [analytics]
    """

    cleaned_value = value.replace(
        "]",
        "]]"
    )

    return f"[{cleaned_value}]"


def escape_sql_literal(
    value: str
) -> str:
    """
    Escape a string that is used as a controlled SQL literal.

    Example:
        O'Brien

    becomes:
        O''Brien
    """

    return value.replace(
        "'",
        "''"
    )


def build_object_name(
    schema_name: str,
    object_name: str
) -> str:
    """
    Build a quoted two-part SQL Server object name.

    Example:
        analytics + PreparedDeclarations

    becomes:
        [analytics].[PreparedDeclarations]
    """

    return (
        f"{quote_identifier(schema_name)}"
        f"."
        f"{quote_identifier(object_name)}"
    )


def build_unquoted_object_name(
    schema_name: str,
    object_name: str
) -> str:
    """
    Build an unquoted two-part object name for OBJECT_ID().

    Example:
        analytics.PreparedDeclarations
    """

    return (
        f"{schema_name}"
        f"."
        f"{object_name}"
    )


# ============================================================
# CREATE ANALYTICS SCHEMA
# ============================================================

def build_create_analytics_schema_sql(
    settings: PipelineSettings
) -> str:
    """
    Create the analytics schema when it does not already exist.
    """

    schema_name = (
        settings.analytics_schema
    )

    quoted_schema = quote_identifier(
        schema_name
    )

    escaped_schema_literal = (
        escape_sql_literal(
            schema_name
        )
    )

    return f"""
SET NOCOUNT ON;
SET XACT_ABORT ON;

IF SCHEMA_ID(
    N'{escaped_schema_literal}'
) IS NULL
BEGIN

    EXEC(
        N'CREATE SCHEMA {quoted_schema} '
        + N'AUTHORIZATION [dbo];'
    );

END;
"""


# ============================================================
# CREATE PIPELINE RUN-LOG TABLE
# ============================================================

def build_pipeline_run_log_sql(
    settings: PipelineSettings
) -> str:
    """
    Create the pipeline run-log table when it does not exist.

    When the table already exists, add any columns introduced
    in later project stages.
    """

    full_table_name = build_object_name(
        settings.analytics_schema,
        settings.run_log_table
    )

    object_name = build_unquoted_object_name(
        settings.analytics_schema,
        settings.run_log_table
    )

    escaped_object_name = (
        escape_sql_literal(
            object_name
        )
    )

    primary_key_name = quote_identifier(
        "PK_"
        + settings.run_log_table
    )

    started_default_name = quote_identifier(
        "DF_"
        + settings.run_log_table
        + "_StartedAt"
    )

    return f"""
-- ===========================================================
-- CREATE PIPELINE RUN-LOG TABLE
-- ===========================================================

IF OBJECT_ID(
    N'{escaped_object_name}',
    N'U'
) IS NULL
BEGIN

    CREATE TABLE {full_table_name}
    (
        RunId
            bigint IDENTITY(1, 1)
            NOT NULL,

        Operation
            varchar(50)
            NOT NULL,

        StartedAt
            datetime2(0)
            NOT NULL
            CONSTRAINT {started_default_name}
            DEFAULT SYSUTCDATETIME(),

        CompletedAt
            datetime2(0)
            NULL,

        Status
            varchar(20)
            NOT NULL,

        SourceRows
            bigint
            NULL,

        PreparedRows
            bigint
            NULL,

        ValidRows
            bigint
            NULL,

        InvalidRows
            bigint
            NULL,

        BenchmarkGroups
            bigint
            NULL,

        CaseRows
            bigint
            NULL,

        ErrorMessage
            nvarchar(4000)
            NULL,

        CONSTRAINT {primary_key_name}
            PRIMARY KEY CLUSTERED
            (
                RunId
            )
    );

END;


-- ===========================================================
-- ADD COLUMNS INTRODUCED AFTER THE INITIAL DEPLOYMENT
-- ===========================================================

IF COL_LENGTH(
    N'{escaped_object_name}',
    N'ValidRows'
) IS NULL
BEGIN

    ALTER TABLE {full_table_name}
    ADD ValidRows bigint NULL;

END;


IF COL_LENGTH(
    N'{escaped_object_name}',
    N'InvalidRows'
) IS NULL
BEGIN

    ALTER TABLE {full_table_name}
    ADD InvalidRows bigint NULL;

END;


IF COL_LENGTH(
    N'{escaped_object_name}',
    N'BenchmarkGroups'
) IS NULL
BEGIN

    ALTER TABLE {full_table_name}
    ADD BenchmarkGroups bigint NULL;

END;


IF COL_LENGTH(
    N'{escaped_object_name}',
    N'CaseRows'
) IS NULL
BEGIN

    ALTER TABLE {full_table_name}
    ADD CaseRows bigint NULL;

END;


IF COL_LENGTH(
    N'{escaped_object_name}',
    N'ErrorMessage'
) IS NULL
BEGIN

    ALTER TABLE {full_table_name}
    ADD ErrorMessage nvarchar(4000) NULL;

END;
"""

# ============================================================
# CREATE PREPARED DECLARATIONS TABLE
# ============================================================

def build_prepared_declarations_table_sql(
    settings: PipelineSettings
) -> str:
    """
    Create analytics.PreparedDeclarations.

    This table stores the source declaration records after:

    - datatype conversion;
    - registration-date preparation;
    - trader and HS standardisation;
    - quantity selection;
    - unit-value calculation;
    - peer-group creation;
    - analytical-validity assessment.
    """

    full_table_name = (
        settings.prepared_full_name
    )

    object_name = (
        settings.prepared_object_name
    )

    escaped_object_name = (
        escape_sql_literal(
            object_name
        )
    )

    created_at_default = quote_identifier(
        "DF_"
        + settings.prepared_table
        + "_CreatedAt"
    )

    return f"""
IF OBJECT_ID(
    N'{escaped_object_name}',
    N'U'
) IS NULL
BEGIN

    CREATE TABLE {full_table_name}
    (
        -- ===================================================
        -- SYSTEM IDENTIFIER
        -- ===================================================

        PreparedDeclarationId
            bigint IDENTITY(1, 1)
            NOT NULL,


        -- ===================================================
        -- SOURCE PERIOD
        -- ===================================================

        [Year]
            smallint
            NULL,

        [Period]
            tinyint
            NULL,

        [Day]
            tinyint
            NULL,

        RegistrationDate
            date
            NULL,

        YearMonth
            char(7)
            NULL,

        YearQuarter
            char(7)
            NULL,


        -- ===================================================
        -- DECLARATION IDENTIFIERS
        -- ===================================================

        Office
            varchar(30)
            NULL,

        Lib_Office
            nvarchar(255)
            NULL,

        DecType
            varchar(20)
            NULL,

        FormNumber
            varchar(60)
            NULL,


        -- ===================================================
        -- TRADER IDENTIFIERS
        -- ===================================================

        Traders
            varchar(60)
            NULL,

        Lib_Traders
            nvarchar(255)
            NULL,


        -- ===================================================
        -- TRANSPORT AND PROCEDURE INFORMATION
        -- ===================================================

        Transport
            varchar(30)
            NULL,

        Lib_Transport
            nvarchar(255)
            NULL,

        EPC
            varchar(20)
            NULL,

        APC
            varchar(20)
            NULL,


        -- ===================================================
        -- TRADE CLASSIFICATION
        -- ===================================================

        TRS_Trade
            varchar(20)
            NULL,

        TRS_Flow
            varchar(20)
            NULL,

        Flows
            varchar(30)
            NULL,

        SACU
            varchar(20)
            NULL,

        SADC
            varchar(20)
            NULL,


        -- ===================================================
        -- PRODUCT CLASSIFICATION
        -- ===================================================

        HS_Chapter
            varchar(10)
            NULL,

        Lib_HS_Chapter
            nvarchar(255)
            NULL,

        HS_Heading
            varchar(12)
            NULL,

        Lib_HS_Heading
            nvarchar(255)
            NULL,

        HS
            varchar(20)
            NULL,

        Lib_HS8
            nvarchar(500)
            NULL,


        -- ===================================================
        -- PARTNER COUNTRY
        -- ===================================================

        Partner
            varchar(20)
            NULL,

        Lib_Partner
            nvarchar(255)
            NULL,


        -- ===================================================
        -- DECLARED VALUES
        -- ===================================================

        FOBValue
            decimal(28, 4)
            NULL,

        CIFValue
            decimal(28, 4)
            NULL,

        SZLValue
            decimal(28, 4)
            NULL,

        USDValue
            decimal(28, 4)
            NULL,


        -- ===================================================
        -- TAX VALUES
        -- ===================================================

        VAT
            decimal(28, 4)
            NULL,

        CDGVal
            decimal(28, 4)
            NULL,

        ATLVal
            decimal(28, 4)
            NULL,

        MVLVal
            decimal(28, 4)
            NULL,

        EDAVal
            decimal(28, 4)
            NULL,


        -- ===================================================
        -- SOURCE QUANTITIES
        -- ===================================================

        NetWeight
            decimal(28, 6)
            NULL,

        QTY
            decimal(28, 6)
            NULL,

        SU
            varchar(30)
            NULL,


        -- ===================================================
        -- ANALYTICAL QUANTITY
        -- ===================================================

        SelectedQuantity
            decimal(28, 6)
            NULL,

        SelectedUnit
            varchar(30)
            NULL,


        -- ===================================================
        -- UNIT-VALUE ANALYSIS
        -- ===================================================

        UnitValue
            decimal(28, 8)
            NULL,

        HSQuarter
            varchar(40)
            NULL,

        PeerKey
            varchar(100)
            NULL,


        -- ===================================================
        -- ANALYTICAL VALIDITY
        -- ===================================================

        IsAnalyticallyValid
            bit
            NOT NULL,

        InvalidReason
            varchar(100)
            NULL,


        -- ===================================================
        -- RECORD METADATA
        -- ===================================================

        CreatedAt
            datetime2(0)
            NOT NULL
            CONSTRAINT {created_at_default}
            DEFAULT SYSUTCDATETIME()
    )
    ON [PRIMARY];

END;
"""


# ============================================================
# CREATE PREPARED TABLE INDEXES
# ============================================================

def build_prepared_declarations_indexes_sql(
    settings: PipelineSettings
) -> str:
    """
    Create indexes required by the main analytical queries.

    We begin with conventional SQL Server indexes to keep
    Stage 2 understandable and easy to troubleshoot.

    Columnstore will be considered after the table has been
    populated and tested.
    """

    full_table_name = (
        settings.prepared_full_name
    )

    object_name = (
        settings.prepared_object_name
    )

    escaped_object_name = (
        escape_sql_literal(
            object_name
        )
    )

    identity_index = quote_identifier(
        "UX_"
        + settings.prepared_table
        + "_Id"
    )

    period_index = quote_identifier(
        "IX_"
        + settings.prepared_table
        + "_Period"
    )

    peer_index = quote_identifier(
        "IX_"
        + settings.prepared_table
        + "_Peer"
    )

    trader_index = quote_identifier(
        "IX_"
        + settings.prepared_table
        + "_Trader"
    )

    declaration_index = quote_identifier(
        "IX_"
        + settings.prepared_table
        + "_Declaration"
    )

    validity_index = quote_identifier(
        "IX_"
        + settings.prepared_table
        + "_Validity"
    )

    return f"""
-- ===========================================================
-- UNIQUE PREPARED-ROW IDENTIFIER
-- ===========================================================

IF NOT EXISTS
(
    SELECT
        1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(
        N'{escaped_object_name}'
    )
      AND name = N'UX_{settings.prepared_table}_Id'
)
BEGIN

    CREATE UNIQUE NONCLUSTERED INDEX
        {identity_index}
    ON {full_table_name}
    (
        PreparedDeclarationId
    );

END;


-- ===========================================================
-- PERIOD FILTERING
-- ===========================================================

IF NOT EXISTS
(
    SELECT
        1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(
        N'{escaped_object_name}'
    )
      AND name = N'IX_{settings.prepared_table}_Period'
)
BEGIN

    CREATE NONCLUSTERED INDEX
        {period_index}
    ON {full_table_name}
    (
        YearQuarter,
        YearMonth
    )
    INCLUDE
    (
        RegistrationDate,
        HS,
        Traders,
        FOBValue,
        VAT,
        UnitValue,
        IsAnalyticallyValid
    );

END;


-- ===========================================================
-- PEER-BENCHMARK GROUPING
-- ===========================================================

IF NOT EXISTS
(
    SELECT
        1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(
        N'{escaped_object_name}'
    )
      AND name = N'IX_{settings.prepared_table}_Peer'
)
BEGIN

    CREATE NONCLUSTERED INDEX
        {peer_index}
    ON {full_table_name}
    (
        YearQuarter,
        HS,
        SelectedUnit
    )
    INCLUDE
    (
        UnitValue,
        SelectedQuantity,
        FOBValue,
        Traders,
        FormNumber,
        IsAnalyticallyValid
    );

END;


-- ===========================================================
-- TRADER-HISTORY LOOKUPS
-- ===========================================================

IF NOT EXISTS
(
    SELECT
        1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(
        N'{escaped_object_name}'
    )
      AND name = N'IX_{settings.prepared_table}_Trader'
)
BEGIN

    CREATE NONCLUSTERED INDEX
        {trader_index}
    ON {full_table_name}
    (
        Traders,
        YearQuarter
    )
    INCLUDE
    (
        Lib_Traders,
        RegistrationDate,
        FormNumber,
        HS,
        Lib_HS8,
        FOBValue,
        VAT,
        SelectedQuantity,
        SelectedUnit,
        UnitValue
    );

END;


-- ===========================================================
-- DECLARATION LOOKUPS
-- ===========================================================

IF NOT EXISTS
(
    SELECT
        1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(
        N'{escaped_object_name}'
    )
      AND name = N'IX_{settings.prepared_table}_Declaration'
)
BEGIN

    CREATE NONCLUSTERED INDEX
        {declaration_index}
    ON {full_table_name}
    (
        FormNumber,
        RegistrationDate
    )
    INCLUDE
    (
        Traders,
        HS,
        FOBValue,
        SelectedQuantity,
        UnitValue
    );

END;


-- ===========================================================
-- VALID ANALYTICAL ROWS
-- ===========================================================

IF NOT EXISTS
(
    SELECT
        1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(
        N'{escaped_object_name}'
    )
      AND name = N'IX_{settings.prepared_table}_Validity'
)
BEGIN

    CREATE NONCLUSTERED INDEX
        {validity_index}
    ON {full_table_name}
    (
        IsAnalyticallyValid,
        YearQuarter
    )
    INCLUDE
    (
        HS,
        SelectedUnit,
        UnitValue,
        InvalidReason
    );

END;
"""


# ============================================================
# CREATE ORIGINAL BENCHMARKS TABLE
# ============================================================

def build_original_benchmarks_table_sql(
    settings: PipelineSettings
) -> str:
    """
    Create the table that stores original unit-value benchmarks.

    Each row represents one peer group defined by:

        HS
        + YearQuarter
        + SelectedUnit
    """

    full_table_name = (
        settings.benchmark_full_name
    )

    object_name = (
        settings.benchmark_object_name
    )

    escaped_object_name = (
        escape_sql_literal(
            object_name
        )
    )

    primary_key_name = quote_identifier(
        "PK_"
        + settings.benchmark_table
    )

    calculated_at_default = quote_identifier(
        "DF_"
        + settings.benchmark_table
        + "_CalculatedAt"
    )

    return f"""
IF OBJECT_ID(
    N'{escaped_object_name}',
    N'U'
) IS NULL
BEGIN

    CREATE TABLE {full_table_name}
    (
        -- ===================================================
        -- PEER-GROUP IDENTIFIERS
        -- ===================================================

        HS
            varchar(20)
            NOT NULL,

        YearQuarter
            char(7)
            NOT NULL,

        SelectedUnit
            varchar(30)
            NOT NULL,

        PeerKey
            varchar(100)
            NOT NULL,


        -- ===================================================
        -- PEER-GROUP SIZE
        -- ===================================================

        PeerCount
            bigint
            NOT NULL,


        -- ===================================================
        -- UNIT-VALUE DISTRIBUTION
        -- ===================================================

        OriginalQ1
            decimal(28, 8)
            NULL,

        OriginalMedian
            decimal(28, 8)
            NULL,

        OriginalQ3
            decimal(28, 8)
            NULL,

        MinimumUnitValue
            decimal(28, 8)
            NULL,

        MaximumUnitValue
            decimal(28, 8)
            NULL,

        AverageUnitValue
            decimal(28, 8)
            NULL,

        UnitValueStdDev
            decimal(28, 8)
            NULL,

        InterquartileRange
            decimal(28, 8)
            NULL,


        -- ===================================================
        -- BENCHMARK QUALITY
        -- ===================================================

        IsBenchmarkEligible
            bit
            NOT NULL,

        IneligibilityReason
            varchar(100)
            NULL,


        -- ===================================================
        -- RECORD METADATA
        -- ===================================================

        CalculatedAt
            datetime2(0)
            NOT NULL
            CONSTRAINT {calculated_at_default}
            DEFAULT SYSUTCDATETIME(),


        -- ===================================================
        -- PRIMARY KEY
        -- ===================================================

        CONSTRAINT {primary_key_name}
            PRIMARY KEY CLUSTERED
            (
                HS,
                YearQuarter,
                SelectedUnit
            )
    );

END;
"""

# ============================================================
# UPDATE EXISTING ORIGINAL BENCHMARK TABLE
# ============================================================

def build_original_benchmarks_migration_sql(
    settings: PipelineSettings
) -> str:
    """
    Add benchmark columns that may be missing from an older
    version of analytics.OriginalBenchmarks.

    CREATE TABLE IF NOT EXISTS does not modify tables that
    already exist, so explicit ALTER TABLE migrations are
    required when the schema evolves.
    """

    benchmark_table = (
        settings.benchmark_full_name
    )

    benchmark_object_name = (
        settings.benchmark_object_name
    )

    escaped_object_name = (
        escape_sql_literal(
            benchmark_object_name
        )
    )

    return f"""
-- ===========================================================
-- ADD INTERQUARTILE RANGE WHEN MISSING
-- ===========================================================

IF OBJECT_ID(
    N'{escaped_object_name}',
    N'U'
) IS NOT NULL
AND COL_LENGTH(
    N'{escaped_object_name}',
    N'InterquartileRange'
) IS NULL
BEGIN

    ALTER TABLE {benchmark_table}

    ADD InterquartileRange
        decimal(28, 8)
        NULL;

END;


-- ===========================================================
-- ADD INELIGIBILITY REASON WHEN MISSING
-- ===========================================================

IF OBJECT_ID(
    N'{escaped_object_name}',
    N'U'
) IS NOT NULL
AND COL_LENGTH(
    N'{escaped_object_name}',
    N'IneligibilityReason'
) IS NULL
BEGIN

    ALTER TABLE {benchmark_table}

    ADD IneligibilityReason
        varchar(100)
        NULL;

END;


-- ===========================================================
-- ADD CALCULATED DATE WHEN MISSING
-- ===========================================================

IF OBJECT_ID(
    N'{escaped_object_name}',
    N'U'
) IS NOT NULL
AND COL_LENGTH(
    N'{escaped_object_name}',
    N'CalculatedAt'
) IS NULL
BEGIN

    ALTER TABLE {benchmark_table}

    ADD CalculatedAt
        datetime2(0)
        NULL;

    UPDATE {benchmark_table}

    SET CalculatedAt =
        SYSUTCDATETIME()

    WHERE CalculatedAt IS NULL;

END;
"""

# ============================================================
# CREATE ORIGINAL BENCHMARK INDEXES
# ============================================================

# ============================================================
# CREATE ORIGINAL BENCHMARK INDEXES
# ============================================================

def build_original_benchmark_indexes_sql(
    settings: PipelineSettings
) -> str:
    """
    Create supporting indexes for OriginalBenchmarks.

    The table already has a clustered primary key. These
    indexes support peer-key, eligibility and period lookups.
    """

    benchmark_table = (
        settings.benchmark_full_name
    )

    benchmark_object_name = (
        settings.benchmark_object_name
    )

    escaped_object_name = (
        escape_sql_literal(
            benchmark_object_name
        )
    )

    peer_key_index_name = (
        "UX_"
        + settings.benchmark_table
        + "_PeerKey"
    )

    eligibility_index_name = (
        "IX_"
        + settings.benchmark_table
        + "_Eligibility"
    )

    period_index_name = (
        "IX_"
        + settings.benchmark_table
        + "_Period"
    )

    return f"""
-- ===========================================================
-- UNIQUE PEER-KEY INDEX
-- ===========================================================

IF NOT EXISTS
(
    SELECT
        1

    FROM sys.indexes

    WHERE object_id =
        OBJECT_ID(
            N'{escaped_object_name}'
        )

      AND name =
        N'{peer_key_index_name}'
)
BEGIN

    CREATE UNIQUE NONCLUSTERED INDEX
        [{peer_key_index_name}]

    ON {benchmark_table}
    (
        PeerKey
    );

END;


-- ===========================================================
-- BENCHMARK ELIGIBILITY INDEX
-- ===========================================================

IF NOT EXISTS
(
    SELECT
        1

    FROM sys.indexes

    WHERE object_id =
        OBJECT_ID(
            N'{escaped_object_name}'
        )

      AND name =
        N'{eligibility_index_name}'
)
BEGIN

    CREATE NONCLUSTERED INDEX
        [{eligibility_index_name}]

    ON {benchmark_table}
    (
        IsBenchmarkEligible,
        YearQuarter
    )

    INCLUDE
    (
        HS,
        SelectedUnit,
        PeerCount,
        OriginalQ1,
        OriginalMedian,
        OriginalQ3,
        InterquartileRange
    );

END;


-- ===========================================================
-- PERIOD AND HS INDEX
-- ===========================================================

IF NOT EXISTS
(
    SELECT
        1

    FROM sys.indexes

    WHERE object_id =
        OBJECT_ID(
            N'{escaped_object_name}'
        )

      AND name =
        N'{period_index_name}'
)
BEGIN

    CREATE NONCLUSTERED INDEX
        [{period_index_name}]

    ON {benchmark_table}
    (
        YearQuarter,
        HS,
        SelectedUnit
    )

    INCLUDE
    (
        PeerCount,
        OriginalQ1,
        OriginalMedian,
        OriginalQ3,
        MinimumUnitValue,
        MaximumUnitValue,
        AverageUnitValue,
        UnitValueStdDev,
        InterquartileRange,
        IsBenchmarkEligible
    );

END;
"""

# ============================================================
# COMPLETE SCHEMA DEPLOYMENT
# ============================================================

def build_complete_schema_sql(
    settings: PipelineSettings | None = None
) -> str:
    """
    Build the complete schema-deployment script.

    The deployment creates:

    1. analytics schema;
    2. pipeline run-log table;
    3. prepared declarations table;
    4. prepared-table indexes;
    5. original benchmark table;
    6. benchmark-table indexes.
    """

    if settings is None:

        settings = (
            PipelineSettings
            .from_environment()
        )

    settings.validate()

    sql_sections = [
    build_create_analytics_schema_sql(
        settings
    ),

    build_pipeline_run_log_sql(
        settings
    ),

    build_prepared_declarations_table_sql(
        settings
    ),

    build_prepared_declarations_indexes_sql(
        settings
    ),

    build_original_benchmarks_table_sql(
        settings
    ),

    build_original_benchmarks_migration_sql(
        settings
    ),

    build_original_benchmark_indexes_sql(
        settings
    )
    ]

    
    complete_sql = "\n\n".join(
        section.strip()
        for section in sql_sections
        if section.strip()
    )

    return (
        complete_sql
        + "\n"
    )