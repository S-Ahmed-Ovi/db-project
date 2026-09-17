"""
db_project/connectors/nosql.py — MongoDB connector.

Kept intentionally minimal: MongoDB covers the overwhelming majority of
"NoSQL data source" needs. Extend with the same pattern (connect/disconnect/
fetch_collection/write_dataframe) if you later need Cassandra or DynamoDB.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from ..exceptions import AuthenticationError, ConnectionError as DBConnectionError, IngestionError
from ..logging_utils import logger


class MongoConnector:
    def __init__(
        self,
        host: str,
        port: int = 27017,
        database: str = "",
        username: Optional[str] = None,
        password: Optional[str] = None,
        connect_timeout: int = 30,
        label: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.connect_timeout = connect_timeout
        self.label = label or f"mongodb:{database}"
        self._client = None

    def __enter__(self) -> "MongoConnector":
        self.connect()
        return self

    def __exit__(self, *_exc) -> None:
        self.disconnect()

    def connect(self) -> None:
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("Install pymongo: pip install pymongo")
        if self.username and self.password:
            uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            uri = f"mongodb://{self.host}:{self.port}/{self.database}"

        logger.info("Connecting to mongodb (%s)", self.label)
        try:
            from pymongo.errors import OperationFailure, ServerSelectionTimeoutError
            self._client = MongoClient(uri, serverSelectionTimeoutMS=self.connect_timeout * 1000)
            self._client.server_info()
        except OperationFailure as exc:
            self._client = None
            raise AuthenticationError(f"Authentication failed for mongodb source '{self.label}': {exc}") from exc
        except ServerSelectionTimeoutError as exc:
            self._client = None
            raise DBConnectionError(f"Could not reach mongodb source '{self.label}': {exc}") from exc
        logger.info("Connected to mongodb (%s)", self.label)

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Disconnected from mongodb (%s)", self.label)

    def fetch_collection(self, collection: str, query: Optional[dict] = None, limit: int = 0) -> pd.DataFrame:
        self._require_connected()
        logger.info("Fetching collection %s.%s", self.label, collection)
        db = self._client[self.database]
        docs = list(db[collection].find(query or {}, limit=limit))
        df = pd.DataFrame(docs)
        if "_id" in df.columns:
            df["_id"] = df["_id"].astype(str)
        logger.info("Fetched %d document(s) from %s.%s", len(df), self.label, collection)
        return df

    def write_dataframe(
        self, df: pd.DataFrame, collection: str, mode: str = "replace",
        upsert_keys: Optional[list[str]] = None,
    ) -> int:
        """mode: 'replace' clears the collection first, 'append' inserts only,
        'upsert' matches on `upsert_keys` (updates existing docs, inserts new ones)."""
        self._require_connected()
        if mode not in ("replace", "append", "upsert"):
            raise ValueError("mode must be 'replace', 'append', or 'upsert'")
        logger.info("Writing %d row(s) to %s.%s (mode=%s)", len(df), self.label, collection, mode)
        try:
            db = self._client[self.database]
            col = db[collection]
            records = df.to_dict(orient="records")
            if mode == "replace":
                col.delete_many({})
                if records:
                    col.insert_many(records)
            elif mode == "append":
                if records:
                    col.insert_many(records)
            else:  # upsert
                if not upsert_keys:
                    raise ValueError("mode='upsert' requires upsert_keys=[...]")
                from pymongo import ReplaceOne
                ops = [
                    ReplaceOne({k: rec[k] for k in upsert_keys}, rec, upsert=True)
                    for rec in records
                ]
                if ops:
                    col.bulk_write(ops)
        except ValueError:
            raise
        except Exception as exc:
            raise IngestionError(f"Failed writing to {self.label}.{collection}: {exc}") from exc
        logger.info("Wrote %d row(s) to %s.%s", len(df), self.label, collection)
        return len(df)

    def _require_connected(self) -> None:
        if self._client is None:
            raise RuntimeError("Not connected. Use `with MongoConnector(...) as conn:` or call connect().")
