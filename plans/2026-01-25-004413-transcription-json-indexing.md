# Transcription JSON File Indexing Implementation Plan

**Created:** 2026-01-25 00:44:13 UTC  
**Author:** Copilot Agent  
**Related Feature:** castchat (AI-powered podcast exploration)

## Overview

This plan outlines the implementation for indexing transcription JSON files directly into ChromaDB for the `castchat` feature. Currently, castchat indexes from the SQLite database (`transcription_segments` table). This enhancement will add the ability to index directly from JSON transcription files stored on disk, enabling users to explore transcriptions even if they haven't been ingested into the database yet.

## Background

### Current Architecture

1. **Transcription Flow:**
   - Audio files → Transcription Backend (MLX/faster-whisper) → `TranscriptionResult`
   - Results saved in multiple formats (JSON, TXT, SRT, VTT) to disk
   - Results saved to SQLite database (`transcriptions` + `transcription_segments` tables)
   - JSON format contains: text, language, duration, word_count, segment_count, speakers, segments, metadata

2. **castchat Current Indexing:**
   - Reads from `transcription_segments` table joined with `transcriptions` table
   - Indexes segment text with metadata into ChromaDB
   - Requires database to be populated

### Problem Statement

Users may have transcription JSON files but haven't loaded them into the database. We need to support:
- Indexing directly from JSON files in a directory tree
- Discovering JSON files in `output_dir` structure (organized by podcast/episode)
- Loading and parsing JSON transcription format
- Indexing segments with equivalent metadata as database approach
- Incremental indexing (skip already-indexed files)
- Option to rebuild index from JSON files

## Goals

1. ✅ Support indexing from JSON files as an alternative to database
2. ✅ Maintain compatibility with existing database indexing
3. ✅ Enable hybrid approach (index from both sources)
4. ✅ Provide CLI options for JSON-based indexing
5. ✅ Track indexed files to avoid re-processing
6. ✅ Preserve metadata fidelity between JSON and database approaches

## Technical Design

### 1. JSON File Discovery

**Component:** `TranscriptionJSONScanner`  
**Location:** `src/retrocast/transcription_json_scanner.py`

**Responsibilities:**
- Scan directory tree for `*.json` transcription files
- Filter files by JSON structure (must match transcription format)
- Extract metadata from file path and content
- Return list of discovered transcription files

**Directory Structure:**
```
output_dir/
├── Podcast Name A/
│   ├── Episode 1.json
│   ├── Episode 2.json
│   └── ...
├── Podcast Name B/
│   └── Episode X.json
└── ...
```

**Scanner Methods:**
```python
class TranscriptionJSONScanner:
    def __init__(self, base_dir: Path)
    def scan(self) -> list[TranscriptionFile]
    def is_valid_transcription_json(self, path: Path) -> bool
    def parse_transcription_json(self, path: Path) -> dict
    def extract_metadata_from_path(self, path: Path) -> dict
```

### 2. JSON Indexing Integration

**Component:** `ChromaDBManager` enhancements  
**Location:** `src/retrocast/chromadb_manager.py`

**New Methods:**
```python
def index_from_json_files(
    self, 
    json_dir: Path, 
    batch_size: int = 100,
    force: bool = False
) -> int:
    """Index transcription segments from JSON files."""

def index_from_json_file(
    self, 
    json_path: Path,
    podcast_title: str | None = None,
    episode_title: str | None = None
) -> int:
    """Index a single JSON file."""

def is_file_indexed(self, file_path: Path) -> bool:
    """Check if JSON file has already been indexed."""

def mark_file_indexed(self, file_path: Path, file_hash: str) -> None:
    """Mark JSON file as indexed."""
```

**Index Tracking:**
- Store indexed file paths and hashes in ChromaDB metadata
- Use collection-level metadata or separate tracking collection
- Enable incremental updates (only index new/changed files)

### 3. Unified Indexing Interface

**Enhanced Method:**
```python
def index_transcriptions(
    self,
    datastore: Datastore | None = None,
    json_dir: Path | None = None,
    batch_size: int = 100,
    force: bool = False,
    source: str = "auto"  # "auto", "database", "json", "both"
) -> dict[str, int]:
    """Index from database, JSON files, or both.
    
    Returns:
        Dict with counts: {"database": N, "json": M, "total": N+M}
    """
```

