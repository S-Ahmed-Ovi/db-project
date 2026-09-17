"""
db_project/config.py — project + data-source configuration.

Every data source is reached one of three ways (see connectors/README or the
package docstring for the diagram):

    Direct          -> connect straight to host:port
    Secure Tunnel
      - SSH/Bastion -> connect through a local port forwarded over SSH
      - Customer VPN -> bring up a WireGuard/OpenVPN interface, then
                        connect straight to host:port (now routable)

A source's `connection_mode` is derived automatically from which of
`tunnel` (SSH) / `vpn` (WireGuard/OpenVPN) is present in its config — a
source may set at most one of the two.

Disk layout
-----------
    projects/
      {project_id}/
        config.json     <- sources registry (this module)
        uploads/         <- raw uploaded files (csv/xlsx/json/parquet)

config.json shape
------------------
    {
      "project_id": "acme",
      "sources": {
        "warehouse": {
          "kind": "sql", "dialect": "postgres",
          "host": "db.acme.com", "port": 5432, "database": "warehouse",
          "username": "svc", "password": "secret", "ssl": true
        },
        "internal_mysql": {
          "kind": "sql", "dialect": "mysql",
          "host": "10.0.4.12", "port": 3306, "database": "app",
          "username": "svc", "password": "secret",
          "tunnel": {
            "ssh_host": "bastion.acme.com", "ssh_username": "deploy",
            "ssh_pkey_path": "/secrets/id_rsa"
          }
        },
        "customer_wireguard_db": {
          "kind": "sql", "dialect": "postgres",
          "host": "10.50.0.5", "port": 5432, "database": "app",
          "username": "svc", "password": "secret",
          "vpn": {
            "vpn_type": "wireguard",
            "config_path": "/secrets/customer_acme.conf"
          }
        },
        "events": {
          "kind": "nosql", "engine": "mongodb",
          "host": "mongo.acme.com", "port": 27017, "database": "events"
        }
      }
    }

Secrets can be omitted from config.json and supplied via env var instead:
    {PROJECT}__{SOURCE}__PASSWORD
    {PROJECT}__{SOURCE}__SSH_PASSWORD
so config.json can be committed to source control without credentials.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .exceptions import ConfigurationError

# Default: a "projects" folder in the current working directory of whatever
# process imports this package. Override with the DB_PROJECTS_ROOT env var,
# e.g. to point at a persistent data directory in production.
#
# NOTE: this intentionally does NOT default to a path next to this file.
# Once this package is pip-installed, this file lives inside site-packages/,
# which is frequently read-only and is never where you want per-project
# runtime data (config.json, uploaded files) to be written.
PROJECTS_ROOT = Path(os.getenv("DB_PROJECTS_ROOT", str(Path.cwd() / "projects")))

VALID_KINDS = ("sql", "nosql", "file")
VALID_CONNECTION_MODES = ("direct", "ssh_tunnel", "vpn")
VALID_VPN_TYPES = ("wireguard", "openvpn")


def _clean_env_key(*parts: str) -> str:
    def c(s: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in s).upper()
    return "__".join(c(p) for p in parts)


def _env_override(project_id: str, source_name: str, field_name: str) -> Optional[str]:
    return os.getenv(_clean_env_key(project_id, source_name, field_name))


@dataclass
class SSHTunnelConfig:
    """Bastion/VPN jump-host details for a source that isn't directly reachable."""
    ssh_host: str
    ssh_username: str
    ssh_port: int = 22
    ssh_password: Optional[str] = None
    ssh_pkey_path: Optional[str] = None
    ssh_pkey_passphrase: Optional[str] = None
    local_bind_port: int = 0        # 0 = OS picks a free local port
    connect_timeout: int = 15

    def __post_init__(self):
        if not self.ssh_password and not self.ssh_pkey_path:
            raise ConfigurationError("SSHTunnelConfig needs ssh_password or ssh_pkey_path.")


@dataclass
class VPNConfig:
    """Customer VPN (WireGuard/OpenVPN) details for a source only reachable
    once a site-to-site / client VPN interface is brought up."""
    vpn_type: str                              # "wireguard" | "openvpn"
    config_path: str                           # .conf (wg) or .ovpn (openvpn)
    auth_user_pass_path: Optional[str] = None  # openvpn --auth-user-pass file
    interface_name: Optional[str] = None       # wg interface; default = config file stem
    use_sudo: bool = True                      # wg-quick/openvpn need root
    up_timeout: int = 30                       # seconds to wait for the tunnel to come up
    verify_connect_host: Optional[str] = None  # optional TCP reachability probe...
    verify_connect_port: Optional[int] = None  # ...defaults to the DB's own host:port

    def __post_init__(self):
        if self.vpn_type not in VALID_VPN_TYPES:
            raise ConfigurationError(f"vpn_type must be one of {VALID_VPN_TYPES}, got '{self.vpn_type}'.")
        if not self.config_path:
            raise ConfigurationError(
                "VPNConfig needs config_path (WireGuard .conf, or OpenVPN .ovpn/.conf file)."
            )


