# about - Display Information About retrocast

The `about` command displays information about the retrocast application, including its purpose, features, and capabilities.

## Command Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["about", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli about [OPTIONS]

  Display information about retrocast

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## Usage

Display information about retrocast:

```bash
retrocast about
```

The command will show:
- Project description and goals
- Key features and capabilities
- Links to documentation and resources
- Version information
