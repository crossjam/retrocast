# Episodes Database Implementation Plan

**Created:** 2025-12-11
**Status:** Ready for Review
**Related Document:** episodes_database.md

## Overview

This plan outlines the implementation strategy for adding a database
layer to track downloaded podcast episodes and their metadata from the
`episode_downloads` directory. The feature will enable users to
initialize, update, and query episode metadata stored alongside
downloaded media files.

## Current State Analysis

### Existing Components

1. **Download System**
   - Location: `src/retrocast/download_commands.py`
   - The `download` group contains the `aria` command and podcast-archiver passthrough
   - Downloads go to `$(APP_DIR)/episode_downloads/`
   - Podcast-archiver integration via `_attach_podcast_archiver_passthroughs` in `cli.py`

2. **Database Layer**
   - Location: `src/retrocast/datastore.py`
   - Single `Datastore` class wrapping sqlite-utils `Database`
   - Manages tables: `feeds`, `feeds_extended`, `episodes`, `episodes_extended`, `playlists`, `chapters`
   - Uses FTS (Full-Text Search) on titles/descriptions
   - Follows pattern: table creation in `_prepare_db()`, operations as methods

3. **Application Directory**
   - Managed via `appdir.py` with `get_app_dir()` function
   - Main database: `retrocast.db`
   - Episode downloads: `episode_downloads/`
   - Podcast-archiver database: `episodes.db` (separate, managed by podcast-archiver)

### Directory Structure Example

```
~/Library/Application Support/net.memexponent.retrocast/
├── retrocast.db                    # Main database (existing)
├── episodes.db                     # Podcast-archiver DB (existing)
└── episode_downloads/              # Downloaded episodes (existing)
    ├── Practical AI/
    │   ├── 2025-12-10 - Episode Title.mp3
    │   └── 2025-12-10 - Episode Title.info.json
    └── Talk Python To Me/
        ├── 2025-12-03 - Episode Title.mp3
        └── 2025-12-03 - Episode Title.info.json
```

## Requirements Summary

From `episodes_database.md`:

1. Set `--write-info-json` to true by default in podcast-archiver passthrough
2. Design database schema for episode downloads in `retrocast.db`
3. Store JSON metadata in SQLite JSON column
4. Track media file paths and modification times
5. Add text indexes for searchability
6. Create new package/module for episode database management
7. Implement filesystem scanner to discover episodes
8. Add `download db` subgroup with `init` and `update` commands

## Architecture Design

### 1. Database Schema

**New Table: `episode_downloads`**

```sql
CREATE TABLE episode_downloads (
    -- Primary key: file path to the media file
    media_path TEXT PRIMARY KEY,

    -- File system metadata
    podcast_title TEXT NOT NULL,
    episode_filename TEXT NOT NULL,
    file_size INTEGER,
    modified_time TEXT,  -- ISO8601 timestamp
    discovered_time TEXT,  -- ISO8601 timestamp when first indexed
    last_verified_time TEXT,  -- ISO8601 timestamp when last checked

    -- JSON metadata (entire .info.json contents)
    metadata_json TEXT,  -- SQLite JSON1 column

    -- Extracted/denormalized fields for indexing and querying
    episode_title TEXT,
    episode_description TEXT,
    episode_summary TEXT,  -- Short summary from metadata
    episode_shownotes TEXT,  -- Full show notes/detailed description
    episode_url TEXT,
    publication_date TEXT,  -- ISO8601
    duration INTEGER,  -- seconds

    -- Status tracking
    metadata_exists INTEGER DEFAULT 0,  -- boolean: has .info.json file
    media_exists INTEGER DEFAULT 1,  -- boolean: media file exists

    UNIQUE(media_path)
);

-- Full-text search index on title, description, summary, and shownotes
CREATE VIRTUAL TABLE episode_downloads_fts USING fts5(
    episode_title,
    episode_description,
    episode_summary,
    episode_shownotes,
    podcast_title,
    content=episode_downloads,
    content_rowid=rowid
);

-- Triggers to keep FTS in sync
CREATE TRIGGER episode_downloads_ai AFTER INSERT ON episode_downloads BEGIN
    INSERT INTO episode_downloads_fts(rowid, episode_title, episode_description, episode_summary, episode_shownotes, podcast_title)
    VALUES (new.rowid, new.episode_title, new.episode_description, new.episode_summary, new.episode_shownotes, new.podcast_title);
END;

CREATE TRIGGER episode_downloads_ad AFTER DELETE ON episode_downloads BEGIN
    DELETE FROM episode_downloads_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER episode_downloads_au AFTER UPDATE ON episode_downloads BEGIN
    UPDATE episode_downloads_fts
    SET episode_title = new.episode_title,
        episode_description = new.episode_description,
        episode_summary = new.episode_summary,
        episode_shownotes = new.episode_shownotes,
        podcast_title = new.podcast_title
    WHERE rowid = new.rowid;
END;

-- Indexes for common queries
CREATE INDEX idx_episode_downloads_podcast ON episode_downloads(podcast_title);
CREATE INDEX idx_episode_downloads_pubdate ON episode_downloads(publication_date DESC);
CREATE INDEX idx_episode_downloads_modified ON episode_downloads(modified_time DESC);
```

