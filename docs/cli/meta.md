# meta - Download Episode Metadata

The `meta` command group provides tools for downloading episode metadata and derived information.

## Command Group Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["meta", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli meta [OPTIONS] COMMAND [ARGS]...

  Download episode metadata and derived information

Options:
  --help  Show this message and exit.

Commands:
  overcast  Retrieve episode metadata and information via overcast plugin

```
<!-- [[[end]]] -->

## Subcommands

### overcast - Overcast Metadata

Retrieve episode metadata via the Overcast plugin.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["meta", "overcast", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli meta overcast [OPTIONS] COMMAND [ARGS]...

  Retrieve episode metadata and information via overcast plugin

Options:
  --help  Show this message and exit.

Commands:
  chapters     Download and store available chapters for all or starred...
  transcripts  Download available transcripts for all or starred episodes.

```
<!-- [[[end]]] -->

#### overcast chapters - Download Chapters

Download and store available chapters for episodes.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["meta", "overcast", "chapters", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli meta overcast chapters [OPTIONS]

  Download and store available chapters for all or starred episodes.

Options:
  -d, --database FILE   Path to database file (defaults to retrocast.db in app
                        directory)
  -p, --path DIRECTORY
  --help                Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
# Download chapters for all episodes
retrocast meta overcast chapters
```

#### overcast transcripts - Download Transcripts

Download available transcripts for episodes.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["meta", "overcast", "transcripts", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli meta overcast transcripts [OPTIONS]

  Download available transcripts for all or starred episodes.

Options:
  -d, --database FILE   Path to database file (defaults to retrocast.db in app
                        directory)
  -p, --path DIRECTORY
  -s, --starred-only
  -v, --verbose
  --help                Show this message and exit.

```
<!-- [[[end]]] -->

**Usage:**

```bash
# Download transcripts for all episodes
retrocast meta overcast transcripts

# Download transcripts for starred episodes only
retrocast meta overcast transcripts --starred-only
```

## What Are Chapters?

Podcast chapters are markers in audio files that divide an episode into segments. They can include:
- Chapter titles
- Start times
- URLs and images
- Descriptions

## What Are Transcripts?

Some podcasts provide pre-generated transcripts in various formats (VTT, SRT, JSON). These transcripts contain:
- Time-stamped text of spoken content
- Speaker labels (in some cases)
- Word-level timing (in some formats)

## Examples

### Download All Chapters

```bash
retrocast meta overcast chapters
```

### Download Transcripts

```bash
retrocast meta overcast transcripts
```

### Download Transcripts for Starred Episodes

```bash
retrocast meta overcast transcripts --starred-only
```

## Storage

Downloaded metadata is stored in:
- **Chapters**: Database table `chapters`
- **Transcripts**: `~/.local/share/net.memexponent.retrocast/transcripts/` directory

## Notes

- Chapter and transcript availability depends on the podcast feed
- Not all podcasts provide chapters or transcripts
- Chapters are embedded in the RSS feed or audio file metadata
- Transcripts may be provided as separate files linked in the feed
