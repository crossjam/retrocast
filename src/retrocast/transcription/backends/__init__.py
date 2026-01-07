"""Transcription backend registry and discovery."""

from typing import Type

from retrocast.transcription.base import TranscriptionBackend

# Backend registry will be populated as backends are implemented
_BACKENDS: list[Type[TranscriptionBackend]] = []


def register_backend(backend_cls: Type[TranscriptionBackend]) -> None:
    """Register a transcription backend.

    Args:
        backend_cls: Backend class to register
    """
    if backend_cls not in _BACKENDS:
        _BACKENDS.append(backend_cls)


def get_all_backends() -> list[Type[TranscriptionBackend]]:
    """Get all registered transcription backends.

    Returns:
        List of backend classes
    """
    # Import and register backends
    try:
        from retrocast.transcription.backends.mlx_whisper import MLXWhisperBackend

        register_backend(MLXWhisperBackend)
    except ImportError:
        pass  # MLX backend dependencies not available

    try:
        from retrocast.transcription.backends.faster_whisper import FasterWhisperBackend

        register_backend(FasterWhisperBackend)
    except ImportError:
        pass  # Faster-Whisper backend dependencies not available

    return _BACKENDS.copy()


def get_available_backends() -> list[TranscriptionBackend]:
    """Get all available (installed and working) backends.

    Returns:
        List of backend instances that are available
    """
    available = []
    for backend_cls in get_all_backends():
        backend = backend_cls()
        if backend.is_available():
            available.append(backend)
    return available
