# Transcription JSON File Indexing Implementation Plan

**Created:** 2026-01-25 00:44:13 UTC  
**Updated:** 2026-01-25 04:50:52 UTC  
**Author:** Copilot Agent  
**Related Feature:** castchat (AI-powered podcast exploration)

## Overview

This plan outlines the implementation for indexing transcription JSON files directly into **ChromaDB** (vector database) for the `castchat` feature, using **Chonkie** (lightweight chunking library) for intelligent text segmentation. Currently, castchat indexes from the SQLite database (`transcription_segments` table). This enhancement will add the ability to index directly from JSON transcription files stored on disk, enabling users to explore transcriptions even if they haven't been ingested into the database yet.

Additionally, this plan includes **SQLite query tools** for the PydanticAI agent to directly query the retrocast SQLite database containing podcast metadata, allowing the agent to answer questions about subscriptions, episodes, playlists, and other structured data beyond just transcription content.

### Key Technologies

- **ChromaDB**: Vector database for semantic search and RAG (already integrated)
- **Chonkie**: Lightweight, fast chunking library for intelligent text segmentation into optimal chunks for embedding
- **sqlite-utils**: Database query and inspection library (already integrated) - will be exposed as agent tools

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

## Why SQLite Query Tools for Agents?

Adding SQLite query capabilities to the PydanticAI agent enables answering questions about structured metadata that complements transcription search:

1. **Hybrid Intelligence**
   - **Semantic Search** (ChromaDB): "What did they say about AI?"
   - **Structured Queries** (SQLite): "How many episodes have I listened to?"
   - **Combined**: "What unplayed episodes discuss machine learning?"

2. **Metadata Access**
   - Podcast subscriptions and feed information
   - Episode metadata (titles, URLs, publish dates, durations)
   - Play history and progress tracking
   - Playlists and organization
   - Download status and file locations

3. **sqlite-utils Advantages**
   - Already integrated into retrocast
   - Safe, read-only query execution
   - Schema discovery (tables, columns, views)
   - Full-text search on indexed fields
   - JSON export for structured results
   - Parameterized queries prevent SQL injection

4. **Agent Tool Design**
   - **query_database**: Execute SELECT queries with safety checks
   - **list_tables**: Discover available tables and views
   - **describe_table**: Get schema information for a table
   - **search_metadata**: Full-text search on episode/podcast titles
   - **get_statistics**: Quick stats (episode count, listening time, etc.)

### Best Practices for SQLite Agent Tools

Based on research and industry best practices for SQL in agentic systems:

1. **Read-Only Access**
   - Only allow SELECT queries
   - No INSERT, UPDATE, DELETE, or DDL operations
   - Open database connections in read-only mode

2. **Query Safety**
   - Validate SQL before execution
   - Reject queries with dangerous keywords (DROP, DELETE, etc.)
   - Use parameterized queries when possible
   - Limit query complexity (no subqueries in subqueries)

3. **Result Management**
   - Always apply LIMIT to prevent overwhelming LLM context
   - Default LIMIT 50, max LIMIT 500
   - Format results as structured JSON
   - Truncate very long text fields

4. **Context Awareness**
   - Provide schema information in tool descriptions
   - Include example queries in tool documentation
   - Suggest relevant tables based on user questions

5. **Error Handling**
   - Graceful handling of syntax errors
   - Clear error messages for the agent
   - Log all queries for debugging
   - Timeout protection for long-running queries

### SQLite Database Schema (retrocast)

The retrocast database contains rich metadata about podcasts and listening history:

**Core Tables:**
- `feeds`: Podcast subscriptions (title, xmlUrl, subscribed status)
- `feeds_extended`: Full feed metadata (description, last updated, link)
- `episodes`: Episode information (title, URL, played status, progress)
- `episodes_extended`: Extended episode metadata (description, enclosure URL)
- `playlists`: User-created playlists
- `transcriptions`: Transcription metadata (backend, model, duration, word count)
- `transcription_segments`: Individual transcript segments (text, timestamps, speakers)
- `episode_downloads`: Downloaded episode file information
- `chapters`: Podcast chapter markers

**Views:**
- `episodes_played`: Played episodes with progress
- `episodes_deleted`: Deleted episodes
- `episodes_starred`: Starred/recommended episodes

