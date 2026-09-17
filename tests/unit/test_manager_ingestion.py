from __future__ import annotations

import pandas as pd
import pytest


def _register_sqlite(pm, tmp_path, name="warehouse"):
    pm.add_sql_source(
        "acme", name, dialect="sqlite", host="", port=0,
        database=str(tmp_path / f"{name}.db"), username="", password="",
    )


def test_upload_csv_to_database_replace(project_manager, tmp_path):
    _register_sqlite(project_manager, tmp_path)
    csv_path = tmp_path / "ratings.csv"
    csv_path.write_text("id,score\n1,5\n2,4\n")
    project_manager.save_upload("acme", "ratings.csv", csv_path.read_bytes())

    rows = project_manager.upload_to_database(
        "acme", "ratings.csv", target_source="warehouse", table_name="ratings",
        if_exists="replace",
    )
    assert rows == 2

    df = project_manager.query_sql("acme", "warehouse", "SELECT * FROM ratings ORDER BY id")
    assert list(df["score"]) == [5, 4]


def test_upload_csv_to_database_upsert(project_manager, tmp_path):
    _register_sqlite(project_manager, tmp_path)
    csv_path = tmp_path / "ratings.csv"
    csv_path.write_text("id,score\n1,5\n2,4\n")
    project_manager.save_upload("acme", "ratings.csv", csv_path.read_bytes())
    project_manager.upload_to_database("acme", "ratings.csv", target_source="warehouse",
                                        table_name="ratings", if_exists="replace")

    update_path = tmp_path / "ratings2.csv"
    update_path.write_text("id,score\n2,9\n3,1\n")
    project_manager.save_upload("acme", "ratings2.csv", update_path.read_bytes())
    project_manager.upload_to_database(
        "acme", "ratings2.csv", target_source="warehouse", table_name="ratings",
        if_exists="upsert", upsert_keys=["id"],
    )

    df = project_manager.query_sql("acme", "warehouse", "SELECT * FROM ratings ORDER BY id")
    assert df.set_index("id")["score"].to_dict() == {1: 5, 2: 9, 3: 1}


def test_dataframe_to_database_direct(project_manager, tmp_path):
    _register_sqlite(project_manager, tmp_path)
    df = pd.DataFrame({"id": [1, 2], "value": ["a", "b"]})
    rows = project_manager.dataframe_to_database("acme", df, "warehouse", "items")
    assert rows == 2


def test_upload_to_database_unknown_source_raises_key_error(project_manager, tmp_path):
    csv_path = tmp_path / "r.csv"
    csv_path.write_text("id\n1\n")
    project_manager.save_upload("acme", "r.csv", csv_path.read_bytes())
    with pytest.raises(KeyError):
        project_manager.upload_to_database("acme", "r.csv", target_source="does_not_exist")


def test_inspect_database_after_write(project_manager, tmp_path):
    _register_sqlite(project_manager, tmp_path)
    df = pd.DataFrame({"id": [1], "name": ["a"]})
    project_manager.dataframe_to_database("acme", df, "warehouse", "people")

    schema = project_manager.inspect_database("acme", "warehouse", "people")
    names = {c["name"] for c in schema}
    assert {"id", "name"} <= names


def test_validate_then_ingest_flow(project_manager, tmp_path):
    _register_sqlite(project_manager, tmp_path)
    df = pd.DataFrame({"id": [1, 2], "price": [9.99, -1.0]})

    result = project_manager.validate(df, schema={"id": "integer", "price": "float"},
                                       range_checks={"price": {"min": 0}})
    assert result["valid"] is False  # negative price caught before it ever hits the DB
