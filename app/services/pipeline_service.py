from __future__ import annotations

import os

from dataclasses import dataclass

from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

ENV_FILE = (
    PROJECT_ROOT
    / ".env"
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv(
    dotenv_path=ENV_FILE
)


# ============================================================
# ENVIRONMENT-VARIABLE HELPERS
# ============================================================

def get_required_environment_variable(
    variable_name: str
) -> str:
    """
    Read a required setting from the environment.

    A clear error is raised when the variable is missing
    or contains only blank spaces.
    """

    value = os.getenv(
        variable_name
    )

    if value is None:

        raise ValueError(
            "Required environment variable "
            f"'{variable_name}' was not found."
        )

    cleaned_value = (
        value.strip()
    )

    if not cleaned_value:

        raise ValueError(
            "Required environment variable "
            f"'{variable_name}' is empty."
        )

    return cleaned_value


def get_environment_boolean(
    variable_name: str,
    default: bool = False
) -> bool:
    """
    Convert an environment setting into a Python boolean.

    Accepted true values:
        1
        true
        yes
        y
        on

    Accepted false values:
        0
        false
        no
        n
        off
    """

    default_text = (
        "yes"
        if default
        else "no"
    )

    raw_value = os.getenv(
        variable_name,
        default_text
    )

    cleaned_value = (
        raw_value
        .strip()
        .lower()
    )

    true_values = {
        "1",
        "true",
        "yes",
        "y",
        "on"
    }

    false_values = {
        "0",
        "false",
        "no",
        "n",
        "off"
    }

    if cleaned_value in true_values:

        return True

    if cleaned_value in false_values:

        return False

    raise ValueError(
        f"Environment variable '{variable_name}' "
        f"contains an invalid boolean value: "
        f"'{raw_value}'."
    )


def get_environment_integer(
    variable_name: str,
    default: int
) -> int:
    """
    Read an integer setting from the environment.
    """

    raw_value = os.getenv(
        variable_name,
        str(default)
    )

    try:

        return int(
            raw_value.strip()
        )

    except (
        TypeError,
        ValueError
    ) as error:

        raise ValueError(
            f"Environment variable '{variable_name}' "
            f"must be an integer. Received: "
            f"'{raw_value}'."
        ) from error


def get_environment_float(
    variable_name: str,
    default: float | None = None
) -> float | None:
    """
    Read an optional floating-point setting.

    An empty setting returns the supplied default.
    """

    raw_value = os.getenv(
        variable_name
    )

    if raw_value is None:

        return default

    cleaned_value = (
        raw_value.strip()
    )

    if not cleaned_value:

        return default

    try:

        return float(
            cleaned_value
        )

    except ValueError as error:

        raise ValueError(
            f"Environment variable '{variable_name}' "
            f"must be numeric. Received: "
            f"'{raw_value}'."
        ) from error


def split_environment_list(
    variable_name: str,
    default: str = ""
) -> tuple[str, ...]:
    """
    Convert a comma-separated environment variable into
    a tuple of cleaned values.

    Example:
        G,2

    becomes:
        ("G", "2")
    """

    raw_value = os.getenv(
        variable_name,
        default
    )

    return tuple(
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    )


def quote_sql_identifier(
    identifier: str
) -> str:
    """
    Safely quote a SQL Server identifier.

    Example:
        analytics

    becomes:
        [analytics]
    """

    cleaned_identifier = (
        identifier.replace(
            "]",
            "]]"
        )
    )

    return (
        f"[{cleaned_identifier}]"
    )


# ============================================================
# DATABASE SETTINGS
# ============================================================

@dataclass(
    frozen=True
)
class DatabaseSettings:
    """
    SQL Server connection settings.

    Values are loaded from the project's .env file.
    """

    server: str

    database: str

    driver: str

    trusted_connection: bool

    encrypt: str

    trust_server_certificate: str

    timeout_seconds: int

    username: str | None = None

    password: str | None = None

    application_name: str = (
        "Optimized UVP"
    )

    @classmethod
    def from_environment(
        cls
    ) -> "DatabaseSettings":
        """
        Create DatabaseSettings from environment variables.
        """

        trusted_connection = (
            get_environment_boolean(
                "DB_TRUSTED_CONNECTION",
                default=True
            )
        )

        username_value = os.getenv(
            "DB_USERNAME"
        )

        password_value = os.getenv(
            "DB_PASSWORD"
        )

        username = (
            username_value.strip()
            if username_value
            else None
        )

        password = (
            password_value
            if password_value
            else None
        )

        return cls(
            server=(
                get_required_environment_variable(
                    "DB_SERVER"
                )
            ),

            database=(
                get_required_environment_variable(
                    "DB_DATABASE"
                )
            ),

            driver=(
                os.getenv(
                    "DB_DRIVER",
                    "ODBC Driver 18 for SQL Server"
                )
                .strip()
            ),

            trusted_connection=(
                trusted_connection
            ),

            encrypt=(
                os.getenv(
                    "DB_ENCRYPT",
                    "yes"
                )
                .strip()
            ),

            trust_server_certificate=(
                os.getenv(
                    "DB_TRUST_SERVER_CERTIFICATE",
                    "yes"
                )
                .strip()
            ),

            timeout_seconds=(
                get_environment_integer(
                    "DB_TIMEOUT_SECONDS",
                    default=0
                )
            ),

            username=username,

            password=password,

            application_name=(
                os.getenv(
                    "DB_APPLICATION_NAME",
                    "Optimized UVP"
                )
                .strip()
            )
        )

    def connection_string(
        self
    ) -> str:
        """
        Build the connection string used by pyodbc.
        """

        connection_parts = [
            f"DRIVER={{{self.driver}}}",

            f"SERVER={self.server}",

            f"DATABASE={self.database}",

            f"Encrypt={self.encrypt}",

            (
                "TrustServerCertificate="
                f"{self.trust_server_certificate}"
            ),

            (
                "APP="
                f"{self.application_name}"
            )
        ]

        if self.trusted_connection:

            connection_parts.append(
                "Trusted_Connection=yes"
            )

        else:

            if not self.username:

                raise ValueError(
                    "DB_USERNAME is required when "
                    "DB_TRUSTED_CONNECTION is disabled."
                )

            if not self.password:

                raise ValueError(
                    "DB_PASSWORD is required when "
                    "DB_TRUSTED_CONNECTION is disabled."
                )

            connection_parts.extend(
                [
                    f"UID={self.username}",

                    f"PWD={self.password}"
                ]
            )

        return (
            ";".join(
                connection_parts
            )
            + ";"
        )


# ============================================================
# PIPELINE SETTINGS
# ============================================================

@dataclass(
    frozen=True
)
class PipelineSettings:
    """
    Settings used by the customs valuation preparation and
    analytical pipeline.

    This includes:
        - source declaration table;
        - analytics output tables;
        - trade filters;
        - benchmark settings;
        - data-extraction batch sizes.
    """

    # --------------------------------------------------------
    # SOURCE TABLE
    # --------------------------------------------------------

    source_schema: str

    source_table: str

    # --------------------------------------------------------
    # ANALYTICS SCHEMA AND TABLES
    # --------------------------------------------------------

    analytics_schema: str

    prepared_table: str

    benchmark_table: str

    period_summary_table: str

    hs_summary_table: str

    trader_summary_table: str

    case_results_table: str

    trader_history_table: str

    run_log_table: str

    # --------------------------------------------------------
    # TRADE FILTERS
    # --------------------------------------------------------

    import_flow_value: str

    merchandise_trade_values: tuple[
        str,
        ...
    ]

    # --------------------------------------------------------
    # ANALYTICAL CONTROLS
    # --------------------------------------------------------

    minimum_peer_count: int

    maximum_unit_value: float | None

    # --------------------------------------------------------
    # PROCESSING CONTROLS
    # --------------------------------------------------------

    extraction_chunk_size: int

    sql_insert_batch_size: int

    @classmethod
    def from_environment(
        cls
    ) -> "PipelineSettings":
        """
        Create PipelineSettings from the project's .env file.
        """

        settings = cls(
            # ------------------------------------------------
            # SOURCE TABLE
            # ------------------------------------------------

            source_schema=(
                os.getenv(
                    "SOURCE_SCHEMA",
                    "stg"
                )
                .strip()
            ),

            source_table=(
                os.getenv(
                    "SOURCE_TABLE",
                    "Declarations"
                )
                .strip()
            ),

            # ------------------------------------------------
            # ANALYTICS OBJECTS
            # ------------------------------------------------

            analytics_schema=(
                os.getenv(
                    "ANALYTICS_SCHEMA",
                    "analytics"
                )
                .strip()
            ),

            prepared_table=(
                os.getenv(
                    "PREPARED_TABLE",
                    "PreparedDeclarations"
                )
                .strip()
            ),

            benchmark_table=(
                os.getenv(
                    "BENCHMARK_TABLE",
                    "OriginalBenchmarks"
                )
                .strip()
            ),

            period_summary_table=(
                os.getenv(
                    "PERIOD_SUMMARY_TABLE",
                    "PeriodSummary"
                )
                .strip()
            ),

            hs_summary_table=(
                os.getenv(
                    "HS_SUMMARY_TABLE",
                    "HSPeriodSummary"
                )
                .strip()
            ),

            trader_summary_table=(
                os.getenv(
                    "TRADER_SUMMARY_TABLE",
                    "TraderPeriodSummary"
                )
                .strip()
            ),

            case_results_table=(
                os.getenv(
                    "CASE_RESULTS_TABLE",
                    "CaseResults"
                )
                .strip()
            ),

            trader_history_table=(
                os.getenv(
                    "TRADER_HISTORY_TABLE",
                    "TraderCaseHistory"
                )
                .strip()
            ),

            run_log_table=(
                os.getenv(
                    "RUN_LOG_TABLE",
                    "PipelineRunLog"
                )
                .strip()
            ),

            # ------------------------------------------------
            # TRADE FILTERS
            # ------------------------------------------------

            import_flow_value=(
                os.getenv(
                    "IMPORT_FLOW_VALUE",
                    "Imports"
                )
                .strip()
            ),

            merchandise_trade_values=(
                split_environment_list(
                    "MERCHANDISE_TRADE_VALUES",
                    default="G,2"
                )
            ),

            # ------------------------------------------------
            # ANALYTICAL CONTROLS
            # ------------------------------------------------

            minimum_peer_count=(
                get_environment_integer(
                    "MINIMUM_PEER_COUNT",
                    default=10
                )
            ),

            maximum_unit_value=(
                get_environment_float(
                    "MAXIMUM_UNIT_VALUE",
                    default=None
                )
            ),

            # ------------------------------------------------
            # PROCESSING CONTROLS
            # ------------------------------------------------

            extraction_chunk_size=(
                get_environment_integer(
                    "EXTRACTION_CHUNK_SIZE",
                    default=250000
                )
            ),

            sql_insert_batch_size=(
                get_environment_integer(
                    "SQL_INSERT_BATCH_SIZE",
                    default=50000
                )
            )
        )

        settings.validate()

        return settings

    def validate(
        self
    ) -> None:
        """
        Validate the pipeline configuration.

        Clear configuration errors are raised before SQL
        statements are generated or executed.
        """

        required_identifiers = {
            "SOURCE_SCHEMA":
                self.source_schema,

            "SOURCE_TABLE":
                self.source_table,

            "ANALYTICS_SCHEMA":
                self.analytics_schema,

            "PREPARED_TABLE":
                self.prepared_table,

            "BENCHMARK_TABLE":
                self.benchmark_table,

            "PERIOD_SUMMARY_TABLE":
                self.period_summary_table,

            "HS_SUMMARY_TABLE":
                self.hs_summary_table,

            "TRADER_SUMMARY_TABLE":
                self.trader_summary_table,

            "CASE_RESULTS_TABLE":
                self.case_results_table,

            "TRADER_HISTORY_TABLE":
                self.trader_history_table,

            "RUN_LOG_TABLE":
                self.run_log_table
        }

        for setting_name, value in (
            required_identifiers.items()
        ):

            if not value:

                raise ValueError(
                    f"{setting_name} cannot be empty."
                )

        if not self.import_flow_value:

            raise ValueError(
                "IMPORT_FLOW_VALUE cannot be empty."
            )

        if not self.merchandise_trade_values:

            raise ValueError(
                "MERCHANDISE_TRADE_VALUES must contain "
                "at least one value."
            )

        if self.minimum_peer_count < 1:

            raise ValueError(
                "MINIMUM_PEER_COUNT must be at least 1."
            )

        if (
            self.maximum_unit_value is not None
            and self.maximum_unit_value <= 0
        ):

            raise ValueError(
                "MAXIMUM_UNIT_VALUE must be greater "
                "than zero when supplied."
            )

        if self.extraction_chunk_size < 1:

            raise ValueError(
                "EXTRACTION_CHUNK_SIZE must be "
                "greater than zero."
            )

        if self.sql_insert_batch_size < 1:

            raise ValueError(
                "SQL_INSERT_BATCH_SIZE must be "
                "greater than zero."
            )

    # ========================================================
    # QUOTED OBJECT NAMES
    # ========================================================

    @property
    def source_full_name(
        self
    ) -> str:
        """
        Return the safely quoted source-table name.

        Example:
            [stg].[Declarations]
        """

        return (
            f"{quote_sql_identifier(self.source_schema)}"
            f"."
            f"{quote_sql_identifier(self.source_table)}"
        )

    @property
    def prepared_full_name(
        self
    ) -> str:
        """
        Return the quoted prepared-declarations table name.
        """

        return self.analytics_object_name(
            self.prepared_table
        )

    @property
    def benchmark_full_name(
        self
    ) -> str:
        """
        Return the quoted original-benchmarks table name.
        """

        return self.analytics_object_name(
            self.benchmark_table
        )

    @property
    def period_summary_full_name(
        self
    ) -> str:
        """
        Return the quoted period-summary table name.
        """

        return self.analytics_object_name(
            self.period_summary_table
        )

    @property
    def hs_summary_full_name(
        self
    ) -> str:
        """
        Return the quoted HS-period summary table name.
        """

        return self.analytics_object_name(
            self.hs_summary_table
        )

    @property
    def trader_summary_full_name(
        self
    ) -> str:
        """
        Return the quoted trader-period summary table name.
        """

        return self.analytics_object_name(
            self.trader_summary_table
        )

    @property
    def case_results_full_name(
        self
    ) -> str:
        """
        Return the quoted case-results table name.
        """

        return self.analytics_object_name(
            self.case_results_table
        )

    @property
    def trader_history_full_name(
        self
    ) -> str:
        """
        Return the quoted trader-history table name.
        """

        return self.analytics_object_name(
            self.trader_history_table
        )

    @property
    def run_log_full_name(
        self
    ) -> str:
        """
        Return the quoted pipeline run-log table name.
        """

        return self.analytics_object_name(
            self.run_log_table
        )

    # ========================================================
    # UNQUOTED OBJECT NAMES
    # ========================================================

    @property
    def source_object_name(
        self
    ) -> str:
        """
        Return an unquoted source-object name for OBJECT_ID().

        Example:
            stg.Declarations
        """

        return (
            f"{self.source_schema}"
            f"."
            f"{self.source_table}"
        )

    @property
    def prepared_object_name(
        self
    ) -> str:
        """
        Return the unquoted prepared-table object name.
        """

        return self.analytics_object_name(
            self.prepared_table,
            quote=False
        )

    @property
    def benchmark_object_name(
        self
    ) -> str:
        """
        Return the unquoted benchmark-table object name.
        """

        return self.analytics_object_name(
            self.benchmark_table,
            quote=False
        )

    @property
    def run_log_object_name(
        self
    ) -> str:
        """
        Return the unquoted run-log object name.
        """

        return self.analytics_object_name(
            self.run_log_table,
            quote=False
        )

    # ========================================================
    # SQL FILTER VALUES
    # ========================================================

    @property
    def merchandise_trade_sql_literals(
        self
    ) -> str:
        """
        Return merchandise-trade values as escaped SQL literals.

        Example:
            N'G', N'2'
        """

        return ", ".join(
            self.sql_string_literal(
                value
            )
            for value in (
                self.merchandise_trade_values
            )
        )

    @property
    def import_flow_sql_literal(
        self
    ) -> str:
        """
        Return the import-flow value as an escaped SQL literal.
        """

        return self.sql_string_literal(
            self.import_flow_value
        )

    # ========================================================
    # HELPER METHODS
    # ========================================================

    def analytics_object_name(
        self,
        table_name: str,
        quote: bool = True
    ) -> str:
        """
        Build a two-part analytical object name.

        When quote=True:
            [analytics].[PreparedDeclarations]

        When quote=False:
            analytics.PreparedDeclarations
        """

        if quote:

            return (
                f"{quote_sql_identifier(self.analytics_schema)}"
                f"."
                f"{quote_sql_identifier(table_name)}"
            )

        return (
            f"{self.analytics_schema}"
            f"."
            f"{table_name}"
        )

    @staticmethod
    def sql_string_literal(
        value: str
    ) -> str:
        """
        Safely escape a Python string for use as a SQL literal.

        This is used only when constructing controlled deployment
        SQL from project configuration. User-entered query values
        should still be passed as SQL parameters.
        """

        escaped_value = value.replace(
            "'",
            "''"
        )

        return (
            f"N'{escaped_value}'"
        )


# ============================================================
# CONVENIENCE FACTORY FUNCTIONS
# ============================================================

def get_database_settings() -> DatabaseSettings:
    """
    Return configured SQL Server settings.
    """

    return (
        DatabaseSettings
        .from_environment()
    )


def get_pipeline_settings() -> PipelineSettings:
    """
    Return configured customs-analytics pipeline settings.
    """

    return (
        PipelineSettings
        .from_environment()
    )