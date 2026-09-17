"""
db_project/logging_utils.py — structured logging + secret redaction.

db_project logs to the standard `logging` module under the "db_project"
logger. Like any well-behaved library, it attaches no handler of its own
(`NullHandler`) — nothing is printed unless the host application configures
logging, e.g.:

    import logging
    logging.basicConfig(level=logging.INFO)

Every log call in this package goes through `redact()` first, so secrets
never reach a log line even if a caller passes a raw config dict to a log
call by mistake.
"""
from __future__ import annotations

import logging
from typing import Any

_SECRET_KEYS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "privatekey",
    "ssh_password",
    "ssh_pkey_path",
    "ssh_pkey_passphrase",
    "auth_user_pass_path",
    "config_path",  # VPN config files contain WireGuard/OpenVPN private keys
}

REDACTED = "********"

logger = logging.getLogger("db_project")
logger.addHandler(logging.NullHandler())


def redact(value: Any) -> Any:
    """Recursively redact known-secret keys in dicts/lists. Non-container
    values are returned unchanged. Safe to call on None."""
    if isinstance(value, dict):
        return {
            k: (REDACTED if _is_secret_key(k) and v not in (None, "") else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return type(value)(redact(v) for v in value)
    return value


def _is_secret_key(key: str) -> bool:
    return str(key).lower() in _SECRET_KEYS


def redact_url(url: str) -> str:
    """Redact the password portion of a DB connection URL such as
    'postgresql+psycopg2://user:secret@host:5432/db'."""
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    creds, _, host_part = rest.partition("@")
    if ":" in creds:
        user, _ = creds.split(":", 1)
        creds = f"{user}:{REDACTED}"
    return f"{scheme}://{creds}@{host_part}"
