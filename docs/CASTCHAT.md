# castchat - AI-Powered Podcast Exploration

## Overview

`castchat` is an interactive AI-powered chat interface for exploring your transcribed podcast archive. It uses ChromaDB for semantic search and PydanticAI with Claude for natural language interactions.

## Features

- **Semantic Search**: Find relevant content across all transcribed episodes using natural language queries
- **Episode Context**: Get results with episode titles, podcast names, timestamps, and speaker information
- **Interactive REPL**: Ask follow-up questions and explore your archive conversationally
- **RAG-based Answers**: The AI agent retrieves relevant transcript segments before answering
- **Flexible Filtering**: Search across all podcasts or filter by specific podcast titles

## Installation

Install the castchat dependencies:

```bash
pip install retrocast[castchat]
```

Or with uv:

```bash
uv sync --extra castchat
```

This installs:
- `chromadb` - Vector database for semantic search
- `pydantic-ai` - AI agent framework with tool support

## Requirements

1. **Transcribed Episodes**: You must have transcribed podcast episodes in your retrocast database
2. **Anthropic API Key**: Set `ANTHROPIC_API_KEY` environment variable with your Claude API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Quick Start

1. Ensure you have transcribed episodes:

```bash
retrocast transcription transcribe
```

2. Start the castchat REPL:

```bash
retrocast castchat
```

On first run, castchat will automatically build an index of your transcription segments. This may take a few moments depending on the size of your archive.

## Usage

### Basic Commands

```bash
# Start castchat with default settings
retrocast castchat

# Use a specific database
retrocast castchat --database /path/to/retrocast.db

# Use a different Claude model
retrocast castchat --model claude-opus-4-20250514

# Rebuild the search index
retrocast castchat --rebuild-index
```

### Example Queries

Once in the REPL, you can ask natural language questions:

```
You: What episodes discussed machine learning?
Agent: [searches transcripts and provides relevant segments with timestamps]

You: Which podcasts featured interviews with scientists?
Agent: [finds episodes with scientist guests]

You: Where did they talk about climate change?
Agent: [locates climate change discussions across episodes]

You: Tell me more about the third result
Agent: [can reference previous results and provide more context]
```

### Search Tools

The castchat agent has access to three tools:

1. **search_transcripts**: Search across all transcribed episodes
2. **search_podcast**: Search within a specific podcast by name
3. **get_collection_info**: Get information about the indexed archive

The agent automatically chooses the right tool based on your query.

### Exiting

To exit the REPL:
- Type `exit` or `quit`
- Press `Ctrl+C`

## How It Works

### Indexing

When you first run castchat (or use `--rebuild-index`), it:

1. Queries all `transcription_segments` from your retrocast database
2. Extracts the text, metadata, and timestamps
3. Indexes them into ChromaDB for semantic search
4. Stores the index in your retrocast app directory (`~/.local/share/retrocast/chromadb/`)

### Search and Retrieval

When you ask a question:

1. Your query is sent to the PydanticAI agent
2. The agent decides which search tool to use
3. ChromaDB performs semantic similarity search on transcript segments
4. The agent receives relevant segments with context
5. Claude generates a natural language response using the retrieved context

### RAG Architecture

castchat uses Retrieval-Augmented Generation (RAG):
- **Retrieval**: ChromaDB finds relevant transcript segments
- **Augmentation**: Segments are formatted with episode/podcast metadata
- **Generation**: Claude uses the context to answer your question accurately

## Configuration

### Database Location

By default, castchat uses the database at `~/.local/share/retrocast/retrocast.db`. Override with:

```bash
retrocast castchat --database /path/to/your/retrocast.db
```

### ChromaDB Storage

The vector index is stored at `~/.local/share/retrocast/chromadb/`. This directory contains:
- Collection metadata
- Vector embeddings
- Indexed segments

### Model Selection

Choose different Claude models:

