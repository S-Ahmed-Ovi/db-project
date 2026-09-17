from __future__ import annotations

import db_project as dbp
from db_project import exceptions as exc


def test_configuration_error_is_also_a_value_error():
    # 0.1.x callers doing `except ValueError` around add_sql_source /
    # SourceConfig must keep working unmodified.
    assert issubclass(exc.ConfigurationError, ValueError)


def test_connectivity_errors_are_also_runtime_errors():
    assert issubclass(exc.ConnectivityError, RuntimeError)
    assert issubclass(exc.ConnectionError, exc.ConnectivityError)
    assert issubclass(exc.AuthenticationError, exc.ConnectivityError)


def test_ingestion_and_validation_and_schema_errors():
    assert issubclass(exc.IngestionError, RuntimeError)
    assert issubclass(exc.ValidationError, ValueError)
    assert issubclass(exc.SchemaError, ValueError)


def test_everything_subclasses_dbprojecterror():
    for cls in (exc.ConfigurationError, exc.ConnectivityError, exc.ConnectionError,
                exc.AuthenticationError, exc.IngestionError, exc.ValidationError,
                exc.SchemaError):
        assert issubclass(cls, exc.DBProjectError)


def test_exceptions_are_exported_from_top_level_package():
    for name in ("DBProjectError", "ConfigurationError", "ConnectivityError",
                 "ConnectionError", "AuthenticationError", "IngestionError",
                 "ValidationError", "SchemaError"):
        assert hasattr(dbp, name)


def test_vpn_error_is_now_a_connectivity_error():
    from db_project.connectors.vpn import VPNError
    assert issubclass(VPNError, exc.ConnectivityError)
