from __future__ import annotations

import pandas as pd
import pytest

from db_project import validate
from db_project.exceptions import ValidationError


def _sales_df():
    return pd.DataFrame({
        "sale_id": [1, 2, 3],
        "price": [9.99, 19.99, 29.99],
        "region": ["us", "eu", "us"],
    })


def test_valid_data_passes():
    result = validate(_sales_df(), schema={"sale_id": "integer", "price": "float"})
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["statistics"]["row_count"] == 3


def test_missing_required_column():
    result = validate(_sales_df(), required_columns=["sale_id", "discount"])
    assert result["valid"] is False
    assert any(e["column"] == "discount" for e in result["errors"])


def test_incorrect_type_reported():
    result = validate(_sales_df(), schema={"sale_id": "string"})
    assert result["valid"] is False
    assert result["errors"][0]["check"] == "dtype"


def test_duplicate_detection():
    df = pd.concat([_sales_df(), _sales_df().iloc[[0]]], ignore_index=True)
    result = validate(df, unique_columns=["sale_id"])
    assert result["valid"] is False
    assert result["errors"][0]["check"] == "duplicate"


def test_null_check():
    df = _sales_df()
    df.loc[0, "price"] = None
    result = validate(df, allow_nulls={"price": False})
    assert result["valid"] is False
    assert result["errors"][0]["check"] == "null"


def test_nulls_allowed_by_default():
    df = _sales_df()
    df.loc[0, "price"] = None
    result = validate(df)
    assert result["valid"] is True


def test_range_check():
    result = validate(_sales_df(), range_checks={"price": {"min": 10}})
    assert result["valid"] is False
    assert result["errors"][0]["check"] == "range"


def test_schema_compatibility_warning_not_error():
    result = validate(_sales_df(), schema={"sale_id": "integer"})
    assert result["valid"] is True
    assert any(w["check"] == "schema_compatibility" for w in result["warnings"])


def test_unknown_schema_type_raises_validation_error():
    with pytest.raises(ValidationError):
        validate(_sales_df(), schema={"sale_id": "not_a_real_type"})


def test_manager_validate_delegates(project_manager):
    result = project_manager.validate(_sales_df(), required_columns=["sale_id"])
    assert result["valid"] is True
