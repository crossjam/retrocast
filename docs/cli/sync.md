# sync - Synchronize Subscription Metadata

The `sync` command group synchronizes your podcast subscription metadata from various sources.

## Command Group Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## Subcommands

### overcast - Sync from Overcast

Synchronize subscription metadata via the Overcast plugin.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

#### overcast all - Run All Steps

Run all synchronization steps in sequence.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "all", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
retrocast sync overcast all
```

This runs all steps: auth check, save, extend, transcripts, and chapters.

#### overcast auth - Authenticate

Save Overcast authentication credentials.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "auth", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
retrocast sync overcast auth
```

Prompts for your Overcast credentials and saves them securely.

#### overcast chapters - Download Chapters

Download and store chapter information.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "chapters", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
# Download chapters for all episodes
retrocast sync overcast chapters
```

#### overcast check - Check Status

Check authentication and database setup.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "check", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
retrocast sync overcast check
```

#### overcast episodes - Export Episodes

Export episodes as CSV or JSON.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "episodes", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
# Export all episodes as JSON
retrocast sync overcast episodes

# Export specific feed episodes
retrocast sync overcast episodes --feed "Podcast Name"
```

#### overcast extend - Download Full Feeds

Download XML feeds and extract all metadata.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "extend", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
retrocast sync overcast extend
```

Downloads full RSS/Atom feeds for all subscriptions to get complete metadata.

#### overcast html - Generate HTML

Generate HTML output for browsing episodes.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "html", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
retrocast sync overcast html
```

#### overcast init - Initialize Database

Initialize the Overcast database.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "init", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
retrocast sync overcast init
```

#### overcast save - Save to Database

Save Overcast subscription info to the database.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "save", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
retrocast sync overcast save
```

Fetches your Overcast OPML data and saves feeds, episodes, and playlists to the database.

#### overcast subscriptions - List Subscriptions

List your subscribed podcast feeds.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "subscriptions", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
retrocast sync overcast subscriptions
```

#### overcast transcripts - Download Transcripts

Download available transcripts.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sync", "overcast", "transcripts", "--help"])
cog.out("```\n{}\n```".format(result.output))
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
# Download transcripts for all episodes
retrocast sync overcast transcripts

# Download transcripts for starred episodes only
retrocast sync overcast transcripts --starred-only
```

## Typical Workflow

### Initial Setup

```bash
# 1. Authenticate with Overcast
retrocast sync overcast auth

# 2. Initialize database
retrocast sync overcast init

# 3. Run all synchronization steps
retrocast sync overcast all
```

### Regular Updates

```bash
# Quick sync of new data
retrocast sync overcast save
retrocast sync overcast extend
```

### Full Refresh

```bash
# Complete synchronization
retrocast sync overcast all
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

- Run `sync overcast auth` first on a new installation
- Use `sync overcast all` for complete synchronization
- Use `sync overcast save` for quick updates
- The `--starred` flag processes only starred episodes
- Extend downloads full feeds for rich metadata
