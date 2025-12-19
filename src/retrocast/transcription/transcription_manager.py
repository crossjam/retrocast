"""Main orchestration class for transcription operations."""

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from loguru import logger

from retrocast.datastore import Datastore
from retrocast.transcription.base import TranscriptionBackend, TranscriptionResult
from retrocast.transcription.output_formats import get_format_writer
from retrocast.transcription.utils import (
    check_transcription_exists,
    compute_audio_hash,
    get_audio_metadata,
    get_output_path,
)


class TranscriptionManager:
    """Main class for managing transcription operations.

    Handles backend selection, transcription processing, output writing,
    and database persistence.
    """

    def __init__(
        self,
        backend: str = "auto",
        model_size: str = "base",
        output_dir: Optional[Path] = None,
        datastore: Optional[Datastore] = None,
    ):
        """Initialize transcription manager.

        Args:
            backend: Backend to use (auto, mlx, faster, whisper)
            model_size: Model size (tiny, base, small, medium, large)
            output_dir: Output directory for transcription files
            datastore: Optional datastore instance for database operations
        """
        self.backend_name = backend
        self.model_size = model_size
        self.output_dir = output_dir
        self.datastore = datastore

        # Backend will be selected lazily on first use
        self._backend: Optional[TranscriptionBackend] = None

    def _select_backend(self) -> TranscriptionBackend:
        """Select and initialize transcription backend.

        Uses auto-detection if backend_name is "auto", otherwise tries
        to load the specified backend.

        Returns:
            TranscriptionBackend instance

        Raises:
            RuntimeError: If no suitable backend is available
        """
        from retrocast.transcription.backends import get_all_backends

        available_backends = get_all_backends()

        if self.backend_name == "auto":
            # Auto-detect: try backends in priority order
            # Priority: mlx (fastest on Apple Silicon) -> faster-whisper -> whisper
            priority_order = ["mlx-whisper", "faster-whisper", "whisper"]

            for backend_name in priority_order:
                for backend_cls in available_backends:
                    backend = backend_cls()
                    if backend.name == backend_name and backend.is_available():
                        logger.info(f"Auto-selected backend: {backend.name}")
                        return backend

            # No backend available
            raise RuntimeError(
                "No transcription backend available. "
                "Please install a transcription backend: "
                "mlx-whisper (macOS), faster-whisper, or openai-whisper"
            )
        # Try to find specified backend
        for backend_cls in available_backends:
            backend = backend_cls()
            if backend.name == self.backend_name:
                if backend.is_available():
                    logger.info(f"Using backend: {backend.name}")
                    return backend
                raise RuntimeError(
                    f"Backend '{self.backend_name}' is not available. "
                    f"Please install required dependencies."
                )

        # Backend not found
        raise RuntimeError(
            f"Unknown backend: {self.backend_name}. "
            f"Available backends: {', '.join(b().name for b in available_backends)}"
        )

    def _get_backend(self) -> TranscriptionBackend:
        """Get or initialize backend instance.

        Returns:
            TranscriptionBackend instance
        """
        if self._backend is None:
            self._backend = self._select_backend()
        return self._backend

    def _compute_hash_and_check_duplicate(
        self, audio_path: Path
    ) -> tuple[str, bool, Optional[dict]]:
        """Compute audio hash and check if transcription already exists.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (audio_hash, exists, existing_record)
        """
        logger.debug(f"Computing hash for {audio_path}")
        audio_hash = compute_audio_hash(audio_path)

        if self.datastore is not None:
            exists, record = check_transcription_exists(self.datastore, audio_hash)
            if exists:
                logger.info(
                    f"Transcription already exists for {audio_path.name} "
                    f"(hash: {audio_hash[:16]}...)"
                )
            return audio_hash, exists, record
        return audio_hash, False, None

    def transcribe_file(
        self,
        audio_path: Path,
        podcast_title: str = "Unknown Podcast",
        episode_title: Optional[str] = None,
        episode_url: Optional[str] = None,
        language: Optional[str] = None,
        output_format: str = "json",
        force: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> TranscriptionResult:
        """Transcribe a single audio file.

        Args:
            audio_path: Path to audio file
            podcast_title: Podcast title for organization
            episode_title: Episode title (defaults to filename if not provided)
            episode_url: Optional episode URL for linking to episode metadata
            language: Optional language code (auto-detect if None)
            output_format: Output format (txt, json, srt, vtt)
            force: If True, re-transcribe even if already exists
            progress_callback: Optional callback for progress updates

        Returns:
            TranscriptionResult

        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Use filename as episode title if not provided
        if episode_title is None:
            episode_title = audio_path.stem

        # Check for existing transcription
        audio_hash, exists, existing_record = self._compute_hash_and_check_duplicate(audio_path)

        if exists and not force:
            logger.info(
                f"Transcription already exists for {episode_title}. Use --force to re-transcribe."
            )
            # Could load and return existing result here
            raise RuntimeError("Transcription already exists. Use --force to re-transcribe.")

        # Get backend
        backend = self._get_backend()

        # Notify progress
        if progress_callback:
            progress_callback(f"Transcribing with {backend.name}...")

        # Transcribe
        logger.info(f"Transcribing {episode_title} with {backend.name} ({self.model_size} model)")
        start_time = datetime.now()

        result = backend.transcribe(
            audio_path=audio_path, language=language, model_size=self.model_size
        )

        end_time = datetime.now()
        transcription_time = (end_time - start_time).total_seconds()

        # Add metadata
        result.metadata["backend"] = backend.name
        result.metadata["model_size"] = self.model_size
        result.metadata["transcription_time"] = transcription_time

        logger.info(
            f"Transcription completed in {transcription_time:.2f}s "
            f"({result.duration:.2f}s audio, "
            f"{result.word_count()} words, "
            f"{result.segment_count()} segments)"
        )

        # Save transcription
        if self.output_dir:
            self._save_transcription(
                result=result,
                podcast_title=podcast_title,
                episode_title=episode_title,
                output_format=output_format,
            )

        # Save to database
        if self.datastore:
            self._save_to_database(
                result=result,
                audio_path=audio_path,
                audio_hash=audio_hash,
                podcast_title=podcast_title,
                episode_title=episode_title,
                episode_url=episode_url,
                transcription_time=transcription_time,
            )

        return result

    def _save_transcription(
        self,
        result: TranscriptionResult,
        podcast_title: str,
        episode_title: str,
        output_format: str,
    ) -> Path:
        """Save transcription to file.

        Args:
            result: TranscriptionResult to save
            podcast_title: Podcast title for directory organization
            episode_title: Episode title for filename
            output_format: Output format (txt, json, srt, vtt)

        Returns:
            Path to saved file
        """
        if self.output_dir is None:
            raise ValueError("output_dir must be set to save transcriptions")

        # Get writer
        writer = get_format_writer(output_format)

        # Determine output path
        output_path = get_output_path(
            self.output_dir, podcast_title, episode_title, writer.extension
        )

        # Write file
        logger.debug(f"Writing transcription to {output_path}")
        writer.write(result, output_path)
        logger.info(f"Saved transcription: {output_path}")

        return output_path

    def _save_to_database(
        self,
        result: TranscriptionResult,
        audio_path: Path,
        audio_hash: str,
        podcast_title: str,
        episode_title: str,
        episode_url: Optional[str],
        transcription_time: float,
    ) -> None:
        """Save transcription to database.

        Args:
            result: TranscriptionResult to save
            audio_path: Path to original audio file
            audio_hash: SHA256 hash of audio content
            podcast_title: Podcast title
            episode_title: Episode title
            episode_url: Optional episode URL
            transcription_time: Time taken to transcribe
        """
        if self.datastore is None:
            return

        # Get audio metadata
        audio_meta = get_audio_metadata(audio_path)

        # Determine transcription file path
        transcription_path = None
        if self.output_dir:
            # Assume JSON was saved (primary format)
            transcription_path = str(
                get_output_path(self.output_dir, podcast_title, episode_title, "json")
            )

        # Save to database
        self.datastore.upsert_transcription(
            audio_content_hash=audio_hash,
            media_path=str(audio_path),
            file_size=audio_meta["file_size"],
            transcription_path=transcription_path,
            episode_url=episode_url,
            podcast_title=podcast_title,
            episode_title=episode_title,
            backend=result.metadata.get("backend", "unknown"),
            model_size=result.metadata.get("model_size", "unknown"),
            language=result.language,
            duration=result.duration,
            transcription_time=transcription_time,
            has_diarization=result.has_speakers(),
            speaker_count=len(result.get_speakers()),
            word_count=result.word_count(),
            segments=result.segments,
        )

        logger.debug(f"Saved transcription to database (hash: {audio_hash[:16]}...)")
