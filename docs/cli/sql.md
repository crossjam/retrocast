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
Usage: cli sql [OPTIONS] COMMAND [ARGS]...

Query and inspect SQLite database

These commands provide read-only access to your scrobbledb database
using the sqlite-utils CLI. The database path defaults to your
scrobbledb database in the XDG data directory.

Default Database Location:
  /home/runner/.local/share/net.memexponent.retrocast/retrocast.db

To check if your database is initialized:
  scrobbledb init --dry-run

Core Scrobble Data Tables:
  artists - Artist information (id, name)
  albums  - Album information (id, title, artist_id)
  tracks  - Track information (id, title, album_id)
  plays   - Play events (track_id, timestamp)

Examples:

  # Query the database
  scrobbledb sql query "SELECT * FROM tracks LIMIT 10"

  # List all tables with row counts
  scrobbledb sql tables --counts

  # View table schema
  scrobbledb sql schema tracks

  # Browse table data
  scrobbledb sql rows plays --limit 20

  # Use a different database
  scrobbledb sql query "SELECT * FROM users" --database /path/to/other.db

Options:
  -d, --database FILE  Database path (default: scrobbledb database in XDG data
                       dir)
  --help               Show this message and exit.

Commands:
  analyze-tables  Analyze the columns in one or more tables.
  dump            Output a SQL dump of the schema and full contents of the...
  indexes         Show indexes for the whole database or specific tables.
  memory          Execute SQL query against an in-memory database,...
  plugins         List installed sqlite-utils plugins.
  query           Execute SQL query and return the results as JSON.
  rows            Output all rows in the specified table.
  schema          Show full schema for this database or for specified tables.
  search          Execute a full-text search against this table.
  tables          List the tables in the database.
  triggers        Show triggers configured in this database.
  views           List the views in the database.

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
Usage: cli sql analyze-tables [OPTIONS] [TABLES]...

  Analyze the columns in one or more tables.

  Example:

          scrobbledb sql analyze-tables tracks
          scrobbledb sql analyze-tables tracks -c artist_name

Options:
  -c, --column TEXT       Specific columns to analyze
  --save                  Save results to _analyze_tables table
  --common-limit INTEGER  How many common values to return for each column
                          (default 10)
  --no-most               Skip most common values
  --no-least              Skip least common values
  --load-extension TEXT   Path to SQLite extension, with optional :entrypoint
  --help                  Show this message and exit.

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
Usage: cli sql dump [OPTIONS]

  Output a SQL dump of the schema and full contents of the database.

  Example:

          scrobbledb sql dump > backup.sql

Options:
  --load-extension TEXT  Path to SQLite extension, with optional :entrypoint
  --help                 Show this message and exit.

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
Usage: cli sql indexes [OPTIONS] [TABLES]...

  Show indexes for the whole database or specific tables.

  Example:

          scrobbledb sql indexes
          scrobbledb sql indexes tracks

Options:
  --aux                  Include auxiliary columns
  --nl                   Output newline-delimited JSON
  --arrays               Output rows as arrays instead of objects
  --csv                  Output CSV
  --tsv                  Output TSV
  --no-headers           Omit CSV headers
  -t, --table            Output as a formatted table
  --fmt TEXT             Table format - see tabulate documentation for available
                         formats
  --json-cols            Detect JSON cols and output them as JSON, not escaped
                         strings
  --load-extension TEXT  Path to SQLite extension, with optional :entrypoint
  --help                 Show this message and exit.

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
Usage: cli sql memory [OPTIONS] [PATHS]... SQL_QUERY

  Execute SQL query against an in-memory database, optionally populated by
  imported data.

  Example:

          scrobbledb sql memory data.csv "SELECT * FROM data LIMIT 10"

Options:
  --functions TEXT            Python code defining one or more custom SQL
                              functions
  --attach <TEXT FILE>...     Additional databases to attach - specify alias and
                              filepath
  --flatten                   Flatten nested JSON objects, so {"foo": {"bar":
                              1}} becomes {"foo_bar": 1}
  --nl                        Output newline-delimited JSON
  --arrays                    Output rows as arrays instead of objects
  --csv                       Output CSV
  --tsv                       Output TSV
  --no-headers                Omit CSV headers
  -t, --table                 Output as a formatted table
  --fmt TEXT                  Table format - see tabulate documentation for
                              available formats
  --json-cols                 Detect JSON cols and output them as JSON, not
                              escaped strings
  -r, --raw                   Raw output, first column of first row
  --raw-lines                 Raw output, first column of each row
  -p, --param <TEXT TEXT>...  Named :parameters for SQL query
  --encoding TEXT             Character encoding for CSV files
  --no-detect-types           Treat all CSV columns as TEXT
  --schema                    Show SQL schema for in-memory database
  --dump                      Dump SQL for in-memory database
  --save FILE                 Save in-memory database to this file
  --analyze                   Analyze resulting tables
  --load-extension TEXT       Path to SQLite extension, with optional
                              :entrypoint
  --help                      Show this message and exit.

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
Usage: cli sql plugins [OPTIONS]

  List installed sqlite-utils plugins.

  Example:

          scrobbledb sql plugins

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
Usage: cli sql query [OPTIONS] SQL_QUERY

  Execute SQL query and return the results as JSON.

  Example:

          scrobbledb sql query "SELECT * FROM tracks WHERE artist_id = :id LIMIT 10" -p id 123

