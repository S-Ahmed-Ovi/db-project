"""SSH-tunnel tests, fully mocked — no real network/bastion involved."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from db_project.config import SSHTunnelConfig
from db_project.connectors.tunnel import open_tunnel
from db_project.exceptions import ConnectivityError


def _cfg():
    return SSHTunnelConfig(ssh_host="bastion.acme.com", ssh_username="deploy",
                            ssh_password="x")


def test_open_tunnel_yields_local_loopback_and_bound_port():
    fake_forwarder = MagicMock()
    fake_forwarder.local_bind_port = 54321

    with patch("sshtunnel.SSHTunnelForwarder", return_value=fake_forwarder):
        with open_tunnel("10.0.4.12", 5432, _cfg()) as (host, port):
            assert host == "127.0.0.1"
            assert port == 54321
    fake_forwarder.start.assert_called_once()
    fake_forwarder.stop.assert_called_once()


def test_tunnel_start_failure_wrapped_as_connectivity_error():
    fake_forwarder = MagicMock()
    fake_forwarder.start.side_effect = RuntimeError("bastion unreachable")

    with patch("sshtunnel.SSHTunnelForwarder", return_value=fake_forwarder):
        with pytest.raises(ConnectivityError):
            with open_tunnel("10.0.4.12", 5432, _cfg()):
                pass
