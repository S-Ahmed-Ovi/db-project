from __future__ import annotations

from db_project.logging_utils import REDACTED, redact, redact_url


def test_redact_flat_dict():
    out = redact({"host": "db.acme.com", "password": "hunter2"})
    assert out["host"] == "db.acme.com"
    assert out["password"] == REDACTED


def test_redact_nested_dict():
    out = redact({"tunnel": {"ssh_host": "bastion", "ssh_password": "s3cr3t"}})
    assert out["tunnel"]["ssh_host"] == "bastion"
    assert out["tunnel"]["ssh_password"] == REDACTED


def test_redact_list_of_dicts():
    out = redact([{"token": "abc"}, {"host": "x"}])
    assert out[0]["token"] == REDACTED
    assert out[1]["host"] == "x"


def test_redact_empty_secret_left_alone():
    # An empty/missing secret isn't "leaked" by staying empty.
    out = redact({"password": ""})
    assert out["password"] == ""


def test_redact_url_hides_password():
    url = "postgresql+psycopg2://svc:hunter2@db.acme.com:5432/warehouse"
    out = redact_url(url)
    assert "hunter2" not in out
    assert "svc" in out
    assert "db.acme.com:5432/warehouse" in out


def test_redact_url_without_credentials_unchanged():
    url = "sqlite:///local.db"
    assert redact_url(url) == url


def test_source_info_never_exposes_password(project_manager):
    project_manager.add_sql_source(
        "acme", "warehouse", dialect="sqlite", host="", port=0,
        database=":memory:", username="u", password="super-secret",
    )
    info = project_manager.source_info("acme", "warehouse")
    assert "password" not in info
    assert "super-secret" not in str(info)
