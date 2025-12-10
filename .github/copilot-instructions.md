# Copilot Instructions for retrocast

## Repository Overview

`retrocast` is a Python tool for archiving and exploring podcast content from Overcast (iOS podcast player). It extracts podcast feeds, episodes, transcripts, and chapters into SQLite databases for analysis and exploration with tools like Datasette.

**Key Technologies**: Python 3.11+, SQLite, Click CLI framework, uv package manager

## Development Setup

```bash
# Install dependencies
uv sync

# Run the CLI
uv run python -m retrocast.cli --help
```

## Essential Commands

### Build & Test
```bash
# Run tests
uv run pytest

# Lint code
uv run ruff check src
uv run ruff format src

# Type checking
uv run ty check src

# Pre-commit hooks
pre-commit run
```

### Running the Application
```bash
# Authenticate to Overcast
uv run python -m retrocast.cli auth

# Full workflow
uv run python -m retrocast.cli all -v

# Individual commands
uv run python -m retrocast.cli save        # Save OPML to SQLite
uv run python -m retrocast.cli extend      # Download full feeds
uv run python -m retrocast.cli transcripts # Download transcripts
uv run python -m retrocast.cli chapters    # Extract chapters
```

## Architecture

### Core Components
- **`cli.py`**: Click-based CLI interface, each subcommand maps to a pipeline stage
- **`datastore.py`**: Central database abstraction layer using sqlite-utils
- **`overcast.py`**: Overcast API integration and authentication
- **`feed.py`**: RSS/Atom feed processing with metadata extraction
- **`episode.py`**: Episode extraction logic from XML
- **`ariafetcher.py`**: Embedded aria2c subprocess manager for downloads

### Data Flow
1. **auth**: Login to Overcast → save session cookies to `auth.json`
2. **save**: Fetch OPML → parse feeds/episodes → store in SQLite
3. **extend**: Download full XML feeds → extract rich metadata
4. **transcripts**: Download transcript files from feed tags
5. **chapters**: Extract chapter markers from feeds

### Database Schema
- **Tables**: `feeds`, `feeds_extended`, `episodes`, `episodes_extended`, `playlists`, `chapters`
- **Views**: `episodes_played`, `episodes_deleted`, `episodes_starred`
- **Primary Keys**: Overcast's `overcastId` for base tables, URLs for extended tables
- **Dynamic Schema**: Extended tables use `alter=True` to accommodate arbitrary RSS tags

## Coding Conventions

### Style
- **Formatting**: Black formatter with 100 character line length
- **Linting**: Ruff with Pycodestyle, Pyflakes, and import order checks
- **Type Hints**: Use type hints throughout (checked with ty/mypy)
- **Column Naming**: 
  - camelCase for Overcast-sourced fields (e.g., `userUpdatedDate`, `overcastId`)
  - snake_case for computed/derived fields

### Key Patterns
1. **Date Handling**: Convert all dates to ISO format via `_parse_date_or_none()` utility
2. **Path Sanitization**: Sanitize feed/episode titles via `_sanitize_for_path()` for filesystem storage
3. **Optional Archiving**: Commands support `--no-archive`/`-na` to skip saving raw files
4. **Verbose Mode**: `-v` flag throughout for debug output
5. **Confirmation Prompts**: Database creation prompts unless file exists
6. **Concurrency**: Use `ThreadPoolExecutor` with `BATCH_SIZE` constant for downloads

### Logging
- Uses `loguru` for logging configuration
- CLI has `-q/--quiet` flag (ERROR level) and `-v/--verbose` flag (DEBUG level)
- External configs via `RETROCAST_LOG_CONFIG` env var or `logging.json` take precedence

## Testing

- **Framework**: pytest
- **Location**: `tests/` directory
- **Mocking**: Use `requests-mock` for HTTP calls
- **Run**: `uv run pytest`

## Important Notes

- This project began as a fork of `overcast-to-sqlite` by Harold Martin (Apache 2.0 license)
- Uses `uv` package manager instead of pip/pipx
- Heavy use of dynamic schema (any XML tag becomes a column in extended tables)
- Network errors during feed fetching are logged but don't stop execution
- Full-text search enabled on feed/episode titles and descriptions

## Common Tasks

### Adding a New CLI Command
1. Add command function to `cli.py` using `@click.command()` decorator
2. Follow existing pattern for database access via `Datastore` class
3. Add progress indicators using Rich library
4. Support `-v/--verbose` flag for debug output
5. Add tests in `tests/` directory

### Adding a New Database Table
1. Define schema in `datastore.py`
2. Create table in `Datastore.__init__()` or relevant method
3. Use foreign keys for referential integrity
4. Consider adding full-text search if appropriate
5. Document the table purpose and schema

### Processing New RSS/Feed Metadata
1. Add extraction logic in `feed.py` or `episode.py`
2. Use `alter=True` for dynamic schema if needed
3. Normalize XML tags/attributes to flat dictionaries
4. Handle nested namespace tags (e.g., `itunes:image:href`)
5. Add error handling for missing/malformed data
