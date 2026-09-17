# Migrating from 0.1.x to 0.3.0

**Short version: you don't need to change anything.** Every `ProjectManager`
method that existed in 0.1.1 has the same name, same arguments (only new
*optional* keyword arguments were added), and same return type in 0.3.0.

```python
# This 0.1.1 code still works, unmodified, on 0.3.0:
from db_project.manager import ProjectManager

pm = ProjectManager()
pm.create_project("acme")
pm.add_sql_source("acme", "warehouse", dialect="postgres", host="db.acme.com",
                   port=5432, database="warehouse", username="svc", password="secret")
pm.upload_to_database("acme", "ratings.csv", target_source="warehouse",
                       table_name="ratings", if_exists="replace")
```

## What actually changed

### 1. New optional capabilities on `ProjectManager` (additive)

| New method | Purpose |
|---|---|
| `pm.validate(df, schema=..., ...)` | Structured data validation |
| `pm.inspect_file(project_id, filename)` | Detected schema of an uploaded file |
| `pm.inspect_dataframe(df)` | Detected schema of a DataFrame |
| `pm.inspect_database(project_id, source, table)` | Schema of an existing DB table |

### 2. New optional keyword arguments (existing calls unaffected)

- `upload_to_database(..., if_exists="upsert", upsert_keys=["id"])`
- `dataframe_to_database(..., if_exists="upsert", upsert_keys=["id"])`

Both `if_exists` still defaults to `"replace"`, exactly as before, if you
don't pass `upsert_keys`.

### 3. Exceptions got more specific — but stayed catchable the same way

0.1.x raised plain `ValueError`/`RuntimeError`/driver exceptions. 0.3.0
raises named exceptions from `db_project.exceptions` that **also** subclass
those same builtins, so existing `except` clauses keep working:

```python
# Still works exactly as it did in 0.1.x:
try:
    pm.add_sql_source("acme", "bad", dialect="postgres", host="h", port=1,
                       database="d", tunnel={...}, vpn={...})
except ValueError as e:
    ...  # now a ConfigurationError, but it *is* a ValueError

try:
    pm.query_sql("acme", "warehouse", "SELECT 1")
except RuntimeError as e:
    ...  # now (likely) a ConnectionError, but it *is* a RuntimeError
```

If you want the more specific type, it's available:

```python
from db_project.exceptions import ConnectivityError, ConfigurationError
```

`db_project.connectors.vpn.VPNError` still exists and is importable exactly
as before — it now additionally subclasses `ConnectivityError`.

### 4. Logging (new, silent by default)

0.1.x didn't log anything. 0.3.0 logs lifecycle events (connect, tunnel-up,
query, write, validate) through the standard `logging` module under the
`"db_project"` logger — but only if *you* configure a handler
(`logging.basicConfig(...)`). If you never touch `logging`, behavior is
identical to 0.1.x: nothing is printed.

### 5. `__init__.py` exports (additive)

`from db_project import ProjectManager` still works. New names
(`validate`, `detect_dataframe_schema`, and the exception classes) were
added to `db_project.__all__`; nothing was removed.

## Nothing was removed or renamed

No public method, class, module, or config-file field was removed, renamed,
or had its default behavior changed. `config.json`'s shape is unchanged, and
old `config.json` files load exactly as they did under 0.1.x.
