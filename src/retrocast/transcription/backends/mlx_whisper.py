"""MLX Whisper backend for Apple Silicon transcription."""

import platform
from pathlib import Path
from typing import Optional

from loguru import logger

from retrocast.transcription.base import (
    TranscriptionBackend,
    TranscriptionResult,
    TranscriptionSegment,
)


class MLXWhisperBackend(TranscriptionBackend):
    """MLX Whisper transcription backend for Apple Silicon (macOS).

    This backend uses the mlx-whisper library which provides highly optimized
    Whisper transcription on Apple Silicon using the MLX framework.
    Performance is significantly better than CPU-based backends on M1/M2/M3 Macs.
    """

    def __init__(self):
        """Initialize MLX Whisper backend."""
        self._model = None
        self._current_model_size = None

    @property
    def name(self) -> str:
        """Return backend identifier."""
        return "mlx-whisper"

    def is_available(self) -> bool:
        """Check if MLX Whisper is available.

        Returns:
            True if mlx_whisper can be imported and platform is macOS
        """
        try:
            import mlx_whisper  # noqa: F401  # type: ignore[import-untyped]

            # MLX only works on Apple Silicon (Darwin)
            if platform.system() != "Darwin":
                logger.debug("MLX Whisper requires macOS (Darwin platform)")
                return False

            return True
        except ImportError:
            logger.debug("mlx_whisper not installed")
            return False

    def platform_info(self) -> str:
        """Return platform information."""
        return "macOS (Apple Silicon)"

    def description(self) -> str:
        """Return backend description."""
        return "MLX Whisper - optimized for Apple Silicon M1/M2/M3"

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model_size: str = "base",
    ) -> TranscriptionResult:
        """Transcribe audio file using MLX Whisper.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., "en", "es"). Auto-detect if None.
            model_size: Model size (tiny, base, small, medium, large)

        Returns:
            TranscriptionResult with segments and metadata

        Raises:
            ImportError: If mlx_whisper is not installed
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
        """
        try:
            import mlx_whisper  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "mlx_whisper is not installed. "
                "Install with: pip install mlx-whisper"
            ) from e

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Load model (with caching)
        model_path = self._get_or_load_model(model_size)

        logger.info(
            f"Transcribing {audio_path.name} with MLX Whisper ({model_size} model)"
        )

        # Transcribe with mlx_whisper
        try:
            result = mlx_whisper.transcribe(
                str(audio_path),
                path_or_hf_repo=model_path,
                language=language,
                verbose=False,
            )
        except Exception as e:
            raise RuntimeError(f"MLX Whisper transcription failed: {e}") from e

        # Convert mlx_whisper result to our TranscriptionResult format
        return self._convert_result(result, audio_path)

    def _get_or_load_model(self, model_size: str) -> str:
        """Get or load Whisper model with caching.

        Args:
            model_size: Model size to load

        Returns:
            Model path/identifier for mlx_whisper

        Raises:
            ValueError: If model_size is invalid
        """
        valid_sizes = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
        if model_size not in valid_sizes:
            raise ValueError(
                f"Invalid model size: {model_size}. "
                f"Valid sizes: {', '.join(valid_sizes)}"
            )

        # MLX Whisper uses model identifiers like "mlx-community/whisper-small-mlx"
        # For simplicity, we'll use the standard format which mlx_whisper handles
        if model_size.startswith("large"):
            model_path = f"mlx-community/whisper-{model_size}-mlx"
        else:
            model_path = f"mlx-community/whisper-{model_size}-mlx"

        # Note: mlx_whisper handles caching internally, so we don't need to cache the model object
        # The library will download models to ~/.cache/huggingface/hub on first use

        if model_size != self._current_model_size:
            logger.debug(f"Using MLX Whisper model: {model_path}")
            self._current_model_size = model_size

        return model_path

    def _convert_result(
        self, mlx_result: dict, audio_path: Path
    ) -> TranscriptionResult:
        """Convert mlx_whisper result to TranscriptionResult.

        Args:
            mlx_result: Result dictionary from mlx_whisper.transcribe()
            audio_path: Path to audio file (for metadata)

        Returns:
            TranscriptionResult
        """
        # Extract segments
        segments = []
        if "segments" in mlx_result:
            for seg in mlx_result["segments"]:
                segments.append(
                    TranscriptionSegment(
                        start=float(seg["start"]),
                        end=float(seg["end"]),
                        text=seg["text"].strip(),
                        speaker=None,  # MLX Whisper doesn't do diarization
                    )
                )

        # Get full text
        full_text = mlx_result.get("text", "").strip()

        # Get language (detected or specified)
        language = mlx_result.get("language", "unknown")

        # Calculate duration from segments or estimate from file
        if segments:
            duration = segments[-1].end
        else:
            # Fallback: try to get duration from file (would need audio library)
            # For now, use 0 if no segments
            duration = 0.0

        # Build metadata
        metadata = {
            "backend": self.name,
            "model_size": self._current_model_size,
            "language": language,
        }

        return TranscriptionResult(
            segments=segments,
            text=full_text,
            language=language,
            duration=duration,
            metadata=metadata,
        )
