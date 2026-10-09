"""
backend/speech/stt.py - Speech-to-Text (STT) Processing Module

Provides Groq Whisper API transcription with Hinglish prompt optimization,
silence hallucination filtering, and optional local fallback.
"""

import io
import re
from typing import Dict, Any, Optional
from groq import Groq

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("campusai.speech.stt")

# Standard Whisper silence hallucination artifacts to filter out
HALLUCINATION_PATTERNS = [
    r"thank\s+you\s+for\s+watching",
    r"thanks\s+for\s+watching",
    r"subtitles?\s+by",
    r"amara\.org",
    r"bye\s+bye",
    r"^\s*\.\s*$",
    r"^(\b\w+\b)(\s+\1){2,}$"  # Repeated single words e.g. "you you you"
]

# Hinglish & College Context Hint Prompt for Whisper
STT_PROMPT_HINT = (
    "CampusAI college reception conversation. Multilingual English, Hindi, Marathi, Hinglish. "
    "Keywords: admission, fees, hostel, timetable, exam, cutoff, eligibility, department, seat, documents, "
    "प्रवेश, फीस, दाखिला, पात्रता, कटऑफ, समयसारणी, परीक्षा, विभाग, छात्रावास, शुल्क।"
)


def filter_hallucinations(text: str) -> str:
    """
    Clean transcribed text and filter out common Whisper silence artifacts.

    Returns:
        Cleaned text string or empty string if flagged as a hallucination.
    """
    clean_text = text.strip()
    if len(clean_text) < 2:
        return ""

    lowered = clean_text.lower()
    for pattern in HALLUCINATION_PATTERNS:
        if re.search(pattern, lowered):
            logger.info("Filtered Whisper hallucination artifact: '%s'", clean_text)
            return ""

    return clean_text


class SpeechToText:
    """STT Processor class wrapping Groq Whisper API with fallback options."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> None:
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model_name = model_name or settings.GROQ_STT_MODEL
        self.client = Groq(api_key=self.api_key)

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio WAV bytes into text using Groq Whisper API.

        Args:
            audio_bytes: Raw bytes of WAV or MP3 audio file.
            filename: File name hint for MIME type detection.
            language: Optional ISO language code override.

        Returns:
            Dictionary with 'text' and 'language'.
        """
        if not audio_bytes or len(audio_bytes) < 100:
            return {"text": "", "language": "en"}

        logger.info("Sending audio (size: %d bytes) to Groq Whisper STT (%s)...", len(audio_bytes), self.model_name)

        try:
            # Wrap audio bytes in an in-memory BytesIO buffer with name
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename

            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model=self.model_name,
                prompt=STT_PROMPT_HINT,
                response_format="json",
                language=language,
                temperature=0.0
            )

            raw_text = transcription.text if hasattr(transcription, "text") else str(transcription)
            filtered_text = filter_hallucinations(raw_text)

            logger.info("STT Transcription Result: '%s'", filtered_text)
            return {
                "text": filtered_text,
                "language": language or "en"
            }

        except Exception as stt_err:
            logger.error("Groq Whisper STT API error: %s", str(stt_err))
            return {"text": "", "language": "en", "error": str(stt_err)}


# Global STT processor instance
_stt_instance: Optional[SpeechToText] = None

def get_stt() -> SpeechToText:
    """Get global cached SpeechToText processor instance."""
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = SpeechToText()
    return _stt_instance
