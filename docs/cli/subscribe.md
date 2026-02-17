# subscribe - Manage Feed Subscriptions

The `subscribe` command group manages feed subscriptions and Overcast synchronization.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["subscribe", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli subscribe [OPTIONS] COMMAND [ARGS]...

  Manage feed subscriptions

Options:
  --help  Show this message and exit.

Commands:
  overcast  Manage subscriptions via overcast plugin

```
<!-- [[[end]]] -->
