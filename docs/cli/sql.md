# sql - Query SQLite Database

The `sql` command group provides read-only access to query and inspect your retrocast SQLite database using the sqlite-utils CLI.

## Command Group Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## Database Location

Default database location:
```
~/.local/share/net.memexponent.retrocast/retrocast.db
```

## Core Database Tables

### Subscription Data
- `feeds` - Podcast feed information from Overcast
- `feeds_extended` - Extended metadata from full RSS feeds
- `episodes` - Episode information from Overcast
- `episodes_extended` - Extended episode metadata from RSS
- `playlists` - Overcast playlist information

### Additional Data
- `chapters` - Episode chapter markers
- `episode_downloads` - Downloaded episode tracking

### Views
- `episodes_played` - Filtered view of played episodes
- `episodes_deleted` - Filtered view of deleted episodes
- `episodes_starred` - Filtered view of starred episodes

## Subcommands

### analyze-tables - Analyze Columns

Analyze the columns in database tables.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "analyze-tables", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### dump - Export Database

Output a SQL dump of the schema and contents.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "dump", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### indexes - Show Indexes

Show indexes for the database or specific tables.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "indexes", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### memory - In-Memory Query

Execute SQL query against an in-memory database.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "memory", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### plugins - List Plugins

List installed sqlite-utils plugins.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "plugins", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### query - Execute SQL

Execute SQL query and return results as JSON.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "query", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### rows - Browse Table Data

Output all rows in a table.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "rows", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### schema - Show Schema

Show schema for database or specific tables.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "schema", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### search - Full-Text Search

Execute full-text search against a table.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "search", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### tables - List Tables

List all tables in the database.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "tables", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### triggers - Show Triggers

Show triggers configured in the database.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "triggers", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

### views - List Views

List all views in the database.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["sql", "views", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## Examples

### List All Tables

```bash
retrocast sql tables --counts
```

### View Table Schema

```bash
retrocast sql schema episodes
```

### Query Episodes

```bash
retrocast sql query "SELECT * FROM episodes LIMIT 10"
```

### Browse Table Data

```bash
retrocast sql rows episodes --limit 20
```

### Full-Text Search

```bash
retrocast sql search episodes "machine learning"
```

### Export Database

```bash
retrocast sql dump > backup.sql
```

### Use Different Database

```bash
retrocast sql query "SELECT * FROM feeds" --database /path/to/other.db
```

## Advanced Queries

### Find Recently Played Episodes

```bash
retrocast sql query "SELECT title, userUpdatedDate FROM episodes_played ORDER BY userUpdatedDate DESC LIMIT 10"
```

### Count Episodes by Feed

```bash
retrocast sql query "SELECT feeds.title, COUNT(episodes.overcastId) as count FROM feeds LEFT JOIN episodes ON feeds.overcastId = episodes.overcastFeedId GROUP BY feeds.overcastId ORDER BY count DESC"
```

### Search Episode Descriptions

```bash
retrocast sql search episodes_extended "artificial intelligence"
```

## Tips

- Use `--csv` or `--json` flags to change output format
- Use `--nl` for newline-delimited JSON
- Use `--table` for pretty table output
- Full-text search works on tables with FTS enabled (feeds, episodes)
- The database is read-only through these commands
