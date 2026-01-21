# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Audio Transcription Module
- New `retrocast transcription` command group for audio-to-text transcription
- Multiple backend support with automatic detection:
  - **MLX Whisper**: Optimized for Apple Silicon (M1/M2/M3) Macs
  - **faster-whisper**: CUDA GPU and CPU support for Linux/Windows
- Whisper model support (tiny, base, small, medium, large)
- Multiple output formats: TXT, JSON, SRT (subtitles), VTT (WebVTT)
- Content-based deduplication using SHA256 hashing
- Full-text search across transcribed content using SQLite FTS5
- Rich CLI with progress bars and colored output

#### Transcription CLI Commands
- `retrocast transcription process PATH...` - Transcribe audio files
- `retrocast transcription backends list` - List available backends with status
- `retrocast transcription backends test BACKEND` - Test specific backend availability
- `retrocast transcription search QUERY` - Full-text search across transcriptions
- `retrocast transcription summary` - Show overall transcription statistics
- `retrocast transcription podcasts list` - List podcasts with transcriptions
- `retrocast transcription podcasts summary [PODCAST]` - Detailed podcast statistics
- `retrocast transcription episodes list` - Paginated episode listing with filters
- `retrocast transcription episodes summary` - Aggregate episode statistics

#### Transcription Database Schema
- New `transcriptions` table for transcription metadata
- New `transcription_segments` table for timestamped text segments
- FTS5 full-text search enabled on segment text
- Content hash indexing for duplicate detection

#### Developer Documentation
- Comprehensive user guide: `docs/TRANSCRIPTION.md`
- Developer documentation: `docs/TRANSCRIPTION_DEVELOPER.md`
- Architecture diagrams and backend implementation guide

### Changed

- Enhanced `pyproject.toml` with optional transcription dependencies:
  - `transcription-mlx` for Apple Silicon
  - `transcription-cuda` for NVIDIA GPU
  - `transcription-cpu` for CPU-only
  - `transcription-diarization` for speaker diarization (future)
- Added poe tasks for transcription backend installation:
  - `poe install:transcription-mlx`
  - `poe install:transcription-cuda`
  - `poe install:transcription-cpu`

### Technical Details

- 126 tests passing with comprehensive coverage
- Type-checked with ty type checker
- Formatted with ruff and black
- Class-based backend architecture with abstract base classes
- Strategy pattern for backend selection
- Platform-specific dependency management via PEP 508 markers

## [0.1.0] - Initial Release

### Added

- Core Overcast data extraction pipeline
- SQLite database storage with sqlite-utils
- Authentication with Overcast API
- OPML import/export
- Feed and episode metadata extraction
- Transcript download from podcast feeds
- Episode download database with full-text search
- HTML output generation
- Integration with podcast-archiver for downloads
- Chapter marker extraction
- Datasette compatibility

[Unreleased]: https://github.com/crossjam/retrocast/compare/main...HEAD
[0.1.0]: https://github.com/crossjam/retrocast/releases/tag/v0.1.0