```bash
# Use Claude Opus (more capable, slower)
retrocast castchat --model claude-opus-4-20250514

# Use Claude Sonnet (default, balanced)
retrocast castchat --model claude-sonnet-4-20250514

# Use Claude Haiku (faster, more economical)
retrocast castchat --model claude-haiku-4-20250514
```

## Tips

### Best Practices

1. **Be Specific**: More specific queries get better results
   - ❌ "Tell me about AI"
   - ✅ "What did they say about reinforcement learning in episode 42?"

2. **Use Context**: Reference podcasts or episodes by name
   - "What topics were covered in the Lex Fridman podcast?"

3. **Ask Follow-ups**: The agent remembers conversation context
   - "Tell me more about that"
   - "Which episode was that from?"

### Rebuilding the Index

Rebuild the index when:
- You've transcribed new episodes
- The index seems out of date
- You want to reset everything

```bash
retrocast castchat --rebuild-index
```

### Performance

- **First Run**: Indexing may take several minutes for large archives
- **Subsequent Runs**: Index is reused, startup is fast
- **Search Speed**: Semantic search is very fast (< 1 second)
- **API Costs**: Each query uses Claude API tokens (retrieval + generation)

## Troubleshooting

### No Transcription Segments Found

```
Error: No transcription segments found!
Run `retrocast transcription transcribe` to transcribe episodes first
```

**Solution**: Transcribe your episodes first:

```bash
retrocast transcription transcribe
```

### Missing Dependencies

```
Error: castchat dependencies not installed
Install with: pip install retrocast[castchat]
```

**Solution**: Install the optional dependencies:

```bash
pip install retrocast[castchat]
```

### Anthropic API Key Not Set

```
Error: ANTHROPIC_API_KEY environment variable not set
```

**Solution**: Set your API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
retrocast castchat
```

### Database Not Found

```
Error: Database not found at /path/to/retrocast.db
Run `retrocast sync overcast` first to create the database
```

**Solution**: Initialize your retrocast database:

```bash
retrocast sync overcast
```

## Advanced Usage

### Custom System Prompts

The agent's system prompt can be customized by modifying `src/retrocast/castchat_agent.py`:

```python
agent = Agent(
    model=model,
    system_prompt="Your custom instructions here..."
)
```

### Filtering by Podcast

While the REPL doesn't expose direct filtering, the agent can understand requests like:
- "Search only the 'This American Life' podcast for stories about education"
- "What did they discuss on Radiolab about neuroscience?"

### Integration with Other Tools

The ChromaDBManager can be used programmatically:

```python
from retrocast.chromadb_manager import ChromaDBManager
from pathlib import Path

# Initialize manager
chroma_dir = Path.home() / ".local/share/retrocast/chromadb"
manager = ChromaDBManager(chroma_dir)

# Search programmatically
results = manager.search("machine learning", n_results=10)
for result in results:
    print(result["text"])
    print(result["metadata"])
```

## Privacy and Security

- **Local Storage**: ChromaDB index is stored locally on your machine
- **API Calls**: Queries are sent to Anthropic's Claude API
- **Data Privacy**: Only search queries and relevant transcript segments are sent to Claude
- **No Telemetry**: ChromaDB telemetry is disabled by default

## Future Enhancements

Potential future features:
- [ ] Support for local LLMs (via Ollama integration)
- [ ] Export conversation history
- [ ] Save and replay favorite queries
- [ ] Advanced filtering (by date, duration, speaker)
- [ ] Multi-modal search (audio + transcripts)
- [ ] Summarization of entire episodes or podcasts

## Related Commands

- `retrocast transcription transcribe` - Transcribe podcast episodes
- `retrocast transcription search` - Simple keyword search (no AI)
- `retrocast download podcast-archiver` - Download podcast episodes
- `retrocast sql` - Direct SQL queries on the database

## Feedback

Found a bug or have a feature request? Please open an issue on GitHub:
https://github.com/crossjam/retrocast/issues
