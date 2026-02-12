# transcription - Manage Audio Transcriptions

The `transcription` command group manages audio transcriptions, allowing you to create, search, and analyze podcast transcripts.

## Command Group Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["transcription", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli transcription[0m [[1;36mOPTIONS[0m] [1;36mCOMMAND[0m [[1;36mARGS[0m]...                                                                   
                                                                                                                        
 Manage audio transcriptions (create, search, analyze).                                                                 
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--help[0m  Show this message and exit.                                                                                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Commands [0m[2m──────────────────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36mbackends[0m[1;36m [0m Manage transcription backends.                                                                             [2m│[0m
[2m│[0m [1;36mepisodes[0m[1;36m [0m Manage and view transcribed episodes.                                                                      [2m│[0m
[2m│[0m [1;36mpodcasts[0m[1;36m [0m Manage and view transcribed podcasts.                                                                      [2m│[0m
[2m│[0m [1;36mprocess [0m[1;36m [0m Process audio files to create transcriptions.                                                              [2m│[0m
[2m│[0m [1;36msearch  [0m[1;36m [0m Search transcribed podcast content.                                                                        [2m│[0m
[2m│[0m [1;36msummary [0m[1;36m [0m Display overall transcription statistics.                                                                  [2m│[0m
[2m│[0m [1;36mvalidate[0m[1;36m [0m Validate all JSON transcription files in the app directory.                                                [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

```
<!-- [[[end]]] -->

## Subcommands

### backends - Manage Backends

Manage transcription backends (MLX Whisper, faster-whisper, etc.).

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["transcription", "backends", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli transcription backends[0m [[1;36mOPTIONS[0m] [1;36mCOMMAND[0m [[1;36mARGS[0m]...                                                          
                                                                                                                        
 Manage transcription backends.                                                                                         
 [2mCommands for listing, testing, and managing transcription backends.[0m                                                    
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--help[0m  Show this message and exit.                                                                                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Commands [0m[2m──────────────────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36mlist[0m[1;36m [0m List available transcription backends.                                                                         [2m│[0m
[2m│[0m [1;36mtest[0m[1;36m [0m Test if a specific backend is available.                                                                       [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["transcription", "episodes", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli transcription episodes[0m [[1;36mOPTIONS[0m] [1;36mCOMMAND[0m [[1;36mARGS[0m]...                                                          
                                                                                                                        
 Manage and view transcribed episodes.                                                                                  
 [2mCommands for listing and summarizing episodes with transcriptions.[0m                                                     
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--help[0m  Show this message and exit.                                                                                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Commands [0m[2m──────────────────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36mlist   [0m[1;36m [0m List transcribed episodes.                                                                                  [2m│[0m
[2m│[0m [1;36msummary[0m[1;36m [0m Show summary statistics for transcribed episodes.                                                           [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["transcription", "podcasts", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli transcription podcasts[0m [[1;36mOPTIONS[0m] [1;36mCOMMAND[0m [[1;36mARGS[0m]...                                                          
                                                                                                                        
 Manage and view transcribed podcasts.                                                                                  
 [2mCommands for listing and summarizing podcasts with transcriptions.[0m                                                     
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--help[0m  Show this message and exit.                                                                                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Commands [0m[2m──────────────────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36mlist   [0m[1;36m [0m List all podcasts with transcriptions.                                                                      [2m│[0m
[2m│[0m [1;36msummary[0m[1;36m [0m Show summary statistics for podcasts.                                                                       [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["transcription", "process", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli transcription process[0m [[1;36mOPTIONS[0m] [[1;36mPATHS[0m]...                                                                  
                                                                                                                        
 Process audio files to create transcriptions.                                                                          
 [2mPATHS: One or more audio files or directories containing audio files.[0m[2m [0m[2mCan be omitted when using --from-downloads.[0m      
                                                                                                                        
 [2mExamples:[0m                                                                                                              
                                                                                                                        
 [40m                                                                                                                      [0m 
 [40m [0m[97;40m# Process a single file[0m[40m                                                                                             [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription process episode.mp3[0m[40m                                                                         [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# Process all files in a directory[0m[40m                                                                                  [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription process /path/to/podcast/[0m[40m                                                                   [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# Use specific backend and model[0m[40m                                                                                    [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription process --backend mlx-whisper --model medium file.mp3[0m[40m                                       [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# Save as SRT subtitle format[0m[40m                                                                                       [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription process --format srt episode.mp3[0m[40m                                                            [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# Process all downloaded episodes from a specific podcast[0m[40m                                                           [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription process --from-downloads --podcast "Tech Podcast"[0m[40m                                           [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# List available podcasts from downloads[0m[40m                                                                            [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription process --list-podcasts[0m[40m                                                                     [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# Process all downloaded episodes[0m[40m                                                                                   [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription process --from-downloads[0m[40m                                                                    [0m[40m [0m 
 [40m                                                                                                                      [0m 
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--from-downloads[0m                                     Process episodes from the episode_downloads directory.          [2m│[0m
[2m│[0m [1;36m--podcast       [0m  [1;33mTEXT                             [0m  Filter by podcast name (use with --from-downloads or directory  [2m│[0m
[2m│[0m                                                      paths).                                                         [2m│[0m
[2m│[0m [1;36m--list-podcasts [0m                                     List available podcasts from downloads and exit.                [2m│[0m
[2m│[0m [1;36m--backend       [0m  [1;2;33m[[0m[1;33mauto[0m[1;2;33m|[0m[1;33mmlx-whisper[0m[1;2;33m|[0m[1;33mfaster-whisper[0m[1;2;33m][0m  Transcription backend to use.                                   [2m│[0m
[2m│[0m [1;36m--model         [0m  [1;2;33m[[0m[1;33mtiny[0m[1;2;33m|[0m[1;33mbase[0m[1;2;33m|[0m[1;33msmall[0m[1;2;33m|[0m[1;33mmedium[0m[1;2;33m|[0m[1;33mlarge[0m[1;2;33m][0m[1;33m   [0m  Whisper model size.                                             [2m│[0m
[2m│[0m [1;36m--language      [0m  [1;33mTEXT                             [0m  Audio language code (e.g., 'en', 'es'). Auto-detected if not    [2m│[0m
[2m│[0m                                                      specified.                                                      [2m│[0m
[2m│[0m [1;36m--output-dir    [0m  [1;33mPATH                             [0m  Output directory for transcription files (defaults to           [2m│[0m
[2m│[0m                                                      app_dir/transcriptions).                                        [2m│[0m
[2m│[0m [1;36m--format        [0m  [1;2;33m[[0m[1;33mtxt[0m[1;2;33m|[0m[1;33mjson[0m[1;2;33m|[0m[1;33msrt[0m[1;2;33m|[0m[1;33mvtt[0m[1;2;33m][0m[1;33m               [0m  Output format for transcription files.                          [2m│[0m
[2m│[0m [1;36m--force         [0m                                     Re-transcribe even if transcription already exists.             [2m│[0m
[2m│[0m [1;36m--db            [0m  [1;33mPATH                             [0m  Path to database file (defaults to app_dir/retrocast.db).       [2m│[0m
[2m│[0m [1;36m--help          [0m                                     Show this message and exit.                                     [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

```
<!-- [[[end]]] -->

**Usage:**

```bash
# Process all downloaded episodes
retrocast transcription process

# Process specific podcast
retrocast transcription process --podcast "Podcast Name"

# Process with specific backend
retrocast transcription process --backend mlx-whisper

# Process with diarization (speaker detection)
retrocast transcription process --diarize
```

### search - Search Transcripts

Search transcribed podcast content.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["transcription", "search", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli transcription search[0m [[1;36mOPTIONS[0m] [1;36mQUERY[0m                                                                        
                                                                                                                        
 Search transcribed podcast content.                                                                                    
 [2mQUERY: Search query string (FTS5 syntax supported).[0m                                                                    
                                                                                                                        
 [2mExamples:[0m                                                                                                              
                                                                                                                        
 [40m                                                                                                                      [0m 
 [40m [0m[97;40m# Simple search[0m[40m                                                                                                     [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription search "machine learning"[0m[40m                                                                   [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# Search with filters[0m[40m                                                                                               [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription search "AI" --podcast "Tech Podcast" --limit 10[0m[40m                                             [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# Search with date range[0m[40m                                                                                            [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription search "python" --date-from "2024-01-01" --date-to "2024-12-31"[0m[40m                             [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# Export results to JSON[0m[40m                                                                                            [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription search "data science" --export json --output results.json[0m[40m                                   [0m[40m [0m 
 [40m [0m[40m                                                                                                                    [0m[40m [0m 
 [40m [0m[97;40m# Search with context and pagination[0m[40m                                                                                [0m[40m [0m 
 [40m [0m[97;40mretrocast transcription search "neural networks" --context 2 --page 2 --limit 10[0m[40m                                    [0m[40m [0m 
 [40m                                                                                                                      [0m 
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--podcast  [0m  [1;33mTEXT           [0m  Filter by podcast title.                                                               [2m│[0m
[2m│[0m [1;36m--speaker  [0m  [1;33mTEXT           [0m  Filter by speaker ID (requires diarization).                                           [2m│[0m
[2m│[0m [1;36m--backend  [0m  [1;33mTEXT           [0m  Filter by transcription backend (e.g., 'mlx-whisper').                                 [2m│[0m
[2m│[0m [1;36m--model    [0m  [1;33mTEXT           [0m  Filter by model size (e.g., 'base', 'medium').                                         [2m│[0m
[2m│[0m [1;36m--date-from[0m  [1;33mTEXT           [0m  Filter by creation date (ISO format, e.g., '2024-01-01').                              [2m│[0m
[2m│[0m [1;36m--date-to  [0m  [1;33mTEXT           [0m  Filter by creation date (ISO format, e.g., '2024-12-31').                              [2m│[0m
[2m│[0m [1;36m--limit    [0m  [1;33mINTEGER        [0m  Maximum number of results to display.                                                  [2m│[0m
[2m│[0m [1;36m--page     [0m  [1;33mINTEGER        [0m  Page number for pagination (starts at 1).                                              [2m│[0m
[2m│[0m [1;36m--context  [0m  [1;33mINTEGER        [0m  Number of surrounding segments to show for context.                                    [2m│[0m
[2m│[0m [1;36m--export   [0m  [1;2;33m[[0m[1;33mjson[0m[1;2;33m|[0m[1;33mcsv[0m[1;2;33m|[0m[1;33mhtml[0m[1;2;33m][0m  Export results to file format.                                                         [2m│[0m
[2m│[0m [1;36m--output   [0m  [1;33mPATH           [0m  Output file path for export (defaults to search_results.{format}).                     [2m│[0m
[2m│[0m [1;36m--db       [0m  [1;33mPATH           [0m  Path to database file (defaults to app_dir/retrocast.db).                              [2m│[0m
[2m│[0m [1;36m--help     [0m                   Show this message and exit.                                                            [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["transcription", "summary", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli transcription summary[0m [[1;36mOPTIONS[0m]                                                                             
                                                                                                                        
 Display overall transcription statistics.                                                                              
 [2mShows a comprehensive summary of all transcriptions in the database,[0m[2m [0m[2mincluding counts, duration, backends used, and [0m   
 [2mmore.[0m                                                                                                                  
                                                                                                                        
 [2mExample:[0m[2m [0m[2mretrocast transcription summary[0m                                                                               
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--db  [0m  [1;33mPATH[0m  Path to database file (defaults to app_dir/retrocast.db).                                              [2m│[0m
[2m│[0m [1;36m--help[0m        Show this message and exit.                                                                            [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["transcription", "validate", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli transcription validate[0m [[1;36mOPTIONS[0m]                                                                            
                                                                                                                        
 Validate all JSON transcription files in the app directory.                                                            
 [2mChecks that all JSON transcription files conform to the expected schema[0m[2m [0m[2musing pydantic validation. Displays progress [0m  
 [2mduring validation and provides[0m[2m [0m[2ma summary report at the end.[0m                                                            
                                                                                                                        
 [2mExample:[0m[2m [0m[2mretrocast transcription validate[0m[2m [0m[2mretrocast transcription validate --verbose[0m[2m [0m[2mretrocast transcription validate [0m 
 [2m--output-dir /custom/path[0m                                                                                              
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--output-dir[0m      [1;33mPATH[0m  Directory containing transcription JSON files (defaults to app_dir/transcriptions).          [2m│[0m
[2m│[0m [1;36m--verbose   [0m  [1;32m-v[0m        Show detailed validation errors for each file.                                               [2m│[0m
[2m│[0m [1;36m--help      [0m            Show this message and exit.                                                                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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

### Process with Diarization

```bash
retrocast transcription process --diarize
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
