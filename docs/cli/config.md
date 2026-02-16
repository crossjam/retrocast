# config - Manage Configuration

The `config` command group manages the retrocast configuration directory and database.

## Command Group Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["config", "--help"])
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

### archive - Archive Configuration

Create a compressed backup of your configuration directory.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["config", "archive", "--help"])
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
retrocast config archive
```

Creates a gzipped tarball of your configuration directory in your home directory.

### check - Check Status

Check the status of your configuration and database without making changes.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["config", "check", "--help"])
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
retrocast config check
```

Reports on:
- Configuration directory location
- Database file existence and location
- Authentication status

### initialize - Initialize Configuration

Create the retrocast configuration directory and database.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["config", "initialize", "--help"])
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
retrocast config initialize
```

Creates the configuration directory structure in the XDG data directory (typically `~/.local/share/net.memexponent.retrocast/` on Linux).

### location - Show Location

Display the path to your configuration directory.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["config", "location", "--help"])
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
retrocast config location
```

Outputs the absolute path to your configuration directory.

### reset-db - Reset Database

Reset the database schema, destroying all existing data.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["config", "reset-db", "--help"])
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
retrocast config reset-db
```

**⚠️ WARNING:** This command destroys all data in the database. Use with caution and only when you want to start fresh.

## Configuration Directory

The configuration directory contains:
- `retrocast.db` - SQLite database with podcast metadata
- `auth.json` - Overcast authentication credentials
- `episode_downloads/` - Downloaded episode files
- `transcripts/` - Episode transcription files
- `chapters/` - Chapter information

## Examples

Check if your setup is ready:

```bash
retrocast config check
```

Initialize a fresh installation:

```bash
retrocast config initialize
```

Find your configuration directory:

```bash
retrocast config location
```

Backup your configuration before major changes:

```bash
retrocast config archive
```
