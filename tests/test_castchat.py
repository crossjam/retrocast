"""Tests for castchat ChromaDB manager and agent."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Mock chromadb before importing
sys.modules["chromadb"] = MagicMock()
sys.modules["chromadb.config"] = MagicMock()


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary retrocast database with test data."""
    from retrocast.datastore import Datastore

    db_path = tmp_path / "test.db"
    ds = Datastore(db_path)

    # Insert test transcription
    ds.db.execute(
        """
        INSERT INTO transcriptions (
            transcription_id, audio_content_hash, media_path, file_size,
            transcription_path, episode_url, podcast_title, episode_title,
            backend, model_size, language, duration, transcription_time,
            has_diarization, speaker_count, word_count, created_time, updated_time
        ) VALUES (
            1, 'hash123', '/test/audio.mp3', 1000,
            '/test/transcript.json', 'https://example.com/episode1',
            'Test Podcast', 'Test Episode 1',
            'mlx-whisper', 'base', 'en', 3600.0, 120.0,
            0, 0, 100, '2025-01-01', '2025-01-01'
        )
    """
    )

    # Insert test segments
    segments = [
        (1, 0, 0.0, 5.0, "This is the first segment about AI.", "Speaker 1"),
        (1, 1, 5.0, 10.0, "This segment discusses machine learning.", "Speaker 2"),
        (1, 2, 10.0, 15.0, "Here we talk about neural networks.", "Speaker 1"),
    ]

    for seg in segments:
        ds.db.execute(
            """
            INSERT INTO transcription_segments (
                transcription_id, segment_index, start_time, end_time, text, speaker
            ) VALUES (?, ?, ?, ?, ?, ?)
        """,
            seg,
        )

    ds.db.conn.commit()
    return ds


@pytest.fixture
def chroma_manager(tmp_path):
    """Create a ChromaDBManager with mocked ChromaDB."""
    from retrocast.chromadb_manager import ChromaDBManager

    chroma_dir = tmp_path / "chromadb"

    # Mock the ChromaDB client
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_collection.count.return_value = 0
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch("retrocast.chromadb_manager.chromadb.PersistentClient", return_value=mock_client):
        manager = ChromaDBManager(chroma_dir)
        manager.collection = mock_collection
        return manager


def test_chromadb_manager_initialization(tmp_path):
    """Test ChromaDBManager initializes correctly."""
    from retrocast.chromadb_manager import ChromaDBManager

    chroma_dir = tmp_path / "chromadb"

    with patch("retrocast.chromadb_manager.chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        manager = ChromaDBManager(chroma_dir)

        assert manager.persist_directory == chroma_dir
        assert chroma_dir.exists()
        mock_client_class.assert_called_once()
        mock_client.get_or_create_collection.assert_called_once_with(
            name="transcription_segments",
            metadata={"description": "Podcast transcription segments with timestamps"},
        )


def test_chromadb_manager_index_transcriptions(temp_db, chroma_manager):
    """Test indexing transcriptions into ChromaDB."""
    # Configure mock to capture add() calls
    add_calls = []

    def capture_add(**kwargs):
        add_calls.append(kwargs)

    chroma_manager.collection.add = capture_add

    # Index transcriptions
    count = chroma_manager.index_transcriptions(temp_db, batch_size=2)

    assert count == 3  # We inserted 3 segments
    assert len(add_calls) == 2  # 2 batches (2 + 1 segments)

    # Check first batch
    first_batch = add_calls[0]
    assert len(first_batch["documents"]) == 2
    assert "AI" in first_batch["documents"][0]
    assert "machine learning" in first_batch["documents"][1]


def test_chromadb_manager_search(chroma_manager):
    """Test searching transcriptions."""
    # Mock search results
    chroma_manager.collection.query.return_value = {
        "documents": [["Test segment about AI", "Another segment"]],
        "metadatas": [
            [
                {
                    "transcription_id": "1",
                    "segment_index": "0",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "speaker": "Speaker 1",
                    "podcast_title": "Test Podcast",
                    "episode_title": "Test Episode",
                    "episode_url": "https://example.com",
                    "media_path": "/test/audio.mp3",
                    "language": "en",
                    "backend": "mlx-whisper",
                    "model_size": "base",
                },
                {
                    "transcription_id": "1",
                    "segment_index": "1",
                    "start_time": 5.0,
                    "end_time": 10.0,
                    "speaker": "Speaker 2",
                    "podcast_title": "Test Podcast",
                    "episode_title": "Test Episode",
                    "episode_url": "https://example.com",
                    "media_path": "/test/audio.mp3",
                    "language": "en",
                    "backend": "mlx-whisper",
                    "model_size": "base",
                },
            ]
        ],
        "distances": [[0.5, 0.7]],
        "ids": [["t1_s0", "t1_s1"]],
    }

    results = chroma_manager.search("AI and machine learning", n_results=2)

    assert len(results) == 2
    assert results[0]["text"] == "Test segment about AI"
    assert results[0]["metadata"]["podcast_title"] == "Test Podcast"
    assert results[0]["distance"] == 0.5


def test_chromadb_manager_get_collection_count(chroma_manager):
    """Test getting collection count."""
    chroma_manager.collection.count.return_value = 42

    count = chroma_manager.get_collection_count()

    assert count == 42
    chroma_manager.collection.count.assert_called_once()


def test_chromadb_manager_reset(chroma_manager):
    """Test resetting the collection."""
    mock_client = MagicMock()
    chroma_manager.client = mock_client

    # Mock the new collection creation
    new_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = new_collection

    chroma_manager.reset()

    mock_client.delete_collection.assert_called_once_with(name="transcription_segments")
    mock_client.get_or_create_collection.assert_called_once()


def test_create_castchat_agent():
    """Test creating the castchat agent."""
    from retrocast.castchat_agent import create_castchat_agent

    mock_chroma_manager = MagicMock()

    with patch("retrocast.castchat_agent.AnthropicModel") as mock_model_class:
        with patch("retrocast.castchat_agent.Agent") as mock_agent_class:
            mock_model = MagicMock()
            mock_model_class.return_value = mock_model
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            result = create_castchat_agent(mock_chroma_manager, model_name="claude-test")

            mock_model_class.assert_called_once_with("claude-test")
            mock_agent_class.assert_called_once()
            # Verify system prompt was set
            call_kwargs = mock_agent_class.call_args[1]
            assert "system_prompt" in call_kwargs
            assert "AI assistant" in call_kwargs["system_prompt"]
            # Verify the agent is returned
            assert result == mock_agent


def test_index_empty_database(tmp_path, chroma_manager):
    """Test indexing when database has no transcriptions."""
    from retrocast.datastore import Datastore

    empty_db_path = tmp_path / "empty.db"
    empty_ds = Datastore(empty_db_path)

    count = chroma_manager.index_transcriptions(empty_ds)

    assert count == 0
