from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

import pandas as pd
import pyodbc

from config.settings import PipelineSettings
from app.database.results_schema_sql import ResultStorageSettings
from app.database.results_repository import (
    replace_cluster_quarter,
    replace_case_quarter,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def cluster_file_path(year_quarter: str) -> Path:
    directory = os.getenv("CLUSTER_OUTPUT_DIRECTORY", "output/clustering").strip()
    return PROJECT_ROOT / directory / f"clustered_{year_quarter}.parquet"


def risk_file_path(year_quarter: str) -> Path:
    directory = os.getenv("RISK_OUTPUT_DIRECTORY", "output/risk").strip()
    return PROJECT_ROOT / directory / f"risk_results_{year_quarter}.parquet"


@dataclass(frozen=True)
class ResultLoadSummary:
    year_quarter: str
    cluster_rows: int
    case_rows: int
    elapsed_seconds: float


def load_cluster_results(
    connection: pyodbc.Connection,
    year_quarter: str,
    pipeline: PipelineSettings | None = None,
    results: ResultStorageSettings | None = None,
) -> int:
    pipeline = pipeline or PipelineSettings.from_environment()
    results = results or ResultStorageSettings.from_environment()
    path = cluster_file_path(year_quarter)
    if not path.exists():
        raise FileNotFoundError(f"Clustering file not found: {path}")
    print(f"Loading clusters for {year_quarter} from {path}")
    dataframe = pd.read_parquet(path)
    if "ModelVersion" not in dataframe.columns:
        dataframe["ModelVersion"] = os.getenv("RISK_MODEL_VERSION", "UVP_SQL_V1")
    inserted = replace_cluster_quarter(
        connection, dataframe, year_quarter, pipeline, results
    )
    print(f"Cluster rows stored: {inserted:,}")
    return inserted


def load_case_results(
    connection: pyodbc.Connection,
    year_quarter: str,
    pipeline: PipelineSettings | None = None,
    results: ResultStorageSettings | None = None,
    potential_cases_only: bool = True,
) -> int:
    pipeline = pipeline or PipelineSettings.from_environment()
    results = results or ResultStorageSettings.from_environment()
    path = risk_file_path(year_quarter)
    if not path.exists():
        raise FileNotFoundError(f"Risk file not found: {path}")
    print(f"Loading risk results for {year_quarter} from {path}")
    dataframe = pd.read_parquet(path)
    inserted = replace_case_quarter(
        connection, dataframe, year_quarter, pipeline, results,
        potential_cases_only=potential_cases_only,
    )
    print(f"Case rows stored: {inserted:,}")
    return inserted


def load_quarter_results(
    connection: pyodbc.Connection,
    year_quarter: str,
    pipeline: PipelineSettings | None = None,
    results: ResultStorageSettings | None = None,
) -> ResultLoadSummary:
    started = datetime.now()
    cluster_rows = load_cluster_results(
        connection, year_quarter, pipeline, results
    )
    case_rows = load_case_results(
        connection, year_quarter, pipeline, results
    )
    return ResultLoadSummary(
        year_quarter=year_quarter,
        cluster_rows=cluster_rows,
        case_rows=case_rows,
        elapsed_seconds=(datetime.now() - started).total_seconds(),
    )
