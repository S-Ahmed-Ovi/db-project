# Changelog

All notable changes to `db-project` are documented here.

## [0.3.0] — Stabilization

**Fully backward compatible with 0.1.x — see `MIGRATION.md`.**

### Added
- `db_project.exceptions` — `DBProjectError` hierarchy (`ConfigurationError`,
  `ConnectivityError`, `ConnectionError`, `AuthenticationError`,
  `IngestionError`, `ValidationError`, `SchemaError`), each also subclassing
  the builtin exception it replaces so existing `except` clauses keep working.
- `db_project.validation.validate()` (also `ProjectManager.validate()`) —
  required-column, dtype, null, duplicate, range, and schema-compatibility
  checks, returning a structured `{valid, errors, warnings, statistics}` result.
- `db_project.schema.detect_dataframe_schema()` (also
  `ProjectManager.inspect_file()` / `.inspect_dataframe()`) — column-level
  schema detection for files/DataFrames.
- `ProjectManager.inspect_database()` and `SQLConnector.get_schema()` —
  column-level schema of an existing database table.
- `if_exists="upsert"` / `upsert_keys=` on `upload_to_database()` and
  `dataframe_to_database()`, for both SQL targets (stage-and-merge,
  dialect-aware) and NoSQL/Mongo targets (`bulk_write` + `ReplaceOne`).
- `db_project.logging_utils` — structured logging under the `"db_project"`
  logger (silent by default) and secret redaction (`redact()`, `redact_url()`)
  used throughout the connectors so passwords/tokens/keys never reach a log line.
- Expanded test suite: `tests/unit/` (71 tests) covering the SQL connector
  against real SQLite, mocked SSH-tunnel/VPN/Mongo connectivity, validation,
  schema detection, upsert, and security/redaction behavior. `tests/integration/`
  scaffold added for opt-in tests against real services.
- `MIGRATION.md` — 0.1.x → 0.3.0 migration guide.

### Changed
- PyPI metadata: author, `Homepage`/`Repository`/`Issues` URLs, `LICENSE`
  copyright line corrected from placeholders. Classifier bumped
  `3 - Alpha` → `4 - Beta`.
- `tests/test_smoke.py` moved to `tests/unit/test_smoke.py` (still passes
  unmodified).

### Notes
- No public method, class, or config-file field was removed or renamed.

## [0.1.1] — Initial PyPI release
- `ProjectManager`: project/source registration, SQL (postgres/mysql/
  mariadb/mssql/sqlite) and NoSQL (MongoDB) connectors, direct/SSH-tunnel/
  Customer-VPN connectivity, CSV/Excel/JSON/Parquet ingestion, upload-to-
  database conversion (replace/append/fail).

## [0.1.0] — Initial internal release
