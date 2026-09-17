"""MongoConnector tests, mocked at the pymongo.MongoClient boundary — no
real MongoDB server required."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from db_project.connectors.nosql import MongoConnector
from db_project.exceptions import AuthenticationError, ConnectionError as DBConnectionError


def _connected_mock_client():
    client = MagicMock()
    client.server_info.return_value = {"ok": 1}
    return client


def test_connect_success():
    with patch("pymongo.MongoClient", return_value=_connected_mock_client()):
        conn = MongoConnector(host="mongo.acme.com", database="events")
        conn.connect()
        assert conn._client is not None
        conn.disconnect()
        assert conn._client is None


def test_connect_auth_failure_wrapped():
    from pymongo.errors import OperationFailure
    client = MagicMock()
    client.server_info.side_effect = OperationFailure("auth failed")
    with patch("pymongo.MongoClient", return_value=client):
        conn = MongoConnector(host="mongo.acme.com", database="events")
        with pytest.raises(AuthenticationError):
            conn.connect()


def test_connect_unreachable_wrapped():
    from pymongo.errors import ServerSelectionTimeoutError
    client = MagicMock()
    client.server_info.side_effect = ServerSelectionTimeoutError("no servers")
    with patch("pymongo.MongoClient", return_value=client):
        conn = MongoConnector(host="mongo.acme.com", database="events")
        with pytest.raises(DBConnectionError):
            conn.connect()


def test_fetch_collection_returns_dataframe():
    client = _connected_mock_client()
    fake_docs = [{"_id": "x1", "a": 1}, {"_id": "x2", "a": 2}]
    client.__getitem__.return_value.__getitem__.return_value.find.return_value = fake_docs
    with patch("pymongo.MongoClient", return_value=client):
        conn = MongoConnector(host="h", database="d")
        conn.connect()
        df = conn.fetch_collection("events")
    assert len(df) == 2
    assert df["_id"].astype(str).tolist() == ["x1", "x2"]


def test_write_dataframe_replace_deletes_then_inserts():
    client = _connected_mock_client()
    collection = client.__getitem__.return_value.__getitem__.return_value
    with patch("pymongo.MongoClient", return_value=client):
        conn = MongoConnector(host="h", database="d")
        conn.connect()
        rows = conn.write_dataframe(pd.DataFrame({"a": [1, 2]}), "events", mode="replace")
    assert rows == 2
    collection.delete_many.assert_called_once_with({})
    collection.insert_many.assert_called_once()


def test_write_dataframe_upsert_requires_keys():
    client = _connected_mock_client()
    with patch("pymongo.MongoClient", return_value=client):
        conn = MongoConnector(host="h", database="d")
        conn.connect()
        with pytest.raises(ValueError):
            conn.write_dataframe(pd.DataFrame({"a": [1]}), "events", mode="upsert")


def test_write_dataframe_upsert_uses_bulk_write():
    client = _connected_mock_client()
    collection = client.__getitem__.return_value.__getitem__.return_value
    with patch("pymongo.MongoClient", return_value=client):
        conn = MongoConnector(host="h", database="d")
        conn.connect()
        conn.write_dataframe(pd.DataFrame({"id": [1, 2], "v": ["a", "b"]}), "events",
                              mode="upsert", upsert_keys=["id"])
    collection.bulk_write.assert_called_once()
