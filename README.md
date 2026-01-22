# retrocast

[![Lint](https://github.com/crossjam/retrocast/actions/workflows/lint.yml/badge.svg)](https://github.com/crossjam/retrocast/actions/workflows/lint.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/🐧️-black-000000.svg)](https://github.com/psf/black)
[![Checked with pytype](https://img.shields.io/badge/🦆-pytype-437f30.svg)](https://google.github.io/pytype/)
[![Versions](https://img.shields.io/pypi/pyversions/retrocast.svg)](https://pypi.python.org/pypi/retrocast)



This is an exploration into using AI capabilities to interactively
explore archived podcast content. 
[Overcast](https://overcast.fm) is a popular iOS podcast player that
exposes some of its data to users. _I (crossjam) also use and
recommend Overcast_.
`retrocast` work began as a clone of [Harold Martin’s
`overcast-to-sqlite`](https://github.com/hbmartin/overcast-to-sqlite)
providing a foundation for pulling podcast information from my
Overcast account. `retrocast` honors the Apache 2.0 license from
`overcast-to-sqlite`.

**Full disclosure, this project is primarily "auditionware".** The
main goal is to provide something for potential external collaborators
or employers to view and review. Yup, it’s a bit about me showing
off. If you have strong opinions feel free to fork this sucker and
take it where your heart desires.

Save listening history and feed/episode info from podcast
subscriptions (sourced via podcast clients such as Overcast) to an
SQLite database. Try exploring your podcast listening habits with
[Datasette](https://datasette.io/)!

- [How to install](#how-to-install)
- [Authentication](#authentication)
- [Fetching and saving updates](#fetching-and-saving-updates)
- [Extending and saving full feeds](#extending-and-saving-full-feeds)
- [Downloading transcripts](#downloading-transcripts)
- [Episode Download Database](#episode-download-database)
- [Audio Transcription](#audio-transcription)

## Quick run
    
	# Install uv -- https://docs.astral.sh/uv/
    $ uvx git+https://github.com/crossjam/retrocast --help

## How to install

	$ uv tool install git+https://github.com/crossjam/retrocast
	# or
    $ pipx install git+https://github.com/crossjam/retrocast
	
Or to upgrade:

	$ uv tool upgrade git+https://github.com/crossjam/retrocast
	# or
    $ pip install --upgrade git+https://github.com/crossjam/retrocast

## Overcast syncing and operations

`retrocast sync overcast` corresponds to the CLI functionality of the
prior overcast-to-sqlite codebase `retrocast` started from. By
default, `retrocast` uses an os specific user application directory to
hold and manage files it creates. `retrocast config location` can be
used to determine this location. Assume that this is the default
location for application files mentioned in the rest of this
documentation.


### Authentication

Run this command to login to Overcast (note: neither your password nor
email are saved, only the auth cookie):

    $ retrocast sync overcast auth

This will create a file called `auth.json` in an XDG conformant
platform user directory containing the required value. To save the
file at a different path or filename, use the `--auth=myauth.json`
option.

If you do not wish to save this information you can manually download
the "All data" file [from the Overcast account
page](https://overcast.fm/account) and pass it into the save command
as described below. 

### Fetching and saving updates

The `retrocast sync overcast save` command retrieves all Overcast info
and stores playlists, podcast feeds, and episodes in their respective
tables with a primary key `overcastId`.

    $ retrocast sync overcast all

By default, this saves to `retrocast.db` in the application directory
but this can be manually set.

    $ retrocast sync overcast save -d someother.db

By default, it will attempt to use the info in `auth.json` file from
the application directory. You can point to a different location
using `-a`:

    $ retrocast sync overcast save -a /path/to/auth.json

Alternately, you can skip authentication by passing in an OPML file
you downloaded from Overcast:

    $ retrocast sync overcast save --load /path/to/overcast.opml

By default, the save command will save any OPML file it downloads
adjacent to the database file in `archive/overcast/`. You can disable
this behavior with `--no-archive` or `-na`.

For increased reporting verbosity, use the `-v` flag.

### Extending and saving full feeds

The `extend` command that will download the XML files for all feeds
you are subscribed to and extract tags and attributes. These are
stored in separate tables `feeds_extended` and `episodes_extended`
with primary keys `xmlUrl` and `enclosureUrl` respectively. (See
points 4 and 5 below for more information.)

    $ retrocast sync overcast extend

Like the save command, this will attempt to archive feeds to
`archive/feeds/` by default. This can be disabled with `--no-archive`
or `-na`. 

It also supports the `-v` flag to print additional information.

There are a few caveats for this functionality:

1. The first time this is invoked will require downloading and parsing
   an XML file for each feed you are subscribed to. (Subsequent
   invocations only require this for new episodes loaded by `save`)
   Because this command may take a long time to run if you have many
   feeds, it is recommended to use the `-v` flag to observe progress.
2. This will increase the size of your database by approximately 2 MB
   per feed, so may result in a large file if you subscribe to many
   feeds.
3. Certain feeds may not load due to e.g. authentication, rate
   limiting, or other issues. These will be logged to the console and
   the feed will be skipped. Likewise, an episode may appear in your
   episodes table but not in the extended information if it is no
   longer available.
4. The `_extended` tables use URLs as their primary key. This may
   potentially lead to unjoinable / orphaned episodes if the enclosure
   URL (i.e. URL of the audio file) has changed since Overcast stored
   it.
5. There is no guarantee of which columns will be present in these
   tables aside from URL, title, and description. This command
   attempts to capture and normalize all XML tags contained in the
   feed so it is likely that many columns will be created and only a
   few rows will have values for uncommon tags/attributes.

Any suggestions for improving on these caveats are welcome, please
[open an issue](https://github.com/crossjam/retrocast/issues)!

### Downloading transcripts

The `transcripts` command will download the transcripts from pod
metadata if available.

The `save` and `extend` commands MUST be run prior to this.

Episodes with a "podcast:transcript:url" value will be downloaded from
that URL and the download's location will then be stored in
"transcriptDownloadPath".

    $ retrocast meta overcast transcripts

Like previous commands, by default this will save transcripts to
`${APP_DIR}/archive/transcripts/<feed title>/<episode title>` by
default.

A different path can be set with the `-p`/`--path` flag.

It also supports the `-v` flag to print additional information.

There is also a `-s` flag to only download transcripts for starred episodes.

### Episode Download Database

The episode download database feature allows you to index and search
podcast episodes downloaded via
[podcast-archiver](https://github.com/janw/podcast-archiver). This
creates a searchable database of your downloaded episode collection. 

There is also stubbed functionality to use `aria2` as an embedded
download server for an alternative, higher performance backend.

#### Downloading Episodes

Use the `download podcast-archiver` command to download podcast episodes:

    $ retrocast download podcast-archiver --feed https://example.com/feed.xml

By default, episodes are downloaded to
`${APP_DIR}/episode_downloads/` with `.info.json` metadata files
created automatically.

For more options, see:

    $ retrocast download podcast-archiver --help

#### Indexing Downloaded Episodes

Initialize the episode database (one-time setup):

    $ retrocast download db init

Scan your downloaded episodes and populate the database:

    $ retrocast download db update

This will:
- Discover all media files in your downloads directory
- Extract metadata from `.info.json` files
- Index episode titles, descriptions, and show notes for full-text search
- Track file locations, sizes, and timestamps

Options:
- `--rescan`: Delete existing records and rebuild from scratch
- `--verify`: Check for missing files and mark them in the database

#### Searching Episodes

Search your downloaded episodes using full-text search:

    $ retrocast sync overcast download db search "machine learning"
    $ retrocast sync overcast download db search "python" --podcast "Talk Python To Me"
    $ retrocast sync overcast download db search "interview" --limit 10

The search looks across:
- Episode titles
- Descriptions
- Summaries
- Show notes
- Podcast titles

Results are displayed in a formatted table with episode details.

### Workflow Example

Complete workflow for downloading and indexing podcasts:

```bash
# One-time setup
retrocast download db init

# Download episodes (creates .info.json files automatically)
retrocast download podcast-archiver --feed https://example.com/feed.xml

# Index the downloaded episodes
retrocast download db update

# Search your collection
retrocast download db search "topic you're interested in"
```

#### Database Schema

Downloaded episodes are stored in the `episode_downloads` table within `retrocast.db` with the following information:

- Media file path and metadata
- Episode title, description, summary, and show notes
- Publication date and duration
- Full `.info.json` metadata as JSON
- File existence tracking

Full-text search is enabled via SQLite FTS5 for fast searching across all text fields.

### Audio Transcription

The transcription module enables you to transcribe podcast audio files
to searchable text using state-of-the-art Whisper speech recognition
models. 

#### Features

- **Multiple Backends**: MLX Whisper (Apple Silicon), faster-whisper (CUDA/CPU)
- **Auto-Detection**: Automatically selects the best available backend for your platform
- **Content Deduplication**: SHA256 hashing prevents re-transcribing the same audio
- **Full-Text Search**: Search across all transcribed content using SQLite FTS5
- **Multiple Formats**: Export as TXT, JSON, SRT (subtitles), or VTT (WebVTT)

#### Installing Transcription Backends

```bash
# For Apple Silicon Macs (M1/M2/M3) - fastest performance
poe install:transcription-mlx

# For Linux/Windows with NVIDIA GPU
poe install:transcription-cuda

# For CPU-only (any platform)
poe install:transcription-cpu
```

### Transcription Quick Start

```bash
# Check available backends
retrocast transcription backends list

# Transcribe a single audio file
retrocast transcription process episode.mp3

# Transcribe with specific options
retrocast transcription process --model medium --format srt episode.mp3

# Transcribe all files in a directory
retrocast transcription process ~/podcasts/

# Search transcribed content
retrocast transcription search "machine learning"
retrocast transcription search --podcast "Tech Talk" "python"
```

### Transcription CLI Commands

| Command | Description |
|---------|-------------|
| `retrocast transcription process PATH...` | Transcribe audio files |
| `retrocast transcription backends list` | List available backends |
| `retrocast transcription backends test BACKEND` | Test a specific backend |
| `retrocast transcription search QUERY` | Search transcribed content |
| `retrocast transcription summary` | Show transcription statistics |
| `retrocast transcription podcasts list` | List podcasts with transcriptions |
| `retrocast transcription episodes list` | List transcribed episodes |

### Options for `transcription process`

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--backend` | auto, mlx-whisper, faster-whisper | auto | Backend to use |
| `--model` | tiny, base, small, medium, large | base | Whisper model size |
| `--language` | en, es, fr, etc. | auto | Audio language |
| `--format` | txt, json, srt, vtt | json | Output format |
| `--force` | flag | false | Re-transcribe existing files |

#### Supported Audio Formats

MP3, M4A, OGG, Opus, WAV, FLAC, AAC

For comprehensive documentation including performance benchmarks,
troubleshooting, and advanced usage, see the [Transcription
Guide](docs/TRANSCRIPTION.md).

## See also

- [Datasette](https://datasette.io/)
- [Podcast Transcript Convert](https://github.com/hbmartin/podcast-transcript-convert/)
- [Overcast Parser](https://github.com/hbmartin/overcast_parser)
- [Podcast Archiver](https://github.com/janw/podcast-archiver)

## Development

**As mentioned above, this project is primarily "auditionware".** 

However, pull requests and issues are welcome, at least as criticism,
feedback, and inspiration! There might be a lag on responding or
acceptance though. You’re likely best off assuming that a PR will take
forever to be accepted if at all. Similarly for addressing issues. For
major changes, please open an issue first to discuss what you would
like to change.

### Setup

```bash
git clone https://github.com/crossjam/retrocast.git
cd retrocast
uv sync
uv run retrocast all -v
```

### Running QA Tasks

This project uses [PoeThePoet](https://poethepoet.natn.io/) for task automation. Available tasks:

```bash
# Run all QA checks (lint, type check, test)
uv run poe qa

# Individual tasks
uv run poe lint        # Run ruff linter
uv run poe lint:fix    # Run ruff and auto-fix issues
uv run poe type        # Run ty type checker
uv run poe test        # Run pytest with verbose output
uv run poe test:cov    # Run pytest with coverage report
uv run poe test:quick  # Run pytest and stop on first failure

# List all available tasks
uv run poe --help
```

### Code Formatting

This project is linted with [ruff](https://docs.astral.sh/ruff/) and
uses [Black](https://github.com/ambv/black) code formatting. 

## Authors

* [Brian M. Dennis](https://bmdphd.info) - bmd at bmdphd dot info
* [Harold Martin](https://www.linkedin.com/in/harold-martin-98526971/) - harold.martin at gmail
