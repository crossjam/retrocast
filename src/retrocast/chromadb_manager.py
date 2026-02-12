"""ChromaDB integration for podcast transcription search and RAG."""

from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.config import Settings
from loguru import logger

from retrocast.datastore import Datastore


class ChromaDBManager:
    """Manages ChromaDB collections for transcription segment indexing."""

    def __init__(self, persist_directory: Path):
        """Initialize ChromaDB client with persistent storage.

        Args:
            persist_directory: Directory path for ChromaDB persistence
        """
        self.persist_directory = persist_directory
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Initializing ChromaDB at {persist_directory}")
        self.client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
        self.collection_name = "transcription_segments"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Podcast transcription segments with timestamps"},
        )

    def index_transcriptions(self, datastore: Datastore, batch_size: int = 100) -> int:
        """Index all transcription segments from the database into ChromaDB.

        Args:
            datastore: Datastore instance for querying transcription data
            batch_size: Number of segments to process per batch

        Returns:
            Number of segments indexed
        """
        logger.info("Starting transcription indexing...")

        # Query all transcription segments with metadata
        query = """
            SELECT
                ts.transcription_id,
                ts.segment_index,
                ts.start_time,
                ts.end_time,
                ts.text,
                ts.speaker,
                t.podcast_title,
                t.episode_title,
                t.episode_url,
                t.media_path,
                t.language,
                t.backend,
                t.model_size
            FROM transcription_segments ts
            JOIN transcriptions t ON ts.transcription_id = t.transcription_id
            ORDER BY ts.transcription_id, ts.segment_index
        """

        segments = list(datastore.db.execute(query).fetchall())
        total_segments = len(segments)

        if total_segments == 0:
            logger.warning("No transcription segments found in database")
            return 0

        logger.info(f"Found {total_segments} segments to index")

        # Process in batches
        indexed_count = 0
        for i in range(0, total_segments, batch_size):
            batch = segments[i : i + batch_size]
            documents = []
            metadatas = []
            ids = []

            for segment in batch:
                # Create unique ID for each segment
                segment_id = f"t{segment[0]}_s{segment[1]}"
                ids.append(segment_id)

                # The text to be embedded and searched
                documents.append(segment[4])  # text column

                # Metadata for context and filtering
                metadatas.append(
                    {
                        "transcription_id": str(segment[0]),
                        "segment_index": str(segment[1]),
                        "start_time": float(segment[2]),
                        "end_time": float(segment[3]),
                        "speaker": str(segment[5] or ""),
                        "podcast_title": str(segment[6] or ""),
                        "episode_title": str(segment[7] or ""),
                        "episode_url": str(segment[8] or ""),
                        "media_path": str(segment[9] or ""),
                        "language": str(segment[10] or ""),
                        "backend": str(segment[11] or ""),
                        "model_size": str(segment[12] or ""),
                    }
                )

            # Add batch to collection
            self.collection.add(documents=documents, metadatas=cast(Any, metadatas), ids=ids)
            indexed_count += len(batch)

            logger.debug(f"Indexed {indexed_count}/{total_segments} segments")

        logger.info(f"Successfully indexed {indexed_count} segments")
        return indexed_count

    def search(
        self, query: str, n_results: int = 5, podcast_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Search transcription segments using semantic similarity.

        Args:
            query: The search query text
            n_results: Maximum number of results to return
            podcast_filter: Optional podcast title to filter results

        Returns:
            List of matching segments with metadata
        """
        where_filter: Any = None
        if podcast_filter:
            where_filter = {"podcast_title": {"$eq": podcast_filter}}

        results = self.collection.query(
            query_texts=[query], n_results=n_results, where=where_filter
        )

        # Format results for easier consumption
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else None

                formatted_results.append(
                    {
                        "text": doc,
                        "metadata": metadata,
                        "distance": distance,
                        "id": results["ids"][0][i] if results["ids"] else None,
                    }
                )

        return formatted_results

    def get_collection_count(self) -> int:
        """Get the number of segments in the collection.

        Returns:
            Number of indexed segments
        """
        return self.collection.count()

    def reset(self) -> None:
        """Clear all data from the collection."""
        logger.warning(f"Resetting collection '{self.collection_name}'")
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Podcast transcription segments with timestamps"},
        )
        logger.info("Collection reset complete")
