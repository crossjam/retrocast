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

The `podcast-archiver` CLI tool is wrapped in the `retrocast` under
the `download` subgroup. The wrapper uses the `retrocast` user app dir
retrieved via `platformdirs` to supply defaults for the
podcast-archiver database (`episodes.db`) and file archive directory
(`episode_downloads`). Separately, `src/retrocast/podcast_archiver_attach.py`
now provides `get_podcast_archiver_db_path()` (derives the default path
next to podcast-archiver’s `config.yaml` via
`podcast_archiver.cli.get_default_config_path()` and
`constants.DEFAULT_DATABASE_FILENAME`), `ARCHIVER_ALIAS` (default
`podcast_archiver`), and `attach_podcast_archiver()` which resolves an
alias (with `_choose_alias`) and returns an `AttachedDatabase` tuple
including table/view listings. Use those helpers instead of inventing
new plumbing.

## Steps
1. Resolve candidate podcast-archiver database locations: the download
   wrapper seeds `episodes.db` within the retrocast app dir, while
   `get_podcast_archiver_db_path()` builds a default path beside
   podcast-archiver’s config (`DEFAULT_DATABASE_FILENAME`). Check both
   paths, decide precedence (prefer the retrocast-managed file if it
   exists), and record absolute paths.
2. Align with the helper’s alias strategy: `ARCHIVER_ALIAS` defaults to
   `podcast_archiver` and `_choose_alias()` appends numeric suffixes if
   already attached. Inspect `PRAGMA database_list` to document current
   aliases and the one chosen for this attachment.
3. Attach via `attach_podcast_archiver(conn)` (or `attach_all` when
   passing explicit alias/path pairs) so alias selection and
   table/view enumeration happen together; define how missing/unreadable
   DBs should be reported.
4. Use the returned `AttachedDatabase.tables` and `.views` to list
   available objects, compare with the base schema to spot naming
   collisions, and decide whether alias-only access suffices or helper
   views are needed.
5. Lay out verification and cleanup steps: `PRAGMA database_list` plus
   a lightweight `select name from [{alias}].sqlite_master` after
   attach, and `detach database [{alias}]` when done; confirm the
   procedure is safe to re-run if no DB is found.
6. Outline tests and reporting: plan tests for path discovery
   precedence, alias-collision handling, and table/view enumeration,
   and note what outcomes to capture in the implementation report.

## Checklist
- [ ] Confirm absolute paths for both retrocast-managed (`appdir`
      `episodes.db`) and podcast-archiver default DB locations, noting
      which will be preferred.
- [ ] Document the alias selection approach (default
      `ARCHIVER_ALIAS`/`_choose_alias`) and current attached aliases.
- [ ] Define the attach flow using `attach_podcast_archiver` (or
      `attach_all`) including behavior when the DB is missing.
- [ ] Enumerate attached tables/views via the helper and map how to
      reference them alongside the base schema.
- [ ] Specify verification (`PRAGMA database_list`, alias-scoped
      `sqlite_master`) and cleanup (`DETACH`) steps.
- [ ] Outline tests covering path discovery precedence, alias-collision
      handling, and table/view enumeration.
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
  
