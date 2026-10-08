"""
backend/api/chat.py - Multi-Agent Integrated Chat API Endpoints

Implements POST /chat, POST /chat/reset, in-memory session history,
script-based language detection, and MultiAgentOrchestrator integration.
"""

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.agents import get_orchestrator
from backend.utils.language import detect_language
from backend.utils.logger import get_logger

logger = get_logger("campusai.api.chat")

router = APIRouter(tags=["Chat"])

# Initialize Multi-Agent Orchestrator singleton
orchestrator = get_orchestrator()

# Session idle expiration limit (15 minutes = 900 seconds)
SESSION_EXPIRY_SECONDS = 900.0
MAX_HISTORY_TURNS = 10


class SessionData:
    """Class representing a visitor's conversation state."""

    def __init__(self) -> None:
        self.history: List[Dict[str, str]] = []
        self.last_activity: float = time.time()

    def update_activity(self) -> None:
        """Update last active timestamp."""
        self.last_activity = time.time()

    def is_expired(self) -> bool:
        """Check if session has timed out after 15 minutes of inactivity."""
        return (time.time() - self.last_activity) > SESSION_EXPIRY_SECONDS

    def add_turn(self, user_msg: str, assistant_reply: str) -> None:
        """Add user message and assistant reply, maintaining a max 10-turn history."""
        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": assistant_reply})
        self.update_activity()

        max_messages = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]


# Global In-Memory Session Storage
session_store: Dict[str, SessionData] = {}


def cleanup_expired_sessions() -> None:
    """Purge sessions that have exceeded the 15-minute idle limit."""
    now = time.time()
    expired_keys = [
        s_id for s_id, s_data in session_store.items()
        if (now - s_data.last_activity) > SESSION_EXPIRY_SECONDS
    ]
    for s_id in expired_keys:
        del session_store[s_id]
        logger.info("Cleaned up expired session: %s", s_id)


def detect_language(text: str) -> str:
    """
    Detect user query language based on Unicode script analysis and keyword matching.

    Returns:
        One of 'en', 'hi', 'mr', 'hinglish'.
    """
    text_clean = text.strip()
    if not text_clean:
        return "en"

    # Check for Devanagari script range (\u0900 - \u097F)
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    if devanagari_pattern.search(text_clean):
        marathi_words = {"आहे", "नाही", "काय", "नमस्कार", "कसे", "कोणता", "कुठे", "तुमचे", "माझे", "होय", "माहिती", "कधी"}
        words = set(re.findall(r'[\u0900-\u097F]+', text_clean))
        if words.intersection(marathi_words):
            return "mr"
        return "hi"

    # Hinglish key term dictionary matching
    hinglish_keywords = {
        "kab", "hai", "kya", "kaise", "kahan", "batao", "namaste", "chahiye",
        "raha", "rahi", "hoon", "hu", "aap", "tum", "mujhe", "ko", "me", "par",
        "dakhila", "timing", "kaha", "konsi", "kiska", "kisko", "tak", "bataiye",
        "chhutti", "sir", "mam", "bhai", "karenge", "milega", "hoga", "kitni", "kitna", "uske", "iska"
    }

    lowered_words = set(re.findall(r'\b[a-zA-Z]+\b', text_clean.lower()))
    hinglish_matches = lowered_words.intersection(hinglish_keywords)

    if len(hinglish_matches) >= 1:
        return "hinglish"

    return "en"


# Request / Response Pydantic Schemas
class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Unique session ID. Auto-generated if omitted.")
    message: str = Field(..., min_length=1, description="User input text message.")
    user_type: Optional[str] = Field(default="visitor", description="User category: student, parent, faculty, visitor.")
    language: Optional[str] = Field(default=None, description="Explicit language code ('en', 'hi', 'mr', 'hinglish').")


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    agent: str
    language_detected: str
    timestamp: str
    sources: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    confident: bool = True
    needs_human: bool = False
    needs_clarification: bool = False
    ui_action: str = "none"
    data: Dict[str, Any] = Field(default_factory=dict)


class ResetRequest(BaseModel):
    session_id: str


class ResetResponse(BaseModel):
    status: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    """
    Main Multi-Agent Chat API Endpoint.

    Routes visitor queries via MultiAgentOrchestrator to specialized agents,
    invokes SQL tools and RAG grounding, and returns standardized response.
    """
    cleanup_expired_sessions()

    session_id = payload.session_id if payload.session_id else str(uuid.uuid4())
    user_message = payload.message.strip()

    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message field cannot be empty."
        )

    # Detect language if not explicitly provided
    detected_lang = payload.language if payload.language else detect_language(user_message)
    logger.info("Session [%s] - User message (%s): '%s'", session_id, detected_lang, user_message)

    # Fetch or create session state
    if session_id not in session_store or session_store[session_id].is_expired():
        session_store[session_id] = SessionData()

    session = session_store[session_id]

    # Process query through Multi-Agent Orchestrator
    orchestrator_result = orchestrator.handle_query(
        user_query=user_message,
        session_id=session_id,
        language=detected_lang,
        user_type=payload.user_type
    )

    reply_text = orchestrator_result.get("reply", "I don't have verified information for that.")

    # Record turn in session memory
    session.add_turn(user_msg=user_message, assistant_reply=reply_text)

    return ChatResponse(
        reply=reply_text,
        session_id=session_id,
        agent=orchestrator_result.get("agent", "reception"),
        language_detected=detected_lang,
        timestamp=datetime.now(timezone.utc).isoformat(),
        sources=orchestrator_result.get("sources", []),
        tools_used=orchestrator_result.get("tools_used", []),
        confident=orchestrator_result.get("confident", True),
        needs_human=orchestrator_result.get("needs_human", False),
        needs_clarification=orchestrator_result.get("needs_clarification", False),
        ui_action=orchestrator_result.get("ui_action", "none"),
        data=orchestrator_result.get("data", {})
    )


@router.post("/chat/reset", response_model=ResetResponse)
async def reset_chat_session(payload: ResetRequest) -> ResetResponse:
    """Reset session history for a given session ID."""
    s_id = payload.session_id
    if s_id in session_store:
        del session_store[s_id]
        logger.info("Reset session memory for session_id: %s", s_id)
    
    return ResetResponse(status="reset", session_id=s_id)
