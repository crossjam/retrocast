"""Faster-Whisper backend for CPU and CUDA transcription."""

import time
from pathlib import Path
from typing import Optional

from loguru import logger

from retrocast.transcription.base import (
    TranscriptionBackend,
    TranscriptionResult,
    TranscriptionSegment,
)


class FasterWhisperBackend(TranscriptionBackend):
    """Faster-Whisper transcription backend for CUDA and CPU.

    This backend uses the faster-whisper library which provides optimized
    Whisper transcription using CTranslate2. It supports both CUDA (GPU)
    and CPU execution, with automatic device detection.

    Performance is significantly better than OpenAI's Whisper, and can
    utilize NVIDIA GPUs when available.
    """

    def __init__(self):
        """Initialize Faster-Whisper backend."""
        self._model = None
        self._current_model_size = None
        self._device = None
        self._compute_type = None

    @property
    def name(self) -> str:
        """Return backend identifier."""
        return "faster-whisper"

    def is_available(self) -> bool:
        """Check if Faster-Whisper is available.

        Returns:
            True if faster_whisper can be imported
        """
        try:
            import faster_whisper  # noqa: F401  # type: ignore[import-untyped]

            return True
        except ImportError:
            logger.debug("faster_whisper not installed")
            return False

    def _detect_device(self) -> tuple[str, str]:
        """Detect the best available device and compute type.

        Returns:
            Tuple of (device, compute_type) where device is 'cuda' or 'cpu'
            and compute_type is optimized for that device.
        """
        try:
            import torch  # type: ignore[import-untyped]

            if torch.cuda.is_available():
                logger.info("CUDA is available, using GPU acceleration")
                # Use float16 for CUDA as it's faster and uses less memory
                return ("cuda", "float16")
        except ImportError:
            pass

        logger.info("CUDA not available, using CPU")
        # Use int8 for CPU as it's faster with minimal quality loss
        return ("cpu", "int8")

    def platform_info(self) -> str:
        """Return platform information."""
        if self._device is None:
            device, _ = self._detect_device()
        else:
            device = self._device

        if device == "cuda":
            try:
                import torch  # type: ignore[import-untyped]

                gpu_name = torch.cuda.get_device_name(0)
                return f"Linux/Windows (CUDA GPU: {gpu_name})"
            except Exception:
                return "Linux/Windows (CUDA GPU)"
        else:
            return "Any platform (CPU)"

    def description(self) -> str:
        """Return backend description."""
        return "Faster-Whisper - optimized Whisper with CUDA/CPU support"

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        model_size: str = "base",
    ) -> TranscriptionResult:
        """Transcribe audio file using Faster-Whisper.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., "en", "es"). Auto-detect if None.
            model_size: Model size (tiny, base, small, medium, large, large-v2, large-v3)

        Returns:
            TranscriptionResult with segments and metadata

        Raises:
            ImportError: If faster_whisper is not installed
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If transcription fails
        """
        try:
            import faster_whisper  # noqa: F401  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError(
                "faster_whisper is not installed. "
                "Install with: pip install faster-whisper\n"
                "For CUDA support: pip install faster-whisper torch --extra-index-url "
                "https://download.pytorch.org/whl/cu121"
            ) from e

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Detect device if not already set
        if self._device is None or self._compute_type is None:
            self._device, self._compute_type = self._detect_device()

        # Load model (with caching)
        self._ensure_model_loaded(model_size)

        # Ensure model is loaded (type checker assertion)
        assert self._model is not None, "Model should be loaded after _ensure_model_loaded()"

        logger.info(
            f"Transcribing {audio_path.name} with Faster-Whisper "
            f"({model_size} model on {self._device})"
        )

        # Transcribe with faster_whisper
        try:
            start_time = time.time()

            # faster_whisper returns segments as an iterator
            segments_iter, info = self._model.transcribe(
                str(audio_path),
                language=language,
                beam_size=5,  # Default beam size for good quality
                vad_filter=True,  # Use VAD to filter out non-speech
            )

            # Convert iterator to list
            segments_list = list(segments_iter)

            transcription_time = time.time() - start_time

        except Exception as e:
            raise RuntimeError(f"Faster-Whisper transcription failed: {e}") from e

        # Convert faster_whisper result to our TranscriptionResult format
        return self._convert_result(
            segments_list, info, audio_path, transcription_time, model_size
        )

    def _ensure_model_loaded(self, model_size: str) -> None:
        """Ensure the Whisper model is loaded with the correct size.

        Args:
            model_size: Model size to load

        Raises:
            ValueError: If model_size is invalid
        """
        valid_sizes = [
            "tiny",
            "tiny.en",
            "base",
            "base.en",
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large-v1",
            "large-v2",
            "large-v3",
            "large",
        ]
        if model_size not in valid_sizes:
            raise ValueError(
                f"Invalid model size: {model_size}. " f"Valid sizes: {', '.join(valid_sizes)}"
            )

        # Only reload if model size changed or model not loaded yet
        if self._model is None or model_size != self._current_model_size:
            from faster_whisper import WhisperModel  # type: ignore[import-untyped]

            logger.info(
                f"Loading Faster-Whisper model: {model_size} "
                f"(device={self._device}, compute_type={self._compute_type})"
            )

            # Load the model
            self._model = WhisperModel(
                model_size,
                device=self._device,
                compute_type=self._compute_type,
                download_root=None,  # Use default cache directory
            )

            self._current_model_size = model_size
            logger.debug(f"Model {model_size} loaded successfully")

    def _convert_result(
        self,
        faster_segments: list,
        info,
        audio_path: Path,
        transcription_time: float,
        model_size: str,
    ) -> TranscriptionResult:
        """Convert faster_whisper result to TranscriptionResult.

        Args:
            faster_segments: List of segment objects from faster_whisper
            info: TranscriptionInfo object from faster_whisper
            audio_path: Path to audio file (for metadata)
            transcription_time: Time taken to transcribe in seconds
            model_size: Model size used

        Returns:
            TranscriptionResult
        """
        # Extract segments
        segments = []
        full_text_parts = []

        for seg in faster_segments:
            text = seg.text.strip()
            if text:  # Skip empty segments
                segments.append(
                    TranscriptionSegment(
                        start=float(seg.start),
                        end=float(seg.end),
                        text=text,
                        speaker=None,  # Faster-Whisper doesn't do diarization by default
                    )
                )
                full_text_parts.append(text)

        # Build full text
        full_text = " ".join(full_text_parts)

        # Get language (detected or specified)
        language = info.language if hasattr(info, "language") else "unknown"

        # Get duration
        duration = info.duration if hasattr(info, "duration") else 0.0
        if duration == 0.0 and segments:
            duration = segments[-1].end

        # Calculate real-time factor (RTF)
        # RTF = transcription_time / audio_duration
        # Lower is better (e.g., 0.5 means it took half the time of the audio)
        rtf = transcription_time / duration if duration > 0 else 0.0

        # Build metadata
        metadata = {
            "backend": self.name,
            "model_size": model_size,
            "language": language,
            "device": self._device,
            "compute_type": self._compute_type,
            "transcription_time": transcription_time,
            "real_time_factor": rtf,
            "language_probability": (
                info.language_probability if hasattr(info, "language_probability") else None
            ),
        }

        logger.info(
            f"Transcription complete: {len(segments)} segments, "
            f"{transcription_time:.2f}s elapsed, RTF={rtf:.2f}x"
        )

        return TranscriptionResult(
            segments=segments,
            text=full_text,
            language=language,
            duration=duration,
            metadata=metadata,
        )
