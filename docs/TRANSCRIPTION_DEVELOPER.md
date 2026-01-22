# Transcription Module - Developer Documentation

This document provides technical documentation for developers working with or extending the retrocast transcription module.

## Architecture Overview

The transcription module follows a **class-based architecture with the Strategy Pattern** for backend implementations. This design was chosen over a plugin system (like pluggy) for several reasons:

1. **Consistency**: Matches existing retrocast codebase patterns
2. **Simplicity**: Only 2-3 backends needed initially
3. **Type Safety**: Better IDE support and type checking
4. **No Plugin Infrastructure**: No dependency on plugin frameworks

### Module Structure

```
src/retrocast/transcription/
├── __init__.py                 # Public API exports
├── base.py                     # Abstract base classes and data models
├── utils.py                    # Path handling, hashing, utilities
├── output_formats.py           # Format writers (TXT, JSON, SRT, VTT)
├── transcription_manager.py    # Main orchestration class
└── backends/
    ├── __init__.py             # Backend registry and discovery
    ├── mlx_whisper.py          # Apple Silicon backend (mlx-whisper)
    └── faster_whisper.py       # CUDA/CPU backend (faster-whisper)
```

### Data Flow

```
Audio File
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│  TranscriptionManager                                        │
│  ├── Compute SHA256 hash                                     │
│  ├── Check for existing transcription (deduplication)        │
│  ├── Select backend (auto or specified)                      │
│  │       │                                                   │
│  │       ▼                                                   │
│  │   ┌─────────────────────────────────────────────────────┐ │
│  │   │  TranscriptionBackend (MLX or faster-whisper)       │ │
│  │   │  └── transcribe(audio_path, language, model_size)   │ │
│  │   └─────────────────────────────────────────────────────┘ │
│  │       │                                                   │
│  │       ▼                                                   │
│  │   TranscriptionResult                                     │
│  │       │                                                   │
│  ├── Save to file (via FormatWriter)                         │
│  └── Save to database (Datastore)                            │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
Output: JSON/TXT/SRT/VTT file + SQLite database record
```

## Class Hierarchy

### Core Data Classes

```
TranscriptionSegment (dataclass)
├── start: float              # Start time in seconds
├── end: float                # End time in seconds
├── text: str                 # Transcribed text
├── speaker: Optional[str]    # Speaker ID (for diarization)
└── Methods:
    ├── duration() -> float
    └── __str__() -> str

TranscriptionResult (dataclass)
├── segments: list[TranscriptionSegment]
├── text: str                 # Full transcription text
├── language: str             # Language code (e.g., "en")
├── duration: float           # Audio duration in seconds
├── metadata: dict            # Backend-specific metadata
└── Methods:
    ├── word_count() -> int
    ├── segment_count() -> int
    ├── has_speakers() -> bool
    └── get_speakers() -> set[str]
```

### Abstract Base Class

```
TranscriptionBackend (ABC)
├── Properties:
│   └── name: str             # Backend identifier
├── Abstract Methods:
│   ├── is_available() -> bool
│   └── transcribe(audio_path, language, model_size) -> TranscriptionResult
└── Default Methods:
    ├── platform_info() -> str
    └── description() -> str
```

### Backend Implementations

```
MLXWhisperBackend(TranscriptionBackend)
├── name: "mlx-whisper"
├── is_available(): Checks mlx_whisper import + Darwin platform
├── transcribe(): Uses mlx_whisper.transcribe()
└── Features: Apple Silicon Metal acceleration

FasterWhisperBackend(TranscriptionBackend)
├── name: "faster-whisper"
├── is_available(): Checks faster_whisper import
├── transcribe(): Uses WhisperModel with auto device detection
└── Features: CUDA acceleration with CPU fallback
```

### Format Writers

```
FormatWriter (ABC)
├── Properties:
│   └── extension: str
└── Abstract Methods:
    └── write(result, output_path) -> None

TXTFormatWriter(FormatWriter)     # Plain text with timestamps
JSONFormatWriter(FormatWriter)    # Full metadata and segments
SRTFormatWriter(FormatWriter)     # SubRip subtitle format
VTTFormatWriter(FormatWriter)     # WebVTT subtitle format
```

