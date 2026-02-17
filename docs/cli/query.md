# query - Query Databases

The `query` command group provides database querying and inspection utilities.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["query", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli query [OPTIONS] COMMAND [ARGS]...

Query and inspect SQLite database

These commands provide read-only access to your scrobbledb database
using the sqlite-utils CLI. The database path defaults to your
scrobbledb database in the XDG data directory.

Default Database Location:
  {PLATFORM_APP_DIR}/retrocast.db


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