**Full-Text Search:**
- FTS5 indexes on feed/episode titles and descriptions
- FTS5 index on transcription segment text

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

### 4. SQLite Query Tools for PydanticAI Agent

**Component:** Enhanced `castchat_agent.py` with database query tools  
**Location:** `src/retrocast/castchat_agent.py`

**Purpose:** Enable the agent to answer questions about structured metadata beyond transcription content, such as subscriptions, listening history, episode details, and playlists.

**New Agent Tools:**

```python
@agent.tool
def query_database(
    ctx: RunContext[Any],
    sql_query: str,
    limit: int = 50
) -> str:
    """Execute a read-only SQL query on the retrocast database.
    
    Use this tool to query structured metadata about podcasts, episodes,
    playlists, and listening history. Only SELECT queries are allowed.
    
    Args:
        ctx: Run context (automatically provided)
        sql_query: SQL SELECT query to execute
        limit: Maximum number of results to return (default 50, max 500)
    
    Returns:
        Query results formatted as JSON or descriptive text
        
    Available tables:
    - feeds: Podcast subscriptions (title, xmlUrl, subscribed)
    - episodes: Episode information (title, URL, played, progress)
    - playlists: User playlists
    - transcriptions: Transcription metadata
    - transcription_segments: Transcript segments with FTS
    - episode_downloads: Downloaded episode files
    
    Example queries:
    - SELECT COUNT(*) FROM episodes WHERE played = 1
    - SELECT title FROM episodes WHERE played = 0 LIMIT 10
    - SELECT title FROM feeds WHERE subscribed = 1
    """

@agent.tool
def list_tables(ctx: RunContext[Any]) -> str:
    """List all available tables and views in the database.
    
    Use this tool to discover what data is available to query.
    
    Returns:
        List of table names with brief descriptions
    """

@agent.tool
def describe_table(ctx: RunContext[Any], table_name: str) -> str:
    """Get schema information for a specific table.
    
    Use this tool to learn about the columns and structure of a table
    before querying it.
    
    Args:
        ctx: Run context (automatically provided)
        table_name: Name of the table to describe
        
    Returns:
        Table schema including column names, types, and sample data
    """

@agent.tool
def search_episodes_metadata(
    ctx: RunContext[Any],
    query: str,
    limit: int = 20
) -> str:
    """Search episode titles and descriptions using SQLite full-text search.
    
    Use this tool to find episodes by keyword in titles or descriptions.
    This is faster than semantic search for exact keyword matching.
    
    Args:
        ctx: Run context (automatically provided)
        query: Search keywords
        limit: Maximum results (default 20, max 100)
        
    Returns:
        Matching episodes with titles, podcast names, and URLs
    """

@agent.tool
def get_listening_stats(ctx: RunContext[Any]) -> str:
    """Get statistics about listening history and podcast collection.
    
    Use this tool to answer questions about listening patterns, totals,
    and collection statistics.
    
    Returns:
        Statistics including:
        - Total episodes played/unplayed
        - Total subscriptions
        - Total transcribed episodes
        - Most listened podcasts
        - Total listening time
    """
```

**Safety Implementation:**

```python
def _validate_sql_query(query: str) -> tuple[bool, str]:
    """Validate SQL query for safety.
    
    Args:
        query: SQL query string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    query_upper = query.upper().strip()
    
    # Must be SELECT query
    if not query_upper.startswith("SELECT"):
        return False, "Only SELECT queries are allowed"
    
    # Forbidden keywords
    forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", 
                 "CREATE", "EXEC", "EXECUTE", "PRAGMA"]
    for keyword in forbidden:
        if keyword in query_upper:
            return False, f"Query contains forbidden keyword: {keyword}"
    
    # Forbid semicolons (multiple statements)
    if ";" in query and not query.strip().endswith(";"):
        return False, "Multiple statements not allowed"
    
    return True, ""

def _execute_safe_query(
    db: Database,
    query: str,
    limit: int = 50
) -> list[dict]:
    """Execute query safely with result limiting.
    
    Args:
        db: Database instance (sqlite-utils)
        query: Validated SQL query
        limit: Maximum results
        
    Returns:
        Query results as list of dicts
    """
    # Enforce LIMIT if not present
    query_upper = query.upper()
    if "LIMIT" not in query_upper:
        query = f"{query.rstrip(';')} LIMIT {min(limit, 500)}"
    
    try:
        # Use sqlite-utils query method
        results = list(db.query(query))
        return results
    except Exception as e:
        logger.error(f"Query error: {e}")
        return []
```

