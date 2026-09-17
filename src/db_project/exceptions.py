"""
db_project/exceptions.py — package-wide exception hierarchy.

Design goals:
  - Callers who already do `except ValueError` / `except RuntimeError` /
    `except KeyError` against 0.1.x must keep working unmodified, so most
    of these subclass the builtin they replace *in addition to*
    DBProjectError (multiple inheritance), rather than being a clean new
    tree that breaks existing except-clauses.
  - The original low-level exception (a DB driver error, a paramiko error,
    etc.) is preserved as `__cause__` via `raise ... from original`.

    DBProjectError
    ├── ConfigurationError   (also a ValueError)
    ├── ConnectivityError    (also a RuntimeError)
    │   ├── ConnectionError
    │   └── AuthenticationError
    ├── IngestionError       (also a RuntimeError)
    ├── ValidationError      (also a ValueError)
    └── SchemaError          (also a ValueError)
"""
from __future__ import annotations


class DBProjectError(Exception):
    """Base class for every error raised by db_project."""


class ConfigurationError(DBProjectError, ValueError):
    """A project/source configuration is invalid (bad dialect, missing
    required field, both `tunnel` and `vpn` set, etc.).

    Subclasses ValueError because 0.1.x already raised plain ValueError
    for these cases (see SourceConfig.__post_init__, add_sql_source)."""


class ConnectivityError(DBProjectError, RuntimeError):
    """Base class for anything that goes wrong establishing a connection,
    tunnel, or VPN interface."""


class ConnectionError(ConnectivityError):
    """Could not reach the target database/collection endpoint."""


class AuthenticationError(ConnectivityError):
    """Reached the endpoint but credentials were rejected."""


class IngestionError(DBProjectError, RuntimeError):
    """Reading a file / writing a DataFrame into a database failed."""


class ValidationError(DBProjectError, ValueError):
    """Raised only for programmer-error style misuse of the validation API
    itself (e.g. an unknown check name). A *failed* data validation is
    reported via ValidationResult, not by raising this."""


class SchemaError(DBProjectError, ValueError):
    """Schema could not be detected/inspected, or is incompatible."""
