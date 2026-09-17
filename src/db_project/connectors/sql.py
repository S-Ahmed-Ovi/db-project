"""
db_project/connectors/sql.py — dialect-agnostic SQL connector.

One class handles postgres/mysql/mariadb/sqlite/mssql via SQLAlchemy's
create_engine dialect string, instead of a class per DB. Reads (query) and
writes (write_dataframe → used to "convert an upload into a database table")
both go through here.

Drivers are installed separately per dialect (see requirements.txt):
    postgres -> psycopg2-binary
    mysql    -> pymysql
    mssql    -> pyodbc (+ system ODBC driver)
    sqlite   -> built into Python, no driver needed
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote_plus

import pandas as pd

from ..exceptions import ConnectionError as DBConnectionError
from ..exceptions import IngestionError
from ..logging_utils import logger, redact_url

_DIALECT_DRIVERS = {
    "postgres":   "postgresql+psycopg2",
    "postgresql": "postgresql+psycopg2",
    "mysql":      "mysql+pymysql",
    "mariadb":    "mysql+pymysql",
    "mssql":      "mssql+pyodbc",
    "sqlite":     "sqlite",
}


class SQLConnector:
    """Tenant/project-agnostic SQL connector. Give it host/port already resolved
    (i.e. if a tunnel was opened, pass the tunneled 127.0.0.1 host/port here)."""

    def __init__(
        self,
        dialect: str,
        host: str = "",
        port: int = 0,
        database: str = "",
        username: str = "",
        password: str = "",
        ssl: bool = True,
        connect_timeout: int = 30,
        extra_params: Optional[dict] = None,
        label: str = "",
    ) -> None:
        self.dialect = dialect.lower()
        if self.dialect not in _DIALECT_DRIVERS:
            raise ValueError(f"Unsupported dialect '{dialect}'. Choose from {sorted(_DIALECT_DRIVERS)}.")
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.ssl = ssl
        self.connect_timeout = connect_timeout
        self.extra_params = extra_params or {}
        self.label = label or f"{dialect}:{database}"
        self._engine = None

    def __enter__(self) -> "SQLConnector":
        self.connect()
        return self

    def __exit__(self, *_exc) -> None:
        self.disconnect()

    # ── connection URL ───────────────────────────────────────────────────

    def _url(self) -> str:
        driver = _DIALECT_DRIVERS[self.dialect]
        if self.dialect == "sqlite":
            # database is a file path here, or ":memory:"
            return "sqlite://" if self.database == ":memory:" else f"sqlite:///{self.database}"
        user = quote_plus(self.username)
        pw = quote_plus(self.password)
        return f"{driver}://{user}:{pw}@{self.host}:{self.port}/{self.database}"

    def connect(self) -> None:
        from sqlalchemy import create_engine, text

        connect_args: dict = {}
        if self.dialect != "sqlite":
            connect_args["connect_timeout"] = self.connect_timeout
            if self.dialect in ("postgres", "postgresql") and self.ssl:
                connect_args["sslmode"] = "require"
            if self.dialect in ("mysql", "mariadb") and self.ssl:
                connect_args["ssl"] = {"ssl_disabled": False}
        connect_args.update(self.extra_params)

        kwargs = dict(connect_args=connect_args, pool_pre_ping=True)
        if self.dialect != "sqlite":
            kwargs.update(pool_size=5, max_overflow=10)

        logger.info("Connecting to %s (%s)", self.dialect, self.label)
        try:
            self._engine = create_engine(self._url(), **kwargs)
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            self._engine = None
            logger.info("Connection failed for %s (%s): %s", self.dialect, self.label,
                        redact_url(self._url()))
            raise DBConnectionError(
                f"Could not connect to {self.dialect} source '{self.label}': {exc}"
            ) from exc
        logger.info("Connected to %s (%s)", self.dialect, self.label)

    def disconnect(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Disconnected from %s (%s)", self.dialect, self.label)

    # ── read ─────────────────────────────────────────────────────────────

    def query(self, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        self._require_connected()
        from sqlalchemy import text
        logger.info("Running query on %s (%s)", self.dialect, self.label)
        with self._engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params or {})
        logger.info("Query returned %d row(s) from %s", len(df), self.label)
        return df

    def get_table_names(self) -> list[str]:
        self._require_connected()
        from sqlalchemy import inspect
        return inspect(self._engine).get_table_names()

    def get_schema(self, table_name: str) -> list[dict]:
        """Column-level schema for `table_name`: name, detected_type
        (SQLAlchemy type as a string), and nullable."""
        self._require_connected()
        from sqlalchemy import inspect
        insp = inspect(self._engine)
        return [
            {"name": col["name"], "detected_type": str(col["type"]), "nullable": bool(col["nullable"])}
            for col in insp.get_columns(table_name)
        ]

    # ── write (the "convert upload -> database" step) ──────────────────────

    def write_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "replace",     # "replace" | "append" | "fail" | "upsert"
        chunksize: int = 5000,
        dtype: Optional[dict] = None,
        upsert_keys: Optional[list[str]] = None,
    ) -> int:
        """
        Write a DataFrame into `table_name` on this connection.
        Returns number of rows written.

        `if_exists="upsert"` requires `upsert_keys` (the column(s) that
        uniquely identify a row) and merges: existing rows with matching
        keys are updated, new rows are inserted. Implemented as
        stage-then-merge so it works the same way across postgres/mysql/
        mariadb/mssql/sqlite without relying on a dialect-specific
        "ON CONFLICT"/"ON DUPLICATE KEY" clause.
        """
        self._require_connected()
        if if_exists not in ("replace", "append", "fail", "upsert"):
            raise ValueError("if_exists must be 'replace', 'append', 'fail', or 'upsert'")

        logger.info("Writing %d row(s) to %s.%s (if_exists=%s)", len(df), self.label,
                    table_name, if_exists)
        try:
            if if_exists == "upsert":
                if not upsert_keys:
                    raise ValueError("if_exists='upsert' requires upsert_keys=[...]")
                rows = self._upsert(df, table_name, upsert_keys, chunksize, dtype)
            else:
                df.to_sql(
                    table_name,
                    self._engine,
                    if_exists=if_exists,
                    index=False,
                    chunksize=chunksize,
                    dtype=dtype,
                    method="multi",
                )
                rows = len(df)
        except ValueError:
            raise
        except Exception as exc:
            raise IngestionError(
                f"Failed writing to {self.label}.{table_name}: {exc}"
            ) from exc
        logger.info("Wrote %d row(s) to %s.%s", rows, self.label, table_name)
        return rows

    def _upsert(
        self, df: pd.DataFrame, table_name: str, keys: list[str],
        chunksize: int, dtype: Optional[dict],
    ) -> int:
        """Stage `df` into a temp table, then MERGE/UPDATE+INSERT it into
        `table_name` inside a single transaction. Works even if
        `table_name` doesn't exist yet (falls back to a plain create)."""
        from sqlalchemy import inspect, text

        insp = inspect(self._engine)
        table_exists = insp.has_table(table_name)
        if not table_exists:
            # Nothing to merge against yet — just create it.
            df.to_sql(table_name, self._engine, if_exists="fail", index=False,
                      chunksize=chunksize, dtype=dtype, method="multi")
            return len(df)

        staging = f"_{table_name}_staging_upsert"
        columns = list(df.columns)
        non_key_cols = [c for c in columns if c not in keys]

        with self._engine.begin() as conn:
            df.to_sql(staging, conn, if_exists="replace", index=False,
                      chunksize=chunksize, dtype=dtype, method="multi")

            key_match = " AND ".join(f"t.{k} = s.{k}" for k in keys)
            if non_key_cols:
                conn.execute(text(self._upsert_update_sql(table_name, staging, keys, non_key_cols)))

            insert_cols = ", ".join(columns)
            select_cols = ", ".join(f"s.{c}" for c in columns)
            not_exists = " AND ".join(f"t.{k} = s.{k}" for k in keys)
            conn.execute(text(
                f"INSERT INTO {table_name} ({insert_cols}) "
                f"SELECT {select_cols} FROM {staging} AS s "
                f"WHERE NOT EXISTS (SELECT 1 FROM {table_name} AS t WHERE {not_exists})"
            ))
            conn.execute(text(f"DROP TABLE {staging}"))
        return len(df)

    def _upsert_update_sql(self, table_name: str, staging: str, keys: list[str],
                            non_key_cols: list[str]) -> str:
        """UPDATE syntax for the rows-that-already-exist half of an upsert.
        Differs per dialect; each branch is functionally equivalent."""
        key_match_t_s = " AND ".join(f"t.{k} = s.{k}" for k in keys)
        set_clause_t = ", ".join(f"t.{c} = s.{c}" for c in non_key_cols)
        set_clause_bare = ", ".join(f"{c} = s.{c}" for c in non_key_cols)

        if self.dialect in ("mysql", "mariadb"):
            return (f"UPDATE {table_name} t JOIN {staging} s ON {key_match_t_s} "
                    f"SET {set_clause_t}")
        if self.dialect == "mssql":
            return (f"UPDATE t SET {set_clause_t} FROM {table_name} AS t "
                    f"JOIN {staging} AS s ON {key_match_t_s}")
        # postgres, sqlite (3.33+): UPDATE ... SET ... FROM ...
        return (f"UPDATE {table_name} SET {set_clause_bare} FROM {staging} AS s "
                f"WHERE {' AND '.join(f'{table_name}.{k} = s.{k}' for k in keys)}")

    def _require_connected(self) -> None:
        if self._engine is None:
            raise RuntimeError("Not connected. Use `with SQLConnector(...) as conn:` or call connect().")
