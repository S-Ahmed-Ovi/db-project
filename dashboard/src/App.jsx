import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area, ScatterChart, Scatter,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Database, Table2, Search, Play, ChevronRight, ChevronDown, Plug,
  RefreshCw, AlertCircle, CheckCircle2, BarChart3, LineChart as LineIcon,
  ScatterChart as ScatterIcon, Hash, CalendarDays, Type as TypeIcon, Layers,
  Plus, Trash2, FolderPlus, KeyRound, Filter, X as XIcon, PieChart as PieIcon,
  AreaChart as AreaIcon, Table as TableIcon, Code2, ArrowUpDown,
} from "lucide-react";

/* ────────────────────────────────────────────────────────────────────────
   DESIGN TOKENS
   Ink / paper console for analysts: dense, mono-forward, instrument-panel
   readout cards. One accent (signal teal) means "connected / healthy",
   amber means "needs attention", indigo carries chart series.
   ──────────────────────────────────────────────────────────────────────── */
const T = {
  ink: "#11151A",
  paper: "#EEF1EF",
  panel: "#FFFFFF",
  line: "#D9DFDC",
  text: "#161A1F",
  muted: "#606A64",
  faint: "#8B948E",
  teal: "#1F8A70",
  tealSoft: "#E4F2ED",
  indigo: "#3A4CBB",
  indigoSoft: "#E7E9F7",
  amber: "#C98A2C",
  amberSoft: "#FBF0DE",
  rose: "#B8463A",
  roseSoft: "#F8E9E7",
};
const SERIES = [T.indigo, T.teal, T.amber, T.rose, "#6B5FA8", "#3E8FA8"];

const CSS = `
  * { box-sizing: border-box; }
  .console { font-family: 'Inter', -apple-system, sans-serif; color: ${T.text}; background: ${T.paper}; min-height: 100%; }
  .mono { font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace; }
  .disp { font-family: 'Space Grotesk', 'Inter', sans-serif; }

  .topbar { background: ${T.ink}; color: #F1F3F1; padding: 10px 16px; display:flex; align-items:center; gap:14px; }
  .topbar .brand { display:flex; align-items:center; gap:8px; font-weight:600; letter-spacing:.02em; font-size:14px; }
  .topbar input, .topbar select { background:#1C222A; border:1px solid #2B333D; color:#EAEDEA; border-radius:6px; padding:6px 10px; font-size:12.5px; }
  .topbar input::placeholder { color:#6E7680; }
  .topbar .field-label { font-size:10px; text-transform:uppercase; letter-spacing:.08em; color:#8890A0; margin-bottom:2px; display:block; }
  .status-pill { display:flex; align-items:center; gap:6px; font-size:11.5px; padding:5px 10px; border-radius:999px; font-family:'JetBrains Mono',monospace; }

  .layout { display:flex; height: calc(100vh - 0px); min-height:640px; }
  .sidebar { width:260px; flex-shrink:0; background:${T.panel}; border-right:1px solid ${T.line}; overflow-y:auto; }
  .side-section-title { font-size:10.5px; text-transform:uppercase; letter-spacing:.09em; color:${T.faint}; padding:14px 14px 6px; font-weight:600; }
  .src-row, .tbl-row { display:flex; align-items:center; gap:8px; padding:7px 14px; cursor:pointer; font-size:13px; }
  .src-row:hover, .tbl-row:hover { background:${T.paper}; }
  .src-row.active { background:${T.indigoSoft}; color:${T.indigo}; font-weight:600; }
  .tbl-row.active { background:${T.tealSoft}; color:${T.teal}; font-weight:600; }
  .dialect-chip { font-size:9.5px; padding:1px 6px; border-radius:4px; background:${T.paper}; color:${T.muted}; font-family:'JetBrains Mono',monospace; margin-left:auto; }

  .main { flex:1; overflow-y:auto; padding:22px 28px 60px; }
  .tabs { display:flex; gap:2px; border-bottom:1px solid ${T.line}; margin-bottom:20px; }
  .tab { padding:9px 16px; font-size:13px; font-weight:600; color:${T.muted}; cursor:pointer; border-bottom:2px solid transparent; display:flex; align-items:center; gap:6px; }
  .tab.active { color:${T.ink}; border-bottom-color:${T.teal}; }

  .empty { display:flex; flex-direction:column; align-items:center; justify-content:center; padding:80px 20px; color:${T.faint}; text-align:center; gap:10px; }
  .empty .disp { font-size:17px; color:${T.muted}; }

  .row-title { display:flex; align-items:baseline; gap:10px; margin-bottom:16px; }
  .row-title h2 { font-size:19px; margin:0; }
  .row-title .meta { font-size:12px; color:${T.faint}; font-family:'JetBrains Mono',monospace; }

  .cardgrid { display:grid; grid-template-columns: repeat(auto-fill, minmax(230px,1fr)); gap:14px; margin-bottom:26px; }
  .readout { background:${T.panel}; border:1px solid ${T.line}; border-radius:10px; padding:14px 16px; }
  .readout .idx { font-family:'JetBrains Mono',monospace; font-size:10px; color:${T.faint}; letter-spacing:.06em; }
  .readout .colname { font-family:'JetBrains Mono',monospace; font-size:13.5px; font-weight:600; margin:2px 0 10px; word-break:break-all; }
  .readout .type-tag { display:inline-flex; align-items:center; gap:4px; font-size:10px; padding:2px 7px; border-radius:5px; margin-bottom:10px; font-weight:600; }
  .type-numeric { background:${T.indigoSoft}; color:${T.indigo}; }
  .type-date { background:${T.tealSoft}; color:${T.teal}; }
  .type-categorical { background:${T.amberSoft}; color:${T.amber}; }
  .statline { display:flex; justify-content:space-between; font-size:12px; padding:2px 0; }
  .statline .k { color:${T.faint}; }
  .statline .v { font-family:'JetBrains Mono',monospace; font-weight:600; }
  .nullbar-track { height:4px; background:${T.paper}; border-radius:2px; margin-top:8px; overflow:hidden; }
  .nullbar-fill { height:100%; background:${T.amber}; }
  .pill-list { display:flex; flex-direction:column; gap:5px; margin-bottom:8px; }
  .pill-item { display:flex; align-items:center; gap:6px; font-size:11px; }
  .pill-label { flex:0 0 72px; font-family:'JetBrains Mono',monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:${T.muted}; }
  .pill-track { flex:1; height:6px; background:${T.paper}; border-radius:3px; overflow:hidden; }
  .pill-fill { display:block; height:100%; background:${T.teal}; }
  .pill-pct { flex:0 0 30px; text-align:right; font-family:'JetBrains Mono',monospace; font-weight:600; }

  .panel { background:${T.panel}; border:1px solid ${T.line}; border-radius:10px; padding:16px 18px; margin-bottom:22px; }
  .panel h3 { font-size:13px; margin:0 0 12px; text-transform:uppercase; letter-spacing:.06em; color:${T.muted}; }

  .btn { display:inline-flex; align-items:center; gap:6px; background:${T.ink}; color:#fff; border:none; border-radius:7px; padding:8px 14px; font-size:12.5px; font-weight:600; cursor:pointer; }
  .btn.teal { background:${T.teal}; }
  .btn:disabled { opacity:.45; cursor:not-allowed; }
  .btn.ghost { background:transparent; color:${T.ink}; border:1px solid ${T.line}; }

  .selectRow { display:flex; gap:10px; flex-wrap:wrap; align-items:flex-end; margin-bottom:14px; }
  .field { display:flex; flex-direction:column; gap:4px; }
  .field label { font-size:10.5px; text-transform:uppercase; letter-spacing:.06em; color:${T.faint}; }
  .field select, .field input { border:1px solid ${T.line}; border-radius:6px; padding:7px 9px; font-size:12.5px; min-width:150px; font-family:'JetBrains Mono',monospace; background:${T.paper}; }
  .chiprow { display:flex; gap:6px; }
  .chip { border:1px solid ${T.line}; background:${T.paper}; border-radius:6px; padding:6px 9px; cursor:pointer; display:flex; align-items:center; gap:5px; font-size:12px; }
  .chip.active { background:${T.ink}; color:#fff; border-color:${T.ink}; }

  textarea.sqlbox { width:100%; min-height:120px; font-family:'JetBrains Mono',monospace; font-size:12.5px; border:1px solid ${T.line}; border-radius:8px; padding:12px; background:${T.ink}; color:#D8F0E6; resize:vertical; }

  table.grid { width:100%; border-collapse:collapse; font-size:12px; font-family:'JetBrains Mono',monospace; }
  table.grid th { text-align:left; background:${T.paper}; padding:7px 10px; border-bottom:1px solid ${T.line}; font-weight:600; position:sticky; top:0; }
  table.grid td { padding:6px 10px; border-bottom:1px solid #EEF0EE; white-space:nowrap; max-width:260px; overflow:hidden; text-overflow:ellipsis; }
  .gridwrap { max-height:360px; overflow:auto; border:1px solid ${T.line}; border-radius:8px; }

  .errbox { background:${T.roseSoft}; color:${T.rose}; border:1px solid #E6C4BF; padding:10px 14px; border-radius:8px; font-size:12.5px; margin-bottom:14px; display:flex; gap:8px; align-items:flex-start; }
  .banner { font-size:11.5px; color:${T.faint}; margin-bottom:10px; }

  .side-hdr { display:flex; align-items:center; justify-content:space-between; padding-right:10px; }
  .icon-btn { background:none; border:1px solid transparent; color:${T.faint}; cursor:pointer; padding:2px 5px; border-radius:5px; display:flex; align-items:center; }
  .icon-btn:hover { background:${T.paper}; color:${T.ink}; }
  .src-row .icon-btn { opacity:0; margin-left:4px; }
  .src-row:hover .icon-btn { opacity:1; }
  .new-project-row { display:flex; gap:6px; padding:4px 14px 12px; }
  .new-project-row input { flex:1; border:1px solid ${T.line}; border-radius:6px; padding:6px 8px; font-size:12px; font-family:'JetBrains Mono',monospace; }

  .formgrid { display:grid; grid-template-columns: repeat(auto-fit, minmax(190px,1fr)); gap:12px; margin-bottom:14px; }
  .formgrid .field select, .formgrid .field input { width:100%; min-width:0; }
  .toggle-row { display:flex; align-items:center; gap:14px; margin:6px 0 16px; }
  .toggle-row label { display:flex; align-items:center; gap:6px; font-size:12.5px; cursor:pointer; }
  .success-box { background:${T.tealSoft}; color:${T.teal}; border:1px solid #BFE4D6; padding:10px 14px; border-radius:8px; font-size:12.5px; margin-bottom:14px; display:flex; gap:8px; align-items:center; }
  .subhead { font-size:11.5px; text-transform:uppercase; letter-spacing:.07em; color:${T.faint}; margin:18px 0 8px; display:flex; align-items:center; gap:6px; }

  .builder { display:grid; grid-template-columns: 260px 1fr; gap:0; }
  .builder-rail { border-right:1px solid ${T.line}; padding-right:20px; }
  .builder-canvas { padding-left:20px; }
  .well { background:${T.paper}; border:1px solid ${T.line}; border-radius:8px; padding:10px 12px; margin-bottom:14px; }
  .well-title { font-size:10.5px; text-transform:uppercase; letter-spacing:.07em; color:${T.faint}; font-weight:700; margin-bottom:8px; display:flex; align-items:center; justify-content:space-between; }
  .measure-row, .filter-row { display:flex; gap:6px; align-items:center; margin-bottom:6px; }
  .measure-row select, .filter-row select, .filter-row input { border:1px solid ${T.line}; border-radius:6px; padding:5px 7px; font-size:11.5px; font-family:'JetBrains Mono',monospace; background:#fff; min-width:0; flex:1; }
  .row-del { background:none; border:none; color:${T.faint}; cursor:pointer; padding:3px; flex:0 0 auto; }
  .row-del:hover { color:${T.rose}; }
  .add-row-btn { display:flex; align-items:center; gap:5px; font-size:11.5px; color:${T.indigo}; cursor:pointer; padding:4px 2px; font-weight:600; }
  .add-row-btn:hover { text-decoration:underline; }
  .charttype-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap:6px; }
  .charttype-btn { border:1px solid ${T.line}; background:#fff; border-radius:7px; padding:8px 4px; display:flex; flex-direction:column; align-items:center; gap:4px; font-size:10px; cursor:pointer; color:${T.muted}; }
  .charttype-btn.active { border-color:${T.indigo}; color:${T.indigo}; background:${T.indigoSoft}; }
  .sql-preview { background:${T.ink}; color:#9FB0E8; font-family:'JetBrains Mono',monospace; font-size:11px; padding:10px 12px; border-radius:8px; margin-bottom:16px; white-space:pre-wrap; word-break:break-all; }
  .kpi-strip { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
  .kpi { background:${T.panel}; border:1px solid ${T.line}; border-radius:8px; padding:10px 16px; min-width:120px; }
  .kpi .v { font-family:'JetBrains Mono',monospace; font-size:18px; font-weight:700; }
  .kpi .k { font-size:10.5px; color:${T.faint}; text-transform:uppercase; letter-spacing:.05em; }
`;

