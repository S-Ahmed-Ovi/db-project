from __future__ import annotations

import pandas as pd

from db_project import detect_dataframe_schema


def test_basic_types_detected():
    df = pd.DataFrame({
        "sale_id": [1, 2, 3],
        "price": [1.5, 2.5, 3.5],
        "active": [True, False, True],
        "name": ["a", "b", "c"],
        "when": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    })
    result = detect_dataframe_schema(df)
    by_name = {c["name"]: c for c in result["columns"]}
    assert by_name["sale_id"]["detected_type"] == "integer"
    assert by_name["price"]["detected_type"] == "float"
    assert by_name["active"]["detected_type"] == "boolean"
    assert by_name["name"]["detected_type"] == "string"
    assert by_name["when"]["detected_type"] == "datetime"
    assert result["row_count"] == 3


def test_nullable_flag():
    df = pd.DataFrame({"a": [1, None, 3]})
    result = detect_dataframe_schema(df)
    assert result["columns"][0]["nullable"] is True


def test_manager_inspect_file(project_manager, tmp_path):
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("sale_id,price\n1,9.99\n2,19.99\n")
    project_manager.save_upload("acme", "sales.csv", csv_path.read_bytes())

    result = project_manager.inspect_file("acme", "sales.csv")
    by_name = {c["name"]: c for c in result["columns"]}
    assert by_name["sale_id"]["detected_type"] == "integer"
    assert by_name["price"]["detected_type"] == "float"


def test_manager_inspect_dataframe(project_manager):
    df = pd.DataFrame({"x": [1, 2]})
    result = project_manager.inspect_dataframe(df)
    assert result["columns"][0]["name"] == "x"
