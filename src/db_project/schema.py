"""
db_project/schema.py — lightweight schema detection.

Deliberately simple (§6 "do not over-engineer automatic type inference
initially"): reads pandas dtypes and maps them to a small set of logical
types (integer/float/boolean/datetime/string), plus a nullable flag from
whether the column actually contains any nulls.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

_LOGICAL_TYPES = ("integer", "float", "boolean", "datetime", "string")


def detect_dataframe_schema(df: pd.DataFrame) -> dict[str, Any]:
    """Inspect a DataFrame's columns. Returns:

        {
          "columns": [
            {"name": "sale_id", "detected_type": "integer", "nullable": False},
            ...
          ],
          "row_count": 1000,
        }
    """
    columns = []
    for name in df.columns:
        series = df[name]
        columns.append({
            "name": str(name),
            "detected_type": _logical_type(series),
            "nullable": bool(series.isna().any()),
        })
    return {"columns": columns, "row_count": int(len(df))}


def _logical_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_object_dtype(series):
        # Cheap best-effort: an all-numeric/all-datetime object column
        # (common after reading CSVs with mixed/NaN-only columns) is
        # reported as such rather than falling back to "string".
        non_null = series.dropna()
        if non_null.empty:
            return "string"
        try:
            pd.to_numeric(non_null)
            return "float" if (non_null.astype(str).str.contains(r"\.")).any() else "integer"
        except (ValueError, TypeError):
            pass
        return "string"
    return "string"
