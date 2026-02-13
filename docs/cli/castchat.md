# castchat - Interactive AI Chat

The `castchat` command starts an interactive AI-powered REPL session for exploring your podcast transcription archive using natural language queries.

## Command Help

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["castchat", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli castchat [OPTIONS]

  Interactive AI chat for exploring transcribed podcast content.

  Start an interactive REPL session powered by PydanticAI to explore your
  podcast transcription archive using natural language queries. The agent can
  search across all transcribed episodes to answer questions about topics,
  guests, and specific content.

  Requires chromadb and pydantic-ai dependencies:     pip install
  retrocast[castchat]

  Example queries:   - What episodes discussed machine learning?   - Where did
  they talk about climate change?   - Which episodes featured interviews with
  scientists?

Options:
  -d, --database PATH  Path to retrocast database (defaults to app directory
                       database)
  -m, --model TEXT     Anthropic model to use for the agent
  --rebuild-index      Rebuild the ChromaDB index from scratch
  --help               Show this message and exit.

```
<!-- [[[end]]] -->

## Requirements

The castchat feature requires optional dependencies:

```bash
pip install retrocast[castchat]
```

This installs:
- `chromadb` - Vector database for semantic search
- `pydantic-ai` - AI agent framework

## Usage

### Basic Usage

Start an interactive chat session:

```bash
retrocast castchat
```

### With Custom Database

Specify a custom database location:

```bash
retrocast castchat --database /path/to/database.db
```

### With Custom Model

Use a specific Anthropic model:

```bash
retrocast castchat --model claude-3-5-sonnet-20241022
```

### Rebuild Index

Rebuild the ChromaDB index from scratch:

```bash
retrocast castchat --rebuild-index
```

## Example Queries

Once in the interactive session, you can ask questions like:

- "What episodes discussed machine learning?"
- "Where did they talk about climate change?"
- "Which episodes featured interviews with scientists?"
- "Find episodes about Python programming"
- "What did they say about AI ethics?"

The agent searches across all transcribed episodes to find relevant content and provide contextualized answers.

## How It Works

1. **Indexing**: Transcriptions are indexed in a ChromaDB vector database
2. **Query Processing**: Your questions are converted to semantic embeddings
3. **Search**: Similar content is retrieved using vector similarity
4. **AI Response**: An AI agent synthesizes the information into a natural language answer

## Tips

- Be specific in your questions for better results
- The quality of answers depends on having transcribed episodes
- Use the `--rebuild-index` flag if you've added new transcriptions
- The agent has context about your entire podcast archive
