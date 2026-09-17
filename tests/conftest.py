"""Shared fixtures for the db_project test suite."""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def project_manager(tmp_path, monkeypatch):
    """A ProjectManager backed by a throwaway temp directory instead of the
    real cwd, with an 'acme' project already created."""
    monkeypatch.setenv("DB_PROJECTS_ROOT", str(tmp_path))

    from db_project import config as config_module
    importlib.reload(config_module)

    from db_project.manager import ProjectManager
    pm = ProjectManager()
    pm.create_project("acme")
    return pm
