# Copilot Instructions for retrocast

## Project Overview

`retrocast` is a Python tool for archiving and exploring podcast content from Overcast (iOS podcast player). It extracts podcast feeds, episodes, transcripts, and chapters into SQLite databases for analysis and exploration with tools like Datasette.

**Project Goals**: Enable AI-assisted retrospective exploration of podcast episode archives. Podcast listeners typically subscribe to many podcasts but only listen to a small fraction of episodes. retrocast helps users comprehensively archive, transcribe, index, and conversationally explore their podcast collections to answer questions like "where did this concept appear?" or "what episodes featured this guest?"

**Key Technologies**: Python 3.11+, SQLite, Click CLI framework, uv package manager

**Origin**: This project began as a fork of [`overcast-to-sqlite`](https://github.com/hbmartin/overcast-to-sqlite) by Harold Martin (Apache 2.0 license) and has expanded to include transcription, full-text search, and AI exploration capabilities.

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
# or using PoeThePoet
uv run poe test

# Lint code
uv run ruff check src
uv run ruff format src
# or using PoeThePoet
uv run poe lint
uv run poe lint:fix

# Type checking
uv run ty check src
# or using PoeThePoet
uv run poe type

# Run all QA checks (lint, type, test)
uv run poe qa

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

## Documentation Resources

### Key Documentation Files
- **[README.md](../README.md)**: User-facing documentation, installation, and usage instructions
- **[ABOUT.md](../ABOUT.md)**: Project vision and goals for AI-assisted podcast exploration
- **[AGENTS.md](../AGENTS.md)**: Guidance for AI coding agents (overlaps with this file but includes CLI command reference)
- **[TRANSCRIPTION.md](../TRANSCRIPTION.md)**: Details on transcription backends (MLX Whisper, faster-whisper, diarization)
- **[ARIA2_FETCHER.md](../ARIA2_FETCHER.md)**: Documentation for the embedded aria2c download manager
- **[CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)**: Community guidelines and conduct expectations

### External Resources
- [Datasette Documentation](https://datasette.io/) - Tool for exploring SQLite databases
- [Overcast](https://overcast.fm/) - Source podcast player application
- [podcast-archiver](https://github.com/janw/podcast-archiver) - Integrated episode downloader
- [uv Documentation](https://docs.astral.sh/uv/) - Python package manager used by this project

## Contributing to retrocast

### Getting Started
1. Fork and clone the repository
2. Run `uv sync` to install dependencies
3. Run `uv run poe qa` to verify your environment setup
4. Review open issues labeled `good first issue` or `help wanted`

### Development Workflow
1. Create a feature branch from `main`
2. Make focused, incremental changes
3. Run `uv run poe lint:fix` to auto-fix linting issues
4. Run `uv run poe type` to check type hints
5. Run `uv run poe test` to validate changes
6. Run `uv run poe qa` before submitting PR
7. Write clear commit messages describing the change
8. Open a PR with a descriptive title and detailed description

### Testing Strategy
- Unit tests for data transformation logic (feed parsing, episode extraction)
- Integration tests for CLI commands using `requests-mock` for HTTP calls
- Avoid testing external APIs directly; use mocks
- Tests live in `tests/` directory and mirror the `src/retrocast/` structure

## Prompting Tips for Copilot

### Effective Prompts for This Repository
When working with Copilot in this codebase, use these patterns for best results:

**For CLI Commands**:
```
# Add a new CLI command to [do X] following the pattern in cli.py
# The command should use Rich for progress, support -v flag, and work with the Datastore class
```

**For Feed Processing**:
```
# Extract [new RSS tag] from podcast feeds in feed.py
# Handle missing values and normalize to flat dictionary format
# Use alter=True for dynamic schema
```

**For Database Operations**:
```
# Add a new table for [feature] to datastore.py
# Include foreign keys, full-text search if appropriate
# Follow the pattern of feeds/episodes tables
```

**For Testing**:
```
# Add tests for [feature] using pytest and requests-mock
# Follow the pattern in test_cli.py for CLI command testing
```

### Context Variables to Use
- Use `#file` to reference specific source files when asking about patterns
- Use `#selection` when asking about specific code blocks
- Reference test files to understand expected behavior: `#file:tests/test_cli.py`
- Reference documentation: `#file:README.md`, `#file:AGENTS.md`

### Common Pitfalls to Avoid
- Don't suggest synchronous HTTP calls in hot loops (use ThreadPoolExecutor with BATCH_SIZE)
- Don't bypass the Datastore abstraction layer (always use methods in datastore.py)
- Don't add new dependencies without checking security advisories
- Don't disable pagers in tests (already handled in test fixtures)
- Don't use class-based Click commands (use function-based with decorators)

## Security and Privacy Guidelines

### Security Practices
- **Never commit secrets**: Auth tokens stored in `auth.json` (gitignored)
- **Sanitize paths**: Always use `_sanitize_for_path()` for filesystem operations
- **Validate URLs**: Check URL schemes before downloading content
- **Handle errors gracefully**: Network failures should log but not crash
- **Use stamina for retries**: Built-in retry logic for transient failures

### Privacy Considerations
- User listening history is personal data - handle with care
- Auth cookies contain sensitive session tokens - never log or expose
- Episode download locations may reveal user interests - keep local
- Transcript content may be copyrighted - respect fair use

### Dependencies
- Run `uv run pip-audit` to check for known vulnerabilities
- Keep dependencies updated via Dependabot (configured in `.github/dependabot.yml`)
- Review new dependencies before adding (check license, maintainer, audit logs)
