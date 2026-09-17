"""
db_project/connectors/vpn.py — Customer VPN (WireGuard / OpenVPN) for
databases that are only reachable once a site-to-site or client VPN
interface is up (the "Customer VPN" branch of the connection diagram).

Unlike the SSH tunnel (connectors/tunnel.py), a VPN doesn't hand back a
rewritten local (host, port) — once the interface is up, the DB's own
host:port (e.g. a 10.x.x.x private IP) becomes routable directly. So
`open_vpn()` just brings the interface up, optionally waits until the DB
is actually reachable, yields nothing, and tears the interface back down
on exit.

Requirements (installed on the HOST, not via pip):
    WireGuard: `wireguard-tools` package -> provides `wg` / `wg-quick`
    OpenVPN:   `openvpn` package -> provides the `openvpn` binary

Both typically require root, so commands are run with `sudo` by default
(set `use_sudo: false` in VPNConfig if the process already runs as root
or has been granted passwordless capability another way, e.g. via
CAP_NET_ADMIN + polkit rules).

The customer/network team hands you a ready-made config file:
  - WireGuard: a `.conf` file (their private key, the DB-side peer's
    public key + allowed-ips, endpoint, etc.) — this module never sees
    or manages WireGuard keys, only the file path.
  - OpenVPN: a `.ovpn`/`.conf` file, optionally + a separate
    `--auth-user-pass` credentials file.
"""
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from ..config import VPNConfig
from ..exceptions import ConnectivityError
from ..logging_utils import logger


class VPNError(ConnectivityError):
    """Kept as the public name for VPN-specific errors (pre-0.2 name).
    Now a ConnectivityError subclass, so it's also catchable generically."""


@contextmanager
def open_vpn(vpn_cfg: VPNConfig, remote_host: Optional[str] = None, remote_port: Optional[int] = None):
    """
    Bring up the customer VPN interface described by vpn_cfg, optionally
    block until (remote_host, remote_port) is reachable through it, yield
    control to the caller, then tear the interface back down.

        with open_vpn(vpn_cfg, remote_host="10.50.0.5", remote_port=5432):
            conn = SQLConnector("postgres", host="10.50.0.5", port=5432, ...)

    Host/port are NOT rewritten — connect to the DB's real address once
    inside the `with` block.
    """
    logger.info("Bringing up %s VPN interface", vpn_cfg.vpn_type)
    handle = _bring_up(vpn_cfg)
    logger.info("%s VPN interface up", vpn_cfg.vpn_type)
    try:
        probe_host = vpn_cfg.verify_connect_host or remote_host
        probe_port = vpn_cfg.verify_connect_port or remote_port
        if probe_host and probe_port and vpn_cfg.up_timeout:
            _wait_for_reachable(probe_host, int(probe_port), vpn_cfg.up_timeout)
        yield None
    finally:
        _bring_down(vpn_cfg, handle)
        logger.info("%s VPN interface brought down", vpn_cfg.vpn_type)


# ── internals ────────────────────────────────────────────────────────────────

def _sudo(vpn_cfg: VPNConfig) -> list[str]:
    return ["sudo", "-n"] if vpn_cfg.use_sudo else []


def _bring_up(vpn_cfg: VPNConfig):
    if vpn_cfg.vpn_type == "wireguard":
        return _wg_up(vpn_cfg)
    if vpn_cfg.vpn_type == "openvpn":
        return _openvpn_up(vpn_cfg)
    raise VPNError(f"Unsupported vpn_type '{vpn_cfg.vpn_type}'.")


def _bring_down(vpn_cfg: VPNConfig, handle) -> None:
    if vpn_cfg.vpn_type == "wireguard":
        _wg_down(vpn_cfg, handle)
    elif vpn_cfg.vpn_type == "openvpn":
        _openvpn_down(vpn_cfg, handle)


# — WireGuard —————————————————————————————————————————————————————————————

def _wg_up(vpn_cfg: VPNConfig) -> str:
    if shutil.which("wg-quick") is None:
        raise VPNError(
            "WireGuard support requires the 'wireguard-tools' package "
            "(provides `wg-quick`/`wg`) installed on this host."
        )
    config_path = Path(vpn_cfg.config_path)
    if not config_path.exists():
        raise VPNError(f"WireGuard config not found: {config_path}")

    iface = vpn_cfg.interface_name or config_path.stem
    cmd = [*_sudo(vpn_cfg), "wg-quick", "up", str(config_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise VPNError(f"`wg-quick up` failed for interface '{iface}': {result.stderr.strip()}")
    return iface


def _wg_down(vpn_cfg: VPNConfig, iface: str) -> None:
    cmd = [*_sudo(vpn_cfg), "wg-quick", "down", vpn_cfg.config_path]
    subprocess.run(cmd, capture_output=True, text=True)  # best-effort teardown


# — OpenVPN ——————————————————————————————————————————————————————————————

def _openvpn_up(vpn_cfg: VPNConfig) -> dict:
    if shutil.which("openvpn") is None:
        raise VPNError("OpenVPN support requires the 'openvpn' package installed on this host.")
    config_path = Path(vpn_cfg.config_path)
    if not config_path.exists():
        raise VPNError(f"OpenVPN config not found: {config_path}")

    pid_file = f"/tmp/db_project_openvpn_{os.getpid()}_{int(time.time() * 1000)}.pid"
    cmd = [*_sudo(vpn_cfg), "openvpn", "--config", str(config_path),
           "--daemon", "--writepid", pid_file]
    if vpn_cfg.auth_user_pass_path:
        cmd += ["--auth-user-pass", vpn_cfg.auth_user_pass_path]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise VPNError(f"Failed to launch openvpn: {result.stderr.strip()}")

    # wait for the daemon to write its pid file (it forks quickly, but not instantly)
    deadline = time.time() + min(10, vpn_cfg.up_timeout)
    while not os.path.exists(pid_file) and time.time() < deadline:
        time.sleep(0.2)
    if not os.path.exists(pid_file):
        raise VPNError("openvpn did not write a pid file in time; check its logs.")

    return {"pid_file": pid_file}


def _openvpn_down(vpn_cfg: VPNConfig, handle: dict) -> None:
    pid_file = handle.get("pid_file")
    if not pid_file or not os.path.exists(pid_file):
        return
    try:
        pid = int(Path(pid_file).read_text().strip())
        kill_cmd = [*_sudo(vpn_cfg), "kill", str(pid)]
        subprocess.run(kill_cmd, capture_output=True, text=True)
    finally:
        Path(pid_file).unlink(missing_ok=True)


# — shared —————————————————————————————————————————————————————————————————

def _wait_for_reachable(host: str, port: int, timeout: int) -> None:
    """Poll a TCP connect to (host, port) until it succeeds or timeout elapses."""
    deadline = time.time() + timeout
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError as exc:
            last_err = exc
            time.sleep(0.5)
    raise VPNError(
        f"VPN came up but {host}:{port} was not reachable within {timeout}s "
        f"(last error: {last_err})."
    )