/* ── dialect-aware SQL helpers (works across postgres/mysql/mariadb/mssql/sqlite) ── */
function listTablesSQL(dialect) {
  if (dialect === "sqlite")
    return `SELECT name AS table_name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name`;
  if (dialect === "mysql" || dialect === "mariadb")
    return `SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() ORDER BY table_name`;
  return `SELECT table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema','sys') ORDER BY table_name`;
}
function listColumnsSQL(dialect, table) {
  if (dialect === "sqlite") return `PRAGMA table_info(${table})`;
  return `SELECT column_name, data_type, ordinal_position FROM information_schema.columns WHERE table_name = '${table}' ORDER BY ordinal_position`;
}
function classify(name, dataType) {
  const t = (dataType || "").toLowerCase();
  const n = (name || "").toLowerCase();
  if (/date|time/.test(t)) return "date";
  // Identifier/key-like columns (store_id, sku, event_id, date_key, osm_id...) get
  // their own lightweight treatment instead of an expensive/slow GROUP BY or a
  // meaningless numeric min/avg/max — this is what was hanging on wide fact
  // tables with high-cardinality text/int keys.
  if (/(^id$|_id$|_key$|^key$|^sku$|_sku$|code$)/.test(n)) return "identifier";
  if (/int|numeric|decimal|double|real|float|money/.test(t)) return "numeric";
  return "categorical";
}
function isFlagLike(name) {
  return /^(is_|has_)/i.test(name || "");
}
/* Dialect-aware month bucketing pushed down to SQL — avoids the old approach
   of pulling a client-side sample (which produced misleading spikes on large
   unordered tables) and scales to tables with 100k+ rows. */
function monthBucketExpr(dialect, col) {
  const c = q(col);
  if (dialect === "mysql" || dialect === "mariadb") return `DATE_FORMAT(${c}, '%Y-%m')`;
  if (dialect === "mssql") return `FORMAT(${c}, 'yyyy-MM')`;
  if (dialect === "sqlite") return `strftime('%Y-%m', ${c})`;
  return `to_char(date_trunc('month', ${c}), 'YYYY-MM')`;
}
function limitClause(dialect, n) {
  return dialect === "mssql" ? "" : ` LIMIT ${n}`;
}
function topPrefix(dialect, n) {
  return dialect === "mssql" ? `TOP ${n} ` : "";
}
function q(id) { return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(id) ? id : `"${id.replace(/"/g, '')}"`; }

let _uid = 0;
function uid() { return `r${++_uid}`; }

const AGGS = ["count", "sum", "avg", "min", "max", "count_distinct"];
function aggExpr(agg, col) {
  if (agg === "count") return "COUNT(*)";
  if (agg === "count_distinct") return `COUNT(DISTINCT ${q(col)})`;
  return `${agg.toUpperCase()}(${q(col)})`;
}
const FILTER_OPS = [
  ["=", "="], ["!=", "≠"], [">", ">"], ["<", "<"], [">=", "≥"], ["<=", "≤"],
  ["contains", "contains"], ["is_null", "is empty"], ["is_not_null", "is not empty"],
];
function filterSQL(f) {
  if (!f.col) return null;
  const col = q(f.col);
  if (f.op === "is_null") return `${col} IS NULL`;
  if (f.op === "is_not_null") return `${col} IS NOT NULL`;
  if (f.val === "" || f.val === undefined) return null;
  const isNum = !isNaN(Number(f.val)) && f.val.trim() !== "";
  if (f.op === "contains") return `${col} LIKE '%${String(f.val).replace(/'/g, "''")}%'`;
  const v = isNum ? f.val : `'${String(f.val).replace(/'/g, "''")}'`;
  return `${col} ${f.op} ${v}`;
}

