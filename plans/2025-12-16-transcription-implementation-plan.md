# Detailed Implementation Plan: Transcription Module for retrocast

**Created**: 2025-12-16
**Status**: Planning
**Related Issue**: https://github.com/crossjam/retrocast/issues/8

## Executive Summary

After thorough exploration of the retrocast codebase, I recommend a
**class-based architecture** over a pluggy-based plugin system for the
transcription module. This recommendation is based on the existing
codebase patterns, simplicity requirements, and the project's current
architecture which doesn't use pluggy anywhere else. 

## Recommended Architecture: Class-Based with Strategy Pattern

### Justification

1. **Consistency with Existing Code**: The retrocast codebase uses
   direct class instantiation patterns (e.g., `AriaDownloader`,
   `EpisodeScanner`, `Datastore`) without any plugin infrastructure. 

2. **Simplicity**: Only 2-3 transcription backends needed initially
   (mlx-whisper, faster-whisper, standard whisper). A class hierarchy
   is simpler than pluggy infrastructure. 

3. **No Existing Plugin System**: Adding pluggy would introduce new
   architectural complexity for minimal benefit given the limited
   number of backends. 

4. **Type Safety**: Class-based approach provides better IDE support
   and type checking with existing tooling (ty, ruff). 

5. **Future Flexibility**: Can still add pluggy later if third-party
   transcription backends are needed. 

## Architecture Design

### Core Module Structure

```
src/retrocast/transcription/
├── __init__.py                    # Public API exports
├── base.py                        # Abstract base classes
├── backends/
│   ├── __init__.py               # Backend registry
│   ├── mlx_whisper.py            # Apple Silicon backend
│   ├── faster_whisper.py         # CUDA/CPU backend (faster-whisper)
│   └── fallback_whisper.py       # Fallback (openai-whisper)
├── diarization.py                # Speaker diarization (pyannote.audio)
├── output_formats.py             # Output format handling (JSON, SRT, TXT, VTT)
├── transcription_manager.py      # Main orchestration class
└── utils.py                      # Path handling, sanitization
```

### Class Hierarchy

```python
# base.py
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class TranscriptionSegment:
    """Represents a single transcription segment."""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None  # For diarization

@dataclass
class TranscriptionResult:
    """Complete transcription result."""
    segments: list[TranscriptionSegment]
    text: str
    language: str
    duration: float
    metadata: dict

class TranscriptionBackend(ABC):
    """Abstract base class for transcription backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend identifier."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend dependencies are available."""
        pass

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model_size: str = "base",
    ) -> TranscriptionResult:
        """Transcribe audio file."""
        pass
```

## Platform-Specific Dependency Management

### pyproject.toml Updates

```toml
[project.optional-dependencies]
# Existing lint dependencies...

# Transcription backends - installed separately by user
transcription-mlx = [
    "mlx-whisper>=0.4.0; platform_system=='Darwin'",
]

transcription-cuda = [
    "faster-whisper>=1.0.0",
    "torch>=2.0.0",  # With CUDA support
]

transcription-cpu = [
    "faster-whisper>=1.0.0",
    "torch>=2.0.0",  # CPU-only
]

transcription-diarization = [
    "pyannote.audio>=3.0.0",
]

# Convenience metapackage for all transcription features
transcription-full = [
    "retrocast[transcription-mlx,transcription-cuda,transcription-diarization]",
]
```

### Backend Auto-Detection Logic

Each backend's `is_available()` method will use try/except to detect if dependencies are installed:

```python
# backends/mlx_whisper.py
def is_available(self) -> bool:
    try:
        import mlx_whisper
        import platform
        return platform.system() == "Darwin"
    except ImportError:
        return False
```

## Database Schema Additions

### Episode Identification Strategy

**Problem**: Using `media_path` as a primary key is fragile because:
- Files can be moved or renamed
- Same episode might be downloaded to different locations
- Difficult to track transcriptions across reorganizations

**Solution**: Multi-layered identification approach

1. **Primary Key**: Auto-incrementing `transcription_id` for stable references
2. **Content Hash**: SHA256 hash of audio file content for deduplication
3. **Media Path**: Non-unique reference to current file location
4. **Episode URL**: Optional link to episode metadata for integration with `episode_downloads`

This allows:
- Finding transcriptions even if files move (via content hash)
- Preventing duplicate transcriptions of the same audio (hash-based deduplication)
- Optional integration with existing episode database (via episode_url)
- Stable foreign key relationships (transcription_id)

