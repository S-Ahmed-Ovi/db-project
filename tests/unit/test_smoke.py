"""
A minimal smoke test: proves the package installs and its basic project/
source-registration workflow works end-to-end, without needing a real
database, SSH bastion, or VPN.

Run with:
    pip install -e ".[all,test]"
    pytest
"""
from __future__ import annotations

import importlib

import pytest


def test_package_imports():
    import db_project

    assert hasattr(db_project, "ProjectManager")
    assert hasattr(db_project, "__version__")


def test_create_project_and_register_sql_source(tmp_path, monkeypatch):
    # Point the package's storage root at a throwaway temp directory instead
    # of the real cwd, and reload the config module so it picks up the
    # environment variable set just now (it's read once, at import time).
    monkeypatch.setenv("DB_PROJECTS_ROOT", str(tmp_path))

    from db_project import config as config_module
    importlib.reload(config_module)

    from db_project.manager import ProjectManager
    pm = ProjectManager()

    pm.create_project("acme")
    assert "acme" in pm.list_projects()

    pm.add_sql_source(
        "acme",
        "warehouse",
        dialect="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "warehouse.db"),
        username="",
        password="",
    )

    cfg = pm.config("acme")
    assert "warehouse" in cfg.sources
    assert cfg.sources["warehouse"].raw["dialect"] == "sqlite"


def test_registering_both_tunnel_and_vpn_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PROJECTS_ROOT", str(tmp_path))

    from db_project import config as config_module
    importlib.reload(config_module)

    from db_project.manager import ProjectManager
    pm = ProjectManager()
    pm.create_project("acme")

    with pytest.raises(ValueError):
        pm.add_sql_source(
            "acme",
            "bad_source",
            dialect="postgres",
            host="10.0.0.1",
            port=5432,
            database="app",
            username="svc",
            password="secret",
            tunnel={"ssh_host": "bastion", "ssh_username": "deploy", "ssh_password": "x"},
            vpn={"vpn_type": "wireguard", "config_path": "/tmp/fake.conf"},
        )
