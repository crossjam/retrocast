# transcription - Manage Audio Transcriptions

The `transcription` command group manages audio transcriptions, allowing you to create, search, and analyze podcast transcripts.

## Command Group Help

<!-- [[[cog
import re
from click.testing import CliRunner
from retrocast.cli import cli

def clean_help_output(text):
    """Strip ANSI codes and replace box-drawing characters with plain ASCII."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    replacements = {
        '╭': '+', '╰': '+', '╮': '+', '╯': '+',
        '─': '-', '│': '|', '├': '+', '┤': '+',
        '┬': '+', '┴': '+', '┼': '+',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

result = CliRunner().invoke(cli, ["transcription", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli transcription [OPTIONS] COMMAND [ARGS]...                                               
                                                                                                    
 Manage audio transcriptions (create, search, analyze).                                             
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+- Commands ---------------------------------------------------------------------------------------+
| backends  Manage transcription backends.                                                         |
| episodes  Manage and view transcribed episodes.                                                  |
| podcasts  Manage and view transcribed podcasts.                                                  |
| process   Process audio files to create transcriptions.                                          |
| search    Search transcribed podcast content.                                                    |
| summary   Display overall transcription statistics.                                              |
| validate  Validate all JSON transcription files in the app directory.                            |
+--------------------------------------------------------------------------------------------------+

```
<!-- [[[end]]] -->

## Subcommands

### backends - Manage Backends

Manage transcription backends (MLX Whisper, faster-whisper, etc.).

<!-- [[[cog
import re
from click.testing import CliRunner
from retrocast.cli import cli

def clean_help_output(text):
    """Strip ANSI codes and replace box-drawing characters with plain ASCII."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    replacements = {
        '╭': '+', '╰': '+', '╮': '+', '╯': '+',
        '─': '-', '│': '|', '├': '+', '┤': '+',
        '┬': '+', '┴': '+', '┼': '+',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

result = CliRunner().invoke(cli, ["transcription", "backends", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli transcription backends [OPTIONS] COMMAND [ARGS]...                                      
                                                                                                    
 Manage transcription backends.                                                                     
 Commands for listing, testing, and managing transcription backends.                                
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+- Commands ---------------------------------------------------------------------------------------+
| list  List available transcription backends.                                                     |
| test  Test if a specific backend is available.                                                   |
+--------------------------------------------------------------------------------------------------+

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
import re
from click.testing import CliRunner
from retrocast.cli import cli

def clean_help_output(text):
    """Strip ANSI codes and replace box-drawing characters with plain ASCII."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    replacements = {
        '╭': '+', '╰': '+', '╮': '+', '╯': '+',
        '─': '-', '│': '|', '├': '+', '┤': '+',
        '┬': '+', '┴': '+', '┼': '+',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

result = CliRunner().invoke(cli, ["transcription", "episodes", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli transcription episodes [OPTIONS] COMMAND [ARGS]...                                      
                                                                                                    
 Manage and view transcribed episodes.                                                              
 Commands for listing and summarizing episodes with transcriptions.                                 
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+- Commands ---------------------------------------------------------------------------------------+
| list     List transcribed episodes.                                                              |
| summary  Show summary statistics for transcribed episodes.                                       |
+--------------------------------------------------------------------------------------------------+

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
import re
from click.testing import CliRunner
from retrocast.cli import cli

def clean_help_output(text):
    """Strip ANSI codes and replace box-drawing characters with plain ASCII."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    replacements = {
        '╭': '+', '╰': '+', '╮': '+', '╯': '+',
        '─': '-', '│': '|', '├': '+', '┤': '+',
        '┬': '+', '┴': '+', '┼': '+',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

result = CliRunner().invoke(cli, ["transcription", "podcasts", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli transcription podcasts [OPTIONS] COMMAND [ARGS]...                                      
                                                                                                    
 Manage and view transcribed podcasts.                                                              
 Commands for listing and summarizing podcasts with transcriptions.                                 
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+- Commands ---------------------------------------------------------------------------------------+
| list     List all podcasts with transcriptions.                                                  |
| summary  Show summary statistics for podcasts.                                                   |
+--------------------------------------------------------------------------------------------------+

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
import re
from click.testing import CliRunner
from retrocast.cli import cli

def clean_help_output(text):
    """Strip ANSI codes and replace box-drawing characters with plain ASCII."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    replacements = {
        '╭': '+', '╰': '+', '╮': '+', '╯': '+',
        '─': '-', '│': '|', '├': '+', '┤': '+',
        '┬': '+', '┴': '+', '┼': '+',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

result = CliRunner().invoke(cli, ["transcription", "process", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli transcription process [OPTIONS] [PATHS]...                                              
                                                                                                    
 Process audio files to create transcriptions.                                                      
 PATHS: One or more audio files or directories containing audio files. Can be omitted when using    
 --from-downloads.                                                                                  
                                                                                                    
 Examples:                                                                                          
                                                                                                    
                                                                                                    
  # Process a single file                                                                           
  retrocast transcription process episode.mp3                                                       
                                                                                                    
  # Process all files in a directory                                                                
  retrocast transcription process /path/to/podcast/                                                 
                                                                                                    
  # Use specific backend and model                                                                  
  retrocast transcription process --backend mlx-whisper --model medium file.mp3                     
                                                                                                    
  # Save as SRT subtitle format                                                                     
  retrocast transcription process --format srt episode.mp3                                          
                                                                                                    
  # Process all downloaded episodes from a specific podcast                                         
  retrocast transcription process --from-downloads --podcast "Tech Podcast"                         
                                                                                                    
  # List available podcasts from downloads                                                          
  retrocast transcription process --list-podcasts                                                   
                                                                                                    
  # Process all downloaded episodes                                                                 
  retrocast transcription process --from-downloads                                                  
                                                                                                    
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --from-downloads                                     Process episodes from the episode_downloads |
|                                                      directory.                                  |
| --podcast         TEXT                               Filter by podcast name (use with            |
|                                                      --from-downloads or directory paths).       |
| --list-podcasts                                      List available podcasts from downloads and  |
|                                                      exit.                                       |
| --backend         [auto|mlx-whisper|faster-whisper]  Transcription backend to use.               |
| --model           [tiny|base|small|medium|large]     Whisper model size.                         |
| --language        TEXT                               Audio language code (e.g., 'en', 'es').     |
|                                                      Auto-detected if not specified.             |
| --output-dir      PATH                               Output directory for transcription files    |
|                                                      (defaults to app_dir/transcriptions).       |
| --format          [txt|json|srt|vtt]                 Output format for transcription files.      |
| --force                                              Re-transcribe even if transcription already |
|                                                      exists.                                     |
| --db              PATH                               Path to database file (defaults to          |
|                                                      app_dir/retrocast.db).                      |
| --help                                               Show this message and exit.                 |
+--------------------------------------------------------------------------------------------------+

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
import re
from click.testing import CliRunner
from retrocast.cli import cli

def clean_help_output(text):
    """Strip ANSI codes and replace box-drawing characters with plain ASCII."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    replacements = {
        '╭': '+', '╰': '+', '╮': '+', '╯': '+',
        '─': '-', '│': '|', '├': '+', '┤': '+',
        '┬': '+', '┴': '+', '┼': '+',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

result = CliRunner().invoke(cli, ["transcription", "search", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli transcription search [OPTIONS] QUERY                                                    
                                                                                                    
 Search transcribed podcast content.                                                                
 QUERY: Search query string (FTS5 syntax supported).                                                
                                                                                                    
 Examples:                                                                                          
                                                                                                    
                                                                                                    
  # Simple search                                                                                   
  retrocast transcription search "machine learning"                                                 
                                                                                                    
  # Search with filters                                                                             
  retrocast transcription search "AI" --podcast "Tech Podcast" --limit 10                           
                                                                                                    
  # Search with date range                                                                          
  retrocast transcription search "python" --date-from "2024-01-01" --date-to "2024-12-31"           
                                                                                                    
  # Export results to JSON                                                                          
  retrocast transcription search "data science" --export json --output results.json                 
                                                                                                    
  # Search with context and pagination                                                              
  retrocast transcription search "neural networks" --context 2 --page 2 --limit 10                  
                                                                                                    
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --podcast    TEXT             Filter by podcast title.                                           |
| --speaker    TEXT             Filter by speaker ID (requires diarization).                       |
| --backend    TEXT             Filter by transcription backend (e.g., 'mlx-whisper').             |
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
retrocast transcription search "machine learning"

# Search within specific podcast
retrocast transcription search "AI" --podcast "Tech Podcast"

# Limit results
retrocast transcription search "python" --limit 10
```

### summary - View Statistics

Display overall transcription statistics.

<!-- [[[cog
import re
from click.testing import CliRunner
from retrocast.cli import cli

def clean_help_output(text):
    """Strip ANSI codes and replace box-drawing characters with plain ASCII."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    replacements = {
        '╭': '+', '╰': '+', '╮': '+', '╯': '+',
        '─': '-', '│': '|', '├': '+', '┤': '+',
        '┬': '+', '┴': '+', '┼': '+',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

result = CliRunner().invoke(cli, ["transcription", "summary", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli transcription summary [OPTIONS]                                                         
                                                                                                    
 Display overall transcription statistics.                                                          
 Shows a comprehensive summary of all transcriptions in the database, including counts, duration,   
 backends used, and more.                                                                           
                                                                                                    
 Example: retrocast transcription summary                                                           
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --db    PATH  Path to database file (defaults to app_dir/retrocast.db).                          |
| --help        Show this message and exit.                                                        |
+--------------------------------------------------------------------------------------------------+

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
import re
from click.testing import CliRunner
from retrocast.cli import cli

def clean_help_output(text):
    """Strip ANSI codes and replace box-drawing characters with plain ASCII."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    replacements = {
        '╭': '+', '╰': '+', '╮': '+', '╯': '+',
        '─': '-', '│': '|', '├': '+', '┤': '+',
        '┬': '+', '┴': '+', '┼': '+',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

result = CliRunner().invoke(cli, ["transcription", "validate", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli transcription validate [OPTIONS]                                                        
                                                                                                    
 Validate all JSON transcription files in the app directory.                                        
 Checks that all JSON transcription files conform to the expected schema using pydantic validation. 
 Displays progress during validation and provides a summary report at the end.                      
                                                                                                    
 Example: retrocast transcription validate retrocast transcription validate --verbose retrocast     
 transcription validate --output-dir /custom/path                                                   
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --output-dir      PATH  Directory containing transcription JSON files (defaults to               |
|                         app_dir/transcriptions).                                                 |
| --verbose     -v        Show detailed validation errors for each file.                           |
| --help                  Show this message and exit.                                              |
+--------------------------------------------------------------------------------------------------+

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
