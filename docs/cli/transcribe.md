# transcribe - Manage Audio Transcriptions

The `transcribe` command group manages audio transcriptions, allowing you to create, search, and analyze podcast transcripts.

## Command Group Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcribe", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                                                                                                                        
 Usage: cli transcribe [OPTIONS] COMMAND [ARGS]...                                                                                                                                                   
                                                                                                                                                                                                        
 Manage audio transcriptions (create, search, analyze).                                                                                                                                                 
                                                                                                                                                                                                        
+--------------------------------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+--------------------------------------------------------------------------------------------------+
| backends  Manage transcribe backends.                                                         |
| episodes  Manage and view transcribed episodes.                                                  |
| podcasts  Manage and view transcribed podcasts.                                                  |
| process   Process audio files to create transcriptions.                                          |
| search    Search transcribed podcast content.                                                    |
| summary   Display overall transcribe statistics.                                              |
| validate  Validate all JSON transcribe files in the app directory.                            |
+--------------------------------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

## Subcommands

### backends - Manage Backends

Manage transcribe backends (MLX Whisper, faster-whisper, etc.).

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcribe", "backends", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                                                                                                                        
 Usage: cli transcribe backends [OPTIONS] COMMAND [ARGS]...                                                                                                                                          
                                                                                                                                                                                                        
 Manage transcribe backends.                                                                                                                                                                         
 Commands for listing, testing, and managing transcribe backends.                                                                                                                                    
                                                                                                                                                                                                        
+--------------------------------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+--------------------------------------------------------------------------------------------------+
| list  List available transcribe backends.                                                     |
| test  Test if a specific backend is available.                                                   |
+--------------------------------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast transcribe backends
```

Shows available transcribe backends and their status.

### episodes - View Transcribed Episodes

View and manage transcribed episodes.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcribe", "episodes", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                                                                                                                        
 Usage: cli transcribe episodes [OPTIONS] COMMAND [ARGS]...                                                                                                                                          
                                                                                                                                                                                                        
 Manage and view transcribed episodes.                                                                                                                                                                  
 Commands for listing and summarizing episodes with transcriptions.                                                                                                                                     
                                                                                                                                                                                                        
+--------------------------------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+--------------------------------------------------------------------------------------------------+
| list     List transcribed episodes.                                                              |
| summary  Show summary statistics for transcribed episodes.                                       |
+--------------------------------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

**Usage:**

```bash
# List all transcribed episodes
retrocast transcribe episodes

# Show episodes for specific podcast
retrocast transcribe episodes --podcast "Podcast Name"
```

### podcasts - View Transcribed Podcasts

View and manage transcribed podcasts.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcribe", "podcasts", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                                                                                                                        
 Usage: cli transcribe podcasts [OPTIONS] COMMAND [ARGS]...                                                                                                                                          
                                                                                                                                                                                                        
 Manage and view transcribed podcasts.                                                                                                                                                                  
 Commands for listing and summarizing podcasts with transcriptions.                                                                                                                                     
                                                                                                                                                                                                        
+--------------------------------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+--------------------------------------------------------------------------------------------------+
| list     List all podcasts with transcriptions.                                                  |
| summary  Show summary statistics for podcasts.                                                   |
+--------------------------------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast transcribe podcasts
```

Lists all podcasts that have at least one transcribed episode.

### process - Create Transcriptions

Process audio files to create transcriptions.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcribe", "process", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                                                                                                                        
 Usage: cli transcribe process [OPTIONS] [PATHS]...                                                                                                                                                  
                                                                                                                                                                                                        
 Process audio files to create transcriptions.                                                                                                                                                          
 PATHS: One or more audio files or directories containing audio files. Can be omitted when using --from-downloads.                                                                                      
                                                                                                                                                                                                        
 Examples:                                                                                                                                                                                              
                                                                                                                                                                                                        
                                                                                                                                                                                                        
  # Process a single file                                                                                                                                                                               
  retrocast transcribe process episode.mp3                                                                                                                                                           
                                                                                                                                                                                                        
  # Process all files in a directory                                                                                                                                                                    
  retrocast transcribe process /path/to/podcast/                                                                                                                                                     
                                                                                                                                                                                                        
  # Use specific backend and model                                                                                                                                                                      
  retrocast transcribe process --backend mlx-whisper --model medium file.mp3                                                                                                                         
                                                                                                                                                                                                        
  # Save as SRT subtitle format                                                                                                                                                                         
  retrocast transcribe process --format srt episode.mp3                                                                                                                                              
                                                                                                                                                                                                        
  # Process all downloaded episodes from a specific podcast                                                                                                                                             
  retrocast transcribe process --from-downloads --podcast "Tech Podcast"                                                                                                                             
                                                                                                                                                                                                        
  # List available podcasts from downloads                                                                                                                                                              
  retrocast transcribe process --list-podcasts                                                                                                                                                       
                                                                                                                                                                                                        
  # Process all downloaded episodes                                                                                                                                                                     
  retrocast transcribe process --from-downloads                                                                                                                                                      
                                                                                                                                                                                                        
                                                                                                                                                                                                        
