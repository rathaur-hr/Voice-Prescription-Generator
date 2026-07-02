"""
Offline speech-to-text using OpenAI's Whisper model (runs fully locally,
no API key / no internet required at inference time).
"""

import whisper


def load_whisper_model(size: str = "base"):
    """
    Load and return a Whisper model.

    size options (accuracy vs speed/RAM tradeoff):
        "tiny"   - fastest, least accurate, ~1GB RAM
        "base"   - good default for free-tier hosting, ~1GB RAM
        "small"  - better accuracy, ~2GB RAM
        "medium" - much better accuracy, ~5GB RAM (needs real compute)
    """
    return whisper.load_model(size)


def transcribe_audio(model, audio_path: str, language: str = "en") -> str:
    """
    Transcribe an audio file on disk and return the plain text transcript.
    """
    result = model.transcribe(audio_path, language=language, fp16=False)
    return result["text"].strip()
