# Transcription Guide for retrocast

## Overview

The retrocast transcription module enables you to transcribe podcast audio files to searchable text using state-of-the-art speech recognition models. The module supports multiple backends optimized for different platforms and use cases.

## Features

- 🎯 **Multiple Backends**: MLX Whisper (Apple Silicon), faster-whisper (CUDA/CPU), OpenAI Whisper
- 🚀 **Auto-Detection**: Automatically selects the best available backend for your platform
- 💾 **Content Deduplication**: SHA256 hashing prevents re-transcribing the same audio
- 🔍 **Full-Text Search**: Search across all transcribed content using SQLite FTS5
- 📝 **Multiple Formats**: Export as TXT, JSON, SRT (subtitles), or VTT (WebVTT)
- 📊 **Rich CLI**: Progress bars, colored output, and detailed status messages

## Installation

retrocast provides convenient poe tasks to install transcription backends for different platforms.

### For Apple Silicon (macOS)

MLX Whisper provides the best performance on M1/M2/M3 Macs:

```bash
# Recommended: Use poe task
poe install:transcription-mlx

# Alternative: Direct installation
uv pip install 'mlx-whisper>=0.4.0'
```

### For Linux with CUDA

For systems with NVIDIA GPUs and CUDA support:

```bash
# Recommended: Use poe task (installs PyTorch with CUDA + faster-whisper)
poe install:transcription-cuda

# Alternative: Manual installation
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
uv pip install 'faster-whisper>=1.0.0'
```

### For CPU-Only (Any Platform)

For systems without GPU acceleration:

```bash
# Recommended: Use poe task
poe install:transcription-cpu

# Alternative: Direct installation
uv pip install 'faster-whisper>=1.0.0' 'torch>=2.0.0'
```

### Verify Installation

After installing a backend, verify it's working:

```bash
# List available backends
retrocast process list-backends

# Test specific backend
retrocast process test-backend mlx-whisper
```

## Quick Start

### 1. Check Available Backends

Before transcribing, check which backends are available on your system:

```bash
retrocast process list-backends
```

Example output:
```
┌───────────────┬────────────────┬───────────────────────┬─────────────────────────────────────┐
│ Backend       │     Status     │ Platform              │ Description                         │
├───────────────┼────────────────┼───────────────────────┼─────────────────────────────────────┤
│ mlx-whisper   │ ✓ Available    │ macOS (Apple Silicon) │ MLX Whisper - optimized for Apple   │
│               │                │                       │ Silicon M1/M2/M3                    │
└───────────────┴────────────────┴───────────────────────┴─────────────────────────────────────┘
```

### 2. Test a Specific Backend

```bash
retrocast process test-backend mlx-whisper
```

### 3. Transcribe Your First File

```bash
# Transcribe a single audio file
retrocast process transcribe episode.mp3

# Transcribe all audio files in a directory
retrocast process transcribe /path/to/podcast/episodes/

# Transcribe with specific options
retrocast process transcribe --model medium --format srt episode.mp3
```

## CLI Command Reference

### `retrocast process transcribe`

Transcribe audio files to text.

**Usage:**
```bash
retrocast process transcribe [OPTIONS] PATHS...
```

**Arguments:**
- `PATHS`: One or more audio files or directories containing audio files

**Options:**

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--backend` | auto, mlx-whisper | auto | Transcription backend to use |
| `--model` | tiny, base, small, medium, large | base | Whisper model size |
| `--language` | en, es, fr, etc. | auto-detect | Audio language code |
| `--output-dir` | PATH | app_dir/transcriptions | Output directory for transcription files |
| `--format` | txt, json, srt, vtt | json | Output format |
| `--force` | flag | false | Re-transcribe even if already exists |
| `--db` | PATH | app_dir/overcast.db | Database file path |

**Supported Audio Formats:**
- MP3 (`.mp3`)
- M4A (`.m4a`)
- OGG (`.ogg`)
- Opus (`.opus`)
- WAV (`.wav`)
- FLAC (`.flac`)
- AAC (`.aac`)

### `retrocast process list-backends`

List all available transcription backends with their status.

**Usage:**
```bash
retrocast process list-backends
```

Shows a table with backend name, availability status, platform requirements, and description.

### `retrocast process test-backend`

Test if a specific backend is available and properly configured.

**Usage:**
```bash
retrocast process test-backend BACKEND_NAME
```

**Example:**
```bash
retrocast process test-backend mlx-whisper
```

### `retrocast process search`

Search transcribed content using full-text search.

**Usage:**
```bash
retrocast process search [OPTIONS] QUERY
```

**Arguments:**
- `QUERY`: Search query (supports full-text search syntax)

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--podcast` | TEXT | - | Filter by podcast title |
| `--limit` | INT | 10 | Maximum number of results |
| `--db` | PATH | app_dir/overcast.db | Database file path |

## Usage Examples

### Basic Transcription

