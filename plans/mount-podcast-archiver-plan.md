# Mount podcast-archiver database into retrocast

**Plan Created:** 2025-12-05T03:31:58Z (UTC)

## Objective
Attach the `podcast-archiver` SQLite database to the currently used
`retrocast` database under a unique alias before issuing any SQL
queries, then expose every table from the attached DB without naming
conflicts.

## Background
In SQLite you can extend an open connection with `ATTACH DATABASE
'<path>' AS <alias>;`. From that point on every table/view in the
attached database is referenced through `<alias>.table_name`, keeping
schema namespaces separate and avoiding collisions. After work is
done, the alias can be removed with `DETACH DATABASE <alias>;` to
clean up the connection.

## Steps
1. Locate both database files by following the code:
   `get_default_db_path()` in `src/retrocast/appdir.py` uses
   `platformdirs.user_data_dir("net.memexponent.retrocast",
   "retrocast")` and appends `retrocast.db`, so the default file lives
   in that application data directory (e.g.,
   `~/.local/share/net.memexponent.retrocast/retrocast.db` on
   Linux). The `podcast_archiver` CLI (in
   `.venv/.../podcast_archiver/cli.py`) defaults `--config` to
   `click.get_app_dir("podcast-archiver") / "config.yaml"`, and
   `Settings.database` is described as falling back to
   `constants.DEFAULT_DATABASE_FILENAME` (`podcast-archiver.db`) in
   the same directory, meaning the secondary DB path is typically
   `~/.config/podcast-archiver/podcast-archiver.db`. Record those
   absolute paths before constructing the `ATTACH DATABASE` call so
   the alias references are unambiguous.
2. Inspect `retrocast`’s current schema (`.tables`, `SELECT name FROM
   sqlite_master`) to list tables/views already defined; use that list
   to ensure the chosen alias for the attachment (e.g., `archiver`,
   `podcast_archive`) does not conflict with existing namespace names.
3. Attach the secondary database using the safe alias (`ATTACH
   DATABASE '<absolute-path>' AS <alias>;`) and document that alias
   for every future cross-database reference.
4. Discover all tables/views in `podcast-archiver` by running `SELECT
   type, name FROM <alias>.sqlite_master WHERE type IN
   ('table','view');` and note any special objects (e.g., virtual
   tables, indexes) that will need explicit qualification.
5. For each discovered table/view, plan how downstream SQL will
   reference it with the alias (e.g., `SELECT * FROM <alias>.feeds;`),
   and if necessary, define short helper views in the main schema to
   surface them without conflict while keeping the alias as part of
   their definition.
6. Verify the attachment succeeded (`PRAGMA database_list;`, sample
   query such as `SELECT name FROM <alias>.sqlite_master LIMIT 1;`)
   before running subsequent queries that rely on the mounted data.
7. Record the cleanup step (`DETACH DATABASE <alias>;`) to run when
   the session is complete or if the alias needs to be reclaimed.

## Checklist
- [ ] Confirm absolute paths for `retrocast.db` and
      `podcast-archiver.db` via `appdir.get_default_db_path()` and the
      podcast-archiver defaults.
- [ ] Inspect the `retrocast` schema to choose a non-conflicting alias
      namespace.
- [ ] Plan the `ATTACH DATABASE` command with resolved paths and a
      documented alias.
- [ ] Enumerate every table/view inside `podcast-archiver`, noting any
      objects requiring special handling.
- [ ] Map how each attached table/view will be referenced (qualified
      SQL or helper views) without overlapping existing names.
- [ ] Specify verification (`PRAGMA database_list;`, alias-scoped
      `sqlite_master` checks) and cleanup (`DETACH`) steps for the
      session.
- [ ] Generate tests to confirm the functionality generated
- [ ] Append an implementation report to this plan

## Coverage Notes
- Always refer to attached tables/view names with the alias to avoid
  collisions with the base `retrocast` schema.
- If any table names also exist in `retrocast`, plan to handle them
  via alias-qualified views or rename logic so both datasets stay
  accessible.
- Keep a short reference (e.g., in comments or docs) listing every
  exposed table from `podcast-archiver` plus the alias that should
  prefix it.
- Do not modify the `podcast-archiver` subcommand’s access or querying
  of it’s own sqlite database
  
