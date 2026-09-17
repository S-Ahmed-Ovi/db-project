# Turning `db_project` into a real Python package — a from-scratch guide

You've never done this before, so this walks through **everything**: what a
package even is, why the files in this zip are arranged the way they are,
and the exact commands to build, install, and (optionally) publish it.

The work of restructuring is already done for you in this zip. You mostly
need to run commands and understand *why*.

---

## 1. What "making it a package" actually means

Right now, `db_project` is just a folder of `.py` files. To turn it into a
real, installable **package**, you need three things:

1. **A standard layout** — the source code lives under `src/db_project/`
   instead of at the repo root. This is called a "src layout" and it's the
   modern best practice (it stops you from accidentally importing your local
   folder instead of the actually-installed version — a very common
   beginner bug).
2. **A build config file** — `pyproject.toml`. This is the modern
   replacement for the old `setup.py`. It tells Python's packaging tools:
   the package's name, version, dependencies, and where the source code is.
3. **A build backend** — a tool that reads `pyproject.toml` and produces
   the actual installable files (a `.whl` "wheel" and a `.tar.gz` "sdist").
   We use `setuptools`, the most common one.

That's it conceptually. Once you have those three things, `pip install`
works on your folder exactly like it works on anything from PyPI (the
`pip install pandas` kind of thing).

## 2. What's in this zip and why

```
db-project/
├── pyproject.toml       <- the package's "recipe": name, version, deps
├── README.md            <- usage docs (shown on PyPI if you ever publish)
├── LICENSE               <- MIT license (edit or replace as you like)
├── PACKAGING_GUIDE.md    <- this file
├── .gitignore
├── src/
│   └── db_project/       <- THE ACTUAL PACKAGE — this is what gets installed
│       ├── __init__.py
│       ├── py.typed      <- tells type checkers this package has type hints
│       ├── config.py
│       ├── manager.py
│       └── connectors/
│           ├── __init__.py
│           ├── sql.py
│           ├── nosql.py
│           ├── tunnel.py
│           ├── vpn.py
│           └── files.py
├── tests/
│   └── test_smoke.py     <- a minimal test so you have something to run
├── main.py               <- optional FastAPI dev/demo harness (not shipped)
└── dashboard/             <- optional React dev UI (not shipped)
```

The only thing that gets zipped up into the installable package is
`src/db_project/`. Everything else (`main.py`, `dashboard/`, tests) is there
to help *you* develop and try it out, but a user who runs `pip install
db-project` will only get the `db_project` Python module.

### One real bug this restructuring fixed

The original code computed its default data-storage folder like this:

```python
PROJECTS_ROOT = Path(__file__).resolve().parent.parent / "projects"
```

That means "a `projects/` folder next to wherever this `.py` file happens to
live." While you're running it straight from a cloned repo, that's fine.
But once it's `pip install`ed, that file lives deep inside your Python
environment's `site-packages/` folder — usually read-only, and definitely
not where you want customer data written. This zip changes the default to
"a `projects/` folder in your current working directory," overridable with
the `DB_PROJECTS_ROOT` environment variable. This is a very common mistake
when people package up code that was never meant to be installed
elsewhere — worth remembering for future projects.

## 3. Build and install it locally

You'll do this inside a **virtual environment** — an isolated Python
install so this package (and its dependencies) don't clash with anything
else on your machine. If you don't already have one:

```bash
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
```

Then, from inside this folder (where `pyproject.toml` is):

```bash
pip install --upgrade pip build

# Editable install — good for while you're actively developing the package,
# since edits to the .py files are picked up immediately, no reinstall needed
pip install -e ".[all]"
```

Check it worked:

```bash
python -c "from db_project.manager import ProjectManager; print(ProjectManager)"
```

You should see something like:
```
<class 'db_project.manager.ProjectManager'>
```

That's it — you now have a working, installed Python package.

## 4. Build the distributable files (wheel + sdist)

This step is only needed when you want to **share** the package with
someone else, or install it on a different machine, without them needing
your source folder:

```bash
python -m build
```

This creates a `dist/` folder with two files, e.g.:

```
dist/
├── db_project-0.1.0-py3-none-any.whl
└── db_project-0.1.0.tar.gz
```

Anyone can now install it directly from that file:

```bash
pip install dist/db_project-0.1.0-py3-none-any.whl
```

or, with extras:

```bash
pip install "dist/db_project-0.1.0-py3-none-any.whl[postgres,files]"
```

This is the file you'd email to a colleague, attach to an internal release,
or upload somewhere private.

## 5. (Optional) Publish it so `pip install db-project` works for anyone

If you eventually want other people to install it by name — the same way
you `pip install pandas` — you publish it to PyPI (or your company's
private package index, if it has one).

**Do a dry run first on TestPyPI** (a sandbox copy of PyPI, so mistakes are
free):

```bash
pip install --upgrade twine
twine check dist/*             # sanity-checks the files you built
twine upload --repository testpypi dist/*
```

You'll need a free account at https://test.pypi.org and an API token
(Account Settings → API tokens) — `twine` will prompt for it.

Then test the install from there:

```bash
pip install --index-url https://test.pypi.org/simple/ db-project
```

Once you're happy, do the real upload:

```bash
twine upload dist/*
```

(needs an account + API token at https://pypi.org instead). Note:
`db-project` (or whatever name you choose) has to be unique on PyPI — check
availability before you get attached to a name.

**You do not need to do this step at all** if this package is only ever
going to be used by you or your team — steps 3–4 (editable install /
building a wheel) are enough for that.

## 6. Bumping the version later

Every time you change the code and want to re-release it:

1. Edit the `version = "0.1.0"` line in `pyproject.toml` (follow
   [semantic versioning](https://semver.org/): bump the last number for
   bug fixes, the middle for new backward-compatible features, the first
   for breaking changes).
2. Re-run `python -m build`.
3. Re-run the `twine upload` step if you're publishing.

## 7. Quick command reference

```bash
# one-time setup
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip build twine

# develop
pip install -e ".[all]"
pytest

# release
python -m build
twine check dist/*
twine upload dist/*          # or --repository testpypi for a dry run
```
