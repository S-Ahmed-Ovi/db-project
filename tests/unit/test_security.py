from __future__ import annotations

import importlib
import logging

import pandas as pd
import pytest


def test_secrets_never_appear_in_log_output(project_manager, tmp_path, caplog):
    project_manager.add_sql_source(
        "acme", "warehouse", dialect="sqlite", host="", port=0,
        database=str(tmp_path / "w.db"), username="svc", password="TOP-SECRET-VALUE",
    )
    with caplog.at_level(logging.INFO, logger="db_project"):
        df = pd.DataFrame({"id": [1]})
        project_manager.dataframe_to_database("acme", df, "warehouse", "t")

    assert "TOP-SECRET-VALUE" not in caplog.text


def test_env_var_password_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PROJECTS_ROOT", str(tmp_path))
    from db_project import config as config_module
    importlib.reload(config_module)
    from db_project.manager import ProjectManager

    pm = ProjectManager()
    pm.create_project("acme")
    pm.add_sql_source(
        "acme", "warehouse", dialect="sqlite", host="", port=0,
        database=str(tmp_path / "w.db"), username="svc", password="config-file-password",
    )

    monkeypatch.setenv("ACME__WAREHOUSE__PASSWORD", "env-var-password")
    pm.refresh("acme")
    src = pm.config("acme").sources["warehouse"]
    assert src.raw["password"] == "env-var-password"


def test_invalid_credentials_fail_safely_not_silently(project_manager, tmp_path):
    # A source with a password that's simply wrong for a real network
    # service should raise a db_project connectivity error, not hang or
    # silently return no data. sqlite has no auth, so this exercises a
    # dialect that does: postgres, against an address nothing is listening on.
    project_manager.add_sql_source(
        "acme", "bad_pg", dialect="postgres", host="127.0.0.1", port=1,
        database="x", username="wrong", password="wrong", connect_timeout=1,
    )
    from db_project.exceptions import ConnectivityError
    with pytest.raises(ConnectivityError):
        project_manager.query_sql("acme", "bad_pg", "SELECT 1")