@dataclass
class SourceConfig:
    """One named data source belonging to a project."""
    name: str
    kind: str                      # "sql" | "nosql" | "file"
    raw: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in VALID_KINDS:
            raise ConfigurationError(f"Invalid source kind '{self.kind}'. Must be one of {VALID_KINDS}.")
        if self.raw.get("tunnel") and self.raw.get("vpn"):
            raise ConfigurationError(
                f"Source '{self.name}': set only ONE secure-tunnel method — either "
                "'tunnel' (SSH/bastion) or 'vpn' (WireGuard/OpenVPN), not both."
            )

    @property
    def tunnel(self) -> Optional[SSHTunnelConfig]:
        t = self.raw.get("tunnel")
        if not t:
            return None
        return SSHTunnelConfig(
            ssh_host=t["ssh_host"],
            ssh_username=t["ssh_username"],
            ssh_port=int(t.get("ssh_port", 22)),
            ssh_password=t.get("ssh_password"),
            ssh_pkey_path=t.get("ssh_pkey_path"),
            ssh_pkey_passphrase=t.get("ssh_pkey_passphrase"),
            local_bind_port=int(t.get("local_bind_port", 0)),
            connect_timeout=int(t.get("connect_timeout", 15)),
        )

    @property
    def vpn(self) -> Optional[VPNConfig]:
        v = self.raw.get("vpn")
        if not v:
            return None
        return VPNConfig(
            vpn_type=v.get("vpn_type", "wireguard"),
            config_path=v["config_path"],
            auth_user_pass_path=v.get("auth_user_pass_path"),
            interface_name=v.get("interface_name"),
            use_sudo=bool(v.get("use_sudo", True)),
            up_timeout=int(v.get("up_timeout", 30)),
            verify_connect_host=v.get("verify_connect_host"),
            verify_connect_port=v.get("verify_connect_port"),
        )

    @property
    def connection_mode(self) -> str:
        """'direct' | 'ssh_tunnel' | 'vpn' — derived from raw config, matches the diagram."""
        if self.raw.get("tunnel"):
            return "ssh_tunnel"
        if self.raw.get("vpn"):
            return "vpn"
        return "direct"


@dataclass
class ProjectConfig:
    project_id: str
    sources: dict[str, SourceConfig] = field(default_factory=dict)

    @property
    def project_dir(self) -> Path:
        d = PROJECTS_ROOT / self.project_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def uploads_dir(self) -> Path:
        d = self.project_dir / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def config_path(self) -> Path:
        return self.project_dir / "config.json"


# ── load / save / list ──────────────────────────────────────────────────────

def load_project(project_id: str) -> ProjectConfig:
    path = PROJECTS_ROOT / project_id / "config.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No project '{project_id}' at {path}. Call ProjectManager.create_project() first."
        )
    raw = json.loads(path.read_text())
    sources = {}
    for name, src_raw in raw.get("sources", {}).items():
        merged = dict(src_raw)
        for f in ("username", "password"):
            override = _env_override(project_id, name, f)
            if override is not None:
                merged[f] = override
        if merged.get("tunnel"):
            override = _env_override(project_id, name, "ssh_password")
            if override is not None:
                merged["tunnel"] = {**merged["tunnel"], "ssh_password": override}
        if merged.get("vpn"):
            # VPN secrets normally live inside the config_path/auth file itself,
            # but allow overriding which file is used per-environment too.
            override = _env_override(project_id, name, "vpn_config_path")
            if override is not None:
                merged["vpn"] = {**merged["vpn"], "config_path": override}
        sources[name] = SourceConfig(name=name, kind=merged.get("kind"), raw=merged)
    return ProjectConfig(project_id=project_id, sources=sources)


def save_project(cfg: ProjectConfig) -> None:
    payload = {
        "project_id": cfg.project_id,
        "sources": {n: {**s.raw, "kind": s.kind} for n, s in cfg.sources.items()},
    }
    cfg.config_path.write_text(json.dumps(payload, indent=2))


def list_projects() -> list[str]:
    if not PROJECTS_ROOT.exists():
        return []
    return sorted(p.name for p in PROJECTS_ROOT.iterdir() if p.is_dir() and (p / "config.json").exists())
