# retrocast CLI Reference

`retrocast` is a command-line tool for archiving and exploring podcast content from Overcast.

## Main Command

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli [OPTIONS] COMMAND [ARGS]...

  Manage podcast subscriptions. Download episodes. Analyze with AI.

Options:
  --version      Show the version and exit.
  -v, --verbose  Enable verbose logging output.
  -q, --quiet    Enable quiet mode (ERROR level logging only).
  --help         Show this message and exit.

Commands:
  about*         Display information about retrocast
  chat           Interactive AI chat for exploring transcribed podcast...
  configure      Manage the retrocast configuration data
  download       Download episode content with pluggable backends
  index          Create and manage search indexes
  query          Query and inspect SQLite database
  subscribe      Manage feed subscriptions
  transcribe     Manage audio transcriptions (create, search, analyze).

```
<!-- [[[end]]] -->

## Available Command Groups

- [about](about.md) - Display information about retrocast
- [chat](chat.md) - Interactive AI chat for exploring transcribed podcasts
- [configure](configure.md) - Manage retrocast configuration
- [download](download.md) - Download episode content
- [query](query.md) - Query and inspect SQLite database
- [subscribe](subscribe.md) - Synchronize subscription metadata
- [transcribe](transcribe.md) - Manage audio transcriptions
- [index](index.md) - Manage search indexes