/* Build a GROUP BY analytics query — dimension(s), any number of measures
   with their own aggregate, filters, sort, and a row limit. Dialect-aware
   (LIMIT vs TOP) so the same builder works across engines. */
function buildAnalyticsSQL({ dialect, table, dim, dim2, measures, filters, sortKey, sortDir, limit }) {
  const dims = [dim, dim2].filter(Boolean);
  const activeMeasures = measures.filter((m) => m.agg === "count" || m.col);
  const selectParts = [
    ...dims.map((d) => `${q(d)} AS ${q(d)}`),
    ...activeMeasures.map((m) => `${aggExpr(m.agg, m.col)} AS ${m.alias}`),
  ];
  const whereParts = filters.map(filterSQL).filter(Boolean);
  const orderExpr = sortKey === "__dim__" ? q(dim) : (activeMeasures.find((m) => m.alias === sortKey)?.alias || activeMeasures[0]?.alias || q(dim));
  const sql = [
    `SELECT ${topPrefix(dialect, limit)}${selectParts.join(", ")}`,
    `FROM ${q(table)}`,
    whereParts.length ? `WHERE ${whereParts.join(" AND ")}` : null,
    dims.length ? `GROUP BY ${dims.map(q).join(", ")}` : null,
    orderExpr ? `ORDER BY ${orderExpr} ${sortDir.toUpperCase()}` : null,
  ].filter(Boolean).join("\n") + limitClause(dialect, limit);
  return sql;
}

/* ── generic API layer against the existing FastAPI app (main.py) ── */
function makeApi(base) {
  const url = (p) => `${base.replace(/\/$/, "")}${p}`;
  const asJson = async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    return data;
  };
  return {
    listProjects: async () => (await fetch(url("/projects")).then(asJson)).projects || [],
    createProject: async (projectId) =>
      asJson(await fetch(url("/projects"), {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId }),
      })),
    listSources: async (pid) => (await fetch(url(`/projects/${pid}/sources`)).then(asJson)).sources || [],
    addSqlSource: async (pid, payload) =>
      asJson(await fetch(url(`/projects/${pid}/sources/sql`), {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })),
    removeSource: async (pid, name) =>
      fetch(url(`/projects/${pid}/sources/${name}`), { method: "DELETE" }),
    query: async (pid, source, sql, timeoutMs = 15000) => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const res = await fetch(url(`/projects/${pid}/sources/${source}/query`), {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sql }), signal: controller.signal,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `Query failed (${res.status})`);
        return data.rows || [];
      } catch (e) {
        if (e.name === "AbortError") throw new Error("Query timed out");
        throw e;
      } finally {
        clearTimeout(timer);
      }
    },
  };
}

function ChartTypeIcon({ type }) {
  if (type === "line") return <LineIcon size={13} />;
  if (type === "scatter") return <ScatterIcon size={13} />;
  return <BarChart3 size={13} />;
}

function GenericChart({ type, data, xKey, yKey }) {
  if (!data || data.length === 0) return <div className="banner">No rows to chart.</div>;
  const yKeys = Array.isArray(yKey) ? yKey.filter(Boolean) : [yKey].filter(Boolean);
  if (yKeys.length === 0) return <div className="banner">Pick at least one measure.</div>;

  if (type === "table") {
    const cols = [xKey, ...yKeys];
    return (
      <div className="gridwrap">
        <table className="grid">
          <thead><tr>{cols.map((k) => <th key={k}>{k}</th>)}</tr></thead>
          <tbody>{data.map((r, i) => <tr key={i}>{cols.map((k) => <td key={k}>{fmt(r[k])}</td>)}</tr>)}</tbody>
        </table>
      </div>
    );
  }

  if (type === "pie") {
    const yk = yKeys[0];
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={data} dataKey={yk} nameKey={xKey} outerRadius={110} label={(d) => d[xKey]}>
            {data.map((_, i) => <Cell key={i} fill={SERIES[i % SERIES.length]} />)}
          </Pie>
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 11 }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      {type === "line" ? (
        <LineChart data={data}>
          <CartesianGrid stroke={T.line} strokeDasharray="3 3" />
          <XAxis dataKey={xKey} tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={60} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {yKeys.map((k, i) => <Line key={k} type="monotone" dataKey={k} stroke={SERIES[i % SERIES.length]} strokeWidth={2} dot={false} />)}
        </LineChart>
      ) : type === "area" ? (
        <AreaChart data={data}>
          <CartesianGrid stroke={T.line} strokeDasharray="3 3" />
          <XAxis dataKey={xKey} tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={60} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {yKeys.map((k, i) => <Area key={k} type="monotone" dataKey={k} stroke={SERIES[i % SERIES.length]} fill={SERIES[i % SERIES.length]} fillOpacity={0.18} />)}
        </AreaChart>
      ) : type === "scatter" ? (
        <ScatterChart>
          <CartesianGrid stroke={T.line} strokeDasharray="3 3" />
          <XAxis dataKey={xKey} name={xKey} tick={{ fontSize: 11 }} />
          <YAxis dataKey={yKeys[0]} name={yKeys[0]} tick={{ fontSize: 11 }} />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={data} fill={T.teal} />
        </ScatterChart>
      ) : (
        <BarChart data={data}>
          <CartesianGrid stroke={T.line} strokeDasharray="3 3" />
          <XAxis dataKey={xKey} tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={60} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {yKeys.map((k, i) => <Bar key={k} dataKey={k} fill={SERIES[i % SERIES.length]} radius={[3, 3, 0, 0]} />)}
        </BarChart>
      )}
    </ResponsiveContainer>
  );
}

