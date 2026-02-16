# transcription - Manage Audio Transcriptions

The `transcription` command group manages audio transcriptions, allowing you to create, search, and analyze podcast transcripts.

## Command Group Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcription", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
Usage: cli about [OPTIONS]
  Display information about retrocast
Options:
  --help  Show this message and exit.
```
<!-- [[[end]]] -->

## Subcommands

### backends - Manage Backends

Manage transcription backends (MLX Whisper, faster-whisper, etc.).

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcription", "backends", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
Usage: cli about [OPTIONS]
  Display information about retrocast
Options:
  --help  Show this message and exit.
```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast transcription backends
```

Shows available transcription backends and their status.

### episodes - View Transcribed Episodes

View and manage transcribed episodes.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcription", "episodes", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
Usage: cli about [OPTIONS]
  Display information about retrocast
Options:
  --help  Show this message and exit.
```
<!-- [[[end]]] -->

**Usage:**

```bash
# List all transcribed episodes
retrocast transcription episodes

# Show episodes for specific podcast
retrocast transcription episodes --podcast "Podcast Name"
```

### podcasts - View Transcribed Podcasts

View and manage transcribed podcasts.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcription", "podcasts", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
Usage: cli about [OPTIONS]
  Display information about retrocast
Options:
  --help  Show this message and exit.
```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast transcription podcasts
```

Lists all podcasts that have at least one transcribed episode.

### process - Create Transcriptions

Process audio files to create transcriptions.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcription", "process", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
Usage: cli about [OPTIONS]
  Display information about retrocast
Options:
  --help  Show this message and exit.
```
<!-- [[[end]]] -->

**Usage:**

```bash
# Process all downloaded episodes
retrocast transcription process

# Process specific podcast
retrocast transcription process --podcast "Podcast Name"

# Process with specific backend and model
retrocast transcription process --backend mlx-whisper --model medium
```

### search - Search Transcripts

Search transcribed podcast content.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcription", "search", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
Usage: cli about [OPTIONS]
  Display information about retrocast
Options:
  --help  Show this message and exit.
```
<!-- [[[end]]] -->

**Usage:**

```bash
# Search all transcripts
retrocast transcription search "machine learning"

# Search within specific podcast
retrocast transcription search "AI" --podcast "Tech Podcast"

# Limit results
retrocast transcription search "python" --limit 10
```

### summary - View Statistics

Display overall transcription statistics.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcription", "summary", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
Usage: cli about [OPTIONS]
  Display information about retrocast
Options:
  --help  Show this message and exit.
```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast transcription summary
```

Shows:
- Total transcribed episodes
- Total transcribed podcasts
- Storage usage
- Backend statistics

### validate - Validate Transcripts

Validate all JSON transcription files.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcription", "validate", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
Usage: cli about [OPTIONS]
  Display information about retrocast
Options:
  --help  Show this message and exit.
```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast transcription validate
```

Checks all transcription JSON files for:
- Valid JSON syntax
- Required fields
- Proper structure

## Transcription Backends

retrocast supports multiple transcription backends:

### MLX Whisper (Apple Silicon only)

Optimized for Apple Silicon Macs with Metal acceleration.

**Installation:**

```bash
pip install retrocast[transcription-mlx]
```

**Features:**
- Fast performance on M1/M2/M3 chips
- Low memory usage
- Metal acceleration

### faster-whisper (CPU)

CPU-based transcription, works on any platform.

**Installation:**

```bash
pip install retrocast[transcription-cpu]
```

### faster-whisper (CUDA)

GPU-accelerated transcription for NVIDIA GPUs.

**Installation:**

```bash
pip install retrocast[transcription-cuda]
```

### Diarization

Speaker detection and labeling (requires additional dependencies).

**Installation:**

```bash
pip install retrocast[transcription-diarization]
```

## Transcript Storage

Transcripts are stored in:
```
~/.local/share/net.memexponent.retrocast/transcripts/
```

Each transcript includes:
- Full text transcription
- Word-level timestamps
- Confidence scores
- Speaker labels (if diarized)
- Metadata (duration, language, etc.)

## Examples

### Process All Episodes

```bash
retrocast transcription process
```

### Search Transcripts

```bash
retrocast transcription search "artificial intelligence"
```

### View Statistics

```bash
retrocast transcription summary
```

### Validate All Transcripts

```bash
retrocast transcription validate
```

## Workflow

### Initial Transcription

```bash
# 1. Install backend (choose one)
pip install retrocast[transcription-mlx]  # Mac
pip install retrocast[transcription-cuda]  # Linux with GPU
pip install retrocast[transcription-cpu]   # Any platform

# 2. Download episodes
retrocast download podcast-archiver --feed <url>

# 3. Create transcriptions
retrocast transcription process

# 4. Search content
retrocast transcription search "topic"
```

### Update Transcriptions

```bash
# Process only new episodes
retrocast transcription process
```

## Performance Tips

- MLX Whisper is fastest on Apple Silicon
- CUDA backend is fastest on NVIDIA GPUs
- CPU backend works everywhere but is slower
- Diarization adds processing time but provides speaker labels
- Process overnight for large archives
- Use `--limit` to test on a few episodes first

## See Also

- [Full Transcription Documentation](../TRANSCRIPTION.md)
- [Transcription Developer Guide](../TRANSCRIPTION_DEVELOPER.md)