### Manager Class

```
TranscriptionManager
├── __init__(backend, model_size, output_dir, datastore)
├── transcribe_file(audio_path, podcast_title, ...) -> TranscriptionResult
├── _select_backend() -> TranscriptionBackend
├── _compute_hash_and_check_duplicate() -> tuple[str, bool, dict|None]
├── _save_transcription() -> Path
└── _save_to_database() -> None
```

## Adding New Backends

To add a new transcription backend, follow these steps:

### Step 1: Create Backend File

Create a new file in `src/retrocast/transcription/backends/`:

```python
# backends/new_backend.py
"""New transcription backend implementation."""

from pathlib import Path
from typing import Optional

from retrocast.transcription.base import (
    TranscriptionBackend,
    TranscriptionResult,
    TranscriptionSegment,
)


class NewBackend(TranscriptionBackend):
    """New backend - description of what makes it special."""

    @property
    def name(self) -> str:
        return "new-backend"

    def is_available(self) -> bool:
        """Check if backend dependencies are available."""
        try:
            import new_backend_library  # noqa: F401
            return True
        except ImportError:
            return False

    def platform_info(self) -> str:
        """Return platform-specific information."""
        return "Any platform"

    def description(self) -> str:
        """Return brief backend description."""
        return "New Backend - description for CLI display"

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model_size: str = "base",
    ) -> TranscriptionResult:
        """Transcribe audio file using new backend."""
        # Import lazily to avoid import errors when not installed
        import new_backend_library

        # Perform transcription
        raw_result = new_backend_library.transcribe(
            str(audio_path),
            language=language,
            model=model_size,
        )

        # Convert to TranscriptionResult
        segments = [
            TranscriptionSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"],
                speaker=None,
            )
            for seg in raw_result["segments"]
        ]

        return TranscriptionResult(
            segments=segments,
            text=raw_result["text"],
            language=raw_result.get("language", "en"),
            duration=raw_result.get("duration", 0.0),
            metadata={
                "backend": self.name,
                "model_size": model_size,
                # Add backend-specific metadata
            },
        )
```

### Step 2: Register Backend

Update `backends/__init__.py` to register the new backend:

```python
def get_all_backends() -> list[Type[TranscriptionBackend]]:
    # ... existing backends ...

    try:
        from retrocast.transcription.backends.new_backend import NewBackend
        register_backend(NewBackend)
    except ImportError:
        pass  # New backend dependencies not available

    return _BACKENDS.copy()
```

### Step 3: Add Optional Dependencies

Update `pyproject.toml`:

```toml
[project.optional-dependencies]
transcription-new = [
    "new-backend-library>=1.0.0",
]
```

### Step 4: Add Tests

Create `tests/transcription/test_new_backend.py`:

```python
"""Tests for new backend."""

import pytest
from unittest.mock import MagicMock, patch

from retrocast.transcription.backends.new_backend import NewBackend


class TestNewBackend:
    """Tests for NewBackend class."""

    def test_name(self):
        """Test backend name property."""
        backend = NewBackend()
        assert backend.name == "new-backend"

    def test_is_available_when_installed(self):
        """Test is_available when library is installed."""
        with patch.dict("sys.modules", {"new_backend_library": MagicMock()}):
            backend = NewBackend()
            assert backend.is_available() is True

    def test_is_available_when_not_installed(self):
        """Test is_available when library is not installed."""
        # Remove from sys.modules if present
        with patch.dict("sys.modules", {"new_backend_library": None}):
            backend = NewBackend()
            # Force import error
            with patch.object(backend, "is_available", return_value=False):
                assert backend.is_available() is False

    def test_transcribe(self):
        """Test transcription with mocked library."""
        mock_result = {
            "text": "Test transcription",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test"}],
            "language": "en",
            "duration": 1.0,
        }

        with patch("new_backend_library.transcribe", return_value=mock_result):
            backend = NewBackend()
            result = backend.transcribe(Path("/test/audio.mp3"))

            assert result.text == "Test transcription"
            assert len(result.segments) == 1
```

