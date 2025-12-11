# AGENTS.md

This file provides guidance to agentic coding agents when working with
code in this repository.

## Project Overview

`retrocast` is a Python tool for archiving and exploring podcast
content from Overcast (iOS podcast player). It extracts podcast feeds,
episodes, transcripts, and chapters into SQLite databases for analysis
and exploration with tools like Datasette. The project began as a fork
of `overcast-to-sqlite` by Harold Martin and honors the Apache 2.0
license.

## Development Commands

### Setup
```bash
# Install with uv
uv sync
```

### Running the CLI
```bash
# Basic invocation
uv run python -m retrocast.cli

# Full workflow (all steps)
uv run python -m retrocast.cli all -v

# Individual commands
uv run python -m retrocast.cli auth                 # Authenticate to Overcast
uv run python -m retrocast.cli save                 # Save OPML data to SQLite
uv run python -m retrocast.cli extend               # Download and parse full XML feeds
uv run python -m retrocast.cli transcripts          # Download transcripts
uv run python -m retrocast.cli chapters             # Extract chapter information
uv run python -m retrocast.cli episodes             # Export episodes as CSV/JSON
uv run python -m retrocast.cli subscriptions        # List subscribed feeds
uv run python -m retrocast.cli html                 # Generate HTML output

# Episode download database commands
uv run python -m retrocast.cli download podcast-archiver  # Download episodes via podcast-archiver
uv run python -m retrocast.cli download db init           # Initialize episode database
uv run python -m retrocast.cli download db update         # Index downloaded episodes
uv run python -m retrocast.cli download db search "query" # Search downloaded episodes
```

### Linting & Type Checking
```bash
# Ruff linting
uv run ruff check src

# Ruff formatting
uv run ruff format src

# Black formatting
uv run black src

# Type checking
uv run ty check src

# Package quality check
uv run pyroma . --min=10
```

### Testing
```bash
# Run tests with pytest
uv run pytest
```

### Pre-commit Hooks
This project uses pre-commit hooks configured in `.pre-commit-config.yaml`:
- Black code formatter
- Ruff linter and formatter
- isort import sorting
- nbstripout for Jupyter notebooks

```bash
# Run pre-commit linting
prek run
```
## Architecture

### Data Flow Pipeline

The application follows a multi-stage ETL pipeline:

1. **Authentication** (`overcast.py`): Login to Overcast and save session cookies to `auth.json`
2. **Save** (`cli.py:save`): Fetch OPML from Overcast, parse feeds/episodes, store in SQLite (tables: `feeds`, `episodes`, `playlists`)
3. **Extend** (`cli.py:extend`): Download full XML feeds for all podcasts, extract rich metadata (tables: `feeds_extended`, `episodes_extended`)
4. **Transcripts** (`cli.py:transcripts`): Download transcript files from `podcast:transcript:url` tags
5. **Chapters** (`cli.py:chapters`): Extract chapter markers from feeds (table: `chapters`)
6. **Episode Downloads** (`download_commands.py`, `episode_db_commands.py`): Download episodes via podcast-archiver and index them in a searchable database (table: `episode_downloads`)

### Core Components

**`datastore.py`**: Central database abstraction layer
- Single `Datastore` class wraps sqlite-utils `Database`
- Responsible for all table creation, schema management, queries
- Creates tables: `feeds`, `feeds_extended`, `episodes`, `episodes_extended`, `playlists`, `chapters`, `episode_downloads`
- Creates views: `episodes_played`, `episodes_deleted`, `episodes_starred`
- Full-text search enabled on feed/episode titles and descriptions
- Uses foreign keys to maintain referential integrity between tables
- Episode downloads methods: `upsert_episode_downloads_batch()`, `search_episode_downloads()`, `mark_missing_episodes()`

**`cli.py`**: Click-based CLI interface
- Each subcommand maps to a pipeline stage
- Heavy use of `ThreadPoolExecutor` for concurrent downloads (controlled by `BATCH_SIZE` constant)
- The `all` command chains multiple stages together via `ctx.invoke()`
- Database confirmation prompts before creating new files

**`overcast.py`**: Overcast API integration
- Session management and authentication
- OPML fetching and parsing
- Converts Overcast-specific XML structure to normalized dictionaries

**`feed.py`**: RSS/Atom feed processing
- Downloads XML feeds via `requests`
- Extracts both feed-level and episode-level metadata
- Uses `podcast_chapter_tools` for chapter parsing
- Normalizes all XML tags/attributes into flat dictionaries (ALTER TABLE used for dynamic columns)

