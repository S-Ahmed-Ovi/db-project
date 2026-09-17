"""Customer VPN (WireGuard/OpenVPN) tests, fully mocked — no real
wg-quick/openvpn binaries or root privileges involved."""
from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

from db_project.config import VPNConfig
from db_project.connectors.vpn import VPNError, open_vpn
from db_project.exceptions import ConnectivityError


def _wg_cfg(tmp_path, **overrides):
    conf = tmp_path / "acme.conf"
    conf.write_text("[Interface]\nPrivateKey = fake\n")
    fields = dict(vpn_type="wireguard", config_path=str(conf), up_timeout=0)
    fields.update(overrides)
    return VPNConfig(**fields)


def test_wireguard_up_and_down(tmp_path):
    cfg = _wg_cfg(tmp_path)
    with patch("shutil.which", return_value="/usr/bin/wg-quick"), \
         patch("subprocess.run", return_value=MagicMock(returncode=0, stderr="")) as run:
        with open_vpn(cfg):
            pass
    calls = [c.args[0] for c in run.call_args_list]
    assert any("up" in c for c in calls)
    assert any("down" in c for c in calls)


def test_wireguard_missing_tool_raises_vpn_error(tmp_path):
    cfg = _wg_cfg(tmp_path)
    with patch("shutil.which", return_value=None):
        with pytest.raises(VPNError):
            with open_vpn(cfg):
                pass


def test_wireguard_up_failure_raises_connectivity_error(tmp_path):
    cfg = _wg_cfg(tmp_path)
    with patch("shutil.which", return_value="/usr/bin/wg-quick"), \
         patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="boom")):
        with pytest.raises(ConnectivityError):
            with open_vpn(cfg):
                pass


def test_missing_config_file_raises(tmp_path):
    cfg = VPNConfig(vpn_type="wireguard", config_path=str(tmp_path / "nope.conf"))
    with patch("shutil.which", return_value="/usr/bin/wg-quick"):
        with pytest.raises(VPNError):
            with open_vpn(cfg):
                pass


def test_reachability_probe_after_vpn_up(tmp_path):
    # verify_connect_host/port + up_timeout triggers a TCP reachability
    # check; make it succeed instantly against a local listening socket.
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    cfg = _wg_cfg(tmp_path, up_timeout=2, verify_connect_host="127.0.0.1",
                  verify_connect_port=port)
    try:
        with patch("shutil.which", return_value="/usr/bin/wg-quick"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0, stderr="")):
            with open_vpn(cfg):
                pass
    finally:
        srv.close()
