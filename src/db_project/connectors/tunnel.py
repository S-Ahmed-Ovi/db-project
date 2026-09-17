"""
db_project/connectors/tunnel.py — SSH tunnel for VPN/bastion-only databases.

Some databases are never exposed publicly — only reachable from inside a
VPC/VPN via an SSH bastion (jump) host. This opens a local forwarded port to
the bastion and returns the (host, port) to connect to instead — 127.0.0.1
and whatever local port got bound. The caller then builds its normal
SQLConnector/MongoConnector against that local endpoint.

Requires: pip install sshtunnel paramiko
"""
from __future__ import annotations

from contextlib import contextmanager

from ..config import SSHTunnelConfig
from ..exceptions import ConnectivityError
from ..logging_utils import logger


@contextmanager
def open_tunnel(remote_host: str, remote_port: int, tunnel_cfg: SSHTunnelConfig):
    """
    Open an SSH tunnel to (remote_host, remote_port) via the bastion described
    by tunnel_cfg. Yields (local_host, local_port) to connect to instead.

        with open_tunnel("10.0.4.12", 5432, tunnel_cfg) as (host, port):
            conn = SQLConnector("postgres", host=host, port=port, ...)
    """
    try:
        from sshtunnel import SSHTunnelForwarder
    except ImportError:
        raise ImportError(
            "VPN/SSH tunnel support requires 'sshtunnel' + 'paramiko': "
            "pip install sshtunnel paramiko"
        )

    forwarder = SSHTunnelForwarder(
        (tunnel_cfg.ssh_host, tunnel_cfg.ssh_port),
        ssh_username=tunnel_cfg.ssh_username,
        ssh_password=tunnel_cfg.ssh_password,
        ssh_pkey=tunnel_cfg.ssh_pkey_path,
        ssh_private_key_password=tunnel_cfg.ssh_pkey_passphrase,
        remote_bind_address=(remote_host, remote_port),
        local_bind_address=("127.0.0.1", tunnel_cfg.local_bind_port),
        set_keepalive=30.0,
    )
    logger.info("Opening SSH tunnel via %s -> %s:%s", tunnel_cfg.ssh_host, remote_host, remote_port)
    try:
        forwarder.start()
    except Exception as exc:
        raise ConnectivityError(f"Could not establish SSH tunnel via {tunnel_cfg.ssh_host}: {exc}") from exc
    logger.info("SSH tunnel established (local port %s)", forwarder.local_bind_port)
    try:
        yield "127.0.0.1", forwarder.local_bind_port
    finally:
        forwarder.stop()
        logger.info("SSH tunnel closed")