```bash
# Transcribe a single file with defaults (base model, JSON output)
retrocast process transcribe episode.mp3
```

### Batch Processing

```bash
# Transcribe all MP3 files in a directory
retrocast process transcribe ~/Downloads/podcasts/

# Transcribe multiple specific files
retrocast process transcribe episode1.mp3 episode2.mp3 episode3.m4a
```

### Model Selection

```bash
# Use tiny model (fastest, lowest accuracy)
retrocast process transcribe --model tiny episode.mp3

# Use medium model (balanced speed/accuracy)
retrocast process transcribe --model medium episode.mp3

# Use large model (slowest, highest accuracy)
retrocast process transcribe --model large episode.mp3
```

**Model Size Comparison:**

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny | 39M | Fastest | Lowest | Quick drafts, testing |
| base | 74M | Fast | Good | General use (default) |
| small | 244M | Moderate | Better | Higher quality needed |
| medium | 769M | Slow | Very Good | Professional transcripts |
| large | 1550M | Slowest | Best | Maximum accuracy |

### Language Specification

```bash
# Transcribe Spanish audio
retrocast process transcribe --language es podcast_espanol.mp3

# Transcribe French audio
retrocast process transcribe --language fr interview.mp3

# Auto-detect language (default)
retrocast process transcribe podcast.mp3
```

### Output Formats

```bash
# Plain text with timestamps
retrocast process transcribe --format txt episode.mp3

# JSON with full metadata and segments
retrocast process transcribe --format json episode.mp3

# SRT subtitle format (for video)
retrocast process transcribe --format srt episode.mp3

# WebVTT format (for web players)
retrocast process transcribe --format vtt episode.mp3
```

**Format Details:**

- **TXT**: Human-readable plain text with optional timestamps and speaker labels
- **JSON**: Machine-readable format with complete metadata, segments, and timing
- **SRT**: SubRip subtitle format for video players
- **VTT**: WebVTT format for HTML5 video players

### Re-transcribing Files

```bash
# By default, already-transcribed files are skipped
retrocast process transcribe episode.mp3
# Output: "Already transcribed (use --force to re-transcribe)"

# Force re-transcription (e.g., to try a different model)
retrocast process transcribe --force --model large episode.mp3
```

### Custom Output Directory

```bash
# Save transcriptions to a specific directory
retrocast process transcribe --output-dir ~/transcripts/ episode.mp3

# Organize by project
retrocast process transcribe --output-dir ~/projects/podcast-analysis/transcripts/ *.mp3
```

### Searching Transcriptions

```bash
# Search all transcriptions
retrocast process search "machine learning"

# Search within a specific podcast
retrocast process search --podcast "My Podcast" "neural networks"

# Limit results
retrocast process search --limit 5 "python programming"

# Search for phrases
retrocast process search "artificial intelligence"
```

**Search Results Example:**
```
Found 3 result(s) for: machine learning

1. Tech Talk - Episode 42
   Time: 15:23
   We discuss the fundamentals of machine learning and how it's transforming...

2. AI Weekly - The Future of ML
   Time: 08:45
   Machine learning models have become increasingly sophisticated in recent...

3. Data Science Podcast - ML Basics
   Time: 22:10
   Let's dive into machine learning algorithms and their applications...
```

## Workflow Examples

### Transcribe a Podcast Series

```bash
# 1. Download episodes (using podcast-archiver or manually)
# 2. List available backends
retrocast process list-backends

# 3. Transcribe entire directory with medium model for better quality
retrocast process transcribe --model medium --format json ~/podcasts/my-show/

# 4. Search the transcribed content
retrocast process search "topic of interest"
```

### Create Subtitles for Video

```bash
# Extract audio from video first (using ffmpeg)
ffmpeg -i video.mp4 -vn -acodec copy audio.m4a

# Transcribe to SRT format
retrocast process transcribe --format srt --model medium audio.m4a

# The .srt file can now be used with video players
```

### Multi-language Podcast Analysis

```bash
# Transcribe English episodes
retrocast process transcribe --language en --podcast "English Show" english_episodes/

# Transcribe Spanish episodes
retrocast process transcribe --language es --podcast "Spanish Show" spanish_episodes/

# Search across both
retrocast process search "technology"
```

## Understanding Output

### Directory Structure

Transcriptions are saved in a structured directory:

```
~/.config/retrocast/transcriptions/
├── Podcast Name/
│   ├── Episode Title.json
│   ├── Episode Title.txt
│   ├── Episode Title.srt
│   └── Episode Title.vtt
└── Another Podcast/
    └── ...
```

### JSON Format

The JSON output includes complete metadata:

```json
{
  "text": "Full transcription text...",
  "language": "en",
  "duration": 3600.5,
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "Welcome to the show.",
      "speaker": null
    }
  ],
  "metadata": {
    "backend": "mlx-whisper",
    "model_size": "base",
    "transcription_time": 120.5
  }
}
```

