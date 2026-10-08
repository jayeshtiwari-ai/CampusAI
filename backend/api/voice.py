"""
backend/api/voice.py - Voice Pipeline API Endpoints

Provides REST endpoints for:
1. POST /voice/stt - Audio WAV upload to transcribed text
2. POST /voice/tts - Text synthesis to MP3 speech audio
3. POST /voice/chat - End-to-end voice chat (Audio -> STT -> RAG LLM -> TTS -> Audio base64)
"""

import base64
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Response, status
from pydantic import BaseModel, Field

from backend.speech.stt import get_stt
from backend.speech.tts import get_tts
from backend.agents import get_orchestrator
from backend.utils.language import detect_language
from backend.utils.logger import get_logger

logger = get_logger("campusai.api.voice")

router = APIRouter(prefix="/voice", tags=["Voice"])

stt_processor = get_stt()
tts_processor = get_tts()
orchestrator = get_orchestrator()


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text string to synthesize into speech.")
    language: Optional[str] = Field(default="en", description="Target voice language code ('en', 'hi', 'mr', 'hinglish').")


class VoiceChatResponse(BaseModel):
    transcript: str
    reply: str
    language_detected: str
    sources: List[str]
    confident: bool
    needs_human: bool
    audio_base64: str


@router.post("/stt")
async def voice_to_text(file: UploadFile = File(...)):
    """Convert uploaded audio file into text using Groq Whisper STT."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty."
        )

    result = stt_processor.transcribe(audio_bytes, filename=file.filename or "audio.wav")
    return result


@router.post("/tts")
async def text_to_voice(payload: TTSRequest):
    """Synthesize text string into MP3 speech audio."""
    audio_bytes = await tts_processor.synthesize(payload.text, language=payload.language)
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Speech synthesis failed."
        )

    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/chat", response_model=VoiceChatResponse)
async def end_to_end_voice_chat(file: UploadFile = File(...)):
    """
    Full End-to-End Voice Chat Pipeline.
    1. Transcribe audio -> Text (STT)
    2. Detect language & query RAG Receptionist Agent
    3. Synthesize reply text -> Speech Audio (TTS)
    4. Return JSON response with base64 encoded audio
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio payload."
        )

    # 1. Speech-To-Text (STT)
    stt_res = stt_processor.transcribe(audio_bytes, filename=file.filename or "voice_chat.wav")
    transcript = stt_res.get("text", "").strip()

    if not transcript:
        return VoiceChatResponse(
            transcript="",
            reply="I could not hear any speech. Please try speaking again.",
            language_detected="en",
            sources=[],
            confident=False,
            needs_human=False,
            audio_base64=""
        )

    # 2. Language Detection & Multi-Agent Orchestrator Query
    detected_lang = detect_language(transcript)
    agent_res = orchestrator.handle_query(user_query=transcript, session_id="voice_session", language=detected_lang)
    reply_text = agent_res.get("reply", "")

    # 3. Text-To-Speech (TTS)
    reply_audio_bytes = await tts_processor.synthesize(reply_text, language=detected_lang)
    audio_b64 = base64.b64encode(reply_audio_bytes).decode("utf-8") if reply_audio_bytes else ""

    return VoiceChatResponse(
        transcript=transcript,
        reply=reply_text,
        language_detected=detected_lang,
        sources=agent_res.get("sources", []),
        confident=agent_res.get("confident", True),
        needs_human=agent_res.get("needs_human", False),
        audio_base64=audio_b64
    )
