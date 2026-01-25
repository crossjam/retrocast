# Transcription JSON File Indexing Implementation Plan

**Created:** 2026-01-25 00:44:13 UTC  
**Updated:** 2026-01-25 00:47:12 UTC  
**Author:** Copilot Agent  
**Related Feature:** castchat (AI-powered podcast exploration)

## Overview

This plan outlines the implementation for indexing transcription JSON files directly into **ChromaDB** (vector database) for the `castchat` feature, using **Chonkie** (lightweight chunking library) for intelligent text segmentation. Currently, castchat indexes from the SQLite database (`transcription_segments` table). This enhancement will add the ability to index directly from JSON transcription files stored on disk, enabling users to explore transcriptions even if they haven't been ingested into the database yet.

### Key Technologies

- **ChromaDB**: Vector database for semantic search and RAG (already integrated)
- **Chonkie**: Lightweight, fast chunking library for intelligent text segmentation into optimal chunks for embedding

## Why Chonkie?

Chonkie is the ideal chunking library for this implementation for several reasons:

1. **Lightweight & Fast**
   - Only 505KB package size (vs 1-12MB for alternatives)
   - 33x faster than slowest alternative for token chunking
   - 2.5x faster for semantic chunking
   - Perfect fit for retrocast's lean philosophy

2. **Purpose-Built for RAG**
   - Designed specifically for retrieval-augmented generation pipelines
   - Optimized chunk sizes for embeddings and search
   - Multiple strategies for different use cases

3. **Easy Integration**
   - Simple API: `chunker = RecursiveChunker()` → `chunks = chunker(text)`
   - Minimal dependencies (just tqdm and numpy)
   - No conflicts with existing retrocast stack

4. **ChromaDB Integration**
   - Works seamlessly with ChromaDB (already in use)
   - Chunks → documents → vectors workflow
   - Metadata preservation

5. **Flexible Chunking Strategies**
   - **RecursiveChunker**: Fast, hierarchical, semantically meaningful
   - **SemanticChunker**: Groups by similarity (best for search quality)
   - **TokenChunker**: Fixed-size fallback
   - **SentenceChunker**: Natural sentence boundaries

6. **Production Ready**
   - Well-documented (docs.chonkie.ai)
   - Active development and community
   - Used in production RAG systems

### Comparison: Database Segments vs Chonkie Chunks

| Aspect | Database Segments | Chonkie Chunks |
|--------|------------------|----------------|
| Source | Pre-segmented by transcription backend | Intelligently chunked from full text |
| Size | Fixed by backend (often very short) | Optimized for embedding (configurable) |
| Semantics | May split mid-thought | Respects semantic boundaries |
| Quality | Depends on transcription backend | Consistently high for RAG |
| Overlap | None | Configurable overlap for context |
| Speed | Fast (already segmented) | Still fast (33x faster than alternatives) |

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

### Example Usage with Chonkie

```python
from chonkie import RecursiveChunker, SemanticChunker
from retrocast.chromadb_manager import ChromaDBManager
from pathlib import Path

# Initialize ChromaDB manager
manager = ChromaDBManager(persist_directory=Path("~/.retrocast/chromadb"))

# Index from JSON with recursive chunking (default)
count = manager.index_from_json_files(
    json_dir=Path("~/transcriptions"),
    chunking_strategy="recursive",
    chunk_size=512,
    overlap=50
)
print(f"Indexed {count} chunks")

# Or use semantic chunking for better search quality
count = manager.index_from_json_files(
    json_dir=Path("~/transcriptions"),
    chunking_strategy="semantic",
    chunk_size=512
)

# Or use existing segments from JSON (no Chonkie)
count = manager.index_from_json_files(
    json_dir=Path("~/transcriptions"),
    chunking_strategy="segments"  # Use pre-segmented chunks
)
```

### 2. JSON Indexing Integration with Chonkie

**Component:** `ChromaDBManager` enhancements with Chonkie chunking  
**Location:** `src/retrocast/chromadb_manager.py`

**Why Chonkie?**
- **Intelligent Chunking**: Unlike fixed-size segments from database, Chonkie provides semantic chunking
- **Optimized for RAG**: Chunks are sized and structured for optimal embedding and retrieval
- **Lightweight**: Minimal dependencies, fast performance (33x faster than alternatives)
- **Multiple Strategies**: Supports recursive, semantic, and sentence-based chunking

**Chunking Strategy:**
When indexing from JSON files, use Chonkie to intelligently chunk the full transcript text:
- **RecursiveChunker**: Split hierarchically for semantically meaningful chunks
- **SemanticChunker**: Group based on semantic similarity (better for search)
- **Fallback to segments**: If JSON has pre-segmented chunks, use those directly