### 4. CLI Enhancement

**Component:** `castchat` command in `cli.py`

**New Options:**
```python
@cli.command()
@click.option("--json-dir", type=Path, help="Directory containing JSON transcription files")
@click.option("--index-source", type=click.Choice(["auto", "database", "json", "both"]), 
              default="auto", help="Source for indexing")
@click.option("--force-reindex", is_flag=True, help="Force re-indexing of all files")
def castchat(...):
    """Enhanced with JSON indexing support"""
```

**Behavior:**
- `--index-source auto`: Use database if available, fallback to JSON
- `--index-source database`: Only index from database (current behavior)
- `--index-source json`: Only index from JSON files in `--json-dir`
- `--index-source both`: Index from both sources (union)
- If `--json-dir` not specified, use transcription output directory from config

### 5. File Hash Tracking

**Approach:**
Store indexed file metadata in ChromaDB collection metadata:

```python
{
    "indexed_files": {
        "/path/to/file.json": {
            "hash": "sha256...",
            "indexed_at": "2026-01-25T00:44:13Z",
            "segment_count": 42
        },
        ...
    }
}
```

Or use separate tracking collection:
```python
collection = client.get_or_create_collection("transcription_file_index")
# Store file path as ID, hash in metadata
```

### 6. Error Handling

**Scenarios to Handle:**
- Invalid JSON format
- Missing required fields
- Corrupted files
- Permission errors
- Mixed database + JSON conflicts (same episode in both)

**Strategy:**
- Log warnings for invalid files, continue processing
- Provide summary of successful/failed indexing
- Option to skip or overwrite duplicates

## Implementation Checklist

### Phase 1: JSON Scanner (Foundation)
- [ ] Create `src/retrocast/transcription_json_scanner.py`
- [ ] Implement `TranscriptionJSONScanner` class
  - [ ] `scan()` method to walk directory tree
  - [ ] `is_valid_transcription_json()` validator
  - [ ] `parse_transcription_json()` parser
  - [ ] `extract_metadata_from_path()` helper
- [ ] Add unit tests for scanner
  - [ ] Test directory scanning
  - [ ] Test JSON validation
  - [ ] Test metadata extraction
  - [ ] Test error handling

### Phase 2: ChromaDB Integration
- [ ] Enhance `src/retrocast/chromadb_manager.py`
  - [ ] Add `index_from_json_file()` method
  - [ ] Add `index_from_json_files()` method
  - [ ] Add file tracking functionality
    - [ ] `is_file_indexed()` method
    - [ ] `mark_file_indexed()` method
    - [ ] `get_indexed_files()` method
  - [ ] Refactor `index_transcriptions()` for unified interface
- [ ] Add unit tests for JSON indexing
  - [ ] Test single file indexing
  - [ ] Test batch directory indexing
  - [ ] Test incremental updates
  - [ ] Test duplicate handling
  - [ ] Test file tracking

### Phase 3: CLI Enhancement
- [ ] Update `src/retrocast/cli.py`
  - [ ] Add `--json-dir` option to `castchat` command
  - [ ] Add `--index-source` option
  - [ ] Add `--force-reindex` flag
  - [ ] Update help text with JSON examples
  - [ ] Add validation for option combinations
- [ ] Update progress display for JSON indexing
  - [ ] Show "Scanning JSON files..." status
  - [ ] Show file count and progress
  - [ ] Show indexed vs skipped counts

### Phase 4: Documentation
- [ ] Update `docs/CASTCHAT.md`
  - [ ] Add "Indexing from JSON Files" section
  - [ ] Add examples for JSON-based workflow
  - [ ] Document `--json-dir` and `--index-source` options
  - [ ] Add troubleshooting for JSON issues
- [ ] Update `README.md`
  - [ ] Add JSON indexing to castchat section
  - [ ] Add example commands
- [ ] Update docstrings
  - [ ] `ChromaDBManager` class
  - [ ] New scanner class
  - [ ] CLI command