/* ── column profile card (the signature "readout") ── */
function ColumnReadout({ col, idx, profile, loading, timedOut, onProfileNow }) {
  const kind = col.kind;
  const icon = kind === "numeric" ? <Hash size={10} /> : kind === "date" ? <CalendarDays size={10} /> : kind === "identifier" ? <KeyRound size={10} /> : <TypeIcon size={10} />;
  return (
    <div className="readout">
      <div className="idx">COL {String(idx + 1).padStart(2, "0")}</div>
      <div className="colname">{col.name}</div>
      <span className={`type-tag type-${kind === "identifier" ? "numeric" : kind}`}>{icon} {kind}</span>
      {loading && <div className="banner">profiling…</div>}
      {timedOut && (
        <>
          <div className="banner" style={{ color: T.amber }}>timed out on this large table</div>
          <div className="add-row-btn" onClick={onProfileNow}><RefreshCw size={11} /> Try again</div>
        </>
      )}
      {!loading && !timedOut && profile?.skipped && (
        <>
          <div className="banner">Skipped automatically — this is a full-table scan on a large table.</div>
          <div className="add-row-btn" onClick={onProfileNow}><Play size={11} /> Profile this column</div>
        </>
      )}
      {!loading && !timedOut && profile && !profile.skipped && kind === "numeric" && (
        <>
          <div className="statline"><span className="k">min</span><span className="v">{fmt(profile.min_v)}</span></div>
          <div className="statline"><span className="k">avg</span><span className="v">{fmt(profile.avg_v)}</span></div>
          <div className="statline"><span className="k">max</span><span className="v">{fmt(profile.max_v)}</span></div>
          {profile.hist && profile.hist.length > 0 && (
            <div style={{ height: 40, margin: "8px 0 2px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={profile.hist}>
                  <Bar dataKey="cnt" fill={T.indigo} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <NullBar pct={profile.nullPct} />
        </>
      )}
      {!loading && !timedOut && profile && !profile.skipped && kind === "identifier" && (
        <>
          <div className="statline"><span className="k">distinct values</span><span className="v">{profile.distinct !== undefined ? profile.distinct.toLocaleString() : "—"}</span></div>
          <NullBar pct={profile.nullPct} />
        </>
      )}
      {!loading && !timedOut && profile && !profile.skipped && kind === "date" && (
        <>
          <div className="statline"><span className="k">earliest</span><span className="v">{fmt(profile.min_v)}</span></div>
          <div className="statline"><span className="k">latest</span><span className="v">{fmt(profile.max_v)}</span></div>
          <NullBar pct={profile.nullPct} />
        </>
      )}
      {!loading && !timedOut && profile && !profile.skipped && kind === "categorical" && profile.top && (
        isFlagLike(col.name) || profile.top.length <= 3 ? (
          <>
            <div className="pill-list">
              {profile.top.map((r) => {
                const pct = profile.total ? (Number(r.cnt) / profile.total) * 100 : 0;
                return (
                  <div key={String(r.label)} className="pill-item">
                    <span className="pill-label">{fmt(r.label)}</span>
                    <span className="pill-track"><span className="pill-fill" style={{ width: `${pct}%` }} /></span>
                    <span className="pill-pct">{pct.toFixed(0)}%</span>
                  </div>
                );
              })}
            </div>
            <NullBar pct={profile.nullPct} />
          </>
        ) : (
          <>
            <div className="statline"><span className="k">distinct (top)</span><span className="v">{profile.top.length}</span></div>
            <div className="statline"><span className="k">most common</span><span className="v">{profile.top[0] ? String(profile.top[0].label) : "—"}</span></div>
            <NullBar pct={profile.nullPct} />
          </>
        )
      )}
    </div>
  );
}
function NullBar({ pct }) {
  if (pct === undefined) return null;
  return (
    <>
      <div className="statline"><span className="k">nulls</span><span className="v">{pct.toFixed(1)}%</span></div>
      <div className="nullbar-track"><div className="nullbar-fill" style={{ width: `${Math.min(pct, 100)}%` }} /></div>
    </>
  );
}
function fmt(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2);
  return String(v).slice(0, 19);
}

const DEFAULT_PORTS = { postgres: 5432, postgresql: 5432, mysql: 3306, mariadb: 3306, mssql: 1433, sqlite: 0 };

function emptySourceForm() {
  return {
    name: "", dialect: "postgres", host: "", port: 5432, database: "",
    username: "", password: "", ssl: true, connect_timeout: 30,
    secure: "direct", // direct | ssh | vpn
    ssh_host: "", ssh_username: "", ssh_port: 22, ssh_password: "", ssh_pkey_path: "",
    vpn_type: "wireguard", vpn_config_path: "",
  };
}

/* ── "Connect a database" form — registers a new SQL source via
   POST /projects/{id}/sources/sql. Works for any dialect the backend
   supports; this form is the same regardless of what schema lives inside. */
function ConnectForm({ projects, projectId, setProjectId, onCreateProject, onAddSource, error, success }) {
  const [newProject, setNewProject] = useState("");
  const [form, setForm] = useState(emptySourceForm());
  const [submitting, setSubmitting] = useState(false);
  const set = (k) => (e) => {
    const v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [k]: v, ...(k === "dialect" ? { port: DEFAULT_PORTS[v] ?? f.port } : {}) }));
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      await onAddSource(form);
      setForm(emptySourceForm());
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="panel">
      <h3>Connect a database</h3>

      {!projectId && (
        <div className="banner">Pick a project above, or create one below, before registering a source.</div>
      )}
      <div className="selectRow">
        <div className="field">
          <label>Project</label>
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">Select…</option>
            {projects.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Or new project</label>
          <input placeholder="e.g. acme" value={newProject} onChange={(e) => setNewProject(e.target.value)} />
        </div>
        <button className="btn ghost" disabled={!newProject} onClick={async () => { await onCreateProject(newProject); setNewProject(""); }}>
          <FolderPlus size={13} /> Create project
        </button>
      </div>

      {error && <div className="errbox"><AlertCircle size={15} /> {error}</div>}
      {success && <div className="success-box"><CheckCircle2 size={15} /> {success}</div>}

      <div className="subhead"><Database size={12} /> Connection</div>
      <div className="formgrid">
        <div className="field"><label>Source name</label><input placeholder="warehouse" value={form.name} onChange={set("name")} /></div>
        <div className="field"><label>Dialect</label>
          <select value={form.dialect} onChange={set("dialect")}>
            {["postgres", "mysql", "mariadb", "mssql", "sqlite"].map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        {form.dialect !== "sqlite" && (
          <>
            <div className="field"><label>Host</label><input placeholder="localhost" value={form.host} onChange={set("host")} /></div>
            <div className="field"><label>Port</label><input type="number" value={form.port} onChange={set("port")} /></div>
          </>
        )}
        <div className="field"><label>Database</label><input placeholder="your_db_name" value={form.database} onChange={set("database")} /></div>
        {form.dialect !== "sqlite" && (
          <>
            <div className="field"><label>Username</label><input value={form.username} onChange={set("username")} /></div>
            <div className="field"><label>Password</label><input type="password" value={form.password} onChange={set("password")} /></div>
          </>
        )}
      </div>

      {form.dialect !== "sqlite" && (
        <div className="toggle-row">
          <label><input type="checkbox" checked={form.ssl} onChange={set("ssl")} /> Use SSL</label>
        </div>
      )}

      <div className="subhead"><KeyRound size={12} /> How it's reached</div>
      <div className="chiprow" style={{ marginBottom: 14 }}>
        {[["direct", "Direct"], ["ssh", "SSH / Bastion"], ["vpn", "Customer VPN"]].map(([v, label]) => (
          <div key={v} className={`chip ${form.secure === v ? "active" : ""}`} onClick={() => setForm((f) => ({ ...f, secure: v }))}>{label}</div>
        ))}
      </div>

      {form.secure === "ssh" && (
        <div className="formgrid">
          <div className="field"><label>SSH host</label><input value={form.ssh_host} onChange={set("ssh_host")} /></div>
          <div className="field"><label>SSH port</label><input type="number" value={form.ssh_port} onChange={set("ssh_port")} /></div>
          <div className="field"><label>SSH username</label><input value={form.ssh_username} onChange={set("ssh_username")} /></div>
          <div className="field"><label>SSH password</label><input type="password" value={form.ssh_password} onChange={set("ssh_password")} /></div>
          <div className="field"><label>Private key path (optional)</label><input value={form.ssh_pkey_path} onChange={set("ssh_pkey_path")} /></div>
        </div>
      )}
      {form.secure === "vpn" && (
        <div className="formgrid">
          <div className="field"><label>VPN type</label>
            <select value={form.vpn_type} onChange={set("vpn_type")}>
              <option value="wireguard">WireGuard</option>
              <option value="openvpn">OpenVPN</option>
            </select>
          </div>
          <div className="field"><label>Config file path</label><input value={form.vpn_config_path} onChange={set("vpn_config_path")} /></div>
        </div>
      )}

      <button className="btn teal" disabled={submitting || !projectId || !form.name || !form.database} onClick={submit}>
        <Plug size={13} /> {submitting ? "Connecting…" : "Connect database"}
      </button>
    </div>
  );
}

export default function AnalystConsole() {
  const [apiBase, setApiBase] = useState(
    import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"
  );
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [sources, setSources] = useState([]); // {name, dialect, kind, ...}
  const [sourceName, setSourceName] = useState("");
  const [tables, setTables] = useState([]);
  const [table, setTable] = useState("");
  const [columns, setColumns] = useState([]); // {name, kind}
  const [tab, setTab] = useState("connect");
  const [status, setStatus] = useState({ state: "idle", msg: "" });
  const [error, setError] = useState("");
  const [connectError, setConnectError] = useState("");
  const [connectSuccess, setConnectSuccess] = useState("");

  const [profiles, setProfiles] = useState({});
  const [timedOutCols, setTimedOutCols] = useState({});
  const [rowCount, setRowCount] = useState(null);
  const [trendData, setTrendData] = useState(null);
  const [trendCol, setTrendCol] = useState("");
  const [sampleSize, setSampleSize] = useState(50000); // null = full table

  const [exploreDim, setExploreDim] = useState("");
  const [exploreDim2, setExploreDim2] = useState("");
  const [exploreMeasures, setExploreMeasures] = useState([{ id: uid(), col: "", agg: "count" }]);
  const [exploreFilters, setExploreFilters] = useState([]);
  const [exploreType, setExploreType] = useState("bar");
  const [exploreSortDir, setExploreSortDir] = useState("desc");
  const [exploreLimit, setExploreLimit] = useState(20);
  const [exploreData, setExploreData] = useState(null);
  const [exploreLoading, setExploreLoading] = useState(false);
  const [exploreSql, setExploreSql] = useState("");

  const [sql, setSql] = useState("SELECT 1");
  const [sqlRows, setSqlRows] = useState(null);
  const [sqlLoading, setSqlLoading] = useState(false);
  const [sqlChart, setSqlChart] = useState({ on: false, type: "bar", x: "", y: "" });

  const api = useMemo(() => makeApi(apiBase), [apiBase]);
  const source = sources.find((s) => s.name === sourceName);
  const dialect = source?.dialect || "postgres";

  const connect = useCallback(async () => {
    setStatus({ state: "connecting", msg: "" });
    setError("");
    try {
      const p = await api.listProjects();
      setProjects(p);
      setStatus({ state: "connected", msg: `${p.length} project(s)` });
    } catch (e) {
      setStatus({ state: "error", msg: "" });
      setError(`Couldn't reach the API at ${apiBase}. ${e.message}`);
    }
  }, [api, apiBase]);

  useEffect(() => { connect(); /* eslint-disable-next-line */ }, []);

  useEffect(() => {
    if (!projectId) { setSources([]); return; }
    refreshSources();
  }, [projectId]); // eslint-disable-line

  async function refreshSources() {
    if (!projectId) return;
    try {
      const s = await api.listSources(projectId);
      setSources(s);
      setSourceName((cur) => (s.find((x) => x.name === cur) ? cur : s[0]?.name || ""));
    } catch (e) { setError(e.message); }
  }

  const handleCreateProject = useCallback(async (newId) => {
    if (!newId) return;
    setConnectError(""); setConnectSuccess("");
    try {
      await api.createProject(newId);
      const p = await api.listProjects();
      setProjects(p);
      setProjectId(newId);
      setConnectSuccess(`Project "${newId}" created.`);
    } catch (e) { setConnectError(e.message); }
  }, [api]); // eslint-disable-line

  const handleAddSource = useCallback(async (form) => {
    setConnectError(""); setConnectSuccess("");
    if (!projectId) { setConnectError("Pick or create a project first."); return; }
    const payload = {
      name: form.name,
      dialect: form.dialect,
      host: form.dialect === "sqlite" ? "" : form.host,
      port: form.dialect === "sqlite" ? 0 : Number(form.port),
      database: form.database,
      username: form.dialect === "sqlite" ? "" : form.username,
      password: form.dialect === "sqlite" ? "" : form.password,
      ssl: form.ssl,
      connect_timeout: 30,
    };
    if (form.secure === "ssh") {
      payload.tunnel = {
        ssh_host: form.ssh_host,
        ssh_username: form.ssh_username,
        ssh_port: Number(form.ssh_port) || 22,
        ...(form.ssh_password ? { ssh_password: form.ssh_password } : {}),
        ...(form.ssh_pkey_path ? { ssh_pkey_path: form.ssh_pkey_path } : {}),
      };
    } else if (form.secure === "vpn") {
      payload.vpn = { vpn_type: form.vpn_type, config_path: form.vpn_config_path };
    }
    try {
      await api.addSqlSource(projectId, payload);
      await refreshSources();
      setSourceName(form.name);
      setConnectSuccess(`"${form.name}" connected. Pick it from the sidebar to explore its tables.`);
    } catch (e) { setConnectError(e.message); throw e; }
  }, [api, projectId]); // eslint-disable-line

  const handleRemoveSource = useCallback(async (name) => {
    try {
      await api.removeSource(projectId, name);
      await refreshSources();
    } catch (e) { setError(e.message); }
  }, [api, projectId]); // eslint-disable-line


  useEffect(() => {
    if (!projectId || !sourceName) { setTables([]); return; }
    (async () => {
      try {
        setError("");
        const rows = await api.query(projectId, sourceName, listTablesSQL(dialect));
        const names = rows.map((r) => r.table_name || r.TABLE_NAME || Object.values(r)[0]);
        setTables(names);
        setTable(names[0] || "");
      } catch (e) { setError(e.message); setTables([]); }
    })();
  }, [projectId, sourceName]); // eslint-disable-line

  useEffect(() => {
    if (!table) { setColumns([]); return; }
    (async () => {
      try {
        setError("");
        setProfiles({});
        setTimedOutCols({});
        setRowCount(null);
        setTrendData(null);
        setSampleSize(50000);
        const rows = await api.query(projectId, sourceName, listColumnsSQL(dialect, table));
        const cols = rows.map((r) => {
          const name = r.column_name || r.name || r.COLUMN_NAME;
          const type = r.data_type || r.type || r.DATA_TYPE || "";
          return { name, kind: classify(name, type) };
        });
        setColumns(cols);
        setExploreDim(cols.find((c) => c.kind !== "numeric")?.name || cols[0]?.name || "");
        setExploreDim2("");
        setExploreMeasures([{ id: uid(), col: cols.find((c) => c.kind === "numeric")?.name || "", agg: "count" }]);
        setExploreFilters([]);
        setExploreData(null);
        setExploreSql("");
        const dateCol = cols.find((c) => c.kind === "date");
        setTrendCol(dateCol?.name || "");
      } catch (e) { setError(e.message); setColumns([]); }
    })();
  }, [table]); // eslint-disable-line

  // auto-profile once columns are known. Identifier-like columns (store_id, sku,
  // *_key…) get a single cheap COUNT(DISTINCT) instead of a GROUP BY.
  //
  // Two more changes vs. a naive per-column sequential loop:
  //  1. Columns are profiled in PARALLEL (Promise.allSettled), not one at a
  //     time — a table with 16 columns no longer waits on 16 round-trips in
  //     series, so the whole card grid fills in roughly as fast as the
  //     single slowest column, not the sum of all of them.
  //  2. On big remote tables, ANY full scan can be slow — not just GROUP BY.
  //     Rather than fight that per-query, Overview profiles a bounded,
  //     recent SAMPLE of the table (latest N rows by a date/id column) when
  //     `sampleSize` is set, instead of scanning everything. This is a
  //     visible, user-controlled trade-off (see the "Sample" picker), not a
  //     silent skip — switching to "All rows" always scans the real table.
  const dateColForOrdering = useMemo(() => columns.find((c) => c.kind === "date")?.name, [columns]);
  const orderingCol = dateColForOrdering || columns.find((c) => c.kind === "identifier")?.name;

  const fromExpr = useCallback((tbl) => {
    if (!sampleSize) return q(tbl);
    if (orderingCol) return `(SELECT ${topPrefix(dialect, sampleSize)}* FROM ${q(tbl)} ORDER BY ${q(orderingCol)} DESC${limitClause(dialect, sampleSize)}) AS smp`;
    return `(SELECT ${topPrefix(dialect, sampleSize)}* FROM ${q(tbl)}${limitClause(dialect, sampleSize)}) AS smp`;
  }, [sampleSize, orderingCol, dialect]);

  const profileOneColumn = useCallback(async (col, table) => {
    const from = fromExpr(table);
    if (col.kind === "numeric") {
      const r = await api.query(projectId, sourceName,
        `SELECT MIN(${q(col.name)}) AS min_v, MAX(${q(col.name)}) AS max_v, AVG(${q(col.name)}) AS avg_v, COUNT(*)-COUNT(${q(col.name)}) AS nulls, COUNT(*) AS total FROM ${from}`, 25000);
      const row = r[0] || {};
      const total = Number(row.total) || 1;
      const minV = Number(row.min_v), maxV = Number(row.max_v);
      let hist = [];
      if (isFinite(minV) && isFinite(maxV) && maxV > minV) {
        try {
          const width = (maxV - minV) / 8;
          const hr = await api.query(projectId, sourceName,
            `SELECT FLOOR((${q(col.name)} - ${minV}) / ${width}) AS bucket, COUNT(*) AS cnt FROM ${from} WHERE ${q(col.name)} IS NOT NULL GROUP BY bucket ORDER BY bucket`, 20000);
          const byBucket = {};
          hr.forEach((row2) => { const b = Math.min(7, Math.max(0, Number(row2.bucket) || 0)); byBucket[b] = (byBucket[b] || 0) + Number(row2.cnt); });
          hist = Array.from({ length: 8 }, (_, i) => ({ bucket: i, cnt: byBucket[i] || 0 }));
        } catch { /* histogram is a nice-to-have, skip on failure/timeout */ }
      }
      return { min_v: minV, max_v: maxV, avg_v: Number(row.avg_v), nullPct: (Number(row.nulls) / total) * 100, hist };
    }
    if (col.kind === "date") {
      const r = await api.query(projectId, sourceName,
        `SELECT MIN(${q(col.name)}) AS min_v, MAX(${q(col.name)}) AS max_v, COUNT(*)-COUNT(${q(col.name)}) AS nulls, COUNT(*) AS total FROM ${from}`, 25000);
      const row = r[0] || {};
      const total = Number(row.total) || 1;
      return { min_v: row.min_v, max_v: row.max_v, nullPct: (Number(row.nulls) / total) * 100 };
    }
    if (col.kind === "identifier") {
      const r = await api.query(projectId, sourceName,
        `SELECT COUNT(DISTINCT ${q(col.name)}) AS dc, COUNT(*)-COUNT(${q(col.name)}) AS nulls, COUNT(*) AS total FROM ${from}`, 25000);
      const row = r[0] || {};
      const total = Number(row.total) || 1;
      return { distinct: Number(row.dc), nullPct: (Number(row.nulls) / total) * 100 };
    }
    // categorical
    const r = await api.query(projectId, sourceName,
      `SELECT ${topPrefix(dialect, 8)}${q(col.name)} AS label, COUNT(*) AS cnt FROM ${from} GROUP BY ${q(col.name)} ORDER BY cnt DESC${limitClause(dialect, 8)}`, 25000);
    const r2 = await api.query(projectId, sourceName,
      `SELECT COUNT(*)-COUNT(${q(col.name)}) AS nulls, COUNT(*) AS total FROM ${from}`, 25000);
    const total = Number(r2[0]?.total) || 1;
    return { top: r, nullPct: (Number(r2[0]?.nulls) / total) * 100, total };
  }, [projectId, sourceName, dialect, fromExpr]);

  const profileColumnNow = useCallback(async (col) => {
    setTimedOutCols((t) => { const n = { ...t }; delete n[col.name]; return n; });
    setProfiles((p) => { const n = { ...p }; delete n[col.name]; return n; });
    try {
      const result = await profileOneColumn(col, table);
      setProfiles((p) => ({ ...p, [col.name]: result }));
    } catch {
      setTimedOutCols((t) => ({ ...t, [col.name]: true }));
    }
  }, [profileOneColumn, table]);

  useEffect(() => {
    if (!table || columns.length === 0) return;
    let cancelled = false;
    (async () => {
      try {
        const cnt = await api.query(projectId, sourceName, `SELECT COUNT(*) AS n FROM ${q(table)}`, 25000);
        if (!cancelled) setRowCount(Number(Object.values(cnt[0])[0]));
      } catch { /* non-fatal */ }
      await Promise.allSettled(columns.map(async (col) => {
        try {
          const result = await profileOneColumn(col, table);
          if (!cancelled) setProfiles((p) => ({ ...p, [col.name]: result }));
        } catch {
          if (!cancelled) setTimedOutCols((t2) => ({ ...t2, [col.name]: true }));
        }
      }));
    })();
    return () => { cancelled = true; };
  }, [table, columns, sampleSize]); // eslint-disable-line

  // Date trend — bucketed server-side by dialect (date_trunc / DATE_FORMAT /
  // FORMAT / strftime), against the same sampled window as the rest of Overview.
  useEffect(() => {
    if (!table || !trendCol) { setTrendData(null); return; }
    (async () => {
      try {
        const bucket = monthBucketExpr(dialect, trendCol);
        const from = fromExpr(table);
        const sqlText = `SELECT ${bucket} AS period, COUNT(*) AS count FROM ${from} WHERE ${q(trendCol)} IS NOT NULL GROUP BY period ORDER BY period`;
        const rows = await api.query(projectId, sourceName, sqlText, 25000);
        setTrendData(rows.map((r) => ({ period: r.period, count: Number(r.count) })));
      } catch { setTrendData(null); }
    })();
  }, [table, trendCol, sampleSize]); // eslint-disable-line

  // Heuristic KPI tiles for the Overview header: sum common measure-like
  // numeric columns (revenue, qty_sold, discount, lost_sales_*…) once their
  // profile is in. Pattern-based, so it generalizes to any similarly-named
  // sales/inventory schema rather than this one table specifically.
  const kpiTiles = useMemo(() => {
    const measurePattern = /revenue|sales_amount|sales_value|qty_sold|quantity|lost_sales|amount|discount|value|volume/i;
    return columns
      .filter((c) => c.kind === "numeric" && measurePattern.test(c.name) && profiles[c.name])
      .slice(0, 4);
  }, [columns, profiles]);

  const [kpiSums, setKpiSums] = useState({});
  useEffect(() => {
    if (!table || kpiTiles.length === 0) { setKpiSums({}); return; }
    let cancelled = false;
    (async () => {
      const sums = {};
      const from = fromExpr(table);
      for (const c of kpiTiles) {
        try {
          const r = await api.query(projectId, sourceName, `SELECT SUM(${q(c.name)}) AS s FROM ${from}`, 20000);
          sums[c.name] = Number(r[0]?.s) || 0;
        } catch { /* skip */ }
      }
      if (!cancelled) setKpiSums(sums);
    })();
    return () => { cancelled = true; };
  }, [table, kpiTiles.map((c) => c.name).join(","), sampleSize]); // eslint-disable-line

  // Domain-aware "signature" read on out-of-stock detection tables: any table
  // with an is_oos_detected-style flag gets an OOS-rate readout, paired with
  // whatever lost-sales measures are already in the KPI strip. Purely
  // name-pattern driven, so it applies to any similarly-shaped OOS table,
  // not just this one.
  const oosFlagCol = useMemo(() => columns.find((c) => /oos_detected|is_oos/i.test(c.name) && c.kind === "categorical"), [columns]);
  const oosProfile = oosFlagCol && profiles[oosFlagCol.name];
  const oosRate = useMemo(() => {
    if (!oosProfile || !oosProfile.top || !oosProfile.total) return null;
    const hit = oosProfile.top.find((r) => /^(true|t|1|yes)$/i.test(String(r.label)));
    if (!hit) return null;
    return (Number(hit.cnt) / oosProfile.total) * 100;
  }, [oosProfile]);
  const lostValueCol = columns.find((c) => /lost_sales_value/i.test(c.name));
  const lostVolumeCol = columns.find((c) => /lost_sales_volume/i.test(c.name));


  const runExplore = useCallback(async () => {
    if (!table || !exploreDim) return;
    setExploreLoading(true);
    try {
      const measuresWithAlias = exploreMeasures
        .filter((m) => m.agg === "count" || m.col)
        .map((m, i) => ({ ...m, alias: `m${i}_${m.agg}` }));
      if (measuresWithAlias.length === 0) { setError("Add at least one measure."); setExploreLoading(false); return; }
      const sortKey = measuresWithAlias[0]?.alias;
      const sqlText = buildAnalyticsSQL({
        dialect, table, dim: exploreDim, dim2: exploreDim2 || null,
        measures: measuresWithAlias, filters: exploreFilters,
        sortKey, sortDir: exploreSortDir, limit: exploreLimit,
      });
      setExploreSql(sqlText);
      const rows = await api.query(projectId, sourceName, sqlText);
      const clean = rows.map((r) => {
        const out = { [exploreDim]: fmt(r[exploreDim]) };
        if (exploreDim2) out[exploreDim2] = fmt(r[exploreDim2]);
        measuresWithAlias.forEach((m) => { out[m.alias] = Number(r[m.alias]) || 0; });
        return out;
      });
      setExploreData(clean);
      setError("");
    } catch (e) { setError(e.message); } finally { setExploreLoading(false); }
  }, [table, exploreDim, exploreDim2, exploreMeasures, exploreFilters, exploreSortDir, exploreLimit, dialect, projectId, sourceName]); // eslint-disable-line

  const addMeasure = () => setExploreMeasures((m) => [...m, { id: uid(), col: "", agg: "sum" }]);
  const updateMeasure = (id, patch) => setExploreMeasures((m) => m.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  const removeMeasure = (id) => setExploreMeasures((m) => m.filter((x) => x.id !== id));

  const addFilter = () => setExploreFilters((f) => [...f, { id: uid(), col: columns[0]?.name || "", op: "=", val: "" }]);
  const updateFilter = (id, patch) => setExploreFilters((f) => f.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  const removeFilter = (id) => setExploreFilters((f) => f.filter((x) => x.id !== id));

  const exploreMeasureAliases = useMemo(
    () => exploreMeasures.filter((m) => m.agg === "count" || m.col).map((m, i) => `m${i}_${m.agg}`),
    [exploreMeasures]
  );

  const runSql = useCallback(async () => {
    if (!sourceName) { setError("Pick a source first."); return; }
    setSqlLoading(true);
    setError("");
    try {
      const rows = await api.query(projectId, sourceName, sql);
      setSqlRows(rows);
      const keys = rows[0] ? Object.keys(rows[0]) : [];
      setSqlChart((c) => ({ ...c, x: keys[0] || "", y: keys[1] || keys[0] || "" }));
    } catch (e) { setError(e.message); setSqlRows(null); } finally { setSqlLoading(false); }
  }, [sql, projectId, sourceName]); // eslint-disable-line

  const sqlKeys = sqlRows && sqlRows[0] ? Object.keys(sqlRows[0]) : [];
  const sqlChartData = sqlRows ? sqlRows.map((r) => ({ ...r, [sqlChart.x]: fmt(r[sqlChart.x]), [sqlChart.y]: Number(r[sqlChart.y]) })) : [];

  return (
    <div className="console">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');
        ${CSS}
      `}</style>

      <div className="topbar">
        <div className="brand disp"><Database size={16} /> Analyst Console</div>
        <div>
          <span className="field-label">API base</span>
          <input value={apiBase} onChange={(e) => setApiBase(e.target.value)} onBlur={connect} style={{ width: 220 }} />
        </div>
        <div>
          <span className="field-label">Project</span>
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">Select…</option>
            {projects.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <button className="btn ghost" style={{ color: "#EAEDEA", borderColor: "#2B333D" }} onClick={connect}><RefreshCw size={13} /> Refresh</button>
        <div style={{ marginLeft: "auto" }}>
          {status.state === "connected" && <span className="status-pill" style={{ background: "#173328", color: "#79E0B8" }}><CheckCircle2 size={13} /> connected · {status.msg}</span>}
          {status.state === "connecting" && <span className="status-pill" style={{ background: "#2B2A1C", color: "#E0C879" }}><RefreshCw size={13} /> connecting…</span>}
          {status.state === "error" && <span className="status-pill" style={{ background: "#331C1C", color: "#E09B79" }}><AlertCircle size={13} /> offline</span>}
        </div>
      </div>

      <div className="layout">
        <div className="sidebar">
          <div className="side-hdr">
            <div className="side-section-title" style={{ padding: "14px 0 6px" }}>Sources</div>
            <button className="icon-btn" title="Connect a database" onClick={() => setTab("connect")}><Plus size={14} /></button>
          </div>
          {sources.length === 0 && <div className="banner" style={{ padding: "0 14px" }}>{projectId ? "No sources registered yet." : "Pick or create a project."}</div>}
          {sources.map((s) => (
            <div key={s.name} className={`src-row ${s.name === sourceName ? "active" : ""}`} onClick={() => { setSourceName(s.name); if (tab === "connect") setTab("overview"); }}>
              <Plug size={13} /> {s.name} <span className="dialect-chip">{s.dialect || s.engine}</span>
              <button className="icon-btn" title="Remove source" onClick={(e) => { e.stopPropagation(); handleRemoveSource(s.name); }}><Trash2 size={12} /></button>
            </div>
          ))}
          <div className="side-section-title">Tables</div>
          {tables.length === 0 && <div className="banner" style={{ padding: "0 14px" }}>{sourceName ? "No tables found." : "—"}</div>}
          {tables.map((t) => (
            <div key={t} className={`tbl-row ${t === table ? "active" : ""}`} onClick={() => { setTable(t); if (tab === "connect") setTab("overview"); }}>
              <Table2 size={13} /> <span className="mono">{t}</span>
            </div>
          ))}
        </div>

        <div className="main">
          {error && <div className="errbox"><AlertCircle size={15} /> {error}</div>}

          <div className="tabs">
            <div className={`tab ${tab === "connect" ? "active" : ""}`} onClick={() => setTab("connect")}><Plug size={13} /> Connect</div>
            <div className={`tab ${tab === "overview" ? "active" : ""}`} onClick={() => setTab("overview")}><Layers size={13} /> Overview</div>
            <div className={`tab ${tab === "explore" ? "active" : ""}`} onClick={() => setTab("explore")}><BarChart3 size={13} /> Explore</div>
            <div className={`tab ${tab === "sql" ? "active" : ""}`} onClick={() => setTab("sql")}><Search size={13} /> SQL</div>
          </div>

          {tab === "connect" && (
            <ConnectForm
              projects={projects}
              projectId={projectId}
              setProjectId={setProjectId}
              onCreateProject={handleCreateProject}
              onAddSource={handleAddSource}
              error={connectError}
              success={connectSuccess}
            />
          )}

          {tab !== "connect" && !table && (
            <div className="empty">
              <Layers size={30} />
              <div className="disp">Pick a source and table, or connect a new database.</div>
              <div>This console works against any Postgres, MySQL, MSSQL, or SQLite source registered in db_project — nothing here is hardcoded to one schema.</div>
            </div>
          )}

          {tab !== "connect" && table && (
            <>
              {tab === "overview" && (
                <>
                  <div className="row-title">
                    <h2 className="disp">{table}</h2>
                    <span className="meta">{rowCount !== null ? `${rowCount.toLocaleString()} rows` : "counting…"} · {columns.length} columns · {dialect}</span>
                    <div className="chiprow" style={{ marginLeft: "auto" }}>
                      {[[1000, "Latest 1k"], [10000, "Latest 10k"], [50000, "Latest 50k"], [null, "All rows"]].map(([v, label]) => (
                        <div key={label} className={`chip ${sampleSize === v ? "active" : ""}`} onClick={() => setSampleSize(v)} title={v ? `Profile only the latest ${label.split(" ")[1]} rows${orderingCol ? ` by ${orderingCol}` : ""} — much faster on large tables` : "Scan the entire table (slower on large tables)"}>
                          {label}
                        </div>
                      ))}
                    </div>
                  </div>
                  {sampleSize && (
                    <div className="banner">
                      Profiling the latest {sampleSize.toLocaleString()} rows{orderingCol ? ` (ordered by ${orderingCol})` : ""} for speed. Row count above is still the real total.
                    </div>
                  )}

                  {(rowCount !== null || kpiTiles.length > 0) && (
                    <div className="kpi-strip">
                      {rowCount !== null && <div className="kpi"><div className="v">{rowCount.toLocaleString()}</div><div className="k">rows</div></div>}
                      {oosRate !== null && <div className="kpi"><div className="v" style={{ color: T.amber }}>{oosRate.toFixed(1)}%</div><div className="k">rows OOS-detected</div></div>}
                      {kpiTiles.map((c) => (
                        <div className="kpi" key={c.name}>
                          <div className="v">{kpiSums[c.name] !== undefined ? fmt(kpiSums[c.name]) : "…"}</div>
                          <div className="k">total {c.name}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {(oosRate !== null || lostValueCol || lostVolumeCol) && (
                    <div className="panel" style={{ borderColor: "#E6C4BF" }}>
                      <h3 style={{ color: T.rose }}>Out-of-stock impact</h3>
                      <div className="kpi-strip" style={{ marginBottom: 0 }}>
                        {oosRate !== null && <div className="kpi"><div className="v">{oosRate.toFixed(1)}%</div><div className="k">of rows flagged OOS</div></div>}
                        {lostValueCol && <div className="kpi"><div className="v">{kpiSums[lostValueCol.name] !== undefined ? fmt(kpiSums[lostValueCol.name]) : "…"}</div><div className="k">total lost sales value</div></div>}
                        {lostVolumeCol && <div className="kpi"><div className="v">{kpiSums[lostVolumeCol.name] !== undefined ? fmt(kpiSums[lostVolumeCol.name]) : "…"}</div><div className="k">total lost sales volume</div></div>}
                      </div>
                    </div>
                  )}

                  <div className="cardgrid">
                    {columns.map((col, i) => (
                      <ColumnReadout
                        key={col.name}
                        col={col}
                        idx={i}
                        profile={profiles[col.name]}
                        loading={profiles[col.name] === undefined && !timedOutCols[col.name]}
                        timedOut={!!timedOutCols[col.name]}
                        onProfileNow={() => profileColumnNow(col)}
                      />
                    ))}
                  </div>

                  {columns.some((c) => c.kind === "date") && (
                    <div className="panel">
                      <h3>Trend over time</h3>
                      <div className="selectRow">
                        <div className="field">
                          <label>Date column</label>
                          <select value={trendCol} onChange={(e) => setTrendCol(e.target.value)}>
                            {columns.filter((c) => c.kind === "date").map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
                          </select>
                        </div>
                      </div>
                      <GenericChart type="line" data={trendData} xKey="period" yKey="count" />
                    </div>
                  )}

                  {columns.some((c) => c.kind === "categorical" && profiles[c.name]?.top && profiles[c.name].top.length > 3 && !isFlagLike(c.name)) && (
                    <div className="panel">
                      <h3>Top categories</h3>
                      {columns.filter((c) => c.kind === "categorical" && profiles[c.name]?.top && profiles[c.name].top.length > 3 && !isFlagLike(c.name)).slice(0, 2).map((c) => (
                        <div key={c.name} style={{ marginBottom: 18 }}>
                          <div className="banner mono">{c.name}</div>
                          <GenericChart type="bar" data={profiles[c.name].top.map((r) => ({ x: fmt(r.label), y: Number(r.cnt) }))} xKey="x" yKey="y" />
                        </div>
                      ))}
                    </div>
                  )}

                </>
              )}

              {tab === "explore" && (
                <div className="panel">
                  <h3>Analysis builder</h3>
                  <div className="builder">
                    <div className="builder-rail">
                      <div className="well">
                        <div className="well-title">Rows</div>
                        <div className="measure-row">
                          <select value={exploreDim} onChange={(e) => setExploreDim(e.target.value)}>
                            {columns.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
                          </select>
                        </div>
                        <div className="measure-row">
                          <select value={exploreDim2} onChange={(e) => setExploreDim2(e.target.value)}>
                            <option value="">+ Break by (optional)</option>
                            {columns.filter((c) => c.name !== exploreDim).map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
                          </select>
                        </div>
                      </div>

                      <div className="well">
                        <div className="well-title">Measures</div>
                        {exploreMeasures.map((m) => (
                          <div className="measure-row" key={m.id}>
                            <select value={m.agg} onChange={(e) => updateMeasure(m.id, { agg: e.target.value })} style={{ flex: "0 0 90px" }}>
                              {AGGS.map((a) => <option key={a} value={a}>{a.replace("_", " ")}</option>)}
                            </select>
                            {m.agg !== "count" && (
                              <select value={m.col} onChange={(e) => updateMeasure(m.id, { col: e.target.value })}>
                                <option value="">column…</option>
                                {(m.agg === "sum" || m.agg === "avg" ? columns.filter((c) => c.kind === "numeric") : columns).map((c) => (
                                  <option key={c.name} value={c.name}>{c.name}</option>
                                ))}
                              </select>
                            )}
                            <button className="row-del" onClick={() => removeMeasure(m.id)} disabled={exploreMeasures.length === 1}><XIcon size={13} /></button>
                          </div>
                        ))}
                        <div className="add-row-btn" onClick={addMeasure}><Plus size={12} /> Add measure</div>
                      </div>

                      <div className="well">
                        <div className="well-title">Filters</div>
                        {exploreFilters.map((f) => (
                          <div className="filter-row" key={f.id}>
                            <select value={f.col} onChange={(e) => updateFilter(f.id, { col: e.target.value })} style={{ flex: "0 0 84px" }}>
                              {columns.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
                            </select>
                            <select value={f.op} onChange={(e) => updateFilter(f.id, { op: e.target.value })} style={{ flex: "0 0 78px" }}>
                              {FILTER_OPS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                            </select>
                            {f.op !== "is_null" && f.op !== "is_not_null" && (
                              <input value={f.val} onChange={(e) => updateFilter(f.id, { val: e.target.value })} placeholder="value" />
                            )}
                            <button className="row-del" onClick={() => removeFilter(f.id)}><Trash2 size={13} /></button>
                          </div>
                        ))}
                        <div className="add-row-btn" onClick={addFilter}><Filter size={12} /> Add filter</div>
                      </div>

                      <div className="well">
                        <div className="well-title">Sort &amp; limit</div>
                        <div className="measure-row">
                          <select value={exploreSortDir} onChange={(e) => setExploreSortDir(e.target.value)} style={{ flex: "0 0 100px" }}>
                            <option value="desc">High → low</option>
                            <option value="asc">Low → high</option>
                          </select>
                          <input type="number" min="1" max="500" value={exploreLimit} onChange={(e) => setExploreLimit(Number(e.target.value) || 20)} style={{ flex: "0 0 70px" }} />
                        </div>
                      </div>

                      <button className="btn teal" style={{ width: "100%", justifyContent: "center" }} onClick={runExplore} disabled={exploreLoading}>
                        <Play size={13} /> {exploreLoading ? "Running…" : "Run analysis"}
                      </button>
                    </div>

                    <div className="builder-canvas">
                      <div className="charttype-grid" style={{ marginBottom: 16, maxWidth: 420 }}>
                        {[["bar", <BarChart3 size={16} key="i" />, "Bar"], ["line", <LineIcon size={16} key="i" />, "Line"], ["area", <AreaIcon size={16} key="i" />, "Area"],
                          ["pie", <PieIcon size={16} key="i" />, "Pie"], ["scatter", <ScatterIcon size={16} key="i" />, "Scatter"], ["table", <TableIcon size={16} key="i" />, "Table"]].map(([t, icon, label]) => (
                          <div key={t} className={`charttype-btn ${exploreType === t ? "active" : ""}`} onClick={() => setExploreType(t)}>
                            {icon}{label}
                          </div>
                        ))}
                      </div>

                      {exploreData && exploreData.length > 0 && (
                        <div className="kpi-strip">
                          {exploreMeasureAliases.map((alias) => {
                            const total = exploreData.reduce((s, r) => s + (r[alias] || 0), 0);
                            const m = exploreMeasures.filter((mm) => mm.agg === "count" || mm.col)[exploreMeasureAliases.indexOf(alias)];
                            return (
                              <div className="kpi" key={alias}>
                                <div className="v">{total.toLocaleString()}</div>
                                <div className="k">{m.agg} {m.col || ""} (sum of rows shown)</div>
                              </div>
                            );
                          })}
                          <div className="kpi"><div className="v">{exploreData.length}</div><div className="k">rows returned</div></div>
                        </div>
                      )}

                      {exploreSql && (
                        <div className="sql-preview"><Code2 size={11} style={{ verticalAlign: -1, marginRight: 6 }} />{exploreSql}</div>
                      )}

                      {exploreLoading ? (
                        <div className="banner">Running…</div>
                      ) : exploreData ? (
                        <GenericChart type={exploreType} data={exploreData} xKey={exploreDim} yKey={exploreMeasureAliases} />
                      ) : (
                        <div className="banner">Set up rows, measures, and filters, then run the analysis.</div>
                      )}
                    </div>
                  </div>
                </div>
              )}


              {tab === "sql" && (
                <div className="panel">
                  <h3>Ad-hoc query · {sourceName}</h3>
                  <textarea className="sqlbox mono" value={sql} onChange={(e) => setSql(e.target.value)} spellCheck={false} />
                  <div style={{ marginTop: 10, marginBottom: 16 }}>
                    <button className="btn teal" onClick={runSql} disabled={sqlLoading}><Play size={13} /> {sqlLoading ? "Running…" : "Run query"}</button>
                  </div>
                  {sqlRows && (
                    <>
                      <div className="banner">{sqlRows.length} row(s) returned</div>
                      <div className="gridwrap">
                        <table className="grid">
                          <thead><tr>{sqlKeys.map((k) => <th key={k}>{k}</th>)}</tr></thead>
                          <tbody>
                            {sqlRows.slice(0, 500).map((r, i) => (
                              <tr key={i}>{sqlKeys.map((k) => <td key={k}>{fmt(r[k])}</td>)}</tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {sqlKeys.length >= 2 && (
                        <div style={{ marginTop: 18 }}>
                          <div className="selectRow">
                            <div className="chiprow">
                              <div className={`chip ${sqlChart.on ? "active" : ""}`} onClick={() => setSqlChart((c) => ({ ...c, on: !c.on }))}><BarChart3 size={13} /> Chart this</div>
                            </div>
                            {sqlChart.on && (
                              <>
                                <div className="field"><label>X</label>
                                  <select value={sqlChart.x} onChange={(e) => setSqlChart((c) => ({ ...c, x: e.target.value }))}>
                                    {sqlKeys.map((k) => <option key={k} value={k}>{k}</option>)}
                                  </select>
                                </div>
                                <div className="field"><label>Y</label>
                                  <select value={sqlChart.y} onChange={(e) => setSqlChart((c) => ({ ...c, y: e.target.value }))}>
                                    {sqlKeys.map((k) => <option key={k} value={k}>{k}</option>)}
                                  </select>
                                </div>
                                <div className="chiprow">
                                  {["bar", "line", "scatter"].map((t) => (
                                    <div key={t} className={`chip ${sqlChart.type === t ? "active" : ""}`} onClick={() => setSqlChart((c) => ({ ...c, type: t }))}><ChartTypeIcon type={t} /> {t}</div>
                                  ))}
                                </div>
                              </>
                            )}
                          </div>
                          {sqlChart.on && <GenericChart type={sqlChart.type} data={sqlChartData} xKey={sqlChart.x} yKey={sqlChart.y} />}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
