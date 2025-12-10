# Add Quiet Flag Plan

**Timestamp:** 2025-12-09T20:57:00.000000+00:00

## Objective

Add a top-level `-q/--quiet` CLI flag that sets logging to ERROR level and is honored across the application.

## Requirements

1. Add a top-level click option `-q/--quiet` to `src/retrocast/cli.py`
2. Store the value in `ctx.obj["quiet"]` and propagate into initial `setup_logging` call
3. Update `src/retrocast/logging_config.py` to accept `quiet: bool = False` parameter
4. Implement log level precedence: quiet → ERROR, verbose → DEBUG, default → INFO
5. Preserve external config file precedence behavior
6. Update spots that re-invoke `setup_logging` to pass the quiet flag
7. Add comprehensive tests for the new functionality

## Implementation Details

### Code Changes

1. **src/retrocast/logging_config.py**
   - Extended `setup_logging` signature to accept `quiet: bool = False` (keyword-only)
   - Implemented log level precedence logic:
     - If `quiet=True`: level = "ERROR"
     - Elif `verbose=True`: level = "DEBUG"
     - Else: level = "INFO"
   - Preserved existing behavior where external config files take precedence

2. **src/retrocast/cli.py**
   - Added `-q/--quiet` option to the top-level `cli` function
   - Stored quiet flag in `ctx.obj["quiet"]`
   - Passed quiet flag to initial `setup_logging` call
   - Updated `config_initialize` command to pass quiet flag when re-invoking `setup_logging`

3. **src/retrocast/download_commands.py**
   - Retrieved quiet flag from `ctx.obj` in the `aria` command
   - Passed quiet flag to `setup_logging` to ensure quiet overrides subcommand-level verbose

### Testing

Created `tests/test_cli_quiet_flag.py` with comprehensive test coverage:

1. **test_quiet_suppresses_info_logs**: Verifies that `-q` flag causes `setup_logging` to be called with `quiet=True`
2. **test_quiet_overrides_verbose**: Verifies that both flags are passed to `setup_logging` when `-q -v` are used together
3. **test_subcommand_respects_quiet**: Verifies that subcommands receive the quiet flag from context
4. **test_quiet_flag_in_logging_config**: Verifies that `setup_logging` with `quiet=True` sets ERROR level
5. **test_verbose_without_quiet**: Verifies that verbose flag works correctly when quiet is not set (DEBUG level)
6. **test_default_logging_level**: Verifies that default logging level is INFO when neither flag is set

All tests pass successfully, including existing tests to ensure no regressions.

## Constraints and Notes

- **External logging configs**: If an external logging config is found via `RETROCAST_LOG_CONFIG` environment variable or `app_dir/logging.json`, that config remains the authoritative source. The quiet/verbose flags only affect the default configuration.
- **Backward compatibility**: Existing tests that monkeypatch `setup_logging` continue to work because the function accepts keyword arguments.
- **Module-level logging**: Some DEBUG logs appear during module import (before `setup_logging` is called). This is expected behavior and does not violate the quiet mode requirement, as those logs occur before the CLI option is processed.

## Testing Instructions

1. Run all tests: `pytest tests/`
2. Test quiet flag: `python -m retrocast.cli -q about` (should show only ERROR level logs or higher)
3. Test verbose flag: `python -m retrocast.cli -v about` (should show DEBUG level logs)
4. Test precedence: `python -m retrocast.cli -q -v about` (quiet should win, showing only ERROR logs)
5. Test in subcommands: `python -m retrocast.cli -q download aria --help` (should respect quiet mode)

## Implementation Report (2025-12-09 21:02 UTC)

Successfully implemented the quiet flag feature with the following changes:

1. ✅ Added `-q/--quiet` option to top-level CLI
2. ✅ Updated `logging_config.py` with quiet parameter and precedence logic
3. ✅ Updated `cli.py` to store and pass quiet flag
4. ✅ Updated `download_commands.py` to honor quiet flag in subcommands
5. ✅ Created comprehensive test suite with 6 tests
6. ✅ All 18 tests pass (12 existing + 6 new)
7. ✅ Manual verification confirms correct behavior

The implementation follows the minimal change principle while fully satisfying the requirements. External logging configurations are preserved, and all existing functionality remains intact.