### Step 5: Update Documentation

Add documentation for the new backend in `TRANSCRIPTION.md`.

## Database Schema

The transcription module uses two SQLite tables managed by the `Datastore` class.

### `transcriptions` Table

Primary table storing transcription metadata.

| Column | Type | Description |
|--------|------|-------------|
| `transcription_id` | INTEGER | Auto-increment primary key |
| `audio_content_hash` | TEXT | SHA256 hash of audio file (unique index) |
| `media_path` | TEXT | Current path to audio file (indexed) |
| `file_size` | INTEGER | Audio file size in bytes |
| `transcription_path` | TEXT | Path to output transcription file |
| `episode_url` | TEXT | Optional URL linking to episode metadata (indexed) |
| `podcast_title` | TEXT | Podcast title for organization |
| `episode_title` | TEXT | Episode title |
| `backend` | TEXT | Backend used (e.g., "mlx-whisper") |
| `model_size` | TEXT | Model size (tiny, base, small, medium, large) |
| `language` | TEXT | Detected/specified language code |
| `duration` | REAL | Audio duration in seconds |
| `transcription_time` | REAL | Processing time in seconds |
| `has_diarization` | INTEGER | Boolean: speaker diarization applied (0/1) |
| `speaker_count` | INTEGER | Number of detected speakers |
| `word_count` | INTEGER | Total words in transcription |
| `created_time` | TEXT | ISO8601 creation timestamp |
| `updated_time` | TEXT | ISO8601 update timestamp |
| `metadata_json` | TEXT | Full result metadata as JSON |

**Indexes:**
- UNIQUE on `audio_content_hash` - prevents duplicate transcriptions
- INDEX on `media_path` - efficient file lookups
- INDEX on `episode_url` - linking to episode metadata

### `transcription_segments` Table

Stores individual transcription segments for full-text search.

| Column | Type | Description |
|--------|------|-------------|
| `transcription_id` | INTEGER | Foreign key to transcriptions |
| `segment_index` | INTEGER | Segment number (0-based) |
| `start_time` | REAL | Start time in seconds |
| `end_time` | REAL | End time in seconds |
| `text` | TEXT | Segment text (FTS5 enabled) |
| `speaker` | TEXT | Optional speaker identifier |

**Indexes:**
- COMPOSITE INDEX on `(transcription_id, segment_index)`
- FTS5 virtual table on `text` column for full-text search

### Content-Based Deduplication

The `audio_content_hash` column stores a SHA256 hash of the audio file content. This enables:

1. **Deduplication**: Same audio won't be transcribed twice
2. **Portability**: Transcriptions survive file moves/renames
3. **Integrity**: Can verify audio hasn't changed

Hash computation:
```python
def compute_audio_hash(audio_path: Path, chunk_size: int = 8192) -> str:
    sha256_hash = hashlib.sha256()
    with open(audio_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()
```

## Testing Strategy

### Test Organization

```
tests/
└── transcription/
    ├── __init__.py
    ├── conftest.py              # Shared fixtures
    ├── test_base.py             # Data class tests
    ├── test_utils.py            # Utility function tests
    ├── test_output_formats.py   # Format writer tests
    ├── test_transcription_manager.py  # Manager tests
    ├── test_datastore_transcription.py  # Database tests
    ├── test_mlx_whisper_backend.py   # MLX backend tests
    ├── test_faster_whisper_backend.py # faster-whisper tests
    └── test_process_commands.py  # CLI tests
```

### Mocking Strategy

Since transcription backends depend on large ML libraries and models, tests use mocking extensively:

