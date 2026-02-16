# subscribe - Synchronize Subscription Metadata

The `subscribe` command group synchronizes your podcast subscription metadata from various sources.

## Command Group Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe [OPTIONS] COMMAND [ARGS]...

  Synchronize subscription metadata

Options:
  --help  Show this message and exit.

Commands:
  overcast  Synchronize subscription metadata via overcast plugin

```
<!-- [[[end]]] -->

## Subcommands

### overcast - Subscribe via Overcast

Synchronize subscription metadata via the Overcast plugin.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast [OPTIONS] COMMAND [ARGS]...

  Synchronize subscription metadata via overcast plugin

Options:
  --help  Show this message and exit.

Commands:
  all            Run all steps to save, extend, download transcripts, and...
  auth           Save authentication credentials to a JSON file.
  chapters       Download and store available chapters for all or starred...
  check          Check authentication and database setup status.
  episodes       Export episodes as CSV or JSON filtered by feed titles.
  extend         Download XML feed and extract all feed and episode tags...
  html           Download and store available chapters for all or starred...
  init           Initialize Overcast database in user platform directory.
  save           Save Overcast info to SQLite database.
  subscriptions  List feed titles.
  transcripts    Download available transcripts for all or starred episodes.

```
<!-- [[[end]]] -->

#### overcast all - Run All Steps

Run all synchronization steps in sequence.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "all", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast all [OPTIONS]

  Run all steps to save, extend, download transcripts, and chapters.

  This command sequentially executes the following: 1. Save Overcast information
  to the SQLite database. 2. Extend the database with new feed and episode data.
  3. Download available transcripts for all or starred episodes. 4. Download and
  store available chapters for all or starred episodes.

Options:
  -d, --database FILE  Path to database file (defaults to retrocast.db in app
                       directory)
  -a, --auth FILE      Custom path to auth.json file (defaults to app directory)
  -v, --verbose
  --help               Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast subscribe overcast all
```

This runs all steps: auth check, save, extend, transcripts, and chapters.

#### overcast auth - Authenticate

Save Overcast authentication credentials.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "auth", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast auth [OPTIONS]

  Save authentication credentials to a JSON file.

Options:
  -a, --auth FILE  Custom path to save auth cookie (defaults to app directory)
  --email TEXT
  --password TEXT
  --help           Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast subscribe overcast auth
```

Prompts for your Overcast credentials and saves them securely.

#### overcast chapters - Download Chapters

Download and store chapter information.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "chapters", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast chapters [OPTIONS]

  Download and store available chapters for all or starred episodes.

Options:
  -d, --database FILE   Path to database file (defaults to retrocast.db in app
                        directory)
  -p, --path DIRECTORY
  --help                Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
# Download chapters for all episodes
retrocast subscribe overcast chapters
```

#### overcast check - Check Status

Check authentication and database setup.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "check", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast check [OPTIONS]

  Check authentication and database setup status.

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast subscribe overcast check
```

#### overcast episodes - Export Episodes

Export episodes as CSV or JSON.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "episodes", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast episodes [OPTIONS] [FEED_TITLES]...

  Export episodes as CSV or JSON filtered by feed titles.

  If no feed titles are provided, exports episodes from all feeds.

Options:
  -d, --database FILE             Path to database file (defaults to
                                  retrocast.db in app directory)
  -o, --output FILE               Output file path (default: stdout)
  --format [csv|json]             Output format.
  --all-episodes / --played-episodes
                                  Only played or all episodes from selected
                                  feeds  [default: played-episodes]
  -a, --all-feeds / --subbed-feeds
                                  Select from subscribed or all feeds.
                                  [default: subbed-feeds]
  -c, --count INTEGER             Limit the number of episodes returned.
  --help                          Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
# Export all episodes as JSON
retrocast subscribe overcast episodes

