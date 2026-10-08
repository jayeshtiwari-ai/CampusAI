"""
backend/speech/tts.py - Text-to-Speech (TTS) Engine & Audio Caching

Synthesizes high-quality neural speech using edge-tts with localized Indian voices:
- en: en-IN-NeerjaNeural
- hi / hinglish: hi-IN-SwaraNeural
- mr: mr-IN-AarohiNeural

Features:
- Disk caching in data/audio_cache/ for instant playback
- Clean text formatting (removes markdown, bullets, URLs, emojis)
- Smart sentence limiting (max 4 sentences + "I can send the rest to your phone")
- MP3 to 16 kHz WAV PCM audio converter
"""

import io
import re
import os
import hashlib
import asyncio
from pathlib import Path
from typing import Optional, Dict, List

import edge_tts
from pydub import AudioSegment

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("campusai.speech.tts")

# Audio cache directory
CACHE_DIR: Path = settings.BASE_DIR / "data" / "audio_cache"

# Voice selection mapping from config / defaults
VOICE_MAP: Dict[str, str] = {
    "en": settings.VOICE_EN,
    "hi": settings.VOICE_HI,
    "hinglish": settings.VOICE_HINGLISH,
    "mr": settings.VOICE_MR,
}


def clean_text_for_tts(text: str) -> str:
    """
    Clean text formatting to ensure natural speakable audio output.
    Strips markdown formatting, bullets, URLs, emojis, and normalizes currency/symbols.

    Args:
        text: Raw input string from LLM/agent.

    Returns:
        Clean, speakable string.
    """
    if not text:
        return ""

    clean = text.strip()

    # Remove URLs (http:// or https:// or www.)
    clean = re.sub(r'https?://\S+|www\.\S+', '', clean)

    # Remove Markdown headers, bold, italics, code blocks
    clean = re.sub(r'#+\s*', '', clean)
    clean = re.sub(r'[*_`~]', '', clean)

    # Remove Markdown link tags [text](url) -> text
    clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)

    # Remove bullets (*, -, •, 1., 2., etc.) at sentence start
    clean = re.sub(r'^\s*[-*•]\s+', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^\s*\d+[\.\)]\s+', '', clean, flags=re.MULTILINE)

    # Remove emojis and non-standard unicode symbols
    clean = re.sub(r'[\U00010000-\U0010ffff]', '', clean)
    clean = re.sub(r'[\u2600-\u26FF\u2700-\u27BF]', '', clean)

    # Expand common symbols and currency terms for spoken naturalness
    clean = re.sub(r'\bINR\b|\bRs\.\b|\bRs\b', 'Rupees', clean, flags=re.IGNORECASE)
    clean = re.sub(r'%', ' percent', clean)
    clean = re.sub(r'&', ' and ', clean)
    clean = re.sub(r'@', ' at ', clean)

    # Collapse multi-space formatting
    clean = re.sub(r'\s+', ' ', clean)

    return clean.strip()


def split_into_sentences(text: str) -> List[str]:
    """Split clean text string into distinct sentences for TTS processing."""
    if not text:
        return []
    # Split by English/Hindi/Marathi sentence end marks (. ! ? ।)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text) if s.strip()]
    return sentences if sentences else [text]


def limit_sentences(text: str, max_sentences: int = 4, lang: str = "en") -> str:
    """
    Limit response text to a maximum number of sentences (default 4).
    Appends a tail notice phrase if response is truncated.

    Args:
        text: Speakable text string.
        max_sentences: Maximum number of sentences to speak.
        lang: Target language code.

    Returns:
        Truncated text if necessary, with tail notice.
    """
    from backend.utils.phrases import get_phrase

    sentences = split_into_sentences(text)
    if len(sentences) <= max_sentences:
        return text

    truncated_sentences = sentences[:max_sentences]
    tail_phrase = get_phrase("long_answer_tail", lang=lang)
    
    truncated_text = " ".join(truncated_sentences)
    if not truncated_text.endswith((".", "!", "?", "।")):
        truncated_text += "."
    
    return f"{truncated_text} {tail_phrase}"


def convert_mp3_to_wav_pcm(mp3_bytes: bytes, target_sample_rate: int = 16000) -> bytes:
    """Convert MP3 bytes into 16 kHz 16-bit mono WAV PCM audio."""
    try:
        audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
        audio = audio.set_frame_rate(target_sample_rate).set_channels(1).set_sample_width(2)

        out_buffer = io.BytesIO()
        audio.export(out_buffer, format="wav")
        return out_buffer.getvalue()
    except Exception as conv_err:
        logger.error("Failed to convert MP3 to WAV PCM: %s", str(conv_err))
        return mp3_bytes


class TextToSpeech:
    """Text-to-Speech manager using edge-tts with disk caching."""

    def __init__(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def get_voice_for_language(self, language: str) -> str:
        """Get neural TTS voice for target language."""
        lang_code = (language or "en").lower().strip()
        return VOICE_MAP.get(lang_code, VOICE_MAP["en"])

    def _get_cache_path(self, text: str, voice: str) -> Path:
        """Generate deterministic cache file path from voice and text hash."""
        key = f"{voice}:{text}"
        hash_str = hashlib.md5(key.encode("utf-8")).hexdigest()
        return CACHE_DIR / f"tts_{hash_str}.mp3"

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        """
        Synthesize text into speech MP3 bytes (with disk cache check).

        Args:
            text: Text string to convert to audio.
            language: Target language code ('en', 'hi', 'mr', 'hinglish').

        Returns:
            Raw MP3 audio bytes.
        """
        clean_text = clean_text_for_tts(text)
        if not clean_text:
            return b""

        voice = self.get_voice_for_language(language)
        cache_path = self._get_cache_path(clean_text, voice)

        # Check disk cache
        if cache_path.exists():
            logger.info("Loaded TTS audio from cache: %s", cache_path.name)
            with open(cache_path, "rb") as f:
                return f.read()

        logger.info("Synthesizing TTS via edge-tts (Voice: %s): '%s'", voice, clean_text[:40])

        try:
            communicate = edge_tts.Communicate(text=clean_text, voice=voice)
            audio_buffer = io.BytesIO()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            mp3_data = audio_buffer.getvalue()

            if mp3_data:
                with open(cache_path, "wb") as f:
                    f.write(mp3_data)

            return mp3_data

        except Exception as tts_err:
            logger.warning("edge-tts synthesis failed: %s", str(tts_err))
            return b""


_tts_instance: Optional[TextToSpeech] = None

def get_tts() -> TextToSpeech:
    """Get global cached TextToSpeech instance."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TextToSpeech()
    return _tts_instance
