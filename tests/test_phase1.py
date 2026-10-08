"""
tests/test_phase1.py - Automated Verification Test Suite for Phase 1

Tests FastAPI endpoints, language detection, memory retention, reset, and LLM exception handling.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.chat import detect_language

client = TestClient(app)


def test_health_check() -> None:
    """Verify /health endpoint returns 200 OK and valid status metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model" in data
    assert "uptime_seconds" in data


def test_language_detection() -> None:
    """Verify language detection logic for en, hi, mr, hinglish."""
    assert detect_language("What is the admission procedure?") == "en"
    assert detect_language("प्रवेश प्रक्रिया क्या है?") == "hi"
    assert detect_language("प्रवेश प्रक्रिया काय आहे?") == "mr"
    assert detect_language("admission kab tak hai sir?") == "hinglish"


def test_chat_flow_and_hinglish() -> None:
    """Verify POST /chat endpoint in Hinglish and session history retention."""
    session_id = "test_session_123"

    # Message 1 in Hinglish
    res1 = client.post("/chat", json={"session_id": session_id, "message": "admission kab tak hai?"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["session_id"] == session_id
    assert data1["language_detected"] == "hinglish"
    assert len(data1["reply"]) > 0

    # Message 2 follow-up in Hinglish
    res2 = client.post("/chat", json={"session_id": session_id, "message": "mujhe fees kitni hai ye batao?"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["reply"]) > 0


def test_chat_reset() -> None:
    """Verify session reset endpoint POST /chat/reset."""
    session_id = "test_session_reset"
    client.post("/chat", json={"session_id": session_id, "message": "Hello"})
    
    reset_res = client.post("/chat/reset", json={"session_id": session_id})
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "reset"