Options:
  --attach <TEXT FILE>...     Additional databases to attach - specify alias and
                              filepath
  --nl                        Output newline-delimited JSON
  --arrays                    Output rows as arrays instead of objects
  --csv                       Output CSV
  --tsv                       Output TSV
  --no-headers                Omit CSV headers
  -t, --table                 Output as a formatted table
  --fmt TEXT                  Table format - see tabulate documentation for
                              available formats
  --json-cols                 Detect JSON cols and output them as JSON, not
                              escaped strings
  -r, --raw                   Raw output, first column of first row
  --raw-lines                 Raw output, first column of each row
  -p, --param <TEXT TEXT>...  Named :parameters for SQL query
  --functions TEXT            Python code defining one or more custom SQL
                              functions
  --load-extension TEXT       Path to SQLite extension, with optional
                              :entrypoint
  --help                      Show this message and exit.

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
Usage: cli sql rows [OPTIONS] TABLE_NAME

  Output all rows in the specified table.

  Example:

          scrobbledb sql rows plays --limit 20
          scrobbledb sql rows tracks -c artist_name -c track_title --limit 10
          scrobbledb sql rows plays --where "timestamp > :date" -p date 2024-01-01

  Security Note:     The --where and --order options accept raw SQL. Use --param
  for untrusted user data     to prevent SQL injection. Column and table names
  are automatically quoted.

Options:
  -c, --column TEXT           Columns to return
  --where TEXT                SQL where clause to filter rows (use --param for
                              user data)
  -o, --order TEXT            Order by ('column' or 'column desc')
  --limit INTEGER             Number of rows to return
  --offset INTEGER            SQL offset to use
  --nl                        Output newline-delimited JSON
  --arrays                    Output rows as arrays instead of objects
  --csv                       Output CSV
  --tsv                       Output TSV
  --no-headers                Omit CSV headers
  -t, --table-format          Output as a formatted table
  --fmt TEXT                  Table format - see tabulate documentation for
                              available formats
  --json-cols                 Detect JSON cols and output them as JSON, not
                              escaped strings
  -p, --param <TEXT TEXT>...  Named :parameters for SQL query
  --load-extension TEXT       Path to SQLite extension, with optional
                              :entrypoint
  --help                      Show this message and exit.

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
Usage: cli sql schema [OPTIONS] [TABLES]...

  Show full schema for this database or for specified tables.

  Example:

          scrobbledb sql schema
          scrobbledb sql schema tracks plays

Options:
  --load-extension TEXT  Path to SQLite extension, with optional :entrypoint
  --help                 Show this message and exit.

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
Usage: cli sql search [OPTIONS] DBTABLE Q

  Execute a full-text search against this table.

  Example:

          scrobbledb sql search tracks "rolling stones" --limit 10

Options:
  -o, --order [relevance|score]  Order by relevance or score (relevance is the
                                 default)
  -c, --column TEXT              Columns to return
  --limit INTEGER                Number of rows to return
  --sql                          Show SQL query that would be run
  --quote                        Apply FTS quoting rules to search term
  --nl                           Output newline-delimited JSON
  --arrays                       Output rows as arrays instead of objects
  --csv-output, --csv            Output CSV
  --tsv                          Output TSV
  --no-headers                   Omit CSV headers
  -t, --table                    Output as a formatted table
  --fmt TEXT                     Table format - see tabulate documentation for
                                 available formats
  --json-cols                    Detect JSON cols and output them as JSON, not
                                 escaped strings
  --load-extension TEXT          Path to SQLite extension, with optional
                                 :entrypoint
  --help                         Show this message and exit.

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
Usage: cli sql tables [OPTIONS]

  List the tables in the database.

  Example:

          scrobbledb sql tables --counts --columns

Options:
  --fts4                 Just show FTS4 enabled tables
  --fts5                 Just show FTS5 enabled tables
  --counts               Include row counts per table
  --nl                   Output newline-delimited JSON
  --arrays               Output rows as arrays instead of objects
  --csv                  Output CSV
  --tsv                  Output TSV
  --no-headers           Omit CSV headers
  -t, --table            Output as a formatted table
  --fmt TEXT             Table format - see tabulate documentation for available
                         formats
  --json-cols            Detect JSON cols and output them as JSON, not escaped
                         strings
  --columns              Include list of columns for each table
  --schema               Include schema for each table
  --load-extension TEXT  Path to SQLite extension, with optional :entrypoint
  --help                 Show this message and exit.

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
Usage: cli sql triggers [OPTIONS] [TABLES]...

  Show triggers configured in this database.

  Example:

          scrobbledb sql triggers

Options:
  --nl                   Output newline-delimited JSON
  --arrays               Output rows as arrays instead of objects
  --csv                  Output CSV
  --tsv                  Output TSV
  --no-headers           Omit CSV headers
  -t, --table            Output as a formatted table
  --fmt TEXT             Table format - see tabulate documentation for available
                         formats
  --json-cols            Detect JSON cols and output them as JSON, not escaped
                         strings
  --load-extension TEXT  Path to SQLite extension, with optional :entrypoint
  --help                 Show this message and exit.

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
Usage: cli sql views [OPTIONS]

  List the views in the database.

  Example:

          scrobbledb sql views --counts

Options:
  --counts               Include row counts per view
  --nl                   Output newline-delimited JSON
  --arrays               Output rows as arrays instead of objects
  --csv                  Output CSV
  --tsv                  Output TSV
  --no-headers           Omit CSV headers
  -t, --table            Output as a formatted table
  --fmt TEXT             Table format - see tabulate documentation for available
                         formats
  --json-cols            Detect JSON cols and output them as JSON, not escaped
                         strings
  --columns              Include list of columns for each view
  --schema               Include schema for each view
  --load-extension TEXT  Path to SQLite extension, with optional :entrypoint
  --help                 Show this message and exit.

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