+--------------------------------------------------------------------------------------------------+
| --from-downloads                                     Process episodes from the episode_downloads |
|                                     directory.                                                   |
| --podcast         TEXT                               Filter by podcast name (use with            |
|                                     --from-downloads or directory paths).                        |
| --list-podcasts                                      List available podcasts from downloads and  |
|                                     exit.                                                        |
| --backend         [auto|mlx-whisper|faster-whisper]  Transcription backend to use.               |
| --model           [tiny|base|small|medium|large]     Whisper model size.                         |
| --language        TEXT                               Audio language code (e.g., 'en', 'es').     |
|                                     Auto-detected if not specified.                              |
| --output-dir      PATH                               Output directory for transcribe files    |
|                                     (defaults to app_dir/transcriptions).                        |
| --format          [txt|json|srt|vtt]                 Output format for transcribe files.      |
| --force                                              Re-transcribe even if transcribe already |
|                                     exists.                                                      |
| --db              PATH                               Path to database file (defaults to          |
|                                     app_dir/retrocast.db).                                       |
| --help                                               Show this message and exit.                 |
+--------------------------------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

**Usage:**

```bash
# Process all downloaded episodes
retrocast transcribe process

# Process specific podcast
retrocast transcribe process --podcast "Podcast Name"

# Process with specific backend and model
retrocast transcribe process --backend mlx-whisper --model medium
```

### search - Search Transcripts

Search transcribed podcast content.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcribe", "search", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                                                                                                                        
 Usage: cli transcribe search [OPTIONS] QUERY                                                                                                                                                        
                                                                                                                                                                                                        
 Search transcribed podcast content.                                                                                                                                                                    
 QUERY: Search query string (FTS5 syntax supported).                                                                                                                                                    
                                                                                                                                                                                                        
 Examples:                                                                                                                                                                                              
                                                                                                                                                                                                        
                                                                                                                                                                                                        
  # Simple search                                                                                                                                                                                       
  retrocast transcribe search "machine learning"                                                                                                                                                     
                                                                                                                                                                                                        
  # Search with filters                                                                                                                                                                                 
  retrocast transcribe search "AI" --podcast "Tech Podcast" --limit 10                                                                                                                               
                                                                                                                                                                                                        
  # Search with date range                                                                                                                                                                              
  retrocast transcribe search "python" --date-from "2024-01-01" --date-to "2024-12-31"                                                                                                               
                                                                                                                                                                                                        
  # Export results to JSON                                                                                                                                                                              
  retrocast transcribe search "data science" --export json --output results.json                                                                                                                     
                                                                                                                                                                                                        
  # Search with context and pagination                                                                                                                                                                  
  retrocast transcribe search "neural networks" --context 2 --page 2 --limit 10                                                                                                                      
                                                                                                                                                                                                        
                                                                                                                                                                                                        
+--------------------------------------------------------------------------------------------------+
| --podcast    TEXT             Filter by podcast title.                                           |
| --speaker    TEXT             Filter by speaker ID (requires diarization).                       |
| --backend    TEXT             Filter by transcribe backend (e.g., 'mlx-whisper').             |
| --model      TEXT             Filter by model size (e.g., 'base', 'medium').                     |
| --date-from  TEXT             Filter by creation date (ISO format, e.g., '2024-01-01').          |
| --date-to    TEXT             Filter by creation date (ISO format, e.g., '2024-12-31').          |
| --limit      INTEGER          Maximum number of results to display.                              |
| --page       INTEGER          Page number for pagination (starts at 1).                          |
| --context    INTEGER          Number of surrounding segments to show for context.                |
| --export     [json|csv|html]  Export results to file format.                                     |
| --output     PATH             Output file path for export (defaults to search_results.{format}). |
| --db         PATH             Path to database file (defaults to app_dir/retrocast.db).          |
| --help                        Show this message and exit.                                        |
+--------------------------------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

