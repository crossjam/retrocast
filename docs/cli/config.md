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
Usage: cli config [OPTIONS] COMMAND [ARGS]...

  Manage the retrocast configuration data

Options:
  --help  Show this message and exit.

Commands:
  archive     Archive the configuration directory as a gzipped tarball
  check       Report configuration status without making changes
  initialize  Create the retrocast configuration directory
  location    Output the location of the configuration directory.
  reset-db    Reset the database schema (WARNING: destroys all data)

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
Usage: cli config archive [OPTIONS]

  Archive the configuration directory as a gzipped tarball

Options:
  -o, --output FILE               Destination for the gzipped archive. Writes to
                                  stdout when omitted.
  -c, --compression-level INTEGER RANGE
                                  Gzip compression level (0-9).  [default: 6;
                                  0<=x<=9]
  -f, --force                     Overwrite the output archive if it exists.
  --help                          Show this message and exit.

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
Usage: cli config check [OPTIONS]

  Report configuration status without making changes

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
Usage: cli config initialize [OPTIONS]

  Create the retrocast configuration directory

Options:
  -y, --yes  Create the directory without confirmation prompts.
  --help     Show this message and exit.

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
Usage: cli config location [OPTIONS]

  Output the location of the configuration directory.

  By default, displays a formatted table showing all configuration paths. Use
  --format json to output all paths as a JSON object. Use --db-path to output
  only the database path as a JSON string. Use --app-dir to output only the app
  directory path as a JSON string.

  Examples:     retrocast config location              # Table view
  retrocast config location --format json  # All paths as JSON     retrocast
  config location --db-path    # Just database path     retrocast config
  location --app-dir    # Just app directory

Options:
  -f, --format [console|json]
  -d, --db-path                Output only the database path as a JSON string
  -a, --app-dir                Output only the app directory path as a JSON
                               string
  --help                       Show this message and exit.

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
Usage: cli config reset-db [OPTIONS]

  Reset the database schema (WARNING: destroys all data)

Options:
  --dry-run  Show what would be reset without actually performing the reset.
  -y, --yes  Skip confirmation prompt and proceed with reset.
  --help     Show this message and exit.

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