**`episode.py`**: Episode extraction logic
- Recursively converts XML elements to dictionaries with `_element_to_dict()`
- Handles nested namespace tags (e.g., `itunes:image:href`)
- Processes `<enclosure>` tags for audio file URLs

**`ariafetcher.py`**: Embedded aria2c subprocess manager
- Launches aria2c RPC server on random ephemeral port
- Uses `stamina` library for retry logic with exponential backoff
- Verifies both TCP socket and XML-RPC endpoint readiness
- Provides clean subprocess lifecycle management

**`html/` module**: Static HTML generation
- `page.py`: Generates browsable HTML from played episodes
- `htmltagfixer.py`: Sanitizes HTML in episode descriptions
- Includes bundled CSS (`mvp.css`) and JavaScript (`search.js`)

**`download_commands.py`**: Download-related CLI commands
- `download` command group for episode downloading
- `aria` command: Download URLs using aria2c fetcher
- Integrates with podcast-archiver via CLI passthrough in `cli.py`

**`episode_scanner.py`**: Filesystem scanner for downloaded episodes
- `EpisodeScanner` class scans `episode_downloads/` directory for media files
- Discovers and pairs media files with `.info.json` metadata
- `scan()`: Walks directory tree, identifies podcasts and episodes
- `read_metadata()`: Parses .info.json files with error handling
- `extract_fields()`: Maps various metadata formats to database columns
- Supports multiple audio formats (.mp3, .m4a, .ogg, .opus, .wav, .flac)
- Date normalization for ISO8601, YYYYMMDD, Unix timestamps, RFC 2822

**`episode_db_commands.py`**: Episode database CLI commands
- `episode_db` command group under `download db`
- `init`: Initialize episode_downloads table and FTS indexes
- `update`: Scan filesystem and populate database with metadata
  - Supports `--rescan` (rebuild from scratch) and `--verify` (check file existence)
  - Uses Rich progress bars for user feedback
- `search`: Full-text search across downloaded episodes
  - Supports `--podcast` filter and `--limit` options
  - Displays formatted results table with episode details

### Database Schema Strategy

**Primary Keys:**
- Base tables (`feeds`, `episodes`): Use Overcast's `overcastId` integers
- Extended tables (`feeds_extended`, `episodes_extended`): Use URLs (xmlUrl, enclosureUrl)
- Episode downloads (`episode_downloads`): Use file path (`media_path`) as primary key
- This dual-key strategy allows joining Overcast metadata with full feed data even when URLs change

**Column Naming:**
- camelCase for Overcast-sourced fields (e.g., `userUpdatedDate`, `overcastId`)
- snake_case for computed/derived fields (where present)

**Dynamic Schema:**
- Extended tables use `alter=True` during inserts to accommodate arbitrary RSS tags
- Any XML tag becomes a column, so schemas vary per feed

**Episode Downloads Schema:**
- `episode_downloads` table tracks downloaded podcast episodes with full-text search
- Core fields: media_path (PK), podcast_title, episode_filename, file_size, timestamps
- Metadata fields: episode_title, episode_description, episode_summary, episode_shownotes, episode_url, publication_date, duration
- Full .info.json stored in metadata_json column as TEXT
- FTS5 virtual table (`episode_downloads_fts`) for full-text search across text fields
- Indexes on podcast_title, publication_date, and modified_time for efficient queries
- Tracks file existence with media_exists and metadata_exists flags

### Threading Model

Concurrent downloads use `ThreadPoolExecutor` with `BATCH_SIZE` (defined in `constants.py`):
- Feed downloads in `extend` command
- Transcript downloads in `transcripts` command
- Each worker handles one feed/transcript, results collected and bulk-inserted

### Error Handling

- Network errors during feed fetching are logged but don't stop execution
- Failed feeds store error codes in the database
- Missing/changed episodes are handled gracefully (no exceptions on missing data)

## Key Patterns

1. **Date Handling**: All dates converted to ISO format via `_parse_date_or_none()` utility
2. **Path Sanitization**: Feed/episode titles sanitized via `_sanitize_for_path()` for filesystem storage
3. **Optional Archiving**: Most commands support `--no-archive`/`-na` to skip saving raw files
4. **Verbose Mode**: `-v` flag throughout for debug output
5. **Confirmation Prompts**: Database creation always prompts unless file exists

## Testing

The project includes pytest configuration in `pyproject.toml` under `[project.optional-dependencies]`:
- `pytest` for test execution
- `requests-mock` for mocking HTTP calls

To run tests:
```bash
uv run pytest
```