**Integration with Agent Creation:**

```python
def create_castchat_agent(
    chroma_manager: ChromaDBManager,
    datastore: Datastore,  # NEW - pass datastore instance
    model_name: str = "claude-sonnet-4-20250514"
) -> Agent:
    """Create agent with both semantic search and database query tools.
    
    Args:
        chroma_manager: ChromaDB manager for semantic search
        datastore: Datastore instance for SQLite queries
        model_name: Anthropic model name
        
    Returns:
        Configured agent with all tools
    """
```

**Usage Examples:**

The agent can now handle queries like:
- "How many unplayed episodes do I have?" → `query_database("SELECT COUNT(*) FROM episodes WHERE played = 0")`
- "What podcasts am I subscribed to?" → `query_database("SELECT title FROM feeds WHERE subscribed = 1")`
- "Which episodes have been transcribed?" → `query_database("SELECT COUNT(*) FROM transcriptions")`
- "Show me my most recent downloads" → Uses `episode_downloads` table
- "What's my listening progress?" → Combines played episodes and progress data

### 5. CLI Enhancement

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

### 6. File Hash Tracking

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

### 7. Error Handling

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

### Phase 3: SQLite Query Tools for Agent
- [ ] Enhance `src/retrocast/castchat_agent.py`
  - [ ] Add `_validate_sql_query()` helper function
  - [ ] Add `_execute_safe_query()` helper function
  - [ ] Add `query_database` tool
    - [ ] SQL validation (SELECT only, no dangerous keywords)
    - [ ] Result limiting and formatting
    - [ ] Error handling
  - [ ] Add `list_tables` tool
  - [ ] Add `describe_table` tool
  - [ ] Add `search_episodes_metadata` tool (FTS)
  - [ ] Add `get_listening_stats` tool
  - [ ] Update agent system prompt to mention database tools
  - [ ] Update `create_castchat_agent()` signature to accept `datastore`
- [ ] Update `src/retrocast/cli.py`
  - [ ] Pass `datastore` instance to `create_castchat_agent()`
  - [ ] Ensure database is available before starting agent
- [ ] Add unit tests for SQLite query tools
  - [ ] Test SQL validation function
  - [ ] Test query execution with limits
  - [ ] Test forbidden query rejection
  - [ ] Test each agent tool
  - [ ] Test error handling for invalid queries
  - [ ] Test result formatting

### Phase 4: CLI Enhancement
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

### Phase 5: Documentation
- [ ] Update `docs/CASTCHAT.md`
  - [ ] Add "Indexing from JSON Files" section
  - [ ] Document Chonkie integration and chunking strategies
  - [ ] Add "SQLite Query Tools" section
  - [ ] Document new agent capabilities (database queries)
  - [ ] Add examples for JSON-based workflow with Chonkie
  - [ ] Add examples of database query interactions
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
  - [ ] Mention SQLite query capabilities
  - [ ] Add example commands with Chonkie options
  - [ ] Add example agent interactions with database
- [ ] Update docstrings
  - [ ] `ChromaDBManager` class (Chonkie methods)
  - [ ] `castchat_agent.py` (new tools)
  - [ ] New scanner class
  - [ ] CLI command with new options

### Phase 6: Testing & Validation
- [ ] Create test fixtures
  - [ ] Sample JSON transcription files
  - [ ] Directory structure with multiple podcasts
  - [ ] Mock database with sample data
  - [ ] Edge cases (empty, malformed, etc.)
- [ ] Integration tests
  - [ ] Test full JSON indexing workflow with Chonkie
  - [ ] Test different chunking strategies (recursive vs semantic)
  - [ ] Test chunk size variations
  - [ ] Test hybrid database + JSON indexing
  - [ ] Test SQLite query tools end-to-end
  - [ ] Test agent with both semantic search and database queries
  - [ ] Test CLI commands end-to-end
- [ ] Manual testing
  - [ ] Index real transcription directory with Chonkie
  - [ ] Compare search results: database vs JSON w/Chonkie
  - [ ] Test database queries through agent
  - [ ] Verify chunk quality and relevance
  - [ ] Test incremental updates
  - [ ] Test combined queries (semantic + structured)