### New Table: transcriptions

```python
# In datastore.py _prepare_db()
if "transcriptions" not in self.db.table_names():
    self._table("transcriptions").create(
        {
            "transcription_id": int,              # Auto-increment primary key
            "audio_content_hash": str,            # SHA256 hash of audio file (for deduplication)
            "media_path": str,                    # Current file path (can change)
            "file_size": int,                     # File size in bytes (for verification)
            "transcription_path": str,            # Output file path
            "episode_url": str,                   # Optional: URL from episode metadata
            "podcast_title": str,                 # For organization/search
            "episode_title": str,                 # For organization/search
            "backend": str,                       # mlx-whisper, faster-whisper, etc.
            "model_size": str,                    # tiny, base, small, medium, large
            "language": str,                      # Detected/specified language
            "duration": float,                    # Audio duration in seconds
            "transcription_time": float,          # Time taken to transcribe
            "has_diarization": int,               # Boolean: speaker diarization applied
            "speaker_count": int,                 # Number of detected speakers
            "word_count": int,                    # Total words transcribed
            "created_time": str,                  # ISO8601 timestamp
            "updated_time": str,                  # ISO8601 timestamp (if re-transcribed)
            "metadata_json": str,                 # Full result metadata as JSON
        },
        pk="transcription_id",
    )
    # Create unique index on content hash to prevent duplicate transcriptions
    self._table("transcriptions").create_index(
        ["audio_content_hash"],
        unique=True,
        if_not_exists=True,
    )
    # Create index on media_path for lookups by file location
    self._table("transcriptions").create_index(
        ["media_path"],
        if_not_exists=True,
    )
    # Create index on episode_url for linking to episode metadata
    self._table("transcriptions").create_index(
        ["episode_url"],
        if_not_exists=True,
    )

# New table: transcription_segments
if "transcription_segments" not in self.db.table_names():
    self._table("transcription_segments").create(
        {
            "transcription_id": int,              # Foreign key to transcriptions
            "segment_index": int,                 # Segment number (0-based)
            "start_time": float,                  # Start time in seconds
            "end_time": float,                    # End time in seconds
            "text": str,                          # Segment text
            "speaker": str,                       # Speaker ID (optional)
        },
        foreign_keys=[("transcription_id", "transcriptions", "transcription_id")],
    )
    # Create composite index for efficient segment lookups
    self._table("transcription_segments").create_index(
        ["transcription_id", "segment_index"],
        if_not_exists=True,
    )
    # Enable full-text search on segment text
    self._table("transcription_segments").enable_fts(
        ["text"],
        create_triggers=True,
    )
```

### Content Hashing Implementation

```python
# In utils.py
import hashlib
from pathlib import Path

def compute_audio_hash(audio_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA256 hash of audio file for content-based deduplication.

    Args:
        audio_path: Path to audio file
        chunk_size: Read chunk size in bytes (default 8KB)

    Returns:
        Hexadecimal SHA256 hash string
    """
    sha256_hash = hashlib.sha256()

    with open(audio_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def check_transcription_exists(
    datastore: Datastore,
    audio_hash: str
) -> tuple[bool, dict | None]:
    """
    Check if transcription already exists for given audio content.

    Args:
        datastore: Datastore instance
        audio_hash: SHA256 hash of audio content

    Returns:
        Tuple of (exists: bool, transcription_record: dict | None)
    """
    table = datastore.db["transcriptions"]
    try:
        record = table.get_by("audio_content_hash", audio_hash)
        return (True, dict(record))
    except Exception:
        return (False, None)
```

## CLI Command Structure

### Command Hierarchy

```
retrocast process                     # New command group
├── transcribe                        # Transcribe audio files
│   ├── --backend [auto|mlx|faster|whisper]
│   ├── --model [tiny|base|small|medium|large]
│   ├── --language [en|es|fr|...]
│   ├── --diarize                     # Enable speaker diarization
│   ├── --output-dir PATH
│   ├── --format [txt|json|srt|vtt]
│   └── PATH [PATH ...]               # Audio files or directories
├── list-backends                     # Show available backends
├── test-backend BACKEND              # Test backend availability
└── search QUERY                      # Search transcribed content
```

### CLI Implementation

