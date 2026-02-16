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
  castchat       Interactive AI chat for exploring transcribed podcast...
  config         Manage the retrocast configuration data
  download       Download episode content with pluggable backends
  meta           Download episode metadata and derived information
  sql            Query and inspect SQLite database
  sync           Synchronize subscription metadata
  transcription  Manage audio transcriptions (create, search, analyze).

```
<!-- [[[end]]] -->

## Available Command Groups

- [about](about.md) - Display information about retrocast
- [castchat](castchat.md) - Interactive AI chat for exploring transcribed podcasts
- [config](config.md) - Manage retrocast configuration
- [download](download.md) - Download episode content
- [meta](meta.md) - Download episode metadata
- [sql](sql.md) - Query and inspect SQLite database
- [sync](sync.md) - Synchronize subscription metadata
- [transcription](transcription.md) - Manage audio transcriptions
