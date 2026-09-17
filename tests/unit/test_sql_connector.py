from __future__ import annotations

import pandas as pd
import pytest

from db_project.connectors.sql import SQLConnector
from db_project.exceptions import ConnectionError as DBConnectionError


def _conn(tmp_path):
    return SQLConnector(dialect="sqlite", database=str(tmp_path / "test.db"))


def test_connect_query_disconnect(tmp_path):
    with _conn(tmp_path) as conn:
        df = conn.query("SELECT 1 AS one")
        assert df["one"].iloc[0] == 1


def test_write_replace_then_append(tmp_path):
    with _conn(tmp_path) as conn:
        df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        rows = conn.write_dataframe(df, "people", if_exists="replace")
        assert rows == 2

        more = pd.DataFrame({"id": [3], "name": ["c"]})
        conn.write_dataframe(more, "people", if_exists="append")
        result = conn.query("SELECT * FROM people ORDER BY id")
        assert list(result["id"]) == [1, 2, 3]


def test_write_upsert_updates_existing_and_inserts_new(tmp_path):
    with _conn(tmp_path) as conn:
        base = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        conn.write_dataframe(base, "people", if_exists="replace")

        changes = pd.DataFrame({"id": [2, 3], "name": ["b-updated", "c"]})
        conn.write_dataframe(changes, "people", if_exists="upsert", upsert_keys=["id"])

        result = conn.query("SELECT * FROM people ORDER BY id").set_index("id")
        assert result.loc[1, "name"] == "a"
        assert result.loc[2, "name"] == "b-updated"
        assert result.loc[3, "name"] == "c"


def test_write_upsert_against_nonexistent_table_creates_it(tmp_path):
    with _conn(tmp_path) as conn:
        df = pd.DataFrame({"id": [1], "name": ["a"]})
        rows = conn.write_dataframe(df, "brand_new", if_exists="upsert", upsert_keys=["id"])
        assert rows == 1
        assert "brand_new" in conn.get_table_names()


def test_upsert_without_keys_raises_value_error(tmp_path):
    with _conn(tmp_path) as conn:
        df = pd.DataFrame({"id": [1], "name": ["a"]})
        conn.write_dataframe(df, "people", if_exists="replace")
        with pytest.raises(ValueError):
            conn.write_dataframe(df, "people", if_exists="upsert")


def test_get_schema(tmp_path):
    with _conn(tmp_path) as conn:
        df = pd.DataFrame({"id": [1], "name": ["a"]})
        conn.write_dataframe(df, "people", if_exists="replace")
        schema = conn.get_schema("people")
        names = {c["name"] for c in schema}
        assert {"id", "name"} <= names


def test_unsupported_dialect_raises_value_error():
    with pytest.raises(ValueError):
        SQLConnector(dialect="not_a_real_db")


def test_connection_failure_wrapped_in_connection_error(tmp_path):
    # An impossible ODBC-style host for a dialect that isn't sqlite fails
    # fast at connect() time; check it's wrapped, not a raw driver exception.
    conn = SQLConnector(dialect="postgres", host="256.256.256.256", port=1,
                         database="x", username="x", password="x", connect_timeout=1)
    with pytest.raises(DBConnectionError):
        conn.connect()


def test_query_before_connect_raises_runtime_error(tmp_path):
    conn = _conn(tmp_path)
    with pytest.raises(RuntimeError):
        conn.query("SELECT 1")