### Phase 5: Testing & Validation
- [ ] Create test fixtures
  - [ ] Sample JSON transcription files
  - [ ] Directory structure with multiple podcasts
  - [ ] Edge cases (empty, malformed, etc.)
- [ ] Integration tests
  - [ ] Test full JSON indexing workflow
  - [ ] Test hybrid database + JSON indexing
  - [ ] Test CLI commands end-to-end
- [ ] Manual testing
  - [ ] Index real transcription directory
  - [ ] Verify search results match database approach
  - [ ] Test incremental updates

### Phase 6: Quality & Security
- [ ] Run linting (ruff check/format)
- [ ] Run type checking (mypy)
- [ ] Run all tests (pytest)
- [ ] Check for security issues (no new dependencies)
- [ ] Request code review
- [ ] Run codeql_checker

## Edge Cases & Considerations

### 1. Duplicate Detection
**Issue:** Same episode in both database and JSON file  
**Solution:** Use file path or episode URL as deduplication key. Option to skip or prefer specific source.

### 2. Metadata Consistency
**Issue:** JSON may have different or missing metadata vs database  
**Solution:** Standardize metadata extraction. Use defaults for missing fields.

### 3. Large Directories
**Issue:** Thousands of JSON files may take time to scan  
**Solution:** Progress indicators, batch processing, caching of file list

### 4. File Modifications
**Issue:** JSON file updated after initial indexing  
**Solution:** Track file hash, re-index if changed (unless `--force-reindex`)

### 5. Mixed Sources
**Issue:** Some episodes in DB, some in JSON only  
**Solution:** Support union indexing with `--index-source both`

## Success Criteria

1. ✅ Users can run `retrocast castchat --json-dir ~/transcriptions` without database
2. ✅ JSON indexing produces equivalent search results to database indexing
3. ✅ Incremental updates work correctly (only new files indexed)
4. ✅ All existing tests continue to pass
5. ✅ New tests achieve >80% coverage of new code
6. ✅ Documentation clearly explains JSON workflow
7. ✅ No performance regression for database indexing path

## Timeline Estimate

- **Phase 1 (Scanner):** 2-3 hours
- **Phase 2 (ChromaDB):** 3-4 hours
- **Phase 3 (CLI):** 1-2 hours
- **Phase 4 (Docs):** 1-2 hours
- **Phase 5 (Testing):** 2-3 hours
- **Phase 6 (QA):** 1 hour

**Total:** 10-15 hours of development time

## Dependencies

**No new dependencies required** - uses existing:
- `pathlib` for file system operations
- `json` for JSON parsing
- `hashlib` for file hashing
- `chromadb` (already in castchat extras)

## Future Enhancements

- [ ] Support other transcription formats (e.g., SRT, VTT) for indexing
- [ ] Watch mode: automatically index new JSON files as they're created
- [ ] CLI command to show indexed files: `retrocast castchat index list`
- [ ] CLI command to remove specific files from index
- [ ] Support for remote JSON files (S3, HTTP)
- [ ] Parallel file processing for faster indexing
- [ ] Delta indexing: only add new segments from modified files

## Related Files

**New Files:**
- `src/retrocast/transcription_json_scanner.py` - JSON file scanner
- `tests/test_transcription_json_scanner.py` - Scanner tests
- `tests/test_json_indexing.py` - JSON indexing integration tests

**Modified Files:**
- `src/retrocast/chromadb_manager.py` - Add JSON indexing methods
- `src/retrocast/cli.py` - Add CLI options for JSON indexing
- `docs/CASTCHAT.md` - Add JSON indexing documentation
- `README.md` - Update castchat examples
- `tests/test_castchat.py` - Add JSON indexing tests

## Notes

- This enhancement maintains backward compatibility with existing database-only workflow
- JSON indexing can serve as backup/recovery mechanism if database is lost
- Enables "offline" exploration of transcriptions without full retrocast setup
- Provides foundation for future distributed/cloud-based transcription workflows

## References

- Original castchat implementation: commits `c83331b` and `500ece8`
- Transcription output format: `src/retrocast/transcription/output_formats.py`
- Current ChromaDB indexing: `src/retrocast/chromadb_manager.py:index_transcriptions()`
- JSON format spec: lines 68-102 in `output_formats.py`
