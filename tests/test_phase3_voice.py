"""
tests/test_phase3_voice.py - Automated Verification Test for Phase 3 Voice Pipeline

Tests STT hallucination filtering, TTS synthesis, language voice mapping,
and /voice API endpoints using FastAPI TestClient.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from backend.main import app
from backend.speech.stt import filter_hallucinations, STT_PROMPT_HINT
from backend.speech.tts import clean_text_for_tts, get_tts

client = TestClient(app)


def test_stt_hallucination_filtering() -> None:
    """Verify Whisper silence artifacts are filtered correctly."""
    assert filter_hallucinations("Thanks for watching!") == ""
    assert filter_hallucinations("Subtitles by Amara.org") == ""
    assert filter_hallucinations("you you you") == ""
    assert filter_hallucinations("a") == ""
    assert filter_hallucinations("Admission last date June 30 tak hai.") == "Admission last date June 30 tak hai."


def test_speakable_text_cleaner() -> None:
    """Verify markdown symbols and abbreviations are cleaned for TTS."""
    raw_text = "Total fee is **INR 1,50,000** per year & includes 100% scholarship."
    clean = clean_text_for_tts(raw_text)
    assert "**" not in clean
    assert "Rupees" in clean
    assert "and" in clean


def test_tts_synthesis() -> None:
    """Verify edge-tts synthesizes non-empty MP3 audio bytes."""
    tts = get_tts()
    audio_bytes = asyncio.run(tts.synthesize("Welcome to CampusAI Engineering College.", language="en"))
    assert len(audio_bytes) > 0
    assert audio_bytes[:3] == b"ID3" or b"TAG" in audio_bytes or len(audio_bytes) > 1000


def test_voice_tts_endpoint() -> None:
    """Verify POST /voice/tts returns audio/mpeg response."""
    res = client.post("/voice/tts", json={"text": "Hello, welcome to college reception.", "language": "en"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    assert len(res.content) > 0
