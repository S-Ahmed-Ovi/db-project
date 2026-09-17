from __future__ import annotations

import json

import pandas as pd
import pytest

from db_project.connectors.files import load_dataframe, save_upload
from db_project.exceptions import IngestionError


def test_csv_roundtrip(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("a,b\n1,x\n2,y\n")
    df = load_dataframe(p)
    assert list(df.columns) == ["a", "b"]
    assert len(df) == 2


def test_json_records(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps([{"a": 1}, {"a": 2}]))
    df = load_dataframe(p)
    assert len(df) == 2


def test_parquet_roundtrip(tmp_path):
    p = tmp_path / "d.parquet"
    pd.DataFrame({"a": [1, 2, 3]}).to_parquet(p)
    df = load_dataframe(p)
    assert len(df) == 3


def test_excel_roundtrip(tmp_path):
    p = tmp_path / "d.xlsx"
    pd.DataFrame({"a": [1, 2]}).to_excel(p, index=False)
    df = load_dataframe(p)
    assert len(df) == 2


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataframe(tmp_path / "nope.csv")


def test_unknown_extension_raises_value_error(tmp_path):
    p = tmp_path / "d.unknownext"
    p.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        load_dataframe(p)


def test_bytes_input_with_explicit_format():
    raw = b"a,b\n1,2\n"
    df = load_dataframe(raw, file_format="csv")
    assert len(df) == 1


def test_save_upload_persists_bytes(tmp_path):
    dest = save_upload(tmp_path, "f.csv", b"a,b\n1,2\n")
    assert dest.exists()
    assert dest.read_bytes() == b"a,b\n1,2\n"


def test_malformed_parquet_wrapped_as_ingestion_error(tmp_path):
    p = tmp_path / "bad.parquet"
    p.write_bytes(b"not actually parquet data")
    with pytest.raises(IngestionError):
        load_dataframe(p)
