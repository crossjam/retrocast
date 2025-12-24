# Retrocast Location JSON Options Implementation Plan

**Created**: 2025-12-24
**Issue**: Extend `retrocast location` command with JSON path output options
**Goal**: Add CLI options to output specific path locations as JSON strings for programmatic use

## Problem Statement

The current `retrocast config location` command provides path information in two formats:
- **Console output** (default): Rich table display with status indicators
- **JSON output** (`--format json`): All three paths (app_dir, auth_path, db_path) as a JSON object

However, there's no convenient way to retrieve individual path values as JSON strings for use in shell scripts or other programmatic contexts. Users need individual path options that output just the requested path as a JSON string.

## Objective

Add two new CLI options to the `retrocast config location` command:
1. `--db-path` / `-d`: Output only the database path as a JSON string
2. `--app-dir` / `-a`: Output only the application directory path as a JSON string

These options will:
- Output single path values as JSON-encoded strings (properly escaped)
- Exit with code 0 on success
- Be mutually exclusive with the existing `--format` option
- Be mutually exclusive with each other (only one path option at a time)

## Current Implementation Analysis

**File**: `src/retrocast/cli.py` (lines 282-357)

**Current behavior**:
- The `location` command already has a `--format` / `-f` option using `LocationOutput` enum
- Two output modes: `CONSOLE` (default) and `JSON`
- Helper functions from `src/retrocast/appdir.py`:
  - `get_app_dir(create=False)` → returns Path object
  - `get_auth_path(create=False)` → returns Path object
  - `get_default_db_path(create=False)` → returns Path object
- When format is JSON, outputs all three paths as an object

**Testing**:
- Tests exist in `tests/test_cli.py` (lines 140-182)
- Tests cover JSON format, missing directory, and ready state scenarios

## Implementation Plan

### Task Checklist

- [ ] **Phase 1: Add CLI options**
  - [ ] Add `--db-path` / `-d` flag to `location` command
  - [ ] Add `--app-dir` / `-a` flag to `location` command
  - [ ] Make the three output options mutually exclusive (--format, --db-path, --app-dir)
  - [ ] Update command help text to document new options

- [ ] **Phase 2: Implement output logic**
  - [ ] Add conditional check for `db_path` flag
  - [ ] Output just the db_path as a JSON string when flag is set
  - [ ] Add conditional check for `app_dir` flag
  - [ ] Output just the app_dir as a JSON string when flag is set
  - [ ] Ensure proper JSON string encoding (handle special characters, spaces, etc.)
  - [ ] Exit with code 0 after JSON output

- [ ] **Phase 3: Testing**
  - [ ] Add test for `--db-path` flag
  - [ ] Add test for `--app-dir` flag
  - [ ] Add test for mutual exclusivity (error when multiple output options used)
  - [ ] Add test to verify proper JSON string encoding
  - [ ] Verify existing tests still pass

- [ ] **Phase 4: Documentation**
  - [ ] Update command docstring with new options
  - [ ] Add usage examples in comments or help text
  - [ ] Update AGENTS.md if necessary

## Technical Details

### Option Design

The new options should be implemented as boolean flags that trigger specialized output:

```python
@config.command()
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(LocationOutput, case_sensitive=False),
    default=LocationOutput.CONSOLE,
)
@click.option(
    "-d",
    "--db-path",
    "db_path",
    is_flag=True,
    help="Output only the database path as a JSON string",
)
@click.option(
    "-a",
    "--app-dir",
    "app_dir",
    is_flag=True,
    help="Output only the app directory path as a JSON string",
)
@click.pass_context
def location(ctx: click.Context, output_format, db_path: bool, app_dir: bool) -> None:
    """Output the location of the configuration directory"""
```

### Mutual Exclusivity

Implement validation to ensure only one output mode is active:

```python
# Count active output options
output_modes = [
    output_format != LocationOutput.CONSOLE,  # --format json specified
    db_path,
    app_dir,
]

if sum(output_modes) > 1:
    raise click.UsageError(
        "Only one output option can be used at a time: "
        "--format, --db-path, or --app-dir"
    )
```

### JSON String Output