**Schema Integration Strategy:**
- Add new methods to existing `Datastore` class rather than creating separate database
- Extend `_prepare_db()` to create the new table and indexes
- Follow existing patterns for FTS and column naming

### 2. Module Structure

**New Module: `src/retrocast/episode_scanner.py`**

Purpose: Scan filesystem and extract episode metadata

Key Components:
```python
@dataclass
class EpisodeFileInfo:
    """Represents discovered episode files on disk."""
    media_path: Path
    podcast_title: str
    episode_filename: str
    file_size: int
    modified_time: datetime
    metadata_path: Path | None
    metadata_exists: bool

class EpisodeScanner:
    """Scans episode_downloads directory for media and metadata."""

    def __init__(self, downloads_dir: Path):
        self.downloads_dir = downloads_dir
        self.supported_extensions = {'.mp3', '.m4a', '.ogg', '.opus'}

    def scan(self) -> list[EpisodeFileInfo]:
        """Discover all episode files in downloads directory."""

    def read_metadata(self, info_json_path: Path) -> dict:
        """Parse .info.json file and return metadata."""

    def extract_fields(self, metadata: dict) -> dict:
        """Extract key fields from metadata for database columns.

        Extracts: title, description, summary, shownotes, url,
        publication_date, duration from various possible JSON field names.
        """
```

**Enhanced Module: `src/retrocast/datastore.py`**

Add new methods to existing `Datastore` class:

```python
class Datastore:
    # ... existing methods ...

    def ensure_episode_downloads_table(self) -> None:
        """Create episode_downloads table and indexes if not exists."""

    def upsert_episode_download(self, episode_info: dict) -> None:
        """Insert or update episode download record."""

    def upsert_episode_downloads_batch(self, episodes: list[dict]) -> None:
        """Batch insert/update episode downloads."""

    def get_episode_downloads(
        self,
        podcast_title: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Query episode downloads with optional filters."""

    def mark_missing_episodes(self, existing_paths: set[str]) -> int:
        """Mark episodes as media_exists=0 if not in existing_paths."""

    def search_episode_downloads(self, query: str) -> list[dict]:
        """Full-text search across episode titles/descriptions."""
```

**New Module: `src/retrocast/episode_db_commands.py`**

Purpose: CLI commands for episode database management

Structure:
```python
@click.group(name="db")
def episode_db():
    """Manage downloaded episodes database."""
    pass

@episode_db.command()
@click.option("--dry-run", is_flag=True)
def init(dry_run: bool):
    """Initialize episode downloads database schema."""

@episode_db.command()
@click.option("--rescan", is_flag=True)
@click.option("--verify", is_flag=True)
def update(rescan: bool, verify: bool):
    """Update episode downloads database from filesystem."""

@episode_db.command()
@click.argument("query")
@click.option("--podcast", help="Filter by podcast title")
@click.option("--limit", type=int, default=20)
def search(query: str, podcast: str | None, limit: int):
    """Search episode downloads."""
```

