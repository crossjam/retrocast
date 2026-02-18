# chat - Interactive AI Chat

The `chat` command starts the agentic AI chat experience for transcribed content.

<!-- [[[cog
from click.testing import CliRunner
from retrocast.cli import cli
result = CliRunner().invoke(cli, ["chat", "--help"])
cog.out("```\n{}\n```".format(result.output))
]]] -->
```
Usage: cli chat [OPTIONS]

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
