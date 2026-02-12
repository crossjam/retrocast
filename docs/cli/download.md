# download - Download Episode Content

The `download` command group provides tools for downloading podcast episode files using different backends.

## Command Group Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["download", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli download[0m [[1;36mOPTIONS[0m] [1;36mCOMMAND[0m [[1;36mARGS[0m]...                                                                        
                                                                                                                        
 Download episode content with pluggable backends                                                                       
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--help[0m  Show this message and exit.                                                                                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Commands [0m[2m──────────────────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36maria            [0m[1;36m [0m Download URLs using the aria2c fetcher.                                                            [2m│[0m
[2m│[0m [1;36mdb              [0m[1;36m [0m Manage downloaded episodes database.                                                               [2m│[0m
[2m│[0m [1;36mpodcast-archiver[0m[1;36m [0m Archive all of your favorite podcasts                                                              [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

```
<!-- [[[end]]] -->

## Subcommands

### aria - Download with aria2c

Download URLs using the embedded aria2c fetcher.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["download", "aria", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli download aria[0m [[1;36mOPTIONS[0m] [[1;36mFILENAME[0m]                                                                          
                                                                                                                        
 Download URLs using the aria2c fetcher.                                                                                
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--directory     [0m  [1;32m-d[0m  [1;33mDIRECTORY           [0m  Directory to store downloaded files.                                     [2m│[0m
[2m│[0m                                             [2m[default: /home/runner/work/retrocast/retrocast]                        [0m [2m│[0m
[2m│[0m [1;36m--max-concurrent[0m  [1;32m-j[0m  [1;33mINTEGER RANGE [0m[1;2;33m[[0m[1;33mx>=1[0m[1;2;33m][0m  Maximum concurrent aria2c downloads.                                     [2m│[0m
[2m│[0m                                             [2m[default: 5]                                                            [0m [2m│[0m
[2m│[0m [1;36m--verbose       [0m  [1;32m-v[0m                        Enable verbose logging for this command.                                 [2m│[0m
[2m│[0m [1;36m--secret        [0m      [1;33mTEXT                [0m  RPC secret token for aria2c.                                             [2m│[0m
[2m│[0m [1;36m--help          [0m                            Show this message and exit.                                              [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["download", "db", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli download db[0m [[1;36mOPTIONS[0m] [1;36mCOMMAND[0m [[1;36mARGS[0m]...                                                                     
                                                                                                                        
 Manage downloaded episodes database.                                                                                   
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--help[0m  Show this message and exit.                                                                                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Commands [0m[2m──────────────────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36minit  [0m[1;36m [0m Initialize episode downloads database schema.                                                                [2m│[0m
[2m│[0m [1;36msearch[0m[1;36m [0m Search episode downloads using full-text search.                                                             [2m│[0m
[2m│[0m [1;36mupdate[0m[1;36m [0m Update episode downloads database from filesystem.                                                           [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

```
<!-- [[[end]]] -->

#### db init - Initialize Database

Initialize the episode downloads database schema.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["download", "db", "init", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli download db init[0m [[1;36mOPTIONS[0m]                                                                                  
                                                                                                                        
 Initialize episode downloads database schema.                                                                          
 [2mCreates the episode_downloads table and indexes in the retrocast database.[0m[2m [0m[2mThis command is idempotent and safe to run [0m 
 [2mmultiple times.[0m                                                                                                        
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--dry-run[0m        Show what would be created without making changes.                                                  [2m│[0m
[2m│[0m [1;36m--db-path[0m  [1;33mFILE[0m  Path to database file. Defaults to app directory.                                                   [2m│[0m
[2m│[0m [1;36m--help   [0m        Show this message and exit.                                                                         [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["download", "db", "search", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli download db search[0m [[1;36mOPTIONS[0m] [1;36mQUERY[0m                                                                          
                                                                                                                        
 Search episode downloads using full-text search.                                                                       
 [2mSearches episode titles, descriptions, summaries, and shownotes.[0m                                                       
                                                                                                                        
 [2mExamples:[0m[2m [0m[2mretrocast download db search "python"[0m[2m [0m[2mretrocast download db search "machine learning" --podcast "Practical [0m  
 [2mAI"[0m[2m [0m[2mretrocast download db search "interview" --limit 10[0m                                                                
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--podcast[0m  [1;33mTEXT   [0m  Filter by podcast title (exact match).                                                           [2m│[0m
[2m│[0m [1;36m--limit  [0m  [1;33mINTEGER[0m  Maximum number of results to display.                                                            [2m│[0m
[2m│[0m                     [2m[default: 20]                                                                                   [0m [2m│[0m
[2m│[0m [1;36m--db-path[0m  [1;33mFILE   [0m  Path to database file. Defaults to app directory.                                                [2m│[0m
[2m│[0m [1;36m--help   [0m           Show this message and exit.                                                                      [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["download", "db", "update", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli download db update[0m [[1;36mOPTIONS[0m]                                                                                
                                                                                                                        
 Update episode downloads database from filesystem.                                                                     
 [2mScans the episode_downloads directory and updates the database with[0m[2m [0m[2mdiscovered episodes and their metadata from [0m       
 [2m.info.json files.[0m                                                                                                      
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--rescan       [0m             Delete existing records and rebuild from scratch.                                        [2m│[0m
[2m│[0m [1;36m--verify       [0m             Verify all files still exist and mark missing ones.                                      [2m│[0m
[2m│[0m [1;36m--db-path      [0m  [1;33mFILE     [0m  Path to database file. Defaults to app directory.                                        [2m│[0m
[2m│[0m [1;36m--downloads-dir[0m  [1;33mDIRECTORY[0m  Path to episode_downloads directory. Defaults to app directory.                          [2m│[0m
[2m│[0m [1;36m--help         [0m             Show this message and exit.                                                              [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m

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
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["download", "podcast-archiver", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
                                                                                                                        
 [33mUsage:[0m [1mcli download podcast-archiver[0m [OPTIONS]                                                                         
                                                                                                                        
 Archive all of your favorite podcasts                                                                                  
                                                                                                                        
[2m╭─[0m[2m Miscellaneous Options [0m[2m─────────────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m--help             [0m  [1;32m-h[0m             Show this message and exit.                                                      [2m│[0m
[2m│[0m [1;36m--feed             [0m  [1;32m-f[0m  [1;33mTEXT     [0m  Feed URLs to archive. Use repeatedly for multiple feeds.                         [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_FEEDS]                                               [0m [2m│[0m
[2m│[0m [1;36m--opml             [0m  [1;32m-o[0m  [1;33mFILE     [0m  OPML files containing feed URLs to archive. OPML files can be exported from a    [2m│[0m
[2m│[0m                                     variety of podcatchers. Use repeatedly for multiple files.                       [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_OPML_FILES]                                          [0m [2m│[0m
[2m│[0m [1;36m--dir              [0m  [1;32m-d[0m  [1;33mDIRECTORY[0m  Directory to which to download the podcast archive. By default, the archive will [2m│[0m
[2m│[0m                                     be created in the current working directory  ('.').                              [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_ARCHIVE_DIRECTORY]                                   [0m [2m│[0m
[2m│[0m [1;36m--filename-template[0m  [1;32m-F[0m  [1;33mTEXT     [0m  Template to be used when generating filenames. Available template variables are: [2m│[0m
[2m│[0m                                     'episode.title, 'episode.published_time, 'episode.original_filename,             [2m│[0m
[2m│[0m                                     'episode.subtitle, 'show.title, 'show.subtitle, 'show.author, 'show.language',   [2m│[0m
[2m│[0m                                     and 'ext' (the filename extension)                                               [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_FILENAME_TEMPLATE]                                   [0m [2m│[0m
[2m│[0m                                     [2m[default: {show.title}/{episode.published_time:%Y-%m-%d} -                      [0m [2m│[0m
[2m│[0m                                     [2m{episode.title}.{ext}]                                                          [0m [2m│[0m
[2m│[0m [1;36m--write-info-json  [0m                 Write episode metadata to a .info.json file next to the media file itself.       [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_WRITE_INFO_JSON]                                     [0m [2m│[0m
[2m│[0m [1;36m--quiet            [0m  [1;32m-q[0m             Print only minimal progress information. Errors will always be emitted.          [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_QUIET]                                               [0m [2m│[0m
[2m│[0m [1;36m--concurrency      [0m  [1;32m-C[0m  [1;33mINTEGER  [0m  Maximum number of simultaneous downloads.                                        [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_CONCURRENCY]                                         [0m [2m│[0m
[2m│[0m [1;36m--dry-run          [0m  [1;32m-n[0m             Do not download any files, just print what would be done.                        [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_DRY_RUN]                                             [0m [2m│[0m
[2m│[0m [1;36m--debug-partial    [0m                 Download only the first 1048576 bytes of episodes for debugging purposes.        [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_DEBUG_PARTIAL]                                       [0m [2m│[0m
[2m│[0m [1;36m--verbose          [0m  [1;32m-v[0m             Increase the level of verbosity while downloading. Can be passed multiple times. [2m│[0m
[2m│[0m                                     Increased verbosity and non-interactive execution (in a cronjob, docker compose, [2m│[0m
[2m│[0m                                     etc.) will disable progress bars. Non-interactive execution also always raises   [2m│[0m
[2m│[0m                                     the verbosity unless --quiet is passed.                                          [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_VERBOSE]                                             [0m [2m│[0m
[2m│[0m [1;36m--slugify          [0m  [1;32m-S[0m             Format filenames in the most compatible way, replacing all special characters.   [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_SLUGIFY_PATHS]                                       [0m [2m│[0m
[2m│[0m [1;36m--max-episodes     [0m  [1;32m-m[0m  [1;33mINTEGER  [0m  Only download the given number of episodes per podcast feed. Useful if you don't [2m│[0m
[2m│[0m                                     really need the entire backlog.                                                  [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_MAXIMUM_EPISODE_COUNT]                               [0m [2m│[0m
[2m│[0m [1;36m--version          [0m  [1;32m-V[0m             Show the version and exit.                                                       [2m│[0m
[2m│[0m [1;36m--config-generate  [0m                 Emit an example YAML config file to stdout and exit.                             [2m│[0m
[2m│[0m [1;36m--config           [0m  [1;32m-c[0m  [1;33mFILE     [0m  Path to a config file. Command line arguments will take precedence.              [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_CONFIG]                                              [0m [2m│[0m
[2m│[0m [1;36m--database         [0m      [1;33mFILE     [0m  Location of the database to keep track of downloaded episodes. By default, the   [2m│[0m
[2m│[0m                                     database will be created as 'podcast-archiver.db' in the directory of the config [2m│[0m
[2m│[0m                                     file.                                                                            [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_DATABASE]                                            [0m [2m│[0m
[2m│[0m [1;36m--ignore-database  [0m                 Ignore the episodes database when downloading. This will cause files to be       [2m│[0m
[2m│[0m                                     downloaded again, even if they already exist in the database.                    [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_IGNORE_DATABASE]                                     [0m [2m│[0m
[2m│[0m [1;36m--sleep-seconds    [0m      [1;33mINTEGER  [0m  Run podcast-archiver continuously. Set to a non-zero number of seconds to sleep  [2m│[0m
[2m│[0m                                     after all available episodes have been downloaded. Otherwise the application     [2m│[0m
[2m│[0m                                     exits after all downloads have been completed.                                   [2m│[0m
[2m│[0m                                     [2;33m[env var: PODCAST_ARCHIVER_SLEEP_SECONDS]                                       [0m [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯[0m


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