### 3. CLI Integration

**Modify:** `src/retrocast/cli.py`

```python
# Add import
from retrocast.episode_db_commands import episode_db

# In _attach_podcast_archiver_passthroughs():
# Add default for --write-info-json
# This requires modifying the podcast-archiver command invocation
# to inject --write-info-json if not already specified

# Register db subgroup under download group
download_command = cli.commands.get("download")
download_command.add_command(episode_db)
```

**Resulting CLI Structure:**
```
retrocast download aria              # existing
retrocast download podcast-archiver  # existing
retrocast download db init           # NEW
retrocast download db update         # NEW
retrocast download db search         # NEW
```

### 4. Podcast-Archiver Integration

**Modify:** `src/retrocast/cli.py` in `_attach_podcast_archiver_passthroughs()`

Current behavior: Passes through all args to podcast-archiver CLI

Required change: Inject `--write-info-json` into args if not present

Implementation approach:
```python
# In podcast_archiver_passthrough function:
# Check if --write-info-json or --no-write-info-json in ctx.args
# If neither present, inject --write-info-json into ctx.args
# This ensures info.json files are created by default
```

Alternative approach:
- Modify podcast-archiver config file (`podcast_archiver.yaml`)
- Set `write_info_json: true` in default config
- More maintainable, respects user config overrides

**Recommendation:** Use config file approach for cleaner separation

## Implementation Phases

### Phase 1: Database Schema & Core Models
**Estimated Complexity:** Low-Medium
**Status:** ✅ COMPLETED

- [x] Extend `Datastore._prepare_db()` to create `episode_downloads` table
- [x] Add FTS virtual table and triggers
- [x] Add indexes for common queries
- [x] Add new methods to `Datastore` class:
  - [x] `ensure_episode_downloads_table()`
  - [x] `upsert_episode_download()`
  - [x] `upsert_episode_downloads_batch()`
  - [x] `get_episode_downloads()`
  - [x] `mark_missing_episodes()`
  - [x] `search_episode_downloads()`
- [ ] Write unit tests for database operations
- [ ] Verify schema with manual SQL queries

**Implementation Notes (2025-12-11):**
- Added `episode_downloads` table creation to `Datastore._prepare_db()` method
- Implemented FTS5 virtual table with triggers for automatic sync
- Created indexes on podcast_title, publication_date, and modified_time
- Added all 6 required methods to Datastore class
- All methods follow existing codebase patterns and conventions

**Acceptance Criteria:**
- `episode_downloads` table created on database init
- FTS search returns relevant results
- Batch upsert handles 100+ episodes efficiently
- Tests cover edge cases (missing metadata, duplicates)

### Phase 2: Filesystem Scanner
**Estimated Complexity:** Medium

- [ ] Create `src/retrocast/episode_scanner.py`
- [ ] Implement `EpisodeFileInfo` dataclass
- [ ] Implement `EpisodeScanner.scan()`:
  - [ ] Walk `episode_downloads/` directory tree
  - [ ] Identify podcast folders (depth 1)
  - [ ] Find media files (.mp3, .m4a, etc.)
  - [ ] Pair media with .info.json files
  - [ ] Extract file metadata (size, mtime)
  - [ ] Handle missing/malformed metadata gracefully
- [ ] Implement `EpisodeScanner.read_metadata()`:
  - [ ] Parse JSON files
  - [ ] Handle encoding issues
  - [ ] Validate JSON structure
- [ ] Implement `EpisodeScanner.extract_fields()`:
  - [ ] Map info.json fields to database columns (title, description, summary, shownotes, url, date, duration)
  - [ ] Handle various metadata field name variations (see Metadata Field Mapping section)
  - [ ] Normalize dates to ISO8601
  - [ ] Sanitize HTML in text fields where needed
