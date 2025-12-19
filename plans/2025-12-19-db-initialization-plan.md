# Database Initialization Implementation Plan

**Created**: 2025-12-19T22:27:45Z  
**Issue**: Implement retrocast.db initialization  
**Goal**: Ensure database schemas are properly initialized with both `retrocast config init` and `retrocast sync overcast init` commands

## Problem Statement

Currently, the database schemas for overcast and transcription tables are not installed when running:
- `retrocast config init` - Only creates the app directory structure
- `retrocast sync overcast init` - Checks if database exists but doesn't initialize schemas

The database schema initialization only happens when a command like `save` is run, which creates a `Datastore` instance. The `Datastore.__init__` method calls `_prepare_db()` which creates all necessary tables.

## Root Cause Analysis

1. **`config initialize` command** (cli.py:150-198):
   - Creates app directory
   - Creates placeholder files for auth and database paths
   - Does NOT create a Datastore instance to initialize schemas

2. **`overcast init` command** (overcast.py:226-267):
   - Checks if database exists using `Datastore.exists()`
   - Reports status but never creates a Datastore instance
   - Schemas are never initialized

3. **Schema initialization happens in**:
   - `Datastore.__init__` → `_prepare_db()` (datastore.py:68-321)
   - Creates all tables: feeds, feeds_extended, episodes, episodes_extended, playlists, chapters
   - Creates transcription tables: episode_downloads, transcriptions, transcription_segments
   - Creates views: episodes_played, episodes_deleted, episodes_starred

## Implementation Plan

### Task Checklist

- [ ] **Phase 1: Fix `overcast init` command**
  - [ ] Modify `overcast.py:init()` to create a Datastore instance
  - [ ] This will ensure all schemas are initialized when the command runs
  - [ ] Update success messages to reflect schema initialization

- [ ] **Phase 2: Update `config initialize` command**
  - [ ] Modify `cli.py:config_initialize()` to initialize database schemas
  - [ ] Create a Datastore instance after creating app directory
  - [ ] Update success messages to indicate database is initialized

- [ ] **Phase 3: Create tests**
  - [ ] Add test for `config initialize` that verifies database tables exist
  - [ ] Add test for `overcast init` that verifies database tables exist
  - [ ] Verify transcription tables are created
  - [ ] Verify views are created

- [ ] **Phase 4: Validate changes**
  - [ ] Run linter on modified files
  - [ ] Run type checker on modified files
  - [ ] Run existing tests to ensure no regressions
  - [ ] Run new tests to verify functionality
  - [ ] Manually test both commands

## Minimal Changes Required

### Change 1: `src/retrocast/overcast.py` - Fix `init` command

**Location**: Line 226-267  
**Change**: Create Datastore instance to initialize schemas

```python
@overcast.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize Overcast database in user platform directory."""
    console = Console()
    app_dir = _ensure_app_dir_from_ctx(ctx)
    db_path = get_default_db_path(create=True)

    # Check if database already exists
    already_exists = Datastore.exists(db_path)

    # Create the database by instantiating Datastore (initializes schemas)
    db = Datastore(db_path)  # ADD THIS LINE

    console.print()
    console.print("[bold cyan]Overcast Database Initialization[/bold cyan]")
    console.print()

    # ... rest of function
```

### Change 2: `src/retrocast/cli.py` - Update `config_initialize` command

**Location**: Line 150-198  
**Change**: Add database schema initialization

```python
@config.command(name="initialize")
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Create the directory without confirmation prompts.",
)
@click.pass_context
def config_initialize(ctx: click.Context, yes: bool) -> None:
    """Create the retrocast configuration directory"""

    console = Console()
    app_dir = get_app_dir(create=False)

    if app_dir.exists() and not yes:
        if not click.confirm(
            f"Configuration directory already exists at {app_dir}. Continue?",
            default=False,
        ):
            console.print("[yellow]Initialization cancelled.[/yellow]")
            ctx.exit(1)

    app_dir = ensure_app_dir()
    setup_logging(
        app_dir,
        verbose=ctx.obj.get("verbose", False),
        quiet=ctx.obj.get("quiet", False),
        log_file=ctx.obj.get("log_file"),
        enable_file_logging=True,
    )

    # Initialize database schemas
    from retrocast.datastore import Datastore  # ADD IMPORT
    db_path = get_default_db_path(create=True)
    db = Datastore(db_path)  # ADD THIS LINE - initializes all schemas

    console.print()
    console.print("[bold cyan]retrocast Initialization[/bold cyan]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Value")
    table.add_row("Config directory:", str(app_dir))
    table.add_row("Auth path:", str(get_auth_path(create=True)))
    table.add_row("Database path:", str(db_path))
    table.add_row("Database schemas:", "[green]✓ Initialized[/green]")  # ADD THIS LINE

    console.print(table)
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print("  1. Authenticate: [cyan]retrocast sync overcast auth[/cyan]")
    console.print("  2. Sync data:    [cyan]retrocast sync overcast save[/cyan]")
    console.print("  3. Download:     [cyan]retrocast meta overcast transcripts[/cyan]")
    console.print()
```

## Expected Outcomes

After these changes:

1. Running `retrocast config init` will:
   - Create app directory
   - Create empty auth.json placeholder
   - Create retrocast.db with all schemas initialized
   - User can immediately start using the database

2. Running `retrocast sync overcast init` will:
   - Create app directory if needed
   - Create retrocast.db with all schemas initialized
   - Report successful initialization

3. All database tables will be available:
   - Overcast tables: feeds, feeds_extended, episodes, episodes_extended, playlists, chapters
   - Transcription tables: episode_downloads, transcriptions, transcription_segments
   - Views: episodes_played, episodes_deleted, episodes_starred

## Testing Strategy

1. **Unit tests**: Verify that after running init commands, all expected tables exist
2. **Integration tests**: Verify that subsequent commands work correctly with initialized database
3. **Manual verification**: Run both commands and inspect database with sqlite3 or Datasette

## Notes

- The fix is minimal - just creating a Datastore instance which triggers `_prepare_db()`
- No changes to schema definitions needed
- No changes to existing command behavior (other than fixing the bug)
- All existing tests should continue to pass
