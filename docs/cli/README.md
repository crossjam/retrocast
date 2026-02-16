# CLI Documentation

This directory contains automatically generated CLI reference documentation for retrocast.

## Documentation Files

- [index.md](index.md) - Main CLI reference with overview of all commands
- [about.md](about.md) - About command documentation
- [chat.md](chat.md) - Interactive AI chat documentation
- [configure.md](configure.md) - Configuration management documentation
- [download.md](download.md) - Episode download documentation
- [query.md](query.md) - SQL query documentation
- [subscribe.md](subscribe.md) - Subscription synchronization documentation
- [transcribe.md](transcribe.md) - Transcription documentation

## Generating Documentation

The documentation is generated using [cog](https://nedbatchelder.com/code/cog/) to extract help text directly from the CLI.

### Update All Documentation

```bash
poe docs:generate
```

Or using cog directly:

```bash
python -m cogapp -r docs/cli/*.md
```

### Check if Documentation is Up to Date

```bash
poe docs:check
```

Or using cog directly:

```bash
python -m cogapp --check docs/cli/*.md
```

## How It Works

Each markdown file contains cog directives that invoke the CLI and capture its help output.

The directives look like this:
- Start marker: `<!-- [[[cog`
- Python code to execute
- End marker: `]]]` followed by `-->`
- Generated content goes between the markers
- End-output marker: `<!-- [[[end]]] -->`

When cog runs, it executes the Python code and replaces the content between the markers with the output.

Example Python code used in directives:
```python
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["command", "--help"])
cog.out("```\n{}\n```".format(result.output))
```

## Installing Dependencies

To generate documentation, you need the cogapp package:

```bash
pip install retrocast[docs]
```

Or directly:

```bash
pip install cogapp
```

## Contributing

When adding new CLI commands:

1. Create or update the appropriate markdown file in `docs/cli/`
2. Add cog directives to automatically capture help output
3. Run `poe docs:generate` to update the documentation
4. Commit both the markdown source and generated output

## CI Integration

The `docs:check` task can be added to CI to ensure documentation stays in sync with code:

```bash
poe docs:check
```

This will fail if the generated documentation doesn't match what's in the files.
