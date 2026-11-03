from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pyodbc

from config.settings import (
    DatabaseSettings
)


# ============================================================
# CREATE DATABASE CONNECTION
# ============================================================

def create_connection(
    settings: DatabaseSettings | None = None
) -> pyodbc.Connection:
    """
    Create and return a SQL Server connection.

    The caller is responsible for closing the connection
    unless database_connection() is used.
    """

    if settings is None:

        settings = (
            DatabaseSettings
            .from_environment()
        )

    connection = pyodbc.connect(
        settings.connection_string(),

        autocommit=False,

        timeout=(
            settings.timeout_seconds
        )
    )

    return connection


# ============================================================
# SAFE CONNECTION CONTEXT
# ============================================================

@contextmanager
def database_connection(
    settings: DatabaseSettings | None = None
) -> Iterator[
    pyodbc.Connection
]:
    """
    Open a SQL Server connection and close it automatically.

    If an error occurs, roll back the active transaction.
    """

    connection = create_connection(
        settings
    )

    try:

        yield connection

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()