```python
# src/retrocast/process_commands.py (NEW FILE)

import rich_click as click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from retrocast.transcription import TranscriptionManager
from retrocast.appdir import get_app_dir
from retrocast.datastore import Datastore

console = Console()

@click.group(name="process")
@click.pass_context
def process(ctx: click.RichContext) -> None:
    """Process podcast audio files (transcription, analysis)."""
    ctx.ensure_object(dict)


@process.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--backend",
    type=click.Choice(["auto", "mlx", "faster", "whisper"], case_sensitive=False),
    default="auto",
    help="Transcription backend to use.",
)
@click.option(
    "--model",
    type=click.Choice(["tiny", "base", "small", "medium", "large"]),
    default="base",
    help="Whisper model size.",
)
@click.option(
    "--language",
    type=str,
    default=None,
    help="Audio language (auto-detected if not specified).",
)
@click.option(
    "--diarize",
    is_flag=True,
    help="Enable speaker diarization.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory (defaults to app_dir/transcriptions).",
)
@click.option(
    "--format",
    type=click.Choice(["txt", "json", "srt", "vtt"]),
    default="json",
    help="Output format.",
)
@click.pass_context
def transcribe(
    ctx: click.RichContext,
    paths: tuple[Path, ...],
    backend: str,
    model: str,
    language: str | None,
    diarize: bool,
    output_dir: Path | None,
    format: str,
) -> None:
    """Transcribe audio files to text."""

    if not paths:
        console.print("[yellow]No audio files specified.[/yellow]")
        console.print("Usage: retrocast process transcribe [OPTIONS] PATH [PATH ...]")
        ctx.exit(1)

    # Initialize manager
    app_dir = get_app_dir(create=True)
    if output_dir is None:
        output_dir = app_dir / "transcriptions"
    output_dir.mkdir(parents=True, exist_ok=True)

    manager = TranscriptionManager(
        backend=backend,
        model_size=model,
        output_dir=output_dir,
    )

    # Process files...


@process.command(name="list-backends")
def list_backends() -> None:
    """List available transcription backends."""

    from retrocast.transcription.backends import get_all_backends

    table = Table(title="Available Transcription Backends")
    table.add_column("Backend", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Platform", style="dim")
    table.add_column("Notes")

    for backend_cls in get_all_backends():
        backend = backend_cls()
        status = "[green]✓ Available[/green]" if backend.is_available() else "[red]✗ Not Available[/red]"
        table.add_row(
            backend.name,
            status,
            backend.platform_info(),
            backend.description(),
        )

    console.print(table)
```

### Register in main CLI

```python
# In cli.py
from retrocast.process_commands import process

# Add after other command registrations
cli.add_command(process)
```

## Output Directory Structure

Following the pattern established by `episode_downloads/`:

```
{app_dir}/transcriptions/
├── Podcast Name/
│   ├── Episode Title.json
│   ├── Episode Title.txt
│   ├── Episode Title.srt
│   └── Episode Title.vtt
└── Another Podcast/
    └── ...
```

The path structure mirrors `episode_downloads/` to maintain consistency. The transcription files will be named based on the audio filename (without extension) plus the format extension.

## Implementation Phases

### Phase 1: Core Infrastructure (Foundation)

**Objective**: Set up the basic transcription module structure without backend implementations.

**Tasks**:
1. Create `src/retrocast/transcription/` directory structure
2. Implement `base.py` with abstract classes and data classes
3. Implement `utils.py` with path sanitization and directory management
4. Implement `output_formats.py` with format writers (TXT, JSON, SRT, VTT)
5. Create basic `TranscriptionManager` class skeleton
6. Add database schema to `datastore.py`
7. Write unit tests for data classes and utilities

**Deliverables**:
- Module skeleton with clear interfaces
- Database tables and methods
- Output format handlers
- Test coverage for utilities

### Phase 2: MLX Whisper Backend (Apple Silicon)

**Objective**: Implement the Apple Silicon backend using mlx-whisper.

**Tasks**:
1. Implement `backends/mlx_whisper.py`
2. Add dependency detection logic
3. Implement `transcribe()` method
4. Add error handling and logging
5. Create integration tests (requires Apple Silicon or mock)
6. Update documentation with installation instructions

**Deliverables**:
- Fully functional MLX backend
- Installation instructions for `retrocast[transcription-mlx]`
- Test coverage with mocks

### Phase 3: Faster-Whisper Backend (CUDA/CPU)

**Objective**: Implement faster-whisper backend for Linux CUDA and CPU fallback.

**Tasks**:
1. Implement `backends/faster_whisper.py`
2. Add GPU detection logic (CUDA availability)
3. Implement CPU fallback
4. Add performance logging (transcription time, real-time factor)
5. Create integration tests
6. Update documentation

