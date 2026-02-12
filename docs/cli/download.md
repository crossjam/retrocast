# download - Download Episode Content

The `download` command group provides tools for downloading podcast episode files using different backends.

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

result = CliRunner().invoke(cli, ["download", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli download [OPTIONS] COMMAND [ARGS]...                                                    
                                                                                                    
 Download episode content with pluggable backends                                                   
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+- Commands ---------------------------------------------------------------------------------------+
| aria              Download URLs using the aria2c fetcher.                                        |
| db                Manage downloaded episodes database.                                           |
| podcast-archiver  Archive all of your favorite podcasts                                          |
+--------------------------------------------------------------------------------------------------+

```
<!-- [[[end]]] -->

## Subcommands

### aria - Download with aria2c

Download URLs using the embedded aria2c fetcher.

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

result = CliRunner().invoke(cli, ["download", "aria", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli download aria [OPTIONS] [FILENAME]                                                      
                                                                                                    
 Download URLs using the aria2c fetcher.                                                            
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --directory       -d  DIRECTORY             Directory to store downloaded files.                 |
| --max-concurrent  -j  INTEGER RANGE [x>=1]  Maximum concurrent aria2c downloads.                 |
|                                             [default: 5]                                         |
| --verbose         -v                        Enable verbose logging for this command.             |
| --secret              TEXT                  RPC secret token for aria2c.                         |
| --help                                      Show this message and exit.                          |
+--------------------------------------------------------------------------------------------------+

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast download aria <urls...>
```

The aria2c fetcher provides:
- Multi-threaded downloads
- Automatic retry on failure
- Progress tracking
- Resume capability

### db - Manage Episode Database

Manage the database of downloaded episodes.

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

result = CliRunner().invoke(cli, ["download", "db", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli download db [OPTIONS] COMMAND [ARGS]...                                                 
                                                                                                    
 Manage downloaded episodes database.                                                               
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --help  Show this message and exit.                                                              |
+--------------------------------------------------------------------------------------------------+
+- Commands ---------------------------------------------------------------------------------------+
| init    Initialize episode downloads database schema.                                            |
| search  Search episode downloads using full-text search.                                         |
| update  Update episode downloads database from filesystem.                                       |
+--------------------------------------------------------------------------------------------------+

```
<!-- [[[end]]] -->

#### db init - Initialize Database

Initialize the episode downloads database schema.

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

result = CliRunner().invoke(cli, ["download", "db", "init", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli download db init [OPTIONS]                                                              
                                                                                                    
 Initialize episode downloads database schema.                                                      
 Creates the episode_downloads table and indexes in the retrocast database. This command is         
 idempotent and safe to run multiple times.                                                         
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --dry-run        Show what would be created without making changes.                              |
| --db-path  FILE  Path to database file. Defaults to app directory.                               |
| --help           Show this message and exit.                                                     |
+--------------------------------------------------------------------------------------------------+

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast download db init
```

Creates the `episode_downloads` table with full-text search capability.

#### db search - Search Episodes

Search downloaded episodes using full-text search.

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

result = CliRunner().invoke(cli, ["download", "db", "search", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli download db search [OPTIONS] QUERY                                                      
                                                                                                    
 Search episode downloads using full-text search.                                                   
 Searches episode titles, descriptions, summaries, and shownotes.                                   
                                                                                                    
 Examples: retrocast download db search "python" retrocast download db search "machine learning"    
 --podcast "Practical AI" retrocast download db search "interview" --limit 10                       
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --podcast  TEXT     Filter by podcast title (exact match).                                       |
| --limit    INTEGER  Maximum number of results to display.                                        |
|                     [default: 20]                                                                |
| --db-path  FILE     Path to database file. Defaults to app directory.                            |
| --help              Show this message and exit.                                                  |
+--------------------------------------------------------------------------------------------------+

```
<!-- [[[end]]] -->

**Usage:**

```bash
# Search all episodes
retrocast download db search "machine learning"

# Filter by podcast
retrocast download db search "AI" --podcast "Tech Podcast"

# Limit results
retrocast download db search "python" --limit 10
```

#### db update - Update Database

Update the episode downloads database by scanning the filesystem.

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

result = CliRunner().invoke(cli, ["download", "db", "update", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli download db update [OPTIONS]                                                            
                                                                                                    
 Update episode downloads database from filesystem.                                                 
 Scans the episode_downloads directory and updates the database with discovered episodes and their  
 metadata from .info.json files.                                                                    
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --rescan                    Delete existing records and rebuild from scratch.                    |
| --verify                    Verify all files still exist and mark missing ones.                  |
| --db-path        FILE       Path to database file. Defaults to app directory.                    |
| --downloads-dir  DIRECTORY  Path to episode_downloads directory. Defaults to app directory.      |
| --help                      Show this message and exit.                                          |
+--------------------------------------------------------------------------------------------------+

```
<!-- [[[end]]] -->

**Usage:**

```bash
# Update database with new episodes
retrocast download db update

# Rebuild database from scratch
retrocast download db update --rescan

# Verify file existence
retrocast download db update --verify
```

### podcast-archiver - Archive Podcasts

Archive podcasts using the podcast-archiver backend.

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
    
    # Replace host-specific paths with placeholder
    # Match pattern: [default: /any/path/to/config.yaml] across multiple lines
    path_pattern = re.compile(r'\[default:\s+.+?/config\.yaml\]', re.DOTALL)
    text = path_pattern.sub('[default: {PLATFORM_APP_DIR}/config.yaml]', text)
    
    # Normalize line lengths to 100 chars for consistent table formatting
    # The CLI output is 120 chars wide, but we normalize to 100 for documentation
    lines = text.split('\n')
    fixed_lines = []
    target_width = 100  # Documentation standard width
    
    for line in lines:
        if line.startswith('|') and line.endswith('|'):
            # This is a table row - normalize to target width
            content = line[:-1].rstrip()
            if len(content) < target_width - 1:
                # Pad to target_width - 1 (leaving room for final |)
                line = content.ljust(target_width - 1) + '|'
            elif len(content) > target_width - 1:
                # Truncate if too long (shouldn't happen after our replacements)
                line = content[:target_width - 1] + '|'
            else:
                line = content + '|'
            fixed_lines.append(line)
        elif line.startswith('+') and line.endswith('+') and '-' in line:
            # This is a border line - normalize to target width
            line = '+' + '-' * (target_width - 2) + '+'
            fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    text = '\n'.join(fixed_lines)
    
    return text

result = CliRunner().invoke(cli, ["download", "podcast-archiver", "--help"])
cog.out("```\n{}\n```".format(clean_help_output(result.output)))
]]] -->
```
                                                                                                    
 Usage: cli download podcast-archiver [OPTIONS]                                                     
                                                                                                    
 Archive all of your favorite podcasts                                                              
                                                                                                    
+- Miscellaneous Options --------------------------------------------------------------------------+
| --help               -h             Show this message and exit.                                  |
| --feed               -f  TEXT       Feed URLs to archive. Use repeatedly for multiple feeds.     |
|                                     [env var: PODCAST_ARCHIVER_FEEDS]                            |
| --opml               -o  FILE       OPML files containing feed URLs to archive. OPML files can   |
|                                     be exported from a variety of podcatchers. Use repeatedly    |
|                                     for multiple files.                                          |
|                                     [env var: PODCAST_ARCHIVER_OPML_FILES]                       |
| --dir                -d  DIRECTORY  Directory to which to download the podcast archive. By       |
|                                     default, the archive will be created in the current working  |
|                                     directory  ('.').                                            |
|                                     [env var: PODCAST_ARCHIVER_ARCHIVE_DIRECTORY]                |
| --filename-template  -F  TEXT       Template to be used when generating filenames. Available     |
|                                     template variables are: 'episode.title,                      |
|                                     'episode.published_time, 'episode.original_filename,         |
|                                     'episode.subtitle, 'show.title, 'show.subtitle,              |
|                                     'show.author, 'show.language', and 'ext' (the filename       |
|                                     extension)                                                   |
|                                     [env var: PODCAST_ARCHIVER_FILENAME_TEMPLATE]                |
|                                     [default: {show.title}/{episode.published_time:%Y-%m-%d} -   |
|                                     {episode.title}.{ext}]                                       |
| --write-info-json                   Write episode metadata to a .info.json file next to the      |
|                                     media file itself.                                           |
|                                     [env var: PODCAST_ARCHIVER_WRITE_INFO_JSON]                  |
| --quiet              -q             Print only minimal progress information. Errors will always  |
|                                     be emitted.                                                  |
|                                     [env var: PODCAST_ARCHIVER_QUIET]                            |
| --concurrency        -C  INTEGER    Maximum number of simultaneous downloads.                    |
|                                     [env var: PODCAST_ARCHIVER_CONCURRENCY]                      |
| --dry-run            -n             Do not download any files, just print what would be done.    |
|                                     [env var: PODCAST_ARCHIVER_DRY_RUN]                          |
| --debug-partial                     Download only the first 1048576 bytes of episodes for        |
|                                     debugging purposes.                                          |
|                                     [env var: PODCAST_ARCHIVER_DEBUG_PARTIAL]                    |
| --verbose            -v             Increase the level of verbosity while downloading. Can be    |
|                                     passed multiple times. Increased verbosity and               |
|                                     non-interactive execution (in a cronjob, docker compose,     |
|                                     etc.) will disable progress bars. Non-interactive execution  |
|                                     also always raises the verbosity unless --quiet is passed.   |
|                                     [env var: PODCAST_ARCHIVER_VERBOSE]                          |
| --slugify            -S             Format filenames in the most compatible way, replacing all   |
|                                     special characters.                                          |
|                                     [env var: PODCAST_ARCHIVER_SLUGIFY_PATHS]                    |
| --max-episodes       -m  INTEGER    Only download the given number of episodes per podcast feed. |
|                                     Useful if you don't really need the entire backlog.          |
|                                     [env var: PODCAST_ARCHIVER_MAXIMUM_EPISODE_COUNT]            |
| --version            -V             Show the version and exit.                                   |
| --config-generate                   Emit an example YAML config file to stdout and exit.         |
| --config             -c  FILE       Path to a config file. Command line arguments will take      |
|                                     precedence.                                                  |
|                                     [env var: PODCAST_ARCHIVER_CONFIG]                           |
|                                     [default: {PLATFORM_APP_DIR}/config.yaml]                    |
| --database               FILE       Location of the database to keep track of downloaded         |
|                                     episodes. By default, the database will be created as        |
|                                     'podcast-archiver.db' in the directory of the config file.   |
|                                     [env var: PODCAST_ARCHIVER_DATABASE]                         |
| --ignore-database                   Ignore the episodes database when downloading. This will     |
|                                     cause files to be downloaded again, even if they already     |
|                                     exist in the database.                                       |
|                                     [env var: PODCAST_ARCHIVER_IGNORE_DATABASE]                  |
| --sleep-seconds          INTEGER    Run podcast-archiver continuously. Set to a non-zero number  |
|                                     of seconds to sleep after all available episodes have been   |
|                                     downloaded. Otherwise the application exits after all        |
|                                     downloads have been completed.                               |
|                                     [env var: PODCAST_ARCHIVER_SLEEP_SECONDS]                    |
+--------------------------------------------------------------------------------------------------+


```
<!-- [[[end]]] -->

**Usage:**

The `podcast-archiver` command passes through to the podcast-archiver CLI. See the [podcast-archiver documentation](https://github.com/janw/podcast-archiver) for detailed usage.

```bash
# Archive specific feeds
retrocast download podcast-archiver --feed <url>

# Archive from OPML file
retrocast download podcast-archiver --opml feeds.opml
```

## Examples

### Download Episode Files

Download episode audio files using aria2c:

```bash
retrocast download aria https://example.com/episode1.mp3 https://example.com/episode2.mp3
```

### Search Downloaded Episodes

Find episodes about specific topics:

```bash
retrocast download db search "climate change"
retrocast download db search "AI safety" --podcast "Future of AI"
```

### Update Episode Database

After downloading new episodes, update the database:

```bash
retrocast download db update
```

### Archive a Podcast Feed

Archive all episodes from a podcast feed:

```bash
retrocast download podcast-archiver --feed https://example.com/feed.xml
```

## Episode Storage

Downloaded episodes are stored in:
```
~/.local/share/net.memexponent.retrocast/episode_downloads/
```

Each episode includes:
- Audio file (mp3, m4a, etc.)
- Metadata file (.info.json) with episode information
