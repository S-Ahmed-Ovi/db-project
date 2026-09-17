"""
db_project/connectors/files.py — CSV / Excel / JSON / Parquet loader.

Handles the "upload" half of the pipeline: raw bytes or an on-disk path
in a project's uploads/ dir -> pandas DataFrame. The manager then hands that
DataFrame to a SQLConnector/MongoConnector to actually create the table.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ..exceptions import IngestionError
from ..logging_utils import logger

FileInput = Union[str, Path, bytes, io.BytesIO]

_EXT_TO_FORMAT = {
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel",
    ".json": "json",
    ".jsonl": "json",
    ".parquet": "parquet",
}


def load_dataframe(
    source: FileInput,
    file_format: str = "auto",
    filename: Optional[str] = None,
) -> pd.DataFrame:
    """Load any supported tabular file (path, bytes, or BytesIO) into a DataFrame."""
    buf, ext = _prepare(source, filename)
    fmt = _resolve_format(file_format, ext)
    logger.info("Reading %s file", fmt)
    try:
        df = _dispatch(buf, fmt)
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise IngestionError(f"Failed reading {fmt} file: {exc}") from exc
    logger.info("Read %d row(s), %d column(s)", len(df), len(df.columns))
    return df


def save_upload(uploads_dir: Path, filename: str, raw_bytes: bytes) -> Path:
    """Persist raw uploaded bytes into a project's uploads/ directory."""
    uploads_dir.mkdir(parents=True, exist_ok=True)
    dest = uploads_dir / filename
    dest.write_bytes(raw_bytes)
    logger.info("Saved upload %s (%d bytes)", filename, len(raw_bytes))
    return dest


# ── internals ────────────────────────────────────────────────────────────────

def _prepare(source: FileInput, filename: Optional[str]):
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path, path.suffix.lower()

    raw = source if isinstance(source, bytes) else source.read()
    ext = Path(filename).suffix.lower() if filename else ""
    return io.BytesIO(raw), ext


def _resolve_format(file_format: str, ext: str) -> str:
    if file_format != "auto":
        return file_format.lower()
    fmt = _EXT_TO_FORMAT.get(ext)
    if not fmt:
        raise ValueError(f"Cannot infer format from extension '{ext}'. Pass file_format explicitly.")
    return fmt


def _dispatch(buf, fmt: str) -> pd.DataFrame:
    if fmt == "csv":
        return pd.read_csv(buf, low_memory=False)
    if fmt == "excel":
        return pd.read_excel(buf, engine="openpyxl")
    if fmt == "json":
        try:
            return pd.read_json(buf, orient="records")
        except ValueError:
            if hasattr(buf, "seek"):
                buf.seek(0)
            return pd.read_json(buf, lines=True)
    if fmt == "parquet":
        return pd.read_parquet(buf)
    raise ValueError(f"Unsupported format '{fmt}'. Choose from: csv, excel, json, parquet.")
