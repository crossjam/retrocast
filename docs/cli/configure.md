# configure - Manage Configuration

The `configure` command group manages local retrocast configuration and database setup.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["configure", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli configure [OPTIONS] COMMAND [ARGS]...

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