**Deliverables**:
- faster-whisper backend with CUDA and CPU support
- Installation instructions for `retrocast[transcription-cuda]` and `retrocast[transcription-cpu]`
- Performance benchmarks

### Phase 4: CLI Integration

**Objective**: Create the `process` command group and `transcribe` command.

**Tasks**:
1. Create `src/retrocast/process_commands.py`
2. Implement `process` group
3. Implement `transcribe` command with all options
4. Implement `list-backends` command
5. Implement `test-backend` command
6. Add Rich progress bars for batch processing
7. Wire up to main CLI in `cli.py`
8. Add CLI tests

**Deliverables**:
- Fully functional CLI commands
- Help documentation
- User-facing error messages
- CLI test coverage

### Phase 5: Speaker Diarization (Optional Enhancement)

**Objective**: Add speaker diarization support via pyannote.audio.

**Tasks**:
1. Implement `diarization.py` module
2. Integrate with pyannote.audio
3. Handle Hugging Face token requirements
4. Merge diarization results with transcription segments
5. Update database schema to store speaker information
6. Add `--diarize` flag support
7. Update documentation

**Deliverables**:
- Speaker diarization functionality
- Installation instructions for `retrocast[transcription-diarization]`
- Updated output formats with speaker labels

### Phase 6: Search and Query Features

**Objective**: Enable searching transcribed content.

**Tasks**:
1. Implement `process search` command
2. Add full-text search across `transcription_segments`
3. Add filters (podcast, date range, speaker)
4. Implement result highlighting
5. Add export options for search results

**Deliverables**:
- Search command with filtering
- Highlighted search results
- Documentation

## Key Design Decisions and Trade-offs

### 1. Class-Based vs. Pluggy Architecture

**Decision**: Class-based with abstract base classes

**Rationale**:
- Simplicity: Only 2-3 backends initially
- Consistency: Matches existing codebase patterns
- Type safety: Better IDE and type checker support
- No existing plugin infrastructure in project

**Trade-offs**:
- Less extensible for third-party plugins
- Acceptable because: User base is small, backends are well-defined, can add pluggy later if needed

### 2. Optional Dependencies with extras_require

**Decision**: Use `[project.optional-dependencies]` with platform markers

**Rationale**:
- Standard Python packaging approach
- Users install only what they need: `pip install retrocast[transcription-mlx]`
- Platform markers prevent installing incompatible packages

**Trade-offs**:
- Users must know which extra to install
- Acceptable because: Clear documentation, `list-backends` command shows what's available

### 3. Backend Auto-Detection

**Decision**: Default `--backend=auto` that tries backends in priority order

**Rationale**:
- Better user experience (just works)
- Priority order: mlx (fastest on Apple Silicon) → faster-whisper (CUDA/CPU) → fallback whisper

**Trade-offs**:
- May select suboptimal backend if preferred is unavailable
- Acceptable because: Users can explicitly specify backend

### 4. Database Schema: Two Tables with Content-Based Identification

**Decision**: Separate `transcriptions` (metadata) and `transcription_segments` (text) tables, with auto-increment PK and SHA256 content hash

**Rationale**:
- Enables full-text search on segments without duplicating metadata
- Efficient queries: join only when needed
- Follows existing pattern (`episodes` vs `episodes_extended`)
- Content hash prevents duplicate transcriptions of same audio
- Survives file moves/renames (hash remains constant)
- Auto-increment PK provides stable foreign key references

**Trade-offs**:
- More complex queries for combined data
- Must compute hash before transcription (adds ~1-2 seconds for large files)
- Acceptable because: Cleaner separation, better performance for search, prevents wasted work re-transcribing same content

### 5. Output Directory Structure

**Decision**: Mirror `episode_downloads/` structure in `transcriptions/`

**Rationale**:
- Consistency with existing patterns
- Users familiar with download structure understand transcription structure
- Easy to correlate audio files with transcriptions

**Trade-offs**:
- Requires duplicating directory hierarchy
- Acceptable because: Disk space is cheap, clarity is valuable

### 6. Output Formats

**Decision**: Support TXT, JSON, SRT, VTT formats

**Rationale**:
- TXT: Human-readable
- JSON: Machine-readable with full metadata
- SRT/VTT: Subtitle formats for video players

**Trade-offs**:
- More code to maintain format writers
- Acceptable because: Standard formats, high utility

