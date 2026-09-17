# db_project dashboard — Analyst Console

A universal, schema-agnostic dashboard for data analysts. It's a plain React +
Vite frontend that talks to the existing `db_project` FastAPI app (`main.py`)
over HTTP — no backend changes required beyond the CORS middleware already
added to `main.py`.

"Universal" means: nothing in this app is hardcoded to any particular
project's tables or columns. It has four tabs:

- **Connect** — register a new database (or create a project first). Fill in
  dialect, host/port, credentials, and optionally an SSH bastion or Customer
  VPN, then hit "Connect database." This calls
  `POST /projects/{id}/sources/sql` on the existing API — no manual curl or
  Swagger UI needed.
- **Overview** — auto-profiles whichever table you pick, tuned for wide
  fact/dimension tables (100k+ rows, many `*_id`/`sku`/`*_key` columns, several
  `is_*` flags):
  - Columns are classified as **numeric**, **date**, **identifier**, or
    **categorical**. Identifier-like columns (`store_id`, `sku`, `event_id`,
    `date_key`…) get a single cheap `COUNT(DISTINCT …)` instead of a
    `GROUP BY` on high-cardinality data.
  - All columns are profiled **in parallel**, not one at a time — a 16-column
    table fills in roughly as fast as its single slowest column, not the sum
    of all of them.
  - **Sample size picker** ("Latest 1k" / "Latest 10k" / "Latest 50k" / "All
    rows", default Latest 50k): on a large remote table, *any* full scan can be slow — not
    just `GROUP BY`. Instead of a per-query skip/retry dance, Overview
    profiles a bounded, recent window of the table (`ORDER BY <date or id
    column> DESC LIMIT N`, pushed into SQL as a subquery) so every card
    finishes quickly. The row count shown is always the real total; only the
    profiling queries are windowed. Switch to "All rows" to scan the whole
    table when you actually need exact global stats. A "Try again" button
    still appears if an individual column times out even at the current
    sample size.
  - Numeric columns show min/avg/max, null %, and an 8-bucket histogram.
  - Boolean-ish columns (`is_*`, `has_*`, or any column with ≤3 distinct
    values) render as compact percentage pills instead of a bar chart.
  - The date trend chart is bucketed by month **server-side** per dialect
    (`date_trunc`/`DATE_FORMAT`/`FORMAT`/`strftime`), over the same sampled
    window as the rest of Overview.
  - A KPI strip totals up any column whose name looks like a sales/inventory
    measure (`revenue`, `qty_sold`, `lost_sales_*`, `discount`, …).
  - Tables with an `is_oos_detected`-style flag get an extra **"Out-of-stock
    impact"** panel: OOS rate plus total lost sales value/volume, pulled
    together from whichever of those columns exist — purely name-pattern
    driven, so it applies to any similarly-shaped OOS table.
- **Explore** — a Power BI–style analysis builder: pick a row dimension (and
  optional "break by" second dimension), add any number of measures (count /
  sum / avg / min / max / count-distinct on any column), stack up filters
  (`=`, `≠`, `>`, `<`, contains, is empty…), set sort direction and a row
  limit, and choose bar / line / area / pie / scatter / table. It shows the
  generated SQL and quick KPI totals above the chart.
- **SQL** — run any ad-hoc SQL against the selected source, see a results
  grid, and chart any two returned columns.

Point it at any registered SQL source (Postgres, MySQL/MariaDB, MSSQL, or
SQLite) and the same four tabs work identically, because table/column
discovery uses dialect-appropriate `information_schema` / `sqlite_master` /
`PRAGMA` queries rather than assuming a fixed schema.

## Run it

```bash
npm install
npm run dev
```

Vite prints a local URL (typically `http://localhost:5173`). Open it, enter
your API base URL at the top (defaults to `http://127.0.0.1:8000`, or set
`VITE_API_BASE` — copy `.env.example` to `.env` and edit it), pick a project,
then a source, then a table.

## Requirements on the API side

Used endpoints, all of which already exist in `main.py`:

- `GET /projects`
- `POST /projects` (create a project, used by the **Connect** tab)
- `GET /projects/{project_id}/sources`
- `POST /projects/{project_id}/sources/sql` (register a source, used by the **Connect** tab)
- `DELETE /projects/{project_id}/sources/{name}` (remove a source, from the sidebar's trash icon)
- `POST /projects/{project_id}/sources/{name}/query` (body: `{"sql": "..."}`)

Because it reuses `query_sql`, any source reachable by `db_project` — direct,
over an SSH/Bastion tunnel, or over a Customer VPN — works here too; the
tunnel/VPN lifecycle is already handled transparently by `ProjectManager`.

**CORS**: since this runs in a browser on a different origin/port than the
API, `main.py` must allow cross-origin requests. This is already set up:

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```

Before deploying anywhere public, replace `allow_origins=["*"]` with the
actual origin(s) the dashboard is served from.

## Build for production

```bash
npm run build
```

Outputs static files to `dist/` — serve them with any static file host
(nginx, Netlify, S3, etc.) and set `VITE_API_BASE` at build time to point at
your deployed API.

## Notes on the SQL it generates

- Table/column listing branches on the source's registered `dialect`
  (`postgres`, `mysql`/`mariadb`, `mssql`, `sqlite`).
- `LIMIT` vs `TOP` is handled per dialect (MSSQL has no `LIMIT`).
- Date trends are bucketed by month **client-side** after pulling the raw
  date column (capped at 20,000 rows), so this works identically across
  every dialect without relying on engine-specific date-truncation
  functions.
- Identifiers are lightly quoted; this tool is meant for internal/analyst use
  against sources you already trust — it is not hardened against adversarial
  table/column names.
