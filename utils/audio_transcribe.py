"""
Offline speech-to-text using faster-whisper (a CTranslate2 reimplementation
of OpenAI's Whisper). Runs fully locally, no API key / no internet required
at inference time, and has no torch/triton dependency — much more reliable
to install on constrained hosts like Streamlit Community Cloud.
"""

from faster_whisper import WhisperModel


def load_whisper_model(size: str = "base"):
    """
    Load and return a faster-whisper model.

    size options (accuracy vs speed/RAM tradeoff):
        "tiny"   - fastest, least accurate
        "base"   - good default for free-tier hosting
        "small"  - better accuracy
        "medium" - much better accuracy, needs more RAM/CPU

    compute_type="int8" keeps RAM/CPU usage low, which matters on
    Streamlit Community Cloud's free tier.
    """
    return WhisperModel(size, device="cpu", compute_type="int8")


def transcribe_audio(model, audio_path: str, language: str = "en") -> str:
    """
    Transcribe an audio file on disk and return the plain text transcript.
    """
    segments, _info = model.transcribe(audio_path, language=language)
    return " ".join(segment.text.strip() for segment in segments).strip()