- [ ] Write unit tests with fixture files
- [ ] Test with actual downloaded episodes

**Acceptance Criteria:**
- Scanner discovers all media files in test directory
- Correctly pairs media with metadata files
- Handles missing metadata gracefully
- Extracts common fields (title, description, summary, shownotes, url, date, duration)
- Performance: Scans 1000+ files in <5 seconds

### Phase 3: CLI Commands
**Estimated Complexity:** Medium

- [ ] Create `src/retrocast/episode_db_commands.py`
- [ ] Implement `episode_db` group
- [ ] Implement `init` command:
  - [ ] Call `Datastore.ensure_episode_downloads_table()`
  - [ ] Display schema confirmation
  - [ ] Support --dry-run flag
  - [ ] Show table/index creation messages
- [ ] Implement `update` command:
  - [ ] Get app_dir and downloads path
  - [ ] Instantiate `EpisodeScanner`
  - [ ] Scan filesystem for episodes
  - [ ] Batch insert/update to database
  - [ ] Mark missing episodes
  - [ ] Display progress (use rich progress bar)
  - [ ] Show summary statistics
  - [ ] Support --rescan (delete and rebuild)
  - [ ] Support --verify (check file existence)
- [ ] Implement `search` command:
  - [ ] Accept search query
  - [ ] Call `Datastore.search_episode_downloads()`
  - [ ] Display results in table format (use rich.Table)
  - [ ] Support --podcast filter
  - [ ] Support --limit
- [ ] Write CLI integration tests
- [ ] Update help text and documentation

**Acceptance Criteria:**
- `retrocast download db init` creates schema
- `retrocast download db update` indexes all episodes
- Progress bar shows during scan
- Summary shows: found, updated, missing counts
- `retrocast download db search "python"` returns relevant episodes
- Commands handle errors gracefully (missing dir, permission issues)

### Phase 4: Podcast-Archiver Default Configuration
**Estimated Complexity:** Low

- [ ] Analyze podcast-archiver config structure
- [ ] Determine best approach:
  - [ ] Option A: Modify default config file generation
  - [ ] Option B: Inject CLI argument in passthrough
  - [ ] Option C: Document manual config change
- [ ] Implement chosen approach
- [ ] Test that .info.json files are created by default
- [ ] Update documentation
- [ ] Verify backward compatibility

**Acceptance Criteria:**
- New podcast-archiver downloads create .info.json by default
- Existing workflow unaffected if user has custom config
- User can still override with --no-write-info-json
- Change documented in README or CHANGELOG

### Phase 5: Integration & Documentation
**Estimated Complexity:** Low-Medium

- [ ] Integrate `episode_db` group into main CLI
- [ ] Register commands in `cli.py`
- [ ] Test complete workflow:
  - [ ] Download episodes with podcast-archiver
  - [ ] Run `download db init`
  - [ ] Run `download db update`
  - [ ] Verify data in database
  - [ ] Run search queries
- [ ] Write user documentation:
  - [ ] Add section to README
  - [ ] Provide usage examples
  - [ ] Document search syntax
  - [ ] Explain metadata schema
- [ ] Write developer documentation:
  - [ ] Update AGENTS.md with new modules
  - [ ] Document database schema
  - [ ] Provide extension examples
- [ ] Add logging throughout:
  - [ ] Scanner progress
  - [ ] Database operations
  - [ ] Error conditions
- [ ] Performance testing:
  - [ ] Test with 500+ episodes
  - [ ] Measure scan time
  - [ ] Measure search performance
- [ ] Update pre-commit hooks if needed

**Acceptance Criteria:**
- Full workflow executes without errors
- README includes "Episode Database" section
- AGENTS.md reflects new architecture
- All operations properly logged
- Performance acceptable for typical podcast library (500-1000 episodes)

### Phase 6: Optional Enhancements
**Estimated Complexity:** Variable

Consider for future iterations:

