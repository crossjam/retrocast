# Pluggable Vector Indexer Architecture for Retrocast

## Overview

This plan describes the design and step-by-step implementation of a pluggable vector
search/indexing framework for retrocast, using [pluggy](https://pluggy.readthedocs.io/en/stable/)
as the plugin machinery — modeled closely on Simon Willison's
[llm](https://github.com/simonw/llm) library.

The goal is to allow multiple vector search backends (ChromaDB, zvec, usearch, and
future engines) to be registered, selected, and used interchangeably for indexing
and querying podcast transcript content, without baking any one backend into the core
codebase.

---

## Motivation & Current State

Today the `index/manager.py` module directly imports and instantiates `chromadb`.  
The `index_commands.py` CLI hard-codes `ChromaDBManager`. This coupling makes it
impossible to swap engines without code changes.

The refactor will:

1. Define an abstract `IndexerBackend` base class (the "contract" every backend must satisfy).
2. Use **pluggy** hook specifications to let external packages (or built-in
   defaults) register backend instances.
3. Introduce a `retrocast plugin` CLI group for discovering and inspecting installed plugins.
4. Refactor `index` CLI commands to be backend-agnostic, selecting the active backend
   via a `--backend` option (defaulting to `chromadb`).
5. Ship the existing ChromaDB integration as a **built-in default plugin** so nothing
   breaks for current users.

---

## Architectural Overview

```
retrocast (core)
├── plugins.py           ← pluggy PluginManager setup + load_plugins()
├── hookspecs.py         ← HookspecMarker + hook signatures
├── indexer.py           ← Abstract IndexerBackend base class + get_backends() helper
├── default_plugins/
│   └── chromadb_backend.py  ← built-in ChromaDB plugin (hookimpl + concrete class)
├── index_commands.py    ← refactored: backend-agnostic, uses hook system
└── cli.py               ← adds `plugin` group

External packages (optional, pip-installed separately):
├── retrocast-zvec        → entry_point group "retrocast", registers ZvecBackend
└── retrocast-usearch     → entry_point group "retrocast", registers UsearchBackend
```

### Plugin Discovery Flow

1. `retrocast/plugins.py` creates a `pluggy.PluginManager("retrocast")`.
2. `load_plugins()` calls `pm.load_setuptools_entrypoints("retrocast")` to discover
   any installed third-party plugins.
3. Built-in default plugins (e.g., ChromaDB) are registered explicitly in `load_plugins()`.
4. CLI commands call `load_plugins()` then use `pm.hook.register_indexer_backends(register=...)`.

### IndexerBackend Contract

```python
# retrocast/indexer.py (abstract base class — no pluggy coupling here)
class IndexerBackend:
    backend_id: str        # e.g. "chromadb", "zvec", "usearch"
    display_name: str      # Human-readable

    def is_available(self) -> tuple[bool, str]: ...  # (True, "") or (False, "reason")
    def configure(self, storage_dir: Path, **kwargs) -> None: ...
    def index_transcriptions(self, datastore: Datastore, batch_size: int) -> int: ...
    def search(self, query: str, n_results: int, podcast_filter: str | None) -> list[dict]: ...
    def get_count(self) -> int: ...
    def reset(self) -> None: ...
```

### Hook Specifications

```python
# retrocast/hookspecs.py
@hookspec
def register_commands(cli):
    """Register additional CLI commands on the root `cli` group."""

@hookspec
def register_indexer_backends(register):
    """Register IndexerBackend instances.
    `register` is a callable: register(backend_instance)
    """
```

---

## Implementation Steps

### Phase 1 — Core Plugin Infrastructure

- [ ] **1.1** Add `pluggy` to `[project.dependencies]` in `pyproject.toml`.

- [ ] **1.2** Create `src/retrocast/hookspecs.py`:
  - Define `hookspec = HookspecMarker("retrocast")`.
  - Define `hookimpl = HookimplMarker("retrocast")`.
  - Add `register_commands(cli)` hookspec (for future third-party CLI extensions).
  - Add `register_indexer_backends(register)` hookspec.

- [ ] **1.3** Create `src/retrocast/plugins.py`:
  - Instantiate `pm = pluggy.PluginManager("retrocast")`.
  - Register hookspecs via `pm.add_hookspecs(hookspecs)`.
  - Implement `load_plugins()` with a `_loaded` guard (identical pattern to llm):
    - Call `pm.load_setuptools_entrypoints("retrocast")` (skipped during tests via
      `sys._called_from_test` sentinel or `RETROCAST_LOAD_PLUGINS` env var).
    - Register all modules listed in `DEFAULT_PLUGINS` unconditionally.
  - Implement `get_plugins(all=False) -> list[dict]` returning name, hooks, version.

- [ ] **1.4** Create `src/retrocast/indexer.py`:
  - Define the abstract `IndexerBackend` base class with the contract above.
  - Implement `get_backends() -> dict[str, IndexerBackend]`:
    - Calls `load_plugins()`.
    - Iterates `pm.hook.register_indexer_backends(register=register)`.
    - Returns mapping of `backend_id → backend_instance`.
  - Implement `get_backend(name: str) -> IndexerBackend` with a clear error message
    listing available backend IDs when the requested one isn't found.

---

### Phase 2 — Built-in ChromaDB Default Plugin

- [ ] **2.1** Create `src/retrocast/default_plugins/` package:
  - Add `__init__.py`.
  - Add `chromadb_backend.py`.

- [ ] **2.2** In `chromadb_backend.py`:
  - Move (not copy) the core logic from `index/manager.py` into a new
    `ChromaDBBackend(IndexerBackend)` class with `backend_id = "chromadb"`.
  - Implement all abstract methods by delegating to chromadb (guard the import so
    missing chromadb gives a clear `ImportError` with install instructions).
  - Add the `@hookimpl` decorated function:
    ```python
    @hookimpl
    def register_indexer_backends(register):
        register(ChromaDBBackend())
    ```

- [ ] **2.3** Add `"retrocast.default_plugins.chromadb_backend"` to `DEFAULT_PLUGINS`
  in `plugins.py`.

- [ ] **2.4** Keep `src/retrocast/index/manager.py` temporarily as a thin shim that
  imports from `ChromaDBBackend` (preserves backwards-compatibility for any code that
  imports `ChromaDBManager` directly).

---

### Phase 3 — Refactor Index CLI Commands

- [ ] **3.1** Refactor `index_commands.py`:
  - Remove the direct import of `ChromaDBManager`.
  - Add `--backend` option to `build_vector_index` (default: `"chromadb"`).
  - Use `get_backend(backend)` to obtain the active backend.
  - Pass `storage_dir` (app_dir / backend_id) to `backend.configure(...)` before use,
    keeping each backend's data in its own subdirectory.

- [ ] **3.2** Add `retrocast index vector backends` sub-command (see full spec below).

- [ ] **3.3** Refactor or add search command (if present):
  - Apply same `--backend` option pattern.

#### 3.2 — `retrocast index vector backends` — Full Specification

**Command path:**
```
retrocast index vector backends
```

**Purpose:** List every `IndexerBackend` that is currently registered via the plugin
system, so users can see at a glance which backends are available before choosing one
with `--backend`.

**Options:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--json` | flag | off | Emit machine-readable JSON instead of the Rich table |
| `--all` | flag | off | Include built-in default backends (normally shown anyway, but makes it explicit and consistent with `plugin list --all`) |

**Default (Rich table) output:**

```
 Installed Index Backends
 ┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
 ┃ Backend ID ┃ Display Name              ┃ Source        ┃ Available ┃
 ┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
 │ chromadb   │ ChromaDB                  │ built-in      │ ✓         │
 │ zvec       │ zvec (zero-copy vectors)  │ retrocast-zvec│ ✓         │
 │ usearch    │ USearch                   │ retrocast-... │ ✗ *       │
 └────────────┴───────────────────────────┴───────────────┴───────────┘
 * usearch: optional dependency 'usearch' not installed.
   Run: retrocast plugin install retrocast-usearch
```

Column definitions:
- **Backend ID** — the string passed to `--backend` on other commands.
- **Display Name** — `backend.display_name` attribute.
- **Source** — `"built-in"` for default plugins; the PyPI package name (from
  `importlib.metadata`) for third-party plugins.
- **Available** — `✓` if the backend's underlying library is importable;
  `✗` with a short reason if the soft import guard in `configure()` / `__init__`
  would fail. Each `IndexerBackend` subclass must implement an
  `is_available() -> tuple[bool, str]` method that returns `(True, "")` or
  `(False, "reason string")` without raising.

**`--json` output shape:**

```json
[
  {
    "backend_id": "chromadb",
    "display_name": "ChromaDB",
    "source": "built-in",
    "available": true,
    "unavailable_reason": null
  },
  {
    "backend_id": "zvec",
    "display_name": "zvec (zero-copy vectors)",
    "source": "retrocast-zvec",
    "available": true,
    "unavailable_reason": null
  },
  {
    "backend_id": "usearch",
    "display_name": "USearch",
    "source": "retrocast-usearch",
    "available": false,
    "unavailable_reason": "optional dependency 'usearch' not installed"
  }
]
```

**Implementation notes:**

- Call `get_backends()` (which calls `load_plugins()` internally) to get the
  registered backends dict.
- For each backend, call `backend.is_available()` to populate the Available column
  without actually constructing or connecting to the backend.
- Determine **Source** by cross-referencing `pm.list_plugin_distinfo()`: if the
  plugin module that registered the backend has a distinfo entry, use
  `distinfo.metadata["Name"]`; otherwise label it `"built-in"`.
- Add `is_available() -> tuple[bool, str]` to the `IndexerBackend` abstract base
  class in `indexer.py`. Default implementation returns `(True, "")` so existing
  backends that don't override it are considered available.
- If **no backends at all** are registered (empty dict), print a friendly message:
  ```
  No index backends are registered.
  Install one with: retrocast plugin install retrocast-<backend>
  ```

**Integration with other commands:**

- The `build_vector_index` and search commands should call `backends` logic (or
  `get_backends()`) on startup and surface a clear error if the requested
  `--backend` is not in the registered set, including a hint to run
  `retrocast index vector backends` to see what is available:
  ```
  Error: backend 'zvec' not found.
  Run 'retrocast index vector backends' to see installed backends.
  ```

---

### Phase 4 — `plugin` CLI Group

- [ ] **4.1** Create `src/retrocast/plugin_commands.py`:
  - Define a `plugin` Click group.
  - Add `plugin list` command:
    - Calls `get_plugins(all)`.
    - Prints a Rich table: Name | Version | Hooks.
    - Supports `--all` flag to include built-in default plugins.
    - Supports `--json` flag for machine-readable output.

- [ ] **4.2** Wire `plugin` group into the root CLI in `cli.py`:
  ```python
  from retrocast.plugin_commands import plugin
  cli.add_command(plugin)
  ```

- [ ] **4.3** At the end of `cli.py` (after all commands are defined), call:
  ```python
  load_plugins()
  pm.hook.register_commands(cli=cli)
  ```
  This allows external plugins to add new top-level CLI commands.

---

### Phase 5 — Entry-point Convention for External Plugins

- [ ] **5.1** Document the entry-point group name (`"retrocast"`) in the developer
  docs / README.

- [ ] **5.2** Add a `pyproject.toml` section showing the entry-point format that
  third-party packages should use:
  ```toml
  [project.entry-points.retrocast]
  zvec = "retrocast_zvec:plugin"
  ```

- [ ] **5.3** Create an example skeleton plugin in `examples/retrocast-zvec-example/`
  (as a reference; no real zvec/usearch code required at this stage):
  - `pyproject.toml` with entry-point declaration.
  - `retrocast_zvec/__init__.py` with:
    - `ZvecBackend(IndexerBackend)` stub class.
    - `@hookimpl register_indexer_backends(register)` function.
  - `README.md` explaining how to build and install a retrocast plugin.

---

### Phase 6 — Test Support Utilities

- [ ] **6.1** Add `sys._called_from_test = True` in `tests/conftest.py` so
  `load_plugins()` skips entrypoint loading during tests (identical to llm's approach).

- [ ] **6.2** Write unit tests in `tests/test_plugins.py`:
  - [ ] Test that `load_plugins()` is idempotent (calling it twice doesn't double-register).
  - [ ] Test `get_plugins()` excludes default plugins unless `all=True`.
  - [ ] Test that a manually registered plugin appears in `get_plugins()`.
  - [ ] Test that `register_commands` hook adds a new CLI command.
  - [ ] Test that `register_indexer_backends` hook adds a new backend to `get_backends()`.

- [ ] **6.3** Write unit tests in `tests/test_index_commands.py`:
  - [ ] Test `build_vector_index` with a mock backend registered via the plugin system.
  - [ ] Test `retrocast index vector backends` default (Rich table) output includes
    Backend ID, Display Name, Source, and Available columns.
  - [ ] Test `retrocast index vector backends --json` produces the correct JSON shape.
  - [ ] Test that a backend whose `is_available()` returns `(False, "reason")` shows
    `✗` in the table and `"available": false` with `"unavailable_reason"` in JSON.
  - [ ] Test that when no backends are registered the command prints the
    "No index backends are registered" message.
  - [ ] Test that an invalid `--backend` name on `build` or `search` prints the
    "Run 'retrocast index vector backends'" hint.

---

### Phase 7 — Cleanup & Documentation

- [ ] **7.1** Remove `src/retrocast/index/manager.py` shim once all internal callsites
  use the new `IndexerBackend` API.

- [ ] **7.2** Remove `chromadb` from the hard `castchat` optional-dependency group
  (or keep it there but make `ChromaDBBackend` a soft import). Ensure the default
  plugin's `configure()` raises a helpful `ImportError` if chromadb isn't installed.

- [ ] **7.3** Update `AGENTS.md` to document:
  - The new `src/retrocast/plugins.py` and `hookspecs.py` modules.
  - The `retrocast plugin` CLI group.
  - The `--backend` flag on index commands.
  - The entry-point convention for external plugins.

- [ ] **7.4** Update `docs/cli/index.md` (if it exists) to reflect the new
  `retrocast index vector backends` sub-command and `--backend` option.

- [ ] **7.5** Run the full QA suite:
  ```bash
  uv run poe qa
  prek run
  ```

---

## Phase 8 — Plugin Install / Uninstall CLI Commands

This phase adds first-class CLI support for installing and uninstalling retrocast
backend plugins **into the correct Python environment** — the same environment that
retrocast itself runs in. This mirrors `llm install` / `llm uninstall` exactly.

### The Core Problem: Installing into the Right Environment

Retrocast is typically run via `uv run` (a uv-managed virtual environment) or via a
pipx-isolated environment. If a user runs a plain `pip install retrocast-zvec` in
their shell, the package lands in the *wrong* Python environment and the plugin is
never discovered. The solution — identical to llm's — is to invoke `pip` from within
the same Python process that is already running retrocast, using `runpy.run_module`.
This guarantees the package is installed into the active retrocast environment
regardless of how retrocast was launched.

### 8.1 — `plugin install` Command

- [ ] **8.1** Add `plugin install` sub-command to the `plugin` Click group in
  `plugin_commands.py`:

  ```python
  from runpy import run_module
  import sys

  @plugin.command(name="install")
  @click.argument("packages", nargs=-1, required=False)
  @click.option("-U", "--upgrade", is_flag=True,
                help="Upgrade packages to the latest version")
  @click.option("-e", "--editable",
                help="Install a project in editable mode from this path")
  @click.option("--force-reinstall", is_flag=True,
                help="Reinstall even if already up-to-date")
  @click.option("--no-cache-dir", is_flag=True, help="Disable the pip cache")
  @click.option("--pre", is_flag=True,
                help="Include pre-release and development versions")
  def plugin_install(packages, upgrade, editable, force_reinstall, no_cache_dir, pre):
      """Install retrocast backend plugins from PyPI into the retrocast environment."""
      args = ["pip", "install"]
      if upgrade:
          args += ["--upgrade"]
      if editable:
          args += ["--editable", editable]
      if force_reinstall:
          args += ["--force-reinstall"]
      if no_cache_dir:
          args += ["--no-cache-dir"]
      if pre:
          args += ["--pre"]
      args += list(packages)
      sys.argv = args
      run_module("pip", run_name="__main__")
  ```

  **Why `runpy.run_module("pip")`?**  
  This executes `pip` as a module inside the *current* Python interpreter's
  environment — the same one where retrocast is running. It is equivalent to
  `python -m pip install ...` but without shelling out, so it always targets the
  right site-packages regardless of whether the user is in a uv venv, pipx
  environment, or a plain venv.

### 8.2 — `plugin uninstall` Command

- [ ] **8.2** Add `plugin uninstall` sub-command:

  ```python
  @plugin.command(name="uninstall")
  @click.argument("packages", nargs=-1, required=True)
  @click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
  def plugin_uninstall(packages, yes):
      """Uninstall retrocast backend plugins from the retrocast environment."""
      sys.argv = ["pip", "uninstall"] + list(packages) + (["-y"] if yes else [])
      run_module("pip", run_name="__main__")
  ```

### 8.3 — Handling Broken Plugins at Startup

A plugin that introduces a syntax error or bad import will cause `load_plugins()` to
raise, preventing retrocast from starting at all. Two mitigations are needed:

- [ ] **8.3a** Wrap each individual entrypoint load inside `load_plugins()` in a
  `try/except Exception` block. Log a warning (via loguru) and continue loading
  remaining plugins. This mirrors pluggy's own recommendation and prevents one bad
  plugin from blocking the entire CLI.

  ```python
  for ep in distribution.entry_points:
      try:
          mod = ep.load()
          pm.register(mod, name=ep.name)
      except Exception as exc:
          logger.warning(f"Plugin '{ep.name}' failed to load: {exc}")
  ```

- [ ] **8.3b** Document the recovery escape hatch in help text for `plugin install`
  and in `AGENTS.md`: if a broken plugin prevents retrocast from starting, the user
  can disable all external plugins with the env var to reach `plugin uninstall`:

  ```bash
  RETROCAST_LOAD_PLUGINS='' retrocast plugin uninstall retrocast-broken-plugin -y
  ```

### 8.4 — `RETROCAST_LOAD_PLUGINS` Environment Variable

The existing plan mentions this variable in Phase 1.3 but it needs its own explicit
implementation steps:

- [ ] **8.4** In `plugins.py`, read `RETROCAST_LOAD_PLUGINS` from the environment
  at module import time:

  ```python
  RETROCAST_LOAD_PLUGINS = os.environ.get("RETROCAST_LOAD_PLUGINS", None)
  ```

  Implement the three-mode behaviour (mirroring llm exactly):

  | Value | Behaviour |
  |---|---|
  | Not set | Load all installed plugins via setuptools entrypoints |
  | `""` (empty string) | Load **no** external plugins (only built-in defaults) |
  | `"pkg-a,pkg-b"` | Load **only** the named packages' retrocast entrypoints |

  The selective-load path must iterate `importlib.metadata.distribution(pkg).entry_points`,
  filter for group `"retrocast"`, and register each. Surface a `logger.warning` for
  any named package that cannot be found rather than raising.

- [ ] **8.5** Add `RETROCAST_LOAD_PLUGINS` to `plugin list --help` output as a note,
  so users know how to limit plugin loading.

### 8.5 — `plugin list` Enhancements (additions to Phase 4.1)

Update the `plugin list` command with richer output now that install/uninstall exist:

- [ ] **8.6** Add `--hook` filter option to `plugin list` (mirrors `llm plugins
  --hook`), so users can ask "which plugins implement `register_indexer_backends`?":

  ```bash
  retrocast plugin list --hook register_indexer_backends
  ```

- [ ] **8.7** The `--json` output for `plugin list` should match this shape (also
  mirroring llm):

  ```json
  [
    {
      "name": "retrocast-zvec",
      "version": "0.2.1",
      "hooks": ["register_indexer_backends"]
    },
    {
      "name": "retrocast-usearch",
      "version": "0.1.0",
      "hooks": ["register_indexer_backends", "register_commands"]
    }
  ]
  ```

### 8.6 — Developer Workflow for Plugin Authors

The example skeleton (Phase 5.3) should be extended to document the full install
loop a plugin author uses during development:

- [ ] **8.8** Update `examples/retrocast-zvec-example/README.md` with the standard
  development loop:

  ```bash
  # Install your plugin in editable mode into the retrocast environment:
  retrocast plugin install -e .

  # Confirm it is registered:
  retrocast plugin list

  # Test a build command using your new backend:
  retrocast index vector build --backend zvec

  # Uninstall when done:
  retrocast plugin uninstall retrocast-zvec -y
  ```

  And the distribution paths (matching llm's tutorial):
  - **Editable local install**: `retrocast plugin install -e ./path/to/my-plugin`
  - **Wheel file**: `retrocast plugin install dist/retrocast_zvec-0.1-py3-none-any.whl`
  - **GitHub ZIP**: `retrocast plugin install 'https://github.com/user/retrocast-zvec/archive/main.zip'`
  - **PyPI**: `retrocast plugin install retrocast-zvec`

### 8.7 — Entry-point Naming Convention

- [ ] **8.9** Establish and document a naming convention for third-party plugins in
  `AGENTS.md` and the example README:

  | Aspect | Convention | Example |
  |---|---|---|
  | PyPI package name | `retrocast-<backend>` | `retrocast-zvec` |
  | Python module name | `retrocast_<backend>` | `retrocast_zvec` |
  | Entry-point group | `retrocast` | (always `retrocast`) |
  | Entry-point name | `<backend>` | `zvec` |
  | `backend_id` attribute | `<backend>` | `"zvec"` |

  The `pyproject.toml` stanza for a third-party plugin:

  ```toml
  [project]
  name = "retrocast-zvec"
  version = "0.1.0"
  dependencies = ["retrocast"]   # retrocast itself is a dependency

  [project.entry-points.retrocast]
  zvec = "retrocast_zvec"        # points to the module, not a function
  ```

  The top-level `retrocast_zvec/__init__.py` (or `retrocast_zvec.py`) then contains
  the `@hookimpl` decorated functions, exactly as llm plugins work.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Mirror llm's `plugins.py` / `hookspecs.py` split | Clear separation; familiar to contributors who know llm |
| `_loaded` guard in `load_plugins()` | Prevents double-registration across multiple CLI invocations |
| Skip entrypoint loading in tests | Avoids test pollution from locally installed plugins |
| `RETROCAST_LOAD_PLUGINS` env var | Allows CI to test specific plugin packages explicitly; enables recovery from broken plugins |
| `plugin install` / `plugin uninstall` use `runpy.run_module("pip")` | Guarantees installation into the correct retrocast environment (uv venv, pipx, plain venv) without shelling out |
| Per-plugin `try/except` in `load_plugins()` | One broken plugin does not prevent retrocast from starting; user can then uninstall it |
| `backend_id`-named subdirectories | Each backend gets its own storage; no cross-contamination |
| Soft import of chromadb in default plugin | Users without `castchat` extras get a clear install hint, not a crash |
| `retrocast-<backend>` package naming convention | Makes plugin packages easy to discover on PyPI; mirrors llm's `llm-<name>` convention |
| Example skeleton plugin in `examples/` | Lowers the barrier for third-party backend authors; documents the full dev → publish loop |

---

## File Summary

| File | Status | Action |
|---|---|---|
| `src/retrocast/hookspecs.py` | New | Create |
| `src/retrocast/plugins.py` | New | Create (includes `RETROCAST_LOAD_PLUGINS` logic, per-plugin error handling) |
| `src/retrocast/indexer.py` | New | Create (includes `is_available()` on base class) |
| `src/retrocast/default_plugins/__init__.py` | New | Create |
| `src/retrocast/default_plugins/chromadb_backend.py` | New | Create (migrate from manager.py) |
| `src/retrocast/index/manager.py` | Existing | Refactor → shim → eventually remove |
| `src/retrocast/index_commands.py` | Existing | Refactor (use plugin system, add `--backend`, add `backends` sub-command) |
| `src/retrocast/plugin_commands.py` | New | Create (`plugin list`, `plugin install`, `plugin uninstall`) |
| `src/retrocast/cli.py` | Existing | Add `plugin` group + `register_commands` hook call at end of file |
| `pyproject.toml` | Existing | Add `pluggy` dependency; document `[project.entry-points.retrocast]` convention |
| `tests/conftest.py` | Existing | Add `sys._called_from_test` sentinel |
| `tests/test_plugins.py` | New | Create (idempotency, `get_plugins`, register hooks, broken plugin handling) |
| `tests/test_index_commands.py` | New/Existing | Create/extend (mock backend, `backends` sub-command, bad `--backend`) |
| `tests/test_plugin_install.py` | New | Create (mock `runpy.run_module`, verify `sys.argv` construction) |
| `examples/retrocast-zvec-example/pyproject.toml` | New | Skeleton plugin package manifest |
| `examples/retrocast-zvec-example/retrocast_zvec/__init__.py` | New | Stub `ZvecBackend` + `@hookimpl` |
| `examples/retrocast-zvec-example/README.md` | New | Full dev-loop documentation |
| `AGENTS.md` | Existing | Update (new modules, `plugin` group, `RETROCAST_LOAD_PLUGINS`, naming convention) |