Use Python's `json.dumps()` to properly encode path strings:

```python
if db_path:
    db_path_value = get_default_db_path(create=False)
    # Output just the path value as a JSON string
    json.dump(str(db_path_value), fp=sys.stdout)
    ctx.exit(0)

if app_dir:
    app_dir_value = get_app_dir(create=False)
    # Output just the path value as a JSON string
    json.dump(str(app_dir_value), fp=sys.stdout)
    ctx.exit(0)
```

### Expected Output Examples

```bash
# Database path as JSON string
$ retrocast config location --db-path
"/home/user/.local/share/retrocast/retrocast.db"

# App directory as JSON string
$ retrocast config location --app-dir
"/home/user/.local/share/retrocast"

# Error on multiple options
$ retrocast config location --format json --db-path
Error: Only one output option can be used at a time: --format, --db-path, or --app-dir
```

## Testing Strategy

### Unit Tests

Add to `tests/test_cli.py`:

1. **test_config_location_db_path**: Verify `--db-path` outputs correct JSON string
2. **test_config_location_app_dir**: Verify `--app-dir` outputs correct JSON string
3. **test_config_location_mutual_exclusivity**: Verify error when multiple output options used
4. **test_config_location_json_encoding**: Verify special characters in paths are properly encoded

### Test Implementation Example

```python
def test_config_location_db_path(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "location", "--db-path"])

    assert result.exit_code == 0, result.output
    # Parse the JSON string output
    assert json.loads(result.stdout) == str(app_dir / "retrocast.db")


def test_config_location_app_dir(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "location", "--app-dir"])

    assert result.exit_code == 0, result.output
    # Parse the JSON string output
    assert json.loads(result.stdout) == str(app_dir)


def test_config_location_mutual_exclusivity(monkeypatch, tmp_path: Path) -> None:
    app_dir = tmp_path / "retrocast-tests"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *_, **__: str(app_dir))

    runner = CliRunner()

    # Test --format json with --db-path
    result = runner.invoke(cli, ["config", "location", "--format", "json", "--db-path"])
    assert result.exit_code != 0
    assert "only one output option" in result.output.lower()

    # Test --db-path with --app-dir
    result = runner.invoke(cli, ["config", "location", "--db-path", "--app-dir"])
    assert result.exit_code != 0
    assert "only one output option" in result.output.lower()
```

## Files to Modify

1. **src/retrocast/cli.py**
   - Add new CLI options to `location` command (~lines 287-296)
   - Add mutual exclusivity validation
   - Add output logic for new flags

2. **tests/test_cli.py**
   - Add new test functions for the new options
   - Add mutual exclusivity tests

## Constraints and Considerations

- **Backward compatibility**: Existing behavior must remain unchanged when new flags are not used
- **JSON encoding**: Must properly handle paths with spaces, special characters, Unicode
- **Exit codes**: Success should exit with 0, errors with non-zero
- **Help text**: Clear documentation of mutual exclusivity and usage
- **Consistency**: Follow existing patterns from `--format json` implementation

## Success Criteria

1. ✅ `--db-path` outputs only the database path as a JSON string
2. ✅ `--app-dir` outputs only the app directory path as a JSON string
3. ✅ Options are mutually exclusive with each other and `--format`
4. ✅ JSON strings are properly encoded and parseable
5. ✅ All new tests pass
6. ✅ All existing tests continue to pass
7. ✅ No breaking changes to existing functionality

## Use Cases

These options enable programmatic access to path values in shell scripts:

```bash
# Get database path in a shell script
DB_PATH=$(retrocast config location --db-path | jq -r)

# Get app directory in a script
APP_DIR=$(retrocast config location --app-dir | jq -r)

# Or without jq (since output is already a valid JSON string):
DB_PATH=$(retrocast config location --db-path | python3 -c "import sys, json; print(json.load(sys.stdin))")
```

## Implementation Notes

- Keep changes minimal and focused
- Reuse existing helper functions (`get_app_dir`, `get_default_db_path`)
- Follow Click framework best practices for option handling
- Maintain consistent error messages with rest of codebase
- Use `json.dump()` from standard library for JSON encoding
