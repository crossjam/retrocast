# Implementation Plan: `retrocast config reset-db`

**Created:** 2025-12-20 00:51:16 UTC
**Completed:** 2025-12-20 01:00:00 UTC

## Objective

Implement `retrocast config reset-db` command to reset/reinstall database schemas and indices with user confirmation and dry-run support.

## Requirements

1. Add `reset-db` subcommand under `config` group ✅
2. Prompt user for confirmation before destructive action ✅
3. Reset or reinstall all database schemas and indices ✅
4. Include `--dry-run` flag that lists actions without executing ✅
5. Support `-y/--yes` flag to skip confirmation prompt ✅

## Implementation Plan

### Phase 1: Create Implementation Plan ✅
- [x] Create timestamped markdown plan with checklist

### Phase 2: Analyze Current Schema Structure ✅
- [x] Review `datastore.py` to understand table creation logic
- [x] Identify all tables, views, indices, and FTS tables
- [x] Document schema recreation process

### Phase 3: Implement `reset-db` Command ✅
- [x] Add `reset-db` command to `config` group in `cli.py`
- [x] Implement dry-run mode that lists all actions
- [x] Implement confirmation prompt (with `-y` override)
- [x] Implement schema reset logic:
  - [x] Drop all existing tables
  - [x] Drop all views
  - [x] Drop all FTS tables
  - [x] Drop all indices
  - [x] Recreate schema using `_prepare_db()`

### Phase 4: Add Helper Method to Datastore ✅
- [x] Add `reset_schema()` method to `Datastore` class
- [x] Add `get_schema_info()` method for dry-run display
- [x] Ensure proper transaction handling

### Phase 5: Testing ✅
- [x] Create test file for `reset-db` command
- [x] Test dry-run mode
- [x] Test with confirmation (yes/no)
- [x] Test with `-y` flag
- [x] Test that schema is properly recreated
- [x] Verify all tables, views, and indices are restored

### Phase 6: Validation ✅
- [x] Run existing tests to ensure no regression
- [x] Manually test the command
- [x] Test with existing database
- [x] Test with non-existent database
- [x] Address code review feedback
- [x] Run security checks

## Technical Details

### Schema Elements to Reset

Based on `datastore.py`, the following need to be recreated:

**Tables:**
- `feeds` (with pk: overcastId)
- `feeds_extended` (with pk: xmlUrl, FTS enabled)
- `episodes` (with pk: overcastId)
- `episodes_extended` (with pk: enclosureUrl, FTS enabled)
- `playlists` (with pk: title)
- `chapters` (with FTS enabled, composite index)
- `episode_downloads` (with pk: media_path, FTS enabled, multiple indices)
- `transcriptions` (with pk: transcription_id, multiple indices)
- `transcription_segments` (with composite index, FTS enabled)

**Views:**
- `episodes_played`
- `episodes_deleted`
- `episodes_starred`

**Foreign Keys:**
- Multiple FK relationships between tables

**Full-Text Search:**
- FTS tables for multiple tables with triggers

**Indices:**
- Various indices on timestamp and lookup columns

### Implementation Approach

1. Query SQLite system tables to get all user objects
2. Drop in correct order (respecting dependencies):
   - FTS triggers
   - Views
   - Tables (with CASCADE if needed)
3. Call `_prepare_db()` to recreate everything

### Security Improvements

- Added SQL identifier quoting using double quotes with escaping
- Prevents any potential SQL injection from malformed schema object names
- Used helper function `quote_identifier()` for consistency

### Code Quality Improvements

- Extracted `format_truncated_list()` helper function for better readability
- Reduced complexity of inline conditional expressions
- Made code more maintainable and testable

## Testing Strategy

1. Unit tests using temporary database ✅
2. Test dry-run output format ✅
3. Test confirmation prompts with mocked input ✅
4. Verify schema integrity after reset ✅

## Success Criteria

✅ Command successfully drops and recreates all schema objects
✅ Dry-run accurately lists all actions without executing
✅ User confirmation works correctly
✅ `-y` flag bypasses confirmation
✅ All tests pass (7 new tests, 7 existing tests)
✅ No data loss warnings displayed to user
✅ Code review passed with improvements
✅ Security scan passed (0 vulnerabilities)
