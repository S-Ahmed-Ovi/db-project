"""
db_project/validation.py — data validation layer.

`validate(df, schema=...)` runs a fixed set of checks and returns a
structured result (never raises for a *failed* validation — only for
programmer misuse of the API itself, e.g. an unknown column in `schema`).

    result = validate(
        df,
        schema={"sale_id": "integer", "price": "float", "sale_date": "datetime"},
        required_columns=["sale_id", "price"],
        unique_columns=["sale_id"],
        range_checks={"price": {"min": 0}},
    )
    result == {
        "valid": False,
        "errors": [...],
        "warnings": [...],
        "statistics": {"row_count": ..., "column_count": ..., "null_counts": {...}},
    }
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from .exceptions import ValidationError as ValidationApiError
from .logging_utils import logger
from .schema import _logical_type

_KNOWN_LOGICAL_TYPES = ("integer", "float", "boolean", "datetime", "string")


def validate(
    df: pd.DataFrame,
    schema: Optional[dict[str, str]] = None,
    required_columns: Optional[list[str]] = None,
    unique_columns: Optional[list[str]] = None,
    range_checks: Optional[dict[str, dict[str, Any]]] = None,
    allow_nulls: Optional[dict[str, bool]] = None,
) -> dict[str, Any]:
    """
    Validate a DataFrame. All parameters are optional — pass only the
    checks that matter for your data.

    schema:           {column: "integer"|"float"|"boolean"|"datetime"|"string"}
                       — checks the column exists and its detected type matches.
    required_columns: columns that must be present (in addition to `schema`).
    unique_columns:   columns (individually) that must contain no duplicates.
    range_checks:     {column: {"min": ..., "max": ...}} — numeric/date range.
    allow_nulls:      {column: False} to fail if that column contains nulls
                       (default: nulls are allowed unless stated otherwise).
    """
    if schema is not None:
        for col in schema:
            if schema[col] not in _KNOWN_LOGICAL_TYPES:
                raise ValidationApiError(
                    f"Unknown type '{schema[col]}' for column '{col}'. "
                    f"Choose from {_KNOWN_LOGICAL_TYPES}."
                )

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    all_required = list(dict.fromkeys((required_columns or []) + list((schema or {}).keys())))
    for col in all_required:
        if col not in df.columns:
            errors.append({"check": "required_column", "column": col,
                            "message": f"Required column '{col}' is missing."})

    if schema:
        for col, expected in schema.items():
            if col not in df.columns:
                continue  # already reported above
            actual = _logical_type(df[col])
            if actual != expected:
                errors.append({
                    "check": "dtype", "column": col,
                    "message": f"Column '{col}' expected type '{expected}', detected '{actual}'.",
                })

    for col, must_not_null in (allow_nulls or {}).items():
        if must_not_null is False and col in df.columns:
            null_count = int(df[col].isna().sum())
            if null_count:
                errors.append({
                    "check": "null", "column": col,
                    "message": f"Column '{col}' has {null_count} null value(s) but nulls are not allowed.",
                })

    for col in (unique_columns or []):
        if col not in df.columns:
            continue
        dup_count = int(df[col].duplicated().sum())
        if dup_count:
            errors.append({
                "check": "duplicate", "column": col,
                "message": f"Column '{col}' has {dup_count} duplicate value(s).",
            })

    for col, bounds in (range_checks or {}).items():
        if col not in df.columns:
            continue
        series = df[col].dropna()
        lo, hi = bounds.get("min"), bounds.get("max")
        if lo is not None:
            below = int((series < lo).sum())
            if below:
                errors.append({
                    "check": "range", "column": col,
                    "message": f"Column '{col}' has {below} value(s) below minimum {lo}.",
                })
        if hi is not None:
            above = int((series > hi).sum())
            if above:
                errors.append({
                    "check": "range", "column": col,
                    "message": f"Column '{col}' has {above} value(s) above maximum {hi}.",
                })

    unexpected_cols = [c for c in df.columns if schema and c not in schema]
    if schema and unexpected_cols:
        warnings.append({
            "check": "schema_compatibility",
            "message": f"Columns present but not in schema: {unexpected_cols}",
        })

    statistics = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "null_counts": {str(c): int(df[c].isna().sum()) for c in df.columns},
    }

    result = {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "statistics": statistics}
    logger.info("Validation completed: valid=%s errors=%d warnings=%d",
                result["valid"], len(errors), len(warnings))
    return result