### 7. Synchronous vs. Asynchronous Processing

**Decision**: Synchronous processing with Rich progress bars

**Rationale**:
- Consistency with existing CLI commands (all are synchronous)
- Simpler implementation
- Transcription is CPU/GPU bound, not I/O bound

**Trade-offs**:
- Cannot process multiple files in parallel
- Acceptable because: Transcription is sequential anyway (GPU/model loading), users can run multiple CLI instances if needed

## Dependency Installation Guide

### For Apple Silicon Users (macOS)

```bash
# Install with MLX Whisper support
uv pip install -e ".[transcription-mlx]"

# Or after installation
pip install mlx-whisper
```

### For Linux/CUDA Users

```bash
# Install PyTorch with CUDA support first
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Then install retrocast with CUDA transcription
uv pip install -e ".[transcription-cuda]"
```

### For CPU-Only Users

```bash
# Install with CPU-only support
uv pip install -e ".[transcription-cpu]"
```

### For All Features (Development)

```bash
# Install everything (may require platform-specific PyTorch)
uv pip install -e ".[transcription-full]"
```

## Testing Strategy

### Unit Tests
- Data classes and utilities
- Format writers
- Backend detection logic (mocked imports)

### Integration Tests
- Each backend with test audio file (short clip)
- Database operations
- CLI command execution

### Mocking Strategy
- Mock expensive operations (model loading, transcription)
- Use small test audio files (< 10 seconds)
- Mock pyannote.audio for diarization tests

## Documentation Requirements

### User Documentation
1. **Installation Guide**: Platform-specific instructions
2. **Quickstart**: Basic transcription example
3. **Backend Selection**: When to use which backend
4. **Output Formats**: Description of each format
5. **Troubleshooting**: Common issues (CUDA not found, etc.)

### Developer Documentation
1. **Architecture Overview**: Class hierarchy diagram
2. **Adding New Backends**: Step-by-step guide
3. **Testing Guide**: How to run and write tests
4. **Database Schema**: Table descriptions and relationships

## Risk Assessment

### High Risk
- **CUDA Installation Complexity**: Users may struggle with CUDA setup
  - Mitigation: Provide detailed installation guide, CPU fallback

- **Model Download Size**: Whisper models are large (140MB to 3GB)
  - Mitigation: Default to "base" model (140MB), document model sizes

### Medium Risk
- **Pyannote.audio Hugging Face Token**: Requires user registration
  - Mitigation: Make diarization optional, document token setup

- **Performance on Large Files**: Hour-long podcasts may take significant time
  - Mitigation: Add progress bars, document expected times

### Low Risk
- **Platform Detection Errors**: May select wrong backend
  - Mitigation: Allow explicit backend selection

## Critical Files for Implementation

Based on this plan, here are the 5 most critical files:

1. **src/retrocast/transcription/base.py** - Core abstractions: `TranscriptionBackend`, `TranscriptionResult`, `TranscriptionSegment` classes that all backends implement

2. **src/retrocast/transcription/transcription_manager.py** - Main orchestration class: handles backend selection, file processing, output writing, and database updates

3. **src/retrocast/datastore.py** - Add transcription tables and methods: `ensure_transcription_tables()`, `upsert_transcription()`, `search_transcriptions()`

4. **src/retrocast/process_commands.py** - New CLI command group: implements `process transcribe`, `list-backends`, and search commands

5. **pyproject.toml** - Dependency management: add `[project.optional-dependencies]` for `transcription-mlx`, `transcription-cuda`, `transcription-cpu`, and `transcription-diarization` extras

## Next Steps

1. Review this plan and provide feedback
2. Begin Phase 1 implementation (Core Infrastructure)
3. Test on both macOS (Apple Silicon) and Linux (CUDA) platforms
4. Iterate based on real-world usage

## References