**New Methods:**
```python
def index_from_json_files(
    self, 
    json_dir: Path, 
    batch_size: int = 100,
    force: bool = False,
    chunking_strategy: str = "recursive"  # "recursive", "semantic", "segments"
) -> int:
    """Index transcription segments from JSON files using Chonkie chunking.
    
    Args:
        json_dir: Directory containing JSON transcription files
        batch_size: Number of segments to process per batch
        force: If True, re-index already-indexed files
        chunking_strategy: Strategy for chunking text
            - "recursive": Chonkie RecursiveChunker (hierarchical)
            - "semantic": Chonkie SemanticChunker (similarity-based)
            - "segments": Use existing segments from JSON
    
    Returns:
        Number of chunks indexed
    """

def index_from_json_file(
    self, 
    json_path: Path,
    podcast_title: str | None = None,
    episode_title: str | None = None,
    chunking_strategy: str = "recursive"
) -> int:
    """Index a single JSON file with Chonkie chunking."""

def _chunk_with_chonkie(
    self,
    text: str,
    strategy: str,
    chunk_size: int = 512,
    overlap: int = 50
) -> list[dict]:
    """Chunk text using Chonkie library.
    
    Args:
        text: Full transcript text to chunk
        strategy: Chunking strategy ("recursive" or "semantic")
        chunk_size: Target chunk size in tokens
        overlap: Overlap between chunks in tokens
        
    Returns:
        List of chunks with text and metadata
    """
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

### Phase 1: Dependencies & Setup
- [ ] Add Chonkie to dependencies
  - [ ] Add `chonkie>=1.5.2` to `castchat` optional group in `pyproject.toml`
  - [ ] Test installation with `pip install retrocast[castchat]`
  - [ ] Run security check with `gh-advisory-database`
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

### Phase 2: ChromaDB Integration with Chonkie
- [ ] Enhance `src/retrocast/chromadb_manager.py`
  - [ ] Add Chonkie imports and initialization
  - [ ] Add `_chunk_with_chonkie()` method
    - [ ] Implement RecursiveChunker strategy
    - [ ] Implement SemanticChunker strategy
    - [ ] Implement fallback to existing segments
  - [ ] Add `index_from_json_file()` method
    - [ ] Parse JSON transcription file
    - [ ] Apply Chonkie chunking strategy
    - [ ] Create ChromaDB documents with metadata
  - [ ] Add `index_from_json_files()` method
    - [ ] Use TranscriptionJSONScanner for discovery
    - [ ] Batch process files
    - [ ] Track indexed files
  - [ ] Add file tracking functionality
    - [ ] `is_file_indexed()` method
    - [ ] `mark_file_indexed()` method
    - [ ] `get_indexed_files()` method
  - [ ] Refactor `index_transcriptions()` for unified interface
    - [ ] Support `source` parameter (auto/database/json/both)
    - [ ] Merge results from multiple sources
- [ ] Add unit tests for JSON indexing
  - [ ] Test Chonkie chunking strategies
  - [ ] Test single file indexing with Chonkie
  - [ ] Test batch directory indexing
  - [ ] Test incremental updates
  - [ ] Test duplicate handling
  - [ ] Test file tracking
  - [ ] Test chunk size and overlap parameters

### Phase 3: CLI Enhancement
- [ ] Update `src/retrocast/cli.py`
  - [ ] Add `--json-dir` option to `castchat` command
  - [ ] Add `--index-source` option
  - [ ] Add `--chunking-strategy` option (recursive/semantic/segments)
  - [ ] Add `--chunk-size` option for Chonkie
  - [ ] Add `--chunk-overlap` option for Chonkie
  - [ ] Add `--force-reindex` flag
  - [ ] Update help text with JSON and Chonkie examples
  - [ ] Add validation for option combinations
- [ ] Update progress display for JSON indexing
  - [ ] Show "Scanning JSON files..." status
  - [ ] Show "Chunking with Chonkie..." status
  - [ ] Show file count and progress
  - [ ] Show indexed vs skipped counts
  - [ ] Show chunk statistics

### Phase 4: Documentation
- [ ] Update `docs/CASTCHAT.md`
  - [ ] Add "Indexing from JSON Files" section
  - [ ] Document Chonkie integration and chunking strategies
  - [ ] Add examples for JSON-based workflow with Chonkie
  - [ ] Document all new CLI options:
    - [ ] `--json-dir` 
    - [ ] `--index-source`
    - [ ] `--chunking-strategy`
    - [ ] `--chunk-size` and `--chunk-overlap`
  - [ ] Add comparison of chunking strategies
  - [ ] Add troubleshooting for JSON and Chonkie issues
- [ ] Update `README.md`
  - [ ] Add JSON indexing to castchat section
  - [ ] Mention Chonkie integration
  - [ ] Add example commands with Chonkie options
- [ ] Update docstrings
  - [ ] `ChromaDBManager` class (Chonkie methods)
  - [ ] New scanner class
  - [ ] CLI command with new options

### Phase 5: Testing & Validation
- [ ] Create test fixtures
  - [ ] Sample JSON transcription files
  - [ ] Directory structure with multiple podcasts
  - [ ] Edge cases (empty, malformed, etc.)
- [ ] Integration tests
  - [ ] Test full JSON indexing workflow with Chonkie
  - [ ] Test different chunking strategies (recursive vs semantic)
  - [ ] Test chunk size variations
  - [ ] Test hybrid database + JSON indexing
  - [ ] Test CLI commands end-to-end
- [ ] Manual testing
  - [ ] Index real transcription directory with Chonkie
  - [ ] Compare search results: database vs JSON w/Chonkie
  - [ ] Verify chunk quality and relevance
  - [ ] Test incremental updates

### Phase 6: Quality & Security
- [ ] Run security check on Chonkie dependency
- [ ] Run linting (ruff check/format)
- [ ] Run type checking (mypy)
- [ ] Run all tests (pytest)
- [ ] Performance benchmarking
  - [ ] Compare Chonkie chunking speeds
  - [ ] Measure indexing time improvements
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

### 6. Chunking Strategy Selection
**Issue:** Different strategies produce different chunk sizes and quality  
**Solution:** 
- Default to `recursive` for speed and general quality
- Allow `semantic` for better retrieval (requires embeddings)
- Provide `segments` fallback to use existing JSON segments

### 7. Chunk Size Optimization
**Issue:** Optimal chunk size varies by use case  
**Solution:**
- Default to 512 tokens (good balance)
- Allow customization via `--chunk-size`
- Document recommended sizes for different scenarios

### 8. ChromaDB Performance
**Issue:** Large numbers of small chunks may impact ChromaDB performance  
**Solution:**
- Batch inserts (already implemented)
- Consider chunk consolidation for very short segments
- Monitor collection size and query latency

## Success Criteria

1. ✅ Users can run `retrocast castchat --json-dir ~/transcriptions` without database
2. ✅ JSON indexing with Chonkie produces high-quality, semantically meaningful chunks
3. ✅ Chonkie chunking improves search relevance compared to fixed-size segments
4. ✅ Multiple chunking strategies (recursive/semantic/segments) work correctly
5. ✅ Incremental updates work correctly (only new files indexed)
6. ✅ All existing tests continue to pass
7. ✅ New tests achieve >80% coverage of new code
8. ✅ Documentation clearly explains JSON workflow and Chonkie options
9. ✅ No performance regression for database indexing path
10. ✅ Chonkie integration adds <2MB to package size

## Timeline Estimate

- **Phase 1 (Dependencies & Scanner):** 2-3 hours
- **Phase 2 (ChromaDB + Chonkie):** 4-5 hours
- **Phase 3 (CLI):** 2 hours
- **Phase 4 (Docs):** 1-2 hours
- **Phase 5 (Testing):** 2-3 hours
- **Phase 6 (QA):** 1 hour

**Total:** 12-16 hours of development time (updated from 10-15 to account for Chonkie integration)

## Dependencies

**New Dependency:**
- `chonkie>=1.5.2` - Lightweight chunking library for intelligent text segmentation

**Existing Dependencies (already in castchat extras):**
- `chromadb>=0.5.23` - Vector database for semantic search
- `pydantic-ai>=0.0.14` - AI agent framework

### Chonkie Installation

Chonkie will be added to the `castchat` optional dependency group:

```toml
# In pyproject.toml
castchat = [
    "chromadb>=0.5.23",
    "pydantic-ai>=0.0.14",
    "chonkie>=1.5.2",
]
```

Users install with:
```bash
pip install retrocast[castchat]
```

### Chonkie Features to Use

1. **RecursiveChunker** (Primary):
   - Hierarchical splitting using customizable rules
   - Creates semantically meaningful chunks
   - Fast and lightweight
   - Good for general transcripts

2. **SemanticChunker** (Optional):
   - Groups text by semantic similarity
   - Better retrieval quality
   - Slightly slower but better for search
   - Requires embeddings

3. **Integration with ChromaDB**:
   - Chonkie chunks → ChromaDB vectors
   - Each chunk becomes a document in ChromaDB
   - Metadata preserved (timestamps, speakers, episode info)

## Future Enhancements

- [ ] Support other transcription formats (e.g., SRT, VTT) for indexing with Chonkie
- [ ] Watch mode: automatically index new JSON files as they're created
- [ ] CLI command to show indexed files: `retrocast castchat index list`
- [ ] CLI command to remove specific files from index
- [ ] Support for remote JSON files (S3, HTTP)
- [ ] Parallel file processing for faster indexing
- [ ] Delta indexing: only add new chunks from modified files
- [ ] Chonkie SemanticChunker with custom embedding models
- [ ] Advanced Chonkie features:
  - [ ] SlumberChunker (LLM-based agentic chunking)
  - [ ] CodeChunker for code-heavy transcripts
  - [ ] Pipeline support for multi-stage chunking
- [ ] Chunk quality metrics and optimization
- [ ] A/B testing different chunking strategies
- [ ] Export Chonkie chunks for analysis/debugging

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