# Export specific feed episodes
retrocast subscribe overcast episodes --feed "Podcast Name"
```

#### overcast extend - Download Full Feeds

Download XML feeds and extract all metadata.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "extend", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast extend [OPTIONS]

  Download XML feed and extract all feed and episode tags and attributes.

Options:
  -d, --database FILE  Path to database file (defaults to retrocast.db in app
                       directory)
  -na, --no-archive
  -v, --verbose
  --help               Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast subscribe overcast extend
```

Downloads full RSS/Atom feeds for all subscriptions to get complete metadata.

#### overcast html - Generate HTML

Generate HTML output for browsing episodes.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "html", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast html [OPTIONS]

  Download and store available chapters for all or starred episodes.

Options:
  -d, --database FILE     Path to database file (defaults to retrocast.db in app
                          directory)
  -o, --output DIRECTORY
  --help                  Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast subscribe overcast html
```

#### overcast init - Initialize Database

Initialize the Overcast database.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "init", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast init [OPTIONS]

  Initialize Overcast database in user platform directory.

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast subscribe overcast init
```

#### overcast save - Save to Database

Save Overcast subscription info to the database.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "save", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast save [OPTIONS]

  Save Overcast info to SQLite database.

Options:
  -d, --database FILE  Path to database file (defaults to retrocast.db in app
                       directory)
  -a, --auth FILE      Custom path to auth.json file (defaults to app directory)
  --load FILE          Load OPML from this file instead of the API
  -na, --no-archive
  -v, --verbose
  --help               Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast subscribe overcast save
```

Fetches your Overcast OPML data and saves feeds, episodes, and playlists to the database.

#### overcast subscriptions - List Subscriptions

List your subscribed podcast feeds.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "subscriptions", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast subscriptions [OPTIONS]

  List feed titles.

  Default is only podcasts subscribed in Overcast.

  Use --json to output detailed feed data in JSON format.

Options:
  -d, --database FILE  Path to database file (defaults to retrocast.db in app
                       directory)
  --all                List all feeds known to Overcast, not just subscribed
                       ones.
  --json               Output feed data in JSON format.
  --help               Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
retrocast subscribe overcast subscriptions
```

#### overcast transcripts - Download Transcripts

Download available transcripts.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "overcast", "transcripts", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe overcast transcripts [OPTIONS]

  Download available transcripts for all or starred episodes.

Options:
  -d, --database FILE   Path to database file (defaults to retrocast.db in app
                        directory)
  -p, --path DIRECTORY
  -s, --starred-only
  -v, --verbose
  --help                Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
# Download transcripts for all episodes
retrocast subscribe overcast transcripts

# Download transcripts for starred episodes only
retrocast subscribe overcast transcripts --starred-only
```

## Typical Workflow

### Initial Setup

```bash
# 1. Authenticate with Overcast
retrocast subscribe overcast auth

# 2. Initialize database
retrocast subscribe overcast init

# 3. Run all synchronization steps
retrocast subscribe overcast all
```

### Regular Updates

```bash
# Quick subscribe of new data
retrocast subscribe overcast save
retrocast subscribe overcast extend
```

### Full Refresh

```bash
# Complete synchronization
retrocast subscribe overcast all
```

## What Gets Synchronized?

### Basic Info (save)
- Podcast feed metadata
- Episode information
- Play history
- Starred episodes
- Playlists

### Extended Info (extend)
- Full RSS feed data
- Rich episode descriptions
- Episode artwork
- Show notes
- All RSS tags and attributes

### Additional Data
- Chapter markers
- Podcast transcripts (when available)

## Storage

All synchronized data is stored in:
```
~/.local/share/net.memexponent.retrocast/retrocast.db
```

## Tips

- Run `subscribe overcast auth` first on a new installation
- Use `subscribe overcast all` for complete synchronization
- Use `subscribe overcast save` for quick updates
- The `--starred` flag processes only starred episodes
- Extend downloads full feeds for rich metadata