**Usage:**

```bash
# Search all transcripts
retrocast transcribe search "machine learning"

# Search within specific podcast
retrocast transcribe search "AI" --podcast "Tech Podcast"

# Limit results
retrocast transcribe search "python" --limit 10
```

### summary - View Statistics

Display overall transcribe statistics.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcribe", "summary", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                                                                                                                        
 Usage: cli transcribe summary [OPTIONS]                                                                                                                                                             
                                                                                                                                                                                                        
 Display overall transcribe statistics.                                                                                                                                                              
 Shows a comprehensive summary of all transcriptions in the database, including counts, duration, backends used, and more.                                                                              
                                                                                                                                                                                                        
 Example: retrocast transcribe summary                                                                                                                                                               
                                                                                                                                                                                                        
+--------------------------------------------------------------------------------------------------+
| --db    PATH  Path to database file (defaults to app_dir/retrocast.db).                          |
| --help        Show this message and exit.                                                        |
+--------------------------------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast transcribe summary
```

Shows:
- Total transcribed episodes
- Total transcribed podcasts
- Storage usage
- Backend statistics

### validate - Validate Transcripts

Validate all JSON transcribe files.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.doc_utils import clean_help_output
from retrocast.cli import cli


result = CliRunner().invoke(cli, ["transcribe", "validate", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                                                                                                                        
 Usage: cli transcribe validate [OPTIONS]                                                                                                                                                            
                                                                                                                                                                                                        
 Validate all JSON transcribe files in the app directory.                                                                                                                                            
 Checks that all JSON transcribe files conform to the expected schema using pydantic validation. Displays progress during validation and provides a summary report at the end.                       
                                                                                                                                                                                                        
 Example: retrocast transcribe validate retrocast transcribe validate --verbose retrocast transcribe validate --output-dir /custom/path                                                        
                                                                                                                                                                                                        
+--------------------------------------------------------------------------------------------------+
| --output-dir      PATH  Directory containing transcribe JSON files (defaults to               |
|                                     app_dir/transcriptions).                                     |
| --verbose     -v        Show detailed validation errors for each file.                           |
| --help                  Show this message and exit.                                              |
+--------------------------------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast transcribe validate
```

Checks all transcribe JSON files for:
- Valid JSON syntax
- Required fields
- Proper structure

## Transcription Backends

retrocast supports multiple transcribe backends:

### MLX Whisper (Apple Silicon only)

Optimized for Apple Silicon Macs with Metal acceleration.

**Installation:**

```bash
pip install retrocast[transcribe-mlx]
```

**Features:**
- Fast performance on M1/M2/M3 chips
- Low memory usage
- Metal acceleration

### faster-whisper (CPU)

CPU-based transcribe, works on any platform.

**Installation:**

```bash
pip install retrocast[transcribe-cpu]
```

### faster-whisper (CUDA)

GPU-accelerated transcribe for NVIDIA GPUs.

**Installation:**

```bash
pip install retrocast[transcribe-cuda]
```

### Diarization

Speaker detection and labeling (requires additional dependencies).

**Installation:**

```bash
pip install retrocast[transcribe-diarization]
```

## Transcript Storage

Transcripts are stored in:
```
~/.local/share/net.memexponent.retrocast/transcripts/
```

Each transcript includes:
- Full text transcribe
- Word-level timestamps
- Confidence scores
- Speaker labels (if diarized)
- Metadata (duration, language, etc.)

## Examples

### Process All Episodes

```bash
retrocast transcribe process
```

### Search Transcripts

```bash
retrocast transcribe search "artificial intelligence"
```

### View Statistics

```bash
retrocast transcribe summary
```

### Validate All Transcripts

```bash
retrocast transcribe validate
```

## Workflow

### Initial Transcription

```bash
# 1. Install backend (choose one)
pip install retrocast[transcribe-mlx]  # Mac
pip install retrocast[transcribe-cuda]  # Linux with GPU
pip install retrocast[transcribe-cpu]   # Any platform

# 2. Download episodes
retrocast download podcast-archiver --feed <url>

# 3. Create transcriptions
retrocast transcribe process

# 4. Search content
retrocast transcribe search "topic"
```

### Update Transcriptions

```bash
# Process only new episodes
retrocast transcribe process
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
