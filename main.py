"""
main.py — FastAPI test harness for db_project.

Exercises every branch of the connection diagram:

    Database Connection
           |
     +-----+-----+
     |           |
   Direct    Secure Tunnel
     |           |
 host:port  +----+----+
            |         |
       SSH/Bastion  Customer VPN
            |        (WireGuard/OpenVPN)
            +----+----+
                 |
                 DB

Run:
    uvicorn main:app --reload --port 8000

Then open http://127.0.0.1:8000/docs for interactive Swagger UI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from db_project.manager import ProjectManager

app = FastAPI(
    title="db_project API",
    description="Register DB connections (Direct / SSH-Bastion / Customer VPN), "
                 "upload files, and convert uploads into real DB tables.",
    version="1.0.0",
)

# Allow the dashboard frontend (running on a different origin/port) to call this API.
# Lock allow_origins down to your actual dashboard's URL(s) before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pm = ProjectManager()


# ── request/response models ─────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    project_id: str


class SSHTunnelIn(BaseModel):
    ssh_host: str
    ssh_username: str
    ssh_port: int = 22
    ssh_password: Optional[str] = None
    ssh_pkey_path: Optional[str] = None
    ssh_pkey_passphrase: Optional[str] = None
    local_bind_port: int = 0
    connect_timeout: int = 15


class VPNIn(BaseModel):
    vpn_type: Literal["wireguard", "openvpn"] = "wireguard"
    config_path: str
    auth_user_pass_path: Optional[str] = None
    interface_name: Optional[str] = None
    use_sudo: bool = True
    up_timeout: int = 30
    verify_connect_host: Optional[str] = None
    verify_connect_port: Optional[int] = None


class AddSQLSourceRequest(BaseModel):
    name: str
    dialect: Literal["postgres", "postgresql", "mysql", "mariadb", "mssql", "sqlite"]
    host: str = ""
    port: int = 0
    database: str
    username: str = ""
    password: str = ""
    ssl: bool = True
    connect_timeout: int = 30
    # secure-tunnel branch — set at most one
    tunnel: Optional[SSHTunnelIn] = None
    vpn: Optional[VPNIn] = None

    @model_validator(mode="after")
    def _one_tunnel_method(self):
        if self.tunnel and self.vpn:
            raise ValueError("Set only one of `tunnel` (SSH) or `vpn` (WireGuard/OpenVPN), not both.")
        return self


class AddNoSQLSourceRequest(BaseModel):
    name: str
    engine: str = "mongodb"
    host: str
    port: int = 27017
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    tunnel: Optional[SSHTunnelIn] = None
    vpn: Optional[VPNIn] = None

    @model_validator(mode="after")
    def _one_tunnel_method(self):
        if self.tunnel and self.vpn:
            raise ValueError("Set only one of `tunnel` (SSH) or `vpn` (WireGuard/OpenVPN), not both.")
        return self


class QuerySQLRequest(BaseModel):
    sql: str
    params: Optional[dict[str, Any]] = None


class FetchNoSQLRequest(BaseModel):
    collection: str
    query: Optional[dict[str, Any]] = None
    limit: int = 100


class UploadToDatabaseRequest(BaseModel):
    filename: str
    target_source: str
    table_name: Optional[str] = None
    if_exists: Literal["replace", "append", "fail"] = "replace"
    file_format: str = "auto"


# ── health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── projects ─────────────────────────────────────────────────────────────────

@app.post("/projects", status_code=201)
def create_project(req: CreateProjectRequest):
    pm.create_project(req.project_id)
    return {"project_id": req.project_id}


@app.get("/projects")
def list_projects():
    return {"projects": pm.list_projects()}


# ── sources ──────────────────────────────────────────────────────────────────

@app.post("/projects/{project_id}/sources/sql", status_code=201)
def add_sql_source(project_id: str, req: AddSQLSourceRequest):
    try:
        pm.add_sql_source(
            project_id, req.name, dialect=req.dialect, host=req.host, port=req.port,
            database=req.database, username=req.username, password=req.password,
            ssl=req.ssl, connect_timeout=req.connect_timeout,
            tunnel=req.tunnel.model_dump() if req.tunnel else None,
            vpn=req.vpn.model_dump() if req.vpn else None,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return pm.source_info(project_id, req.name)


@app.post("/projects/{project_id}/sources/nosql", status_code=201)
def add_nosql_source(project_id: str, req: AddNoSQLSourceRequest):
    try:
        pm.add_nosql_source(
            project_id, req.name, engine=req.engine, host=req.host, port=req.port,
            database=req.database, username=req.username, password=req.password,
            tunnel=req.tunnel.model_dump() if req.tunnel else None,
            vpn=req.vpn.model_dump() if req.vpn else None,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return pm.source_info(project_id, req.name)


@app.get("/projects/{project_id}/sources")
def list_sources(project_id: str):
    try:
        names = pm.list_sources(project_id)
        return {"sources": [pm.source_info(project_id, n) for n in names]}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.delete("/projects/{project_id}/sources/{name}", status_code=204)
def remove_source(project_id: str, name: str):
    pm.remove_source(project_id, name)
    return JSONResponse(status_code=204, content=None)


# ── uploads ──────────────────────────────────────────────────────────────────

@app.post("/projects/{project_id}/uploads", status_code=201)
async def upload_file(project_id: str, file: UploadFile = File(...)):
    raw = await file.read()
    try:
        path = pm.save_upload(project_id, file.filename, raw)
    except FileNotFoundError:
        raise HTTPException(404, f"Project '{project_id}' not found. Create it first.")
    return {"filename": file.filename, "path": str(path), "size_bytes": len(raw)}


@app.get("/projects/{project_id}/uploads")
def list_uploads(project_id: str):
    try:
        return {"uploads": pm.list_uploads(project_id)}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


# ── the conversion step: upload -> real DB table ────────────────────────────

@app.post("/projects/{project_id}/uploads/to-database")
def upload_to_database(project_id: str, req: UploadToDatabaseRequest):
    try:
        rows = pm.upload_to_database(
            project_id, req.filename, target_source=req.target_source,
            table_name=req.table_name, if_exists=req.if_exists, file_format=req.file_format,
        )
    except (FileNotFoundError, KeyError) as e:
        raise HTTPException(404, str(e))
    except Exception as e:  # connection/tunnel/vpn errors etc.
        raise HTTPException(502, f"{type(e).__name__}: {e}")
    return {"rows_written": rows, "table_name": req.table_name or Path(req.filename).stem}


# ── pulling data back out ───────────────────────────────────────────────────

@app.post("/projects/{project_id}/sources/{name}/query")
def query_sql(project_id: str, name: str, req: QuerySQLRequest):
    try:
        df = pm.query_sql(project_id, name, req.sql, params=req.params)
    except Exception as e:
        raise HTTPException(502, f"{type(e).__name__}: {e}")
    return {"rows": df.to_dict(orient="records"), "row_count": len(df)}


@app.post("/projects/{project_id}/sources/{name}/fetch")
def fetch_nosql(project_id: str, name: str, req: FetchNoSQLRequest):
    try:
        df = pm.fetch_nosql(project_id, name, req.collection, query=req.query, limit=req.limit)
    except Exception as e:
        raise HTTPException(502, f"{type(e).__name__}: {e}")
    return {"rows": df.to_dict(orient="records"), "row_count": len(df)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