- [mlx-whisper on PyPI](https://pypi.org/project/mlx-whisper/)
- [faster-whisper on GitHub](https://github.com/SYSTRAN/faster-whisper)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [pyannote.audio](https://github.com/pyannote/pyannote-audio)
- [Python Dependency Specifiers](https://packaging.python.org/en/latest/specifications/dependency-specifiers/)

---

## Implementation Task Checklist

This checklist tracks progress through all implementation phases. Check off tasks as they are completed. This is especially useful for resuming work after interruptions or context limits.

### Phase 1: Core Infrastructure ✅ / ❌

**Module Setup**
- [ ] Create `src/retrocast/transcription/` directory
- [ ] Create `src/retrocast/transcription/__init__.py` with public API exports
- [ ] Create `src/retrocast/transcription/backends/` directory
- [ ] Create `src/retrocast/transcription/backends/__init__.py`

**Base Classes & Data Models** (`base.py`)
- [ ] Implement `TranscriptionSegment` dataclass
- [ ] Implement `TranscriptionResult` dataclass
- [ ] Implement `TranscriptionBackend` abstract base class
  - [ ] Add `name` property
  - [ ] Add `is_available()` method
  - [ ] Add `transcribe()` method
  - [ ] Add `platform_info()` method (for CLI display)
  - [ ] Add `description()` method (for CLI display)

**Utilities** (`utils.py`)
- [ ] Implement `compute_audio_hash()` function (SHA256)
- [ ] Implement `check_transcription_exists()` function
- [ ] Implement `_sanitize_for_path()` function (reuse from existing code if available)
- [ ] Implement `get_output_path()` function (determines transcription file path)
- [ ] Add path resolution utilities for podcast/episode directory structure

**Output Format Writers** (`output_formats.py`)
- [ ] Implement `FormatWriter` base class
- [ ] Implement `TXTFormatWriter` class
  - [ ] Write plain text with optional timestamps
- [ ] Implement `JSONFormatWriter` class
  - [ ] Include full metadata, segments, speaker info
- [ ] Implement `SRTFormatWriter` class
  - [ ] Standard SubRip subtitle format
- [ ] Implement `VTTFormatWriter` class
  - [ ] WebVTT subtitle format
- [ ] Add format writer registry/factory function

**Transcription Manager** (`transcription_manager.py`)
- [ ] Implement `TranscriptionManager` class skeleton
- [ ] Add `__init__()` with backend selection logic
- [ ] Add `_select_backend()` method (auto-detection)
- [ ] Add `transcribe_file()` method stub
- [ ] Add `_compute_hash_and_check_duplicate()` helper
- [ ] Add `_save_transcription()` method stub
- [ ] Add progress callback support (for Rich progress bars)

**Database Schema** (`datastore.py` modifications)
- [ ] Add `transcriptions` table creation in `_prepare_db()`
  - [ ] Add all fields as specified in schema
  - [ ] Set `transcription_id` as auto-increment PK
  - [ ] Create unique index on `audio_content_hash`
  - [ ] Create index on `media_path`
  - [ ] Create index on `episode_url`
- [ ] Add `transcription_segments` table creation
  - [ ] Add all fields as specified in schema
  - [ ] Set foreign key to `transcriptions.transcription_id`
  - [ ] Create composite index on `(transcription_id, segment_index)`
  - [ ] Enable FTS5 on `text` column
- [ ] Implement `upsert_transcription()` method
- [ ] Implement `upsert_transcription_segments()` method
- [ ] Implement `get_transcription_by_hash()` method
- [ ] Implement `get_transcription_by_path()` method
- [ ] Implement `search_transcriptions()` method (FTS)

**Unit Tests**
- [ ] Test `TranscriptionSegment` and `TranscriptionResult` dataclasses
- [ ] Test `compute_audio_hash()` with test audio file
- [ ] Test path sanitization utilities
- [ ] Test all format writers with mock data
- [ ] Test database operations with in-memory SQLite
- [ ] Test duplicate detection logic

**Documentation**
- [ ] Add docstrings to all public classes and methods
- [ ] Document the episode identification strategy
- [ ] Document the content hashing approach

---

### Phase 2: MLX Whisper Backend ✅ / ❌

**Backend Implementation** (`backends/mlx_whisper.py`)
- [ ] Create `MLXWhisperBackend` class inheriting from `TranscriptionBackend`
- [ ] Implement `name` property (return "mlx-whisper")
- [ ] Implement `is_available()` method
  - [ ] Check for `mlx_whisper` import
  - [ ] Verify platform is Darwin (macOS)
- [ ] Implement `platform_info()` method
- [ ] Implement `description()` method
- [ ] Implement `transcribe()` method
  - [ ] Load MLX Whisper model
  - [ ] Call transcription
  - [ ] Convert result to `TranscriptionResult`
  - [ ] Handle errors gracefully
- [ ] Add logging with loguru
- [ ] Add model caching (avoid reloading on each transcription)

**Integration with Manager**
- [ ] Register MLX backend in `backends/__init__.py`
- [ ] Add to backend registry/discovery
- [ ] Test auto-detection on macOS

**Testing**
- [ ] Create mock tests for MLX backend (mock mlx_whisper import)
- [ ] Add integration test with small test audio file (requires macOS)
- [ ] Test error handling (missing dependencies, corrupted files)

**Documentation**
- [ ] Add installation instructions for `[transcription-mlx]`
- [ ] Document MLX-specific settings (model sizes, performance)
- [ ] Add troubleshooting section

---

### Phase 3: Faster-Whisper Backend ✅ / ❌

**Backend Implementation** (`backends/faster_whisper.py`)
- [ ] Create `FasterWhisperBackend` class inheriting from `TranscriptionBackend`
- [ ] Implement `name` property (return "faster-whisper")
- [ ] Implement `is_available()` method
  - [ ] Check for `faster_whisper` import
  - [ ] Detect CUDA availability
- [ ] Implement `platform_info()` method (show CUDA/CPU mode)
- [ ] Implement `description()` method
- [ ] Implement `transcribe()` method
  - [ ] Load faster-whisper model with device auto-detection
  - [ ] Call transcription with appropriate compute type
  - [ ] Convert result to `TranscriptionResult`
  - [ ] Handle errors gracefully
- [ ] Add performance logging (transcription time, real-time factor)
- [ ] Add model caching

**Integration with Manager**
- [ ] Register faster-whisper backend in `backends/__init__.py`
- [ ] Add to backend registry/discovery
- [ ] Test auto-detection on Linux and macOS

**Testing**
- [ ] Create mock tests for faster-whisper backend
- [ ] Add integration test with small test audio file
- [ ] Test CUDA detection (if available)
- [ ] Test CPU fallback
- [ ] Test error handling

**Documentation**
- [ ] Add installation instructions for `[transcription-cuda]` and `[transcription-cpu]`
- [ ] Document CUDA setup (PyTorch installation)
- [ ] Add performance benchmarks
- [ ] Add troubleshooting section (CUDA not found, etc.)

---

### Phase 4: CLI Integration ✅ / ❌

**CLI Command File** (`process_commands.py`)
- [ ] Create new file `src/retrocast/process_commands.py`
- [ ] Import necessary modules (rich_click, Rich, pathlib, etc.)
- [ ] Create `process` command group with `@click.group()`

**`transcribe` Command**
- [ ] Implement `transcribe` command with all options:
  - [ ] `paths` argument (multiple file/directory paths)
  - [ ] `--backend` option (auto, mlx, faster, whisper)
  - [ ] `--model` option (tiny, base, small, medium, large)
  - [ ] `--language` option
  - [ ] `--diarize` flag
  - [ ] `--output-dir` option
  - [ ] `--format` option (txt, json, srt, vtt)
  - [ ] `--force` flag (re-transcribe even if exists)
- [ ] Add path discovery (find audio files in directories)
- [ ] Add Rich progress bars for batch processing
- [ ] Add error handling and user-friendly messages
- [ ] Integrate with `TranscriptionManager`
- [ ] Save results to database

**`list-backends` Command**
- [ ] Implement `list-backends` command
- [ ] Create Rich Table showing:
  - [ ] Backend name
  - [ ] Availability status (✓/✗)
  - [ ] Platform info
  - [ ] Description
- [ ] Test on multiple platforms

**`test-backend` Command**
- [ ] Implement `test-backend BACKEND` command
- [ ] Attempt to load backend and report status
- [ ] Show detailed error messages if unavailable

**`search` Command**
- [ ] Implement `search QUERY` command
- [ ] Add options:
  - [ ] `--podcast` filter
  - [ ] `--limit` option
  - [ ] `--format` output format
- [ ] Perform FTS search on transcription segments
- [ ] Display results in Rich Table with context
- [ ] Add result highlighting

**CLI Integration**
- [ ] Import `process` command group in `cli.py`
- [ ] Add `cli.add_command(process)` to register
- [ ] Test all commands with `uv run python -m retrocast.cli process --help`

**Testing**
- [ ] Test `transcribe` command with test audio files
- [ ] Test `list-backends` on macOS and Linux
- [ ] Test `search` command with sample data
- [ ] Test error handling (invalid paths, missing backends)

**Documentation**
- [ ] Add CLI documentation for all `process` commands
- [ ] Add usage examples
- [ ] Add GIF/screenshots of CLI output

---

### Phase 5: Speaker Diarization (Optional) ✅ / ❌

**Diarization Module** (`diarization.py`)
- [ ] Create `SpeakerDiarizer` class
- [ ] Implement `is_available()` method (check pyannote.audio)
- [ ] Implement `diarize()` method
  - [ ] Load pyannote.audio pipeline
  - [ ] Handle Hugging Face token requirements
  - [ ] Process audio file
  - [ ] Return speaker segments
- [ ] Implement `merge_with_transcription()` method
  - [ ] Align diarization timestamps with transcription segments
  - [ ] Assign speaker labels to segments
- [ ] Add error handling and logging

**Integration with Backends**
- [ ] Add `--diarize` support to `TranscriptionManager`
- [ ] Run diarization after transcription
- [ ] Merge results before saving
- [ ] Update database with speaker information

**Database Updates**
- [ ] Ensure `speaker` column in `transcription_segments` is populated
- [ ] Update `speaker_count` in `transcriptions` table
- [ ] Set `has_diarization` flag

**Testing**
- [ ] Mock tests for diarization module
- [ ] Integration test with small audio file (requires pyannote.audio)
- [ ] Test speaker label assignment

**Documentation**
- [ ] Add installation instructions for `[transcription-diarization]`
- [ ] Document Hugging Face token setup
- [ ] Add examples of diarized output

---

### Phase 6: Search and Query Features ✅ / ❌

**Search Implementation**
- [ ] Enhance `search_transcriptions()` in `datastore.py`
- [ ] Add filters:
  - [ ] Podcast title
  - [ ] Date range
  - [ ] Speaker (if diarization enabled)
  - [ ] Backend/model used
- [ ] Implement result ranking
- [ ] Add context extraction (surrounding segments)

**CLI Enhancements**
- [ ] Add advanced search options to `search` command
- [ ] Implement result highlighting with Rich
- [ ] Add export options (CSV, JSON, HTML)
- [ ] Add pagination for large result sets

**Testing**
- [ ] Test search with various filters
- [ ] Test result ranking
- [ ] Test export formats

**Documentation**
- [ ] Add search query syntax documentation
- [ ] Add filter examples
- [ ] Add search best practices

---

### Phase 7: Dependency Management & Packaging ✅ / ❌

**pyproject.toml Updates**
- [ ] Add `[project.optional-dependencies]` section
- [ ] Add `transcription-mlx` extra with platform markers
- [ ] Add `transcription-cuda` extra
- [ ] Add `transcription-cpu` extra
- [ ] Add `transcription-diarization` extra
- [ ] Add `transcription-full` metapackage
- [ ] Test installation with `uv pip install -e ".[transcription-mlx]"`

**Platform Testing**
- [ ] Test on macOS (Apple Silicon) with MLX
- [ ] Test on Linux with CUDA (if available)
- [ ] Test on Linux with CPU-only
- [ ] Test on Windows (optional, CPU-only)

---

### Phase 8: Documentation & Polish ✅ / ❌

**User Documentation**
- [ ] Write installation guide (all platforms)
- [ ] Write quickstart tutorial
- [ ] Write backend selection guide
- [ ] Write output format guide
- [ ] Write troubleshooting guide
- [ ] Add FAQ section

**Developer Documentation**
- [ ] Document architecture overview
- [ ] Create class hierarchy diagram
- [ ] Write "Adding New Backends" guide
- [ ] Document testing strategy
- [ ] Document database schema

**Code Quality**
- [ ] Run ruff linter and fix all issues
- [ ] Run black formatter
- [ ] Run ty type checker and fix type errors
- [ ] Add comprehensive docstrings
- [ ] Review and refactor for clarity

**Final Testing**
- [ ] Run full test suite
- [ ] Perform end-to-end integration tests
- [ ] Test on real podcast episodes
- [ ] Performance testing (large files, batch processing)

---

### Phase 9: Release Preparation ✅ / ❌

**Pre-Release Checklist**
- [ ] Verify all tests pass
- [ ] Update README.md with transcription features
- [ ] Update CHANGELOG.md
- [ ] Tag release version
- [ ] Create GitHub release with notes
- [ ] Update documentation website (if applicable)

**Post-Release**
- [ ] Monitor for user feedback
- [ ] Address initial bug reports
- [ ] Plan future enhancements

---

## Progress Tracking Notes

**Current Phase**: _[Update this as you progress]_

**Last Completed Task**: _[Note the last completed item]_

**Next Steps**: _[List immediate next 2-3 tasks]_

**Blockers**: _[Note any blockers or issues]_

**Notes**: _[Any important notes or decisions made during implementation]_
