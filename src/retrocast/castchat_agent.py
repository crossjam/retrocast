"""PydanticAI agent for interactive podcast transcript exploration."""

from typing import Any

from loguru import logger
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel

from retrocast.index.manager import ChromaDBManager


def create_castchat_agent(
    chroma_manager: ChromaDBManager, model_name: str = "claude-sonnet-4-20250514"
) -> Agent:
    """Create a PydanticAI agent for exploring podcast transcripts.

    Args:
        chroma_manager: ChromaDB manager instance for searching transcripts
        model_name: Anthropic model name to use

    Returns:
        Configured PydanticAI Agent
    """
    model = AnthropicModel(model_name)

    # Create agent with system prompt
    agent = Agent(
        model=model,
        system_prompt=(
            "You are an AI assistant helping users explore their podcast archive. "
            "You have access to transcribed podcast episodes and can search through "
            "them to answer questions about topics, guests, discussions, and specific "
            "content mentioned across episodes. When searching, provide context about "
            "which podcast and episode the information came from, and include timestamps "
            "when relevant. Be conversational and helpful."
        ),
    )

    @agent.tool
    def search_transcripts(ctx: RunContext[Any], query: str, max_results: int = 5) -> str:
        """Search podcast transcription segments for relevant content.

        Use this tool to find information in podcast transcripts. It performs
        semantic search across all transcribed episodes to find relevant segments
        based on the query.

        Args:
            ctx: Run context (automatically provided)
            query: The search query describing what to look for
            max_results: Maximum number of results to return (default 5, max 10)

        Returns:
            Formatted string with search results including episode info and timestamps
        """
        logger.debug(f"Searching transcripts with query: {query}")

        # Limit max_results
        max_results = min(max_results, 10)

        try:
            results = chroma_manager.search(query, n_results=max_results)

            if not results:
                return "No relevant segments found in the transcription archive."

            # Format results for the agent
            formatted = "Found relevant segments:\n\n"
            for i, result in enumerate(results, 1):
                metadata = result["metadata"]
                text = result["text"]

                # Format timestamp
                start_time = metadata.get("start_time", 0)
                minutes = int(start_time // 60)
                seconds = int(start_time % 60)
                timestamp = f"{minutes}:{seconds:02d}"

                # Build result entry
                formatted += f"{i}. **{metadata.get('podcast_title', 'Unknown Podcast')}**\n"
                formatted += f"   Episode: {metadata.get('episode_title', 'Unknown Episode')}\n"
                formatted += f"   Time: {timestamp}"

                speaker = metadata.get("speaker")
                if speaker:
                    formatted += f" | Speaker: {speaker}"

                formatted += f"\n   > {text}\n\n"

            return formatted

        except Exception as e:
            logger.error(f"Error searching transcripts: {e}")
            return f"Error searching transcripts: {str(e)}"

    @agent.tool
    def search_podcast(
        ctx: RunContext[Any], podcast_title: str, query: str, max_results: int = 5
    ) -> str:
        """Search transcripts within a specific podcast.

        Use this tool when the user asks about a specific podcast by name.
        This filters search results to only that podcast.

        Args:
            ctx: Run context (automatically provided)
            podcast_title: The name of the podcast to search within
            query: The search query describing what to look for
            max_results: Maximum number of results to return (default 5, max 10)

        Returns:
            Formatted string with search results for that podcast
        """
        logger.debug(f"Searching podcast '{podcast_title}' with query: {query}")

        max_results = min(max_results, 10)

        try:
            results = chroma_manager.search(
                query, n_results=max_results, podcast_filter=podcast_title
            )

            if not results:
                return (
                    f"No relevant segments found in '{podcast_title}'. "
                    "The podcast might not be in the archive or might not match exactly."
                )

            # Format results
            formatted = f"Found segments in **{podcast_title}**:\n\n"
            for i, result in enumerate(results, 1):
                metadata = result["metadata"]
                text = result["text"]

                start_time = metadata.get("start_time", 0)
                minutes = int(start_time // 60)
                seconds = int(start_time % 60)
                timestamp = f"{minutes}:{seconds:02d}"

                formatted += f"{i}. Episode: {metadata.get('episode_title', 'Unknown')}\n"
                formatted += f"   Time: {timestamp}"

                speaker = metadata.get("speaker")
                if speaker:
                    formatted += f" | Speaker: {speaker}"

                formatted += f"\n   > {text}\n\n"

            return formatted

        except Exception as e:
            logger.error(f"Error searching podcast transcripts: {e}")
            return f"Error searching podcast: {str(e)}"

    @agent.tool
    def get_collection_info(ctx: RunContext[Any]) -> str:
        """Get information about the indexed transcript collection.

        Use this tool when users ask about what's available in their archive
        or how many episodes have been transcribed.

        Args:
            ctx: Run context (automatically provided)

        Returns:
            Summary of indexed content
        """
        try:
            count = chroma_manager.get_collection_count()
            return (
                f"The transcript archive contains {count:,} indexed segments "
                "from transcribed podcast episodes. You can search across all "
                "of them or filter by specific podcast titles."
            )
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return f"Error accessing collection info: {str(e)}"

    return agent