```python
# Mock entire library import
with patch.dict("sys.modules", {"mlx_whisper": MagicMock()}):
    backend = MLXWhisperBackend()

# Mock transcription call
mock_result = {
    "text": "Test",
    "segments": [{"start": 0.0, "end": 1.0, "text": "Test"}],
}
with patch("mlx_whisper.transcribe", return_value=mock_result):
    result = backend.transcribe(audio_path)
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run transcription tests only
uv run pytest tests/transcription/

# Run with coverage
uv run pytest --cov=retrocast.transcription tests/transcription/

# Run specific test file
uv run pytest tests/transcription/test_mlx_whisper_backend.py -v
```

### Test Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary audio file for testing."""
    audio_path = tmp_path / "test.mp3"
    audio_path.write_bytes(b"fake audio content")
    return audio_path

@pytest.fixture
def mock_transcription_result():
    """Create a mock TranscriptionResult for testing."""
    return TranscriptionResult(
        segments=[TranscriptionSegment(0.0, 1.0, "Test text")],
        text="Test text",
        language="en",
        duration=1.0,
        metadata={"backend": "test"},
    )

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return Datastore(db_path)
```

## CLI Commands

The transcription CLI is implemented in `src/retrocast/process_commands.py`:

```
retrocast transcription
├── process PATHS...          # Transcribe audio files
├── backends
│   ├── list                  # List available backends
│   └── test BACKEND          # Test specific backend
├── search QUERY              # Search transcriptions
├── summary                   # Overall transcription stats
├── podcasts
│   ├── list                  # List podcasts with transcriptions
│   └── summary [PODCAST]     # Podcast-specific stats
└── episodes
    ├── list                  # List transcribed episodes
    └── summary               # Episode aggregate stats
```

### Command Implementation Pattern

```python
@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--backend", type=click.Choice(["auto", "mlx-whisper", "faster-whisper"]))
@click.option("--model", type=click.Choice(["tiny", "base", "small", "medium", "large"]))
@click.pass_context
def process(ctx, paths, backend, model):
    """Transcribe audio files."""
    # Initialize manager
    manager = TranscriptionManager(
        backend=backend,
        model_size=model,
        output_dir=output_dir,
        datastore=datastore,
    )

    # Process files with Rich progress
    with Progress() as progress:
        task = progress.add_task("Transcribing...", total=len(paths))
        for path in paths:
            result = manager.transcribe_file(path)
            progress.advance(task)
```

## Error Handling

### Backend Errors

```python
class TranscriptionError(Exception):
    """Base exception for transcription errors."""
    pass

class BackendNotAvailableError(TranscriptionError):
    """Raised when requested backend is not installed."""
    pass

class TranscriptionFailedError(TranscriptionError):
    """Raised when transcription process fails."""
    pass
```

### Graceful Degradation

The auto-detection system provides graceful degradation:

1. Try MLX Whisper (fastest on Apple Silicon)
2. Fall back to faster-whisper (CUDA if available, else CPU)
3. Raise clear error if no backend available

## Performance Considerations

### Model Caching

Backends should cache loaded models to avoid reloading:

```python
class FasterWhisperBackend(TranscriptionBackend):
    _model = None  # Class-level cache

    def _get_model(self, model_size: str):
        if self._model is None or self._current_size != model_size:
            self._model = WhisperModel(model_size, device=self._device)
            self._current_size = model_size
        return self._model
```

### Memory Management

- Smaller models use less memory (tiny: ~1GB, large: ~10GB)
- CUDA memory is freed automatically when process ends
- For batch processing, consider model_size vs. available memory

### Progress Callbacks

The `TranscriptionManager.transcribe_file()` accepts an optional progress callback:

```python
def progress_callback(message: str):
    console.print(f"[blue]{message}[/blue]")

result = manager.transcribe_file(
    audio_path,
    progress_callback=progress_callback,
)
```

## Related Documentation

- [User Guide](../TRANSCRIPTION.md) - End-user documentation
- [Implementation Plan](../plans/2025-12-16-transcription-implementation-plan.md) - Detailed implementation phases
- [API Reference](./api/) - Generated API documentation (if available)