- [ ] Add `download db stats` command for analytics
- [ ] Add `download db export` to export JSON/CSV
- [ ] Add `download db deduplicate` for cleanup
- [ ] Add `download db validate` to check integrity
- [ ] Add correlation with existing `episodes` table
- [ ] Add playback status tracking
- [ ] Add custom metadata fields
- [ ] Add web UI via Datasette plugin
- [ ] Add automatic indexing on download completion

## Technical Considerations

### Error Handling

1. **Missing Downloads Directory**
   - Detection: Check if `episode_downloads/` exists
   - Action: Create directory or show helpful error

2. **Malformed JSON Metadata**
   - Detection: Try/except on JSON parsing
   - Action: Log warning, store null in metadata_json, continue

3. **File Permission Issues**
   - Detection: OSError on file access
   - Action: Log error with file path, skip file, continue scan

4. **Database Lock**
   - Detection: sqlite3.OperationalError
   - Action: Retry with exponential backoff, or fail gracefully

5. **Orphaned Metadata**
   - Detection: .info.json without matching media
   - Action: Log info, don't insert to database

### Performance Optimization

1. **Batch Database Operations**
   - Use `upsert_all()` instead of individual upserts
   - Batch size: 100-500 records

2. **Filesystem Scanning**
   - Use `os.scandir()` instead of `glob()` for better performance
   - Limit recursion depth to 2 (podcast/episode)
   - Cache file stats to avoid duplicate stat calls

3. **FTS Rebuilding**
   - Use FTS5 `rebuild` command for initial large imports
   - Rely on triggers for incremental updates

4. **Incremental Updates**
   - Track `last_verified_time` to avoid re-scanning unchanged files
   - Use mtime comparison to detect changes
   - Implement `--quick` mode that skips verification

### Data Consistency

1. **File Move/Rename Detection**
   - Current approach: Treat as delete + new insert
   - Future: Could use file hash for deduplication

2. **Duplicate Episodes**
   - Primary key on `media_path` prevents duplicates
   - Different file paths for same episode will create separate records

3. **Deleted Files**
   - Mark `media_exists=0` rather than delete from database
   - Preserves history and allows recovery

4. **Schema Migrations**
   - Follow existing pattern in codebase
   - Use `alter=True` for new columns
   - No formal migration framework currently

### Metadata Field Mapping

The `.info.json` files created by podcast-archiver may contain various field names depending on the source and downloader version. The scanner should handle multiple possible field names:

1. **Summary Field**
   - Common JSON keys: `summary`, `subtitle`, `itunes_summary`
   - Typically a short one-line description (< 200 chars)
   - Falls back to truncated description if not present

2. **Shownotes Field**
   - Common JSON keys: `description`, `content`, `shownotes`, `long_description`
   - Full episode notes, often HTML formatted
   - May contain links, formatting, timestamps

3. **Title Field**
   - Common JSON keys: `title`, `episode`, `episode_title`

4. **Description Field**
   - Common JSON keys: `description`, `subtitle` (if no dedicated description)
   - Medium-length description

5. **Other Fields**
   - `url`, `webpage_url`, `original_url` → episode_url
   - `upload_date`, `release_date`, `pubDate` → publication_date
   - `duration` (in seconds)

**Field Priority Strategy:**
- If multiple candidates exist, prefer more specific fields
- Store original JSON metadata for reference
- Sanitize HTML in text fields for display
- Normalize empty strings to NULL

### Testing Strategy

1. **Unit Tests**
   - Test `EpisodeScanner` with fixture directory
   - Test `Datastore` methods with in-memory database
   - Test metadata extraction with sample JSON

2. **Integration Tests**
   - Test CLI commands end-to-end
   - Test with realistic directory structure
   - Test error conditions

3. **Fixtures**
   - Create `tests/fixtures/episode_downloads/` with sample files
   - Include: valid episodes, malformed JSON, missing metadata
   - Test various metadata field combinations (with/without summary, with/without shownotes)
   - Include HTML in shownotes to test sanitization
   - Use small audio files or mock files

