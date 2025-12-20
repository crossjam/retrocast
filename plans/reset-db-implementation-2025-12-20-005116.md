# Implementation Plan: `retrocast config reset-db`

**Created:** 2025-12-20 00:51:16 UTC

## Objective

Implement `retrocast config reset-db` command to reset/reinstall database schemas and indices with user confirmation and dry-run support.

## Requirements

1. Add `reset-db` subcommand under `config` group
2. Prompt user for confirmation before destructive action
3. Reset or reinstall all database schemas and indices
4. Include `--dry-run` flag that lists actions without executing
5. Support `-y/--yes` flag to skip confirmation prompt

## Implementation Plan

### Phase 1: Create Implementation Plan ✓
- [x] Create timestamped markdown plan with checklist

### Phase 2: Analyze Current Schema Structure
- [ ] Review `datastore.py` to understand table creation logic
- [ ] Identify all tables, views, indices, and FTS tables
- [ ] Document schema recreation process

### Phase 3: Implement `reset-db` Command
- [ ] Add `reset-db` command to `config` group in `cli.py`
- [ ] Implement dry-run mode that lists all actions
- [ ] Implement confirmation prompt (with `-y` override)
- [ ] Implement schema reset logic:
  - [ ] Drop all existing tables
  - [ ] Drop all views
  - [ ] Drop all FTS tables
  - [ ] Drop all indices
  - [ ] Recreate schema using `_prepare_db()`

### Phase 4: Add Helper Method to Datastore
- [ ] Add `reset_schema()` method to `Datastore` class
- [ ] Add `get_schema_info()` method for dry-run display
- [ ] Ensure proper transaction handling

### Phase 5: Testing
- [ ] Create test file for `reset-db` command
- [ ] Test dry-run mode
- [ ] Test with confirmation (yes/no)
- [ ] Test with `-y` flag
- [ ] Test that schema is properly recreated
- [ ] Verify all tables, views, and indices are restored

### Phase 6: Validation
- [ ] Run existing tests to ensure no regression
- [ ] Manually test the command
- [ ] Test with existing database
- [ ] Test with non-existent database

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

## Testing Strategy

1. Unit tests using temporary database
2. Test dry-run output format
3. Test confirmation prompts with mocked input
4. Verify schema integrity after reset

## Success Criteria

- Command successfully drops and recreates all schema objects
- Dry-run accurately lists all actions without executing
- User confirmation works correctly
- `-y` flag bypasses confirmation
- All tests pass
- No data loss warnings displayed to user
