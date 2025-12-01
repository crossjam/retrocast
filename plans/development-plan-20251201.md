# Development Plan for Issues #14, #19, and #20

**Timestamp:** 2025-12-02T21:17:14.000000+00:00

## Objectives
- Introduce a `config` command subgroup to manage the user-specific configuration directory (Issue #19).
- Reorganize CLI commands under `sync` (metadata ingestion) and `retrieve` (media downloads) groups (Issue #14).
- Integrate `loguru-config` for centralized logging configuration (Issue #20).

## Current Context
- The CLI entrypoint (`src/retrocast/cli.py`) defines `cli`, `about`, `init`, and a `sync` group that nests `overcast` commands; initialization currently creates the app directory and displays next steps with `rich`. `DefaultGroup` sets `about` as the default command.
- Application directories are managed in `src/retrocast/appdir.py`, which auto-creates the platform-specific data dir and exposes helper paths for auth and the default DB.
- Logging is not yet configured; `loguru` is a dependency, but no logger setup exists in the CLI or helpers.

## Plan by Issue

### Issue #19: Implement `config` Command Subgroup
- [x] Create a new `config` click group under the top-level CLI to manage the user config directory, using `rich.console.Console` for messaging.
- [x] Add `check` command to report initialization status and required steps without mutating state (e.g., whether app dir exists, auth.json/db presence), formatted via `rich.table.Table` similar to existing `init` output.
- [x] Add `initialize` command that safely creates the user configuration directory and prompts before overwriting existing files; reuse `get_app_dir()` and consider optional flags for non-interactive confirmation.
- [x] Add `archive` command to gzip the configuration directory to a user-specified file or stdout; include safeguards for missing directories and optional compression level/overwrite controls.
- [x] Update help text and docs strings to align with the new subgroup and ensure `config` commands are discoverable from `retrocast --help`.

### Issue #14: Create `sync` Command Subgroup and Separate Retrieval
- [x] Audit existing `overcast` commands under `sync` in `src/retrocast/overcast.py` and identify which focus on metadata ingestion (e.g., OPML/RSS saving, DB setup) versus media downloads (e.g., transcripts or enclosure fetching if present elsewhere).
- [x] Restructure the CLI so metadata-related operations live under `sync` (e.g., `retrocast sync overcast ...`) while media-download operations are grouped under a new `retrieve` subgroup; preserve existing functionality and aliases where practical for backward compatibility with deprecation warnings.
- [x] Update command descriptions, default paths (`get_default_db_path`, archive locations), and user guidance to reflect the new hierarchy, ensuring the `about`/`init` messaging points to the correct commands.
- [x] Expand or adjust tests (unit/CLI) to cover the reorganized command tree, ensuring `DefaultGroup` behavior remains sensible (default `about` or another appropriate default) and that command help output lists the new structure.

### Issue #20: Integrate `loguru-config` for Logging
- [x] Add `loguru-config` as a dependency via `uv add git+https://github.com/crossjam/loguru-config` (update `requirements.txt` and `uv.lock` accordingly) and import/configure it at CLI startup to manage logging sinks and formatting.
- [x] Define a configuration strategy (e.g., default config file in app dir with overrides via env vars/CLI flags) consistent with `loguru-config` usage; ensure compatibility with existing `rich` console output.
- [x] Replace ad-hoc `print` statements with `loguru` logger calls where appropriate, preserving user-facing console tables for status while routing diagnostics through the logger.
- [x] Provide sensible defaults for log level and output (e.g., stderr), and document how users can customize logging via the new config.

## Testing Strategy
- [x] Add or update automated tests to cover new CLI groups/commands, config directory operations (including archive creation), and logging initialization paths.
- [x] Run the full test suite with `uv run pytest` to validate functionality and prevent regressions.

## Implementation Summary (2025-12-01 21:36 UTC)
- Added the `config` command subgroup with check/initialize/archive commands and reorganized CLI commands under `sync` and `retrieve` groups.
- Integrated `loguru-config` for centralized logging defaults and aligned app directory utilities with safer creation semantics.
- Updated tests to cover the new CLI structure and ensured `uv run pytest` passes.

## Implementation Summary (2025-12-01 21:40 UTC)
- Hardened `config archive` to use context-managed output streams and confirmed CLI changes via tests.

## Implementation Summary (2025-12-01 21:59 UTC)
- Added a vendored shim for `loguru-config` to support offline installs and completed ruff linting of the CLI.