### Database Storage

Transcriptions are also stored in SQLite for fast searching:

- **transcriptions** table: Metadata (title, backend, model, duration, etc.)
- **transcription_segments** table: Individual segments with timing and text
- **Full-text search**: Enabled on segment text for fast queries

## Performance Tips

### Model Selection

- **Quick drafts**: Use `--model tiny` for rapid transcription
- **General use**: Use `--model base` (default) for good balance
- **High quality**: Use `--model medium` or `large` for important content

### Backend Selection

- **Apple Silicon**: MLX Whisper is 3-5x faster than CPU alternatives
- **CUDA GPU**: faster-whisper provides excellent performance
- **CPU**: All backends work, but expect longer processing times

### Processing Time

Approximate real-time factors (time to transcribe 1 hour of audio):

| Model | Apple Silicon (MLX) | CUDA GPU | CPU |
|-------|---------------------|----------|-----|
| tiny | 2-3 min | 3-5 min | 10-15 min |
| base | 4-6 min | 6-10 min | 20-30 min |
| small | 8-12 min | 12-20 min | 45-60 min |
| medium | 15-25 min | 25-40 min | 2-3 hours |
| large | 30-45 min | 45-75 min | 4-6 hours |

*Times are approximate and depend on audio quality, speaking rate, and hardware.*

### Batch Processing Tips

```bash
# Process multiple files efficiently
# The CLI shows progress for each file
retrocast process transcribe --model base podcast_dir/*.mp3

# For very large batches, consider using smaller models first
retrocast process transcribe --model tiny large_archive/

# Then re-transcribe important episodes with larger models
retrocast process transcribe --force --model large important_episode.mp3
```

## Troubleshooting

### Backend Not Available

**Problem**: `retrocast process list-backends` shows backend as "Not Available"

**Solution**:
```bash
# For MLX on macOS (Apple Silicon)
poe install:transcription-mlx

# For faster-whisper with CUDA (Linux with GPU)
poe install:transcription-cuda

# For faster-whisper CPU-only (any platform)
poe install:transcription-cpu

# Verify installation
retrocast process test-backend mlx-whisper
```

### CUDA Not Detected

**Problem**: faster-whisper not using GPU

**Solution**:
```bash
# Check PyTorch CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch with CUDA support
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### Out of Memory Errors

**Problem**: Transcription fails with memory errors

**Solution**:
- Use a smaller model: `--model tiny` or `--model base`
- Process files one at a time instead of batches
- Close other applications to free memory

### Slow Transcription Speed

**Problem**: Transcription takes too long

**Solution**:
- Use a smaller model (tiny or base)
- Ensure backend is properly installed (MLX on macOS, CUDA on Linux)
- Check that GPU is being used (if applicable)
- Try a different backend: `--backend mlx-whisper`

### Search Returns No Results

**Problem**: `retrocast process search` finds nothing

**Solution**:
1. Verify transcriptions exist: Check database or output directory
2. Try simpler queries: Single words instead of phrases
3. Check podcast filter: Remove `--podcast` to search all
4. Verify database path: Use `--db` to specify correct database

## Advanced Usage

### Using with Datasette

View and query transcriptions in a web interface:

```bash
# Install datasette
pip install datasette

# Open database in Datasette
datasette ~/.config/retrocast/overcast.db
```

Navigate to the `transcriptions` and `transcription_segments` tables to explore.

### Scripting and Automation

```bash
#!/bin/bash
# Auto-transcribe new podcast downloads

DOWNLOAD_DIR="$HOME/podcasts/downloads"
TRANSCRIPT_DIR="$HOME/podcasts/transcripts"

# Watch for new files and transcribe
for file in "$DOWNLOAD_DIR"/*.mp3; do
  if [ -f "$file" ]; then
    retrocast process transcribe \
      --model base \
      --format json \
      --output-dir "$TRANSCRIPT_DIR" \
      "$file"
  fi
done
```

### Integration with Other Tools

```python
# Python script to process transcriptions
import json
from pathlib import Path

# Read JSON transcription
transcript_path = Path("~/.config/retrocast/transcriptions/Podcast/Episode.json")
with open(transcript_path.expanduser()) as f:
    data = json.load(f)

# Extract full text
full_text = data["text"]

# Process segments
for segment in data["segments"]:
    print(f"[{segment['start']:.1f}s] {segment['text']}")
```

## Next Steps

- **Phase 3**: faster-whisper backend for CUDA/CPU (coming soon)
- **Phase 5**: Speaker diarization to identify different speakers
- **Phase 6**: Enhanced search with highlighting and filters

## Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/crossjam/retrocast/issues
- Implementation Plan: See `plans/2025-12-16-transcription-implementation-plan.md`

## Credits

- Built on [OpenAI Whisper](https://github.com/openai/whisper)
- MLX backend uses [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper)
- faster-whisper backend uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