### Phase 7: Quality & Security
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

### 9. SQL Query Safety
**Issue:** Agent might generate dangerous or malformed SQL queries  
**Solution:**
- Strict validation (SELECT only)
- Keyword blacklist (DROP, DELETE, etc.)
- Result limiting (max 500 rows)
- Query timeout protection
- Comprehensive error handling

### 10. SQL Query Complexity
**Issue:** Agent might generate overly complex queries that are slow  
**Solution:**
- Query complexity analysis
- Timeout limits
- Suggest simpler alternative queries
- Provide query optimization hints in tool descriptions

## Success Criteria

1. ✅ Users can run `retrocast castchat --json-dir ~/transcriptions` without database
2. ✅ JSON indexing with Chonkie produces high-quality, semantically meaningful chunks
3. ✅ Chonkie chunking improves search relevance compared to fixed-size segments
4. ✅ Multiple chunking strategies (recursive/semantic/segments) work correctly
5. ✅ SQLite query tools enable structured metadata queries through the agent
6. ✅ SQL validation prevents dangerous queries (no data modification possible)
7. ✅ Agent can combine semantic search with structured queries effectively
8. ✅ Incremental updates work correctly (only new files indexed)
9. ✅ All existing tests continue to pass
10. ✅ New tests achieve >80% coverage of new code
11. ✅ Documentation clearly explains JSON workflow, Chonkie options, and SQL tools
12. ✅ No performance regression for database indexing path
13. ✅ Chonkie integration adds <2MB to package size

## Timeline Estimate

- **Phase 1 (Dependencies & Scanner):** 2-3 hours
- **Phase 2 (ChromaDB + Chonkie):** 4-5 hours
- **Phase 3 (SQLite Query Tools):** 3-4 hours
- **Phase 4 (CLI):** 2 hours
- **Phase 5 (Docs):** 2-3 hours
- **Phase 6 (Testing):** 3-4 hours
- **Phase 7 (QA):** 1 hour

**Total:** 17-22 hours of development time (updated from 12-16 to account for SQLite query tools integration)

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
- [ ] Advanced SQL query capabilities:
  - [ ] Query history and favorites
  - [ ] Query result caching
  - [ ] Complex aggregations and joins
  - [ ] Query explanation/planning tool
- [ ] Database insights tool for agent:
  - [ ] Trend analysis (listening patterns over time)
  - [ ] Recommendation queries (unplayed episodes matching interests)
  - [ ] Collection analytics (most/least played podcasts)

## Related Files

**New Files:**
- `src/retrocast/transcription_json_scanner.py` - JSON file scanner
- `tests/test_transcription_json_scanner.py` - Scanner tests
- `tests/test_json_indexing.py` - JSON indexing integration tests
- `tests/test_sql_query_tools.py` - SQLite query tool tests

**Modified Files:**
- `src/retrocast/chromadb_manager.py` - Add JSON indexing methods
- `src/retrocast/castchat_agent.py` - Add SQL query tools
- `src/retrocast/cli.py` - Add CLI options for JSON indexing and pass datastore to agent
- `docs/CASTCHAT.md` - Add JSON indexing and SQL query documentation
- `README.md` - Update castchat examples
- `tests/test_castchat.py` - Add JSON indexing and SQL query tests

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
- SQLite CLI wrapper: `src/retrocast/sql_cli.py`
- Datastore implementation: `src/retrocast/datastore.py`

### SQL in Agentic Systems - Best Practices

**Research Sources:**
1. **LangChain SQL Agent Documentation**: Recommends read-only access, query validation, and result limiting
2. **Text-to-SQL Best Practices**: Use schema context, example queries, and clear tool descriptions
3. **sqlite-utils Library**: Provides safe query execution, schema inspection, and JSON export
4. **SQL Injection Prevention**: Parameterized queries, keyword filtering, syntax validation

**Key Principles:**
- **Safety First**: Only SELECT queries, no data modification
- **Context Awareness**: Provide schema information to the agent
- **Result Management**: Limit result sets to prevent context overflow
- **Error Handling**: Graceful failures with clear messages
- **Transparency**: Log all queries for debugging and auditing
