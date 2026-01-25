# castchat

### Overview

With podcast episodes transcribed and the transcription data indexed,
we want an interactive REPL to ask questions of the indexed data.

We use chromadb and PydanticAI to implement the tool enabled and RAG
based chat for cli application named `castchat`. We want to be able to
invoke this cli as a subcommand of retrocast, e.g. `retrocast
castchat`.

Below is an example of creating a tool to integrate with Pydantic’s 
`clai` agentic REPL toolkit.

```python
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
import chromadb

# Setup ChromaDB
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("docs")

# Add sample documents (do this once)
collection.add(
    documents=[
        "Our refund policy: Full refunds within 30 days of purchase",
        "Customer support: Email support@example.com or call 1-800-HELP",
        "Shipping: Free shipping on orders over $50, 5-7 business days"
    ],
    ids=["doc1", "doc2", "doc3"]
)

# Create agent
model = AnthropicModel('claude-sonnet-4-20250514')
agent = Agent(model=model)

@agent.tool
def search_docs(query: str) -> str:
    """Search internal documentation for relevant information.
    
    Args:
        query: The search query text
    """
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    
    if results["documents"] and results["documents"][0]:
        docs = "\n\n".join(results["documents"][0])
        return f"Found relevant documentation:\n{docs}"
    return "No relevant documents found"
```

Here’s an example of firing up `clai` to interact using that tool

````bash
# Start interactive session
clai --agent search_agent.py:agent

# Or specify model explicitly
clai --agent search_agent.py:agent --model anthropic:claude-sonnet-4-20250514
```

**3. Example conversation:**
```
You: What's the refund policy?
Agent: [calls search_docs tool, then responds with the policy]

You: How do I contact support?
Agent: [searches and provides contact info]
````