4. **Manual Testing Checklist**
   - Download real podcast episodes
   - Verify metadata extraction
   - Test search functionality
   - Test rescan behavior
   - Test with large library (100+ episodes)

## Dependencies

### New Dependencies
None required - all functionality can be implemented with existing dependencies:
- `sqlite-utils` (existing): Database operations
- `click` (existing): CLI framework
- `rich` (existing): Console output and progress bars
- `loguru` (existing): Logging

### Modified Files
- `src/retrocast/datastore.py` (extend)
- `src/retrocast/cli.py` (modify)
- `src/retrocast/download_commands.py` (extend)

### New Files
- `src/retrocast/episode_scanner.py` (create)
- `src/retrocast/episode_db_commands.py` (create)
- `tests/test_episode_scanner.py` (create)
- `tests/test_episode_db_commands.py` (create)
- `tests/fixtures/episode_downloads/...` (create)

## Success Metrics

### Functional Requirements Met
- ✓ Episode metadata stored in `retrocast.db`
- ✓ JSON data preserved in database
- ✓ File paths and timestamps tracked
- ✓ Full-text search enabled
- ✓ CLI commands functional
- ✓ Default metadata generation enabled

### Quality Metrics
- Test coverage >80% for new code
- No performance degradation for existing commands
- Scan 500 episodes in <10 seconds
- Search returns results in <1 second
- Zero data loss during updates

### User Experience
- Clear progress indication during operations
- Helpful error messages
- Comprehensive help text
- Examples in documentation
- Works with existing podcast-archiver workflow

## Rollout Plan

### Pre-Release
1. Complete Phases 1-4
2. Run full test suite
3. Manual testing with real data
4. Code review
5. Update documentation

### Release
1. Merge to main branch
2. Tag version (e.g., v0.5.0)
3. Update CHANGELOG
4. Announce in README

### Post-Release
1. Monitor for issues
2. Gather user feedback
3. Consider Phase 6 enhancements
4. Iterate based on usage patterns

## Open Questions

1. **Schema Design**
   - Q: Should we deduplicate based on episode URL or GUID?
   - A: Recommendation - Use file path as PK, allow duplicates for now

2. **Podcast-Archiver Integration**
   - Q: Modify config file or inject CLI args?
   - A: Recommendation - Config file for cleaner approach

3. **Existing Episodes Table**
   - Q: Should we join with existing `episodes` table from Overcast?
   - A: Recommendation - Phase 6 enhancement, not required for MVP

4. **Incremental vs Full Scan**
   - Q: Always rescan all files or track last scan time?
   - A: Recommendation - Full scan for MVP, add `--quick` mode later

5. **Search Scope**
   - Q: Search episode_downloads only or join with other tables?
   - A: Recommendation - Episode downloads only for MVP

## Risk Assessment

### Low Risk
- Database schema addition (follows existing patterns)
- CLI command addition (isolated feature)
- Filesystem scanning (read-only operation)

### Medium Risk
- FTS performance with large datasets (mitigated by indexes)
- JSON parsing edge cases (mitigated by error handling)
- Podcast-archiver default change (mitigated by user override)

### High Risk
- None identified

## Timeline Estimate

**Total: 3-5 days of focused development**

- Phase 1: 0.5-1 day
- Phase 2: 1-1.5 days
- Phase 3: 1-1.5 days
- Phase 4: 0.5 day
- Phase 5: 0.5-1 day

Note: Timeline assumes familiarity with codebase and no major blockers

## References

- Original requirements: `plans/episodes_database.md`
- Existing datastore: `src/retrocast/datastore.py`
- Download commands: `src/retrocast/download_commands.py`
- CLI structure: `src/retrocast/cli.py`
- Architecture guide: `AGENTS.md`

---

**Next Steps:**
1. Review this plan with stakeholders
2. Address open questions
3. Approve Phase 1 implementation
4. Begin development following checklist
