from __future__ import annotations

from pathlib import Path
from typing import Iterable
import math

import numpy as np
import pandas as pd
import pyodbc

from config.settings import PipelineSettings
from app.database.results_schema_sql import ResultStorageSettings


def _python_value(value):
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _records(dataframe: pd.DataFrame, columns: list[str]) -> list[tuple]:
    prepared = dataframe.reindex(columns=columns)
    return [
        tuple(_python_value(value) for value in row)
        for row in prepared.itertuples(index=False, name=None)
    ]


def _execute_many_in_batches(
    cursor: pyodbc.Cursor,
    sql: str,
    rows: list[tuple],
    batch_size: int,
) -> int:
    cursor.fast_executemany = True
    inserted = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        cursor.executemany(sql, batch)
        inserted += len(batch)
        print(f"  Inserted {inserted:,} of {len(rows):,}")
    return inserted


CLUSTER_COLUMNS = [
    "PreparedDeclarationId", "YearQuarter", "PeerKey",
    "ClusterApplied", "ClusterEligible", "ClusterEligibilityReason",
    "ClusterModel", "ClusterCount", "ClusterId", "ClusterPriceTier",
    "ClusterSilhouetteScore", "ClusterPeerCount", "ClusterQ1",
    "ClusterMedian", "ClusterQ3", "ClusterMinimumUnitValue",
    "ClusterMaximumUnitValue", "ClusterAverageUnitValue",
    "ClusterInterquartileRange", "ModelVersion",
]

CASE_COLUMNS = [
    "PreparedDeclarationId", "YearQuarter", "RegistrationDate",
    "FormNumber", "Traders", "Lib_Traders", "HS", "Lib_HS8",
    "SelectedQuantity", "SelectedUnit", "FOBValue", "UnitValue",
    "PeerCount", "OriginalQ1", "OriginalMedian", "OriginalQ3",
    "ClusterApplied", "ClusterId", "ClusterPriceTier",
    "ClusterPeerCount", "ClusterQ1", "ClusterMedian", "ClusterQ3",
    "OriginalFlag", "ClusterFlag", "FinalBenchmarkMethod",
    "FinalBenchmarkQ1", "FinalDeviationPercent", "PotentialValueGap",
    "ModelAgreement", "DeviationRiskComponent", "ValueGapRiskComponent",
    "PeerSupportRiskComponent", "ModelAgreementRiskComponent",
    "TransactionValueRiskComponent", "CaseRiskScore", "CaseRiskLevel",
    "IsPotentialCase", "CaseReason", "ModelVersion",
]


def validate_required_columns(dataframe: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = sorted(set(columns) - set(dataframe.columns))
    if missing:
        raise RuntimeError(
            f"{label} file is missing required columns: " + ", ".join(missing)
        )


def replace_cluster_quarter(
    connection: pyodbc.Connection,
    dataframe: pd.DataFrame,
    year_quarter: str,
    pipeline: PipelineSettings,
    results: ResultStorageSettings,
) -> int:
    validate_required_columns(dataframe, CLUSTER_COLUMNS, "Clustering")
    if not dataframe["YearQuarter"].astype(str).eq(year_quarter).all():
        raise RuntimeError("Clustering file contains rows outside the selected quarter.")

    table = results.quoted_name(pipeline, results.cluster_table)
    placeholders = ", ".join("?" for _ in CLUSTER_COLUMNS)
    column_sql = ", ".join(f"[{column}]" for column in CLUSTER_COLUMNS)
    insert_sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})"
    rows = _records(dataframe, CLUSTER_COLUMNS)

    cursor = connection.cursor()
    try:
        cursor.execute(f"DELETE FROM {table} WHERE YearQuarter = ?;", year_quarter)
        inserted = _execute_many_in_batches(
            cursor, insert_sql, rows, results.insert_batch_size
        )
        cursor.execute(f"SELECT COUNT_BIG(*) FROM {table} WHERE YearQuarter = ?;", year_quarter)
        stored = int(cursor.fetchone()[0])
        if stored != inserted:
            raise RuntimeError(
                f"Cluster validation failed: inserted {inserted:,}, stored {stored:,}."
            )
        connection.commit()
        return inserted
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def replace_case_quarter(
    connection: pyodbc.Connection,
    dataframe: pd.DataFrame,
    year_quarter: str,
    pipeline: PipelineSettings,
    results: ResultStorageSettings,
    potential_cases_only: bool = True,
) -> int:
    validate_required_columns(dataframe, CASE_COLUMNS, "Risk")
    quarter_data = dataframe.loc[
        dataframe["YearQuarter"].astype(str).eq(year_quarter)
    ].copy()
    if len(quarter_data) != len(dataframe):
        raise RuntimeError("Risk file contains rows outside the selected quarter.")
    if potential_cases_only:
        quarter_data = quarter_data.loc[
            quarter_data["IsPotentialCase"].fillna(False).astype(bool)
        ].copy()

    table = results.quoted_name(pipeline, results.case_table)
    placeholders = ", ".join("?" for _ in CASE_COLUMNS)
    column_sql = ", ".join(f"[{column}]" for column in CASE_COLUMNS)
    insert_sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})"
    rows = _records(quarter_data, CASE_COLUMNS)

    cursor = connection.cursor()
    try:
        cursor.execute(f"DELETE FROM {table} WHERE YearQuarter = ?;", year_quarter)
        inserted = _execute_many_in_batches(
            cursor, insert_sql, rows, results.insert_batch_size
        ) if rows else 0
        cursor.execute(f"SELECT COUNT_BIG(*) FROM {table} WHERE YearQuarter = ?;", year_quarter)
        stored = int(cursor.fetchone()[0])
        if stored != inserted:
            raise RuntimeError(
                f"Case validation failed: inserted {inserted:,}, stored {stored:,}."
            )
        connection.commit()
        return inserted
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
