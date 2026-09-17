"""
db_project/manager.py — the one class you actually import.

ProjectManager gives every project:
  - a folder for registered DB connections (SQL/NoSQL, with optional VPN/SSH
    tunnel) stored in projects/{id}/config.json
  - a folder for uploaded files: projects/{id}/uploads/
  - the ability to pull any registered source into a DataFrame
  - the ability to push an uploaded file (or any DataFrame) INTO a registered
    database connection as a real table/collection — the "convert upload to
    database connection" step
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from .config import (
    ProjectConfig,
    SourceConfig,
    load_project,
    save_project,
    list_projects,
)
from .connectors.files import load_dataframe, save_upload as _save_upload_bytes
from .connectors.sql import SQLConnector
from .connectors.nosql import MongoConnector
from .connectors.tunnel import open_tunnel
from .connectors.vpn import open_vpn
from .exceptions import ConfigurationError
from .logging_utils import logger
from .schema import detect_dataframe_schema
from .validation import validate as _validate


class ProjectManager:
    def __init__(self) -> None:
        self._cache: dict[str, ProjectConfig] = {}

    # ── project lifecycle ────────────────────────────────────────────────

    def create_project(self, project_id: str) -> ProjectConfig:
        cfg = ProjectConfig(project_id=project_id)
        save_project(cfg)
        self._cache[project_id] = cfg
        logger.info("Created project '%s'", project_id)
        return cfg

    def list_projects(self) -> list[str]:
        return list_projects()

    def config(self, project_id: str) -> ProjectConfig:
        if project_id not in self._cache:
            self._cache[project_id] = load_project(project_id)
        return self._cache[project_id]

    def refresh(self, project_id: str) -> None:
        self._cache.pop(project_id, None)

    # ── registering DB connections ──────────────────────────────────────

    def add_sql_source(
        self, project_id: str, name: str, *, dialect: str, host: str, port: int,
        database: str, username: str = "", password: str = "", ssl: bool = True,
        connect_timeout: int = 30, tunnel: Optional[dict] = None, vpn: Optional[dict] = None,
    ) -> None:
        """
        Register a SQL connection (postgres/mysql/mariadb/mssql/sqlite).

        Connection reaches the DB one of three ways (pick at most one):
          - default (no tunnel/vpn): Direct — connect straight to host:port
          - `tunnel={...}`: Secure Tunnel via SSH/Bastion — see
            db_project.config.SSHTunnelConfig fields
          - `vpn={...}`: Secure Tunnel via Customer VPN (WireGuard/OpenVPN) —
            see db_project.config.VPNConfig fields
        """
        if tunnel and vpn:
            raise ConfigurationError("Pass only one of `tunnel` (SSH) or `vpn` (WireGuard/OpenVPN), not both.")
        fields = dict(dialect=dialect, host=host, port=port, database=database,
                       username=username, password=password, ssl=ssl,
                       connect_timeout=connect_timeout)
        if tunnel:
            fields["tunnel"] = tunnel
        if vpn:
            fields["vpn"] = vpn
        self._add_source(project_id, name, "sql", fields)

    def add_nosql_source(
        self, project_id: str, name: str, *, engine: str = "mongodb", host: str,
        port: int = 27017, database: str, username: Optional[str] = None,
        password: Optional[str] = None, tunnel: Optional[dict] = None, vpn: Optional[dict] = None,
    ) -> None:
        """Register a NoSQL connection. Currently: mongodb.
        Same Direct / SSH-tunnel / Customer-VPN choice as add_sql_source."""
        if tunnel and vpn:
            raise ConfigurationError("Pass only one of `tunnel` (SSH) or `vpn` (WireGuard/OpenVPN), not both.")
        fields = dict(engine=engine, host=host, port=port, database=database,
                       username=username, password=password)
        if tunnel:
            fields["tunnel"] = tunnel
        if vpn:
            fields["vpn"] = vpn
        self._add_source(project_id, name, "nosql", fields)

    def _add_source(self, project_id: str, name: str, kind: str, fields: dict) -> None:
        try:
            cfg = self.config(project_id)
        except FileNotFoundError:
            cfg = self.create_project(project_id)
        cfg.sources[name] = SourceConfig(name=name, kind=kind, raw=fields)  # validates in __post_init__
        save_project(cfg)
        self.refresh(project_id)
        logger.info("Registered %s source '%s' on project '%s'", kind, name, project_id)

    def remove_source(self, project_id: str, name: str) -> None:
        cfg = self.config(project_id)
        cfg.sources.pop(name, None)
        save_project(cfg)
        self.refresh(project_id)

    def list_sources(self, project_id: str) -> list[str]:
        return sorted(self.config(project_id).sources)

    def source_info(self, project_id: str, source_name: str) -> dict:
        """Non-secret summary of a source: kind, connection_mode (direct/ssh_tunnel/vpn), host, port, database."""
        src = self.config(project_id).sources[source_name]
        r = src.raw
        info = {
            "name": source_name,
            "kind": src.kind,
            "connection_mode": src.connection_mode,
            "host": r.get("host"),
            "port": r.get("port"),
            "database": r.get("database"),
        }
        if src.kind == "sql":
            info["dialect"] = r.get("dialect")
        if src.kind == "nosql":
            info["engine"] = r.get("engine")
        if src.connection_mode == "ssh_tunnel":
            info["ssh_host"] = r["tunnel"]["ssh_host"]
        if src.connection_mode == "vpn":
            info["vpn_type"] = r["vpn"].get("vpn_type")
        return info

    # ── uploads ──────────────────────────────────────────────────────────

    def save_upload(self, project_id: str, filename: str, raw_bytes: bytes) -> Path:
        """Save an uploaded CSV/XLSX/JSON/Parquet file into the project's uploads/ dir."""
        cfg = self.config(project_id)
        return _save_upload_bytes(cfg.uploads_dir, filename, raw_bytes)

    def list_uploads(self, project_id: str) -> list[str]:
        cfg = self.config(project_id)
        return sorted(f.name for f in cfg.uploads_dir.iterdir() if f.is_file())

    def load_upload(self, project_id: str, filename: str, file_format: str = "auto") -> pd.DataFrame:
        """Load an already-saved upload into a DataFrame."""
        cfg = self.config(project_id)
        return load_dataframe(cfg.uploads_dir / filename, file_format=file_format)

    # ── pulling a registered source into a DataFrame ────────────────────

    def query_sql(self, project_id: str, source_name: str, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        with self._open_sql(project_id, source_name) as conn:
            return conn.query(sql, params=params)

    def fetch_nosql(self, project_id: str, source_name: str, collection: str,
                     query: Optional[dict] = None, limit: int = 0) -> pd.DataFrame:
        with self._open_nosql(project_id, source_name) as conn:
            return conn.fetch_collection(collection, query=query, limit=limit)

    # ── THE CONVERSION STEP: upload -> real database table ─────────────

    def upload_to_database(
        self,
        project_id: str,
        filename: str,
        target_source: str,
        table_name: Optional[str] = None,
        if_exists: str = "replace",
        file_format: str = "auto",
        upsert_keys: Optional[list[str]] = None,
    ) -> int:
        """
        Load `filename` from the project's uploads/ dir and write it as a
        real table into the SQL connection registered as `target_source`
        (which may itself be behind a VPN/SSH tunnel — handled transparently).
        Returns rows written.

        `if_exists="upsert"` merges on `upsert_keys` (the column(s) that
        uniquely identify a row) instead of replacing/appending wholesale.
        """
        df = self.load_upload(project_id, filename, file_format=file_format)
        table_name = table_name or Path(filename).stem
        return self.dataframe_to_database(
            project_id, df, target_source, table_name,
            if_exists=if_exists, upsert_keys=upsert_keys,
        )

    def dataframe_to_database(
        self, project_id: str, df: pd.DataFrame, target_source: str,
        table_name: str, if_exists: str = "replace",
        upsert_keys: Optional[list[str]] = None,
    ) -> int:
        """Same as upload_to_database, but for a DataFrame you already have in memory."""
        src = self.config(project_id).sources[target_source]
        if src.kind == "sql":
            with self._open_sql(project_id, target_source) as conn:
                return conn.write_dataframe(df, table_name, if_exists=if_exists, upsert_keys=upsert_keys)
        elif src.kind == "nosql":
            mode = {"replace": "replace", "append": "append", "upsert": "upsert"}.get(if_exists, "append")
            with self._open_nosql(project_id, target_source) as conn:
                return conn.write_dataframe(df, table_name, mode=mode, upsert_keys=upsert_keys)
        raise ValueError(f"target_source '{target_source}' must be kind sql or nosql, got '{src.kind}'")

    # ── schema inspection ───────────────────────────────────────────────

    def inspect_file(self, project_id: str, filename: str, file_format: str = "auto") -> dict:
        """Detected column-level schema of an already-uploaded file, without
        writing it anywhere. See db_project.schema.detect_dataframe_schema."""
        df = self.load_upload(project_id, filename, file_format=file_format)
        return detect_dataframe_schema(df)

    def inspect_dataframe(self, df: pd.DataFrame) -> dict:
        """Detected column-level schema of a DataFrame you already have."""
        return detect_dataframe_schema(df)

    def inspect_database(self, project_id: str, source_name: str, table_name: str) -> list[dict]:
        """Column-level schema (name/detected_type/nullable) of an existing
        table in a registered SQL source, straight from the database."""
        with self._open_sql(project_id, source_name) as conn:
            return conn.get_schema(table_name)

    # ── validation ───────────────────────────────────────────────────────

    def validate(
        self,
        data: pd.DataFrame,
        schema: Optional[dict] = None,
        required_columns: Optional[list[str]] = None,
        unique_columns: Optional[list[str]] = None,
        range_checks: Optional[dict] = None,
        allow_nulls: Optional[dict] = None,
    ) -> dict:
        """Validate a DataFrame. See db_project.validation.validate for the
        full parameter/return-value description."""
        return _validate(
            data, schema=schema, required_columns=required_columns,
            unique_columns=unique_columns, range_checks=range_checks,
            allow_nulls=allow_nulls,
        )

    # ── internal: open connectors, transparently tunneling if configured ──

    def _open_sql(self, project_id: str, source_name: str) -> SQLConnector:
        src = self._get_source(project_id, source_name, "sql")
        r = src.raw
        host, port = r["host"], int(r["port"])
        mode = src.connection_mode  # "direct" | "ssh_tunnel" | "vpn"

        if mode == "ssh_tunnel":
            tunnel_ctx = open_tunnel(host, port, src.tunnel)
            tunneled_host, tunneled_port = tunnel_ctx.__enter__()
            return _TunneledSQLConnector(tunnel_ctx, dialect=r["dialect"],
                                          host=tunneled_host, port=tunneled_port, database=r.get("database", ""),
                                          username=r.get("username", ""), password=r.get("password", ""),
                                          ssl=r.get("ssl", True), connect_timeout=r.get("connect_timeout", 30),
                                          label=source_name)

        if mode == "vpn":
            vpn_ctx = open_vpn(src.vpn, remote_host=host, remote_port=port)
            vpn_ctx.__enter__()  # brings the WireGuard/OpenVPN interface up; host:port unchanged
            return _VPNSQLConnector(vpn_ctx, dialect=r["dialect"],
                                     host=host, port=port, database=r.get("database", ""),
                                     username=r.get("username", ""), password=r.get("password", ""),
                                     ssl=r.get("ssl", True), connect_timeout=r.get("connect_timeout", 30),
                                     label=source_name)

        return SQLConnector(dialect=r["dialect"], host=host, port=port, database=r.get("database", ""),
                             username=r.get("username", ""), password=r.get("password", ""),
                             ssl=r.get("ssl", True), connect_timeout=r.get("connect_timeout", 30),
                             label=source_name)

    def _open_nosql(self, project_id: str, source_name: str) -> MongoConnector:
        src = self._get_source(project_id, source_name, "nosql")
        r = src.raw
        host, port = r["host"], int(r.get("port", 27017))
        mode = src.connection_mode

        if mode == "ssh_tunnel":
            tunnel_ctx = open_tunnel(host, port, src.tunnel)
            tunneled_host, tunneled_port = tunnel_ctx.__enter__()
            return _TunneledMongoConnector(tunnel_ctx, host=tunneled_host, port=tunneled_port,
                                            database=r.get("database", ""), username=r.get("username"),
                                            password=r.get("password"), label=source_name)

        if mode == "vpn":
            vpn_ctx = open_vpn(src.vpn, remote_host=host, remote_port=port)
            vpn_ctx.__enter__()
            return _VPNMongoConnector(vpn_ctx, host=host, port=port,
                                       database=r.get("database", ""), username=r.get("username"),
                                       password=r.get("password"), label=source_name)

        return MongoConnector(host=host, port=port, database=r.get("database", ""),
                               username=r.get("username"), password=r.get("password"), label=source_name)

    def _get_source(self, project_id: str, source_name: str, expected_kind: str) -> SourceConfig:
        cfg = self.config(project_id)
        src = cfg.sources.get(source_name)
        if src is None:
            raise KeyError(f"Project '{project_id}' has no source '{source_name}'. Available: {sorted(cfg.sources)}")
        if src.kind != expected_kind:
            raise ValueError(f"Source '{source_name}' is kind '{src.kind}', expected '{expected_kind}'")
        return src


class _TunneledSQLConnector(SQLConnector):
    """SQLConnector that also closes its SSH tunnel on __exit__."""
    def __init__(self, tunnel_ctx, **kwargs):
        super().__init__(**kwargs)
        self._tunnel_ctx = tunnel_ctx

    def __exit__(self, *exc) -> None:
        try:
            super().__exit__(*exc)
        finally:
            self._tunnel_ctx.__exit__(*exc if any(exc) else (None, None, None))


class _TunneledMongoConnector(MongoConnector):
    """MongoConnector that also closes its SSH tunnel on __exit__."""
    def __init__(self, tunnel_ctx, **kwargs):
        super().__init__(**kwargs)
        self._tunnel_ctx = tunnel_ctx

    def __exit__(self, *exc) -> None:
        try:
            super().__exit__(*exc)
        finally:
            self._tunnel_ctx.__exit__(*exc if any(exc) else (None, None, None))


class _VPNSQLConnector(SQLConnector):
    """SQLConnector that also brings the Customer VPN interface down on __exit__."""
    def __init__(self, vpn_ctx, **kwargs):
        super().__init__(**kwargs)
        self._vpn_ctx = vpn_ctx

    def __exit__(self, *exc) -> None:
        try:
            super().__exit__(*exc)
        finally:
            self._vpn_ctx.__exit__(*exc if any(exc) else (None, None, None))


class _VPNMongoConnector(MongoConnector):
    """MongoConnector that also brings the Customer VPN interface down on __exit__."""
    def __init__(self, vpn_ctx, **kwargs):
        super().__init__(**kwargs)
        self._vpn_ctx = vpn_ctx

    def __exit__(self, *exc) -> None:
        try:
            super().__exit__(*exc)
        finally:
            self._vpn_ctx.__exit__(*exc if any(exc) else (None, None, None))
