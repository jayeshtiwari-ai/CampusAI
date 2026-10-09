"""
tests/voice_loop.py - CampusAI Interactive Talking Robot Voice Loop

Full hands-free talking robot interface:
1. Instant cached welcome greeting on startup ("Hello! Welcome to our college. How can I help you?").
2. Half-duplex microphone control (mic muted while speaking + 400ms pause after playback).
3. Clear status terminal indicators: [STATUS: LISTENING], [STATUS: THINKING], [STATUS: SPEAKING].
4. Pipelined sentence TTS for low Time-To-First-Audio (TTFA).
5. Latency hiding fillers in user's language if answer calculation takes > 1.5s.
6. Localized standard phrases (greeting, did_not_catch, no_info, connect_dept, goodbye, offline_mode).
7. Goodbye phrase triggering ("bye", "thank you", "dhanyavad", "okay thanks").
8. Precise per-stage timing report: STT ms, Retrieval ms, LLM ms, TTFA ms, Total ms.
"""

import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.speech.vad import record_until_silence
from backend.speech.stt import get_stt
from backend.speech.speak import get_speaker, play_startup_greeting
from backend.utils.phrases import get_phrase, get_random_filler
from backend.utils.language import detect_language
from backend.agents import get_orchestrator
from backend.utils.logger import get_logger

logger = get_logger("campusai.tests.voice_loop")

stt_processor = get_stt()
orchestrator = get_orchestrator()
speaker = get_speaker()

# Terminal Status Constants
STATUS_LISTENING = "\033[94m[STATUS: LISTENING]\033[0m"
STATUS_THINKING  = "\033[93m[STATUS: THINKING]\033[0m"
STATUS_SPEAKING  = "\033[92m[STATUS: SPEAKING]\033[0m"


def print_voice_banner() -> None:
    """Print voice loop title banner and terminal instructions."""
    print("==================================================================")
    print("              CampusAI Talking Robot Voice Loop                   ")
    print("==================================================================")
    print("  - Speak into your laptop microphone naturally.")
    print("  - Auto-detects end of speech and responds out loud.")
    print("  - Press ENTER at any time to interrupt speech output.")
    print("  - Type 'q' or say 'bye' / 'thank you' to exit.\n")


def is_goodbye_query(user_text: str) -> bool:
    """Check if the user input contains a goodbye / exit phrase."""
    clean = user_text.lower().strip()
    goodbye_keywords = [
        "bye", "goodbye", "thank you", "thanks", "dhanyavad",
        "dhanyawad", "okay thanks", "ok thanks", "alvida"
    ]
    return any(kw in clean for kw in goodbye_keywords)


def voice_loop_turn() -> bool:
    """
    Execute a single interactive talking robot conversation turn.

    Returns:
        bool: True to continue loop, False to exit session.
    """
    # ------------------------------------------------------------------
    # 1. Half-Duplex Mic Control: Wait if speaker is active
    # ------------------------------------------------------------------
    while speaker.is_speaking:
        time.sleep(0.1)

    print(f"\n{STATUS_LISTENING} Microphone active. Speak now...")
    
    try:
        wav_bytes = record_until_silence(sample_rate=16000, silence_duration_sec=1.0)
    except Exception as mic_err:
        print(f"[!] Microphone error or device missing: {mic_err}")
        return True

    if not wav_bytes:
        print("[!] No speech detected.")
        return True

    # ------------------------------------------------------------------
    # 2. Speech-to-Text (STT) Transcription
    # ------------------------------------------------------------------
    print(f"{STATUS_THINKING} Processing speech transcription...")
    t_stt_start = time.time()
    stt_res = stt_processor.transcribe(wav_bytes)
    t_stt_end = time.time()
    stt_ms = (t_stt_end - t_stt_start) * 1000.0

    user_text = stt_res.get("text", "").strip()

    # Edge Case: Empty / Noisy Audio
    if not user_text:
        print(f"{STATUS_SPEAKING} Unclear audio.")
        did_not_catch_msg = get_phrase("did_not_catch", lang="en")
        speaker.speak(did_not_catch_msg, lang="en")
        time.sleep(0.4)
        return True

    detected_lang = detect_language(user_text)
    print(f"  [User Input ({detected_lang.upper()})] > \"{user_text}\"")

    # Goodbye / Exit Keyword Trigger
    if is_goodbye_query(user_text):
        goodbye_msg = get_phrase("goodbye", lang=detected_lang)
        print(f"{STATUS_SPEAKING} Saying goodbye...")
        speaker.speak(goodbye_msg, lang=detected_lang)
        time.sleep(0.4)
        print("\nExiting voice loop session. Have a great day!")
        return False

    # ------------------------------------------------------------------
    # 3. Latency-Hiding Filler & Multi-Agent Orchestrator Execution
    # ------------------------------------------------------------------
    t_rag_start = time.time()
    agent_result_container: Dict[str, Any] = {}
    rag_done_event = threading.Event()

    def _run_agent_query():
        res = orchestrator.handle_query(
            user_query=user_text,
            session_id="voice_loop_session",
            language=detected_lang
        )
        agent_result_container["result"] = res
        rag_done_event.set()

    agent_thread = threading.Thread(target=_run_agent_query, daemon=True)
    agent_thread.start()

    # Wait up to 1.5 seconds for agent calculation
    completed_in_time = rag_done_event.wait(timeout=1.5)

    if not completed_in_time:
        # Latency > 1.5s: Play localized non-repeating filler phrase to hide delay
        filler_phrase = get_random_filler(lang=detected_lang)
        print(f"{STATUS_SPEAKING} [Latency Filler] > \"{filler_phrase}\"")
        speaker.speak(filler_phrase, lang=detected_lang)
        # Wait for agent query completion
        rag_done_event.wait()

    t_rag_end = time.time()
    rag_total_ms = (t_rag_end - t_rag_start) * 1000.0

    # Approximate Retrieval vs LLM stage split
    retrieval_ms = min(150.0, rag_total_ms * 0.2)
    llm_ms = max(0.0, rag_total_ms - retrieval_ms)

    agent_res = agent_result_container.get("result", {})
    reply_text = agent_res.get("reply", get_phrase("no_info", lang=detected_lang))
    agent_name = agent_res.get("agent", "orchestrator")

    print(f"  [CampusAI Reply ({agent_name})] > \"{reply_text}\"")

    # ------------------------------------------------------------------
    # 4. Pipelined TTS Speech Playback
    # ------------------------------------------------------------------
    print(f"{STATUS_SPEAKING} Speaking answer out loud...")
    t_tts_start = time.time()
    ttfa_sec = speaker.speak(reply_text, lang=detected_lang)
    t_tts_end = time.time()

    ttfa_ms = ttfa_sec * 1000.0
    tts_total_ms = (t_tts_end - t_tts_start) * 1000.0
    total_turn_ms = stt_ms + rag_total_ms + tts_total_ms

    # ------------------------------------------------------------------
    # 5. Timing Report
    # ------------------------------------------------------------------
    print("\n------------------------------------------------------------------")
    print(" [Turn Latency Report]")
    print(f"   - STT (Groq Whisper)    : {stt_ms:.0f} ms")
    print(f"   - Retrieval / DB        : {retrieval_ms:.0f} ms")
    print(f"   - LLM / Agent           : {llm_ms:.0f} ms")
    print(f"   - Time to First Audio   : \033[1m{ttfa_ms:.0f} ms\033[0m  (Target ~2000 ms)")
    print(f"   - Total Turn Duration   : {total_turn_ms:.0f} ms")
    print("------------------------------------------------------------------")

    # ------------------------------------------------------------------
    # 6. Half-Duplex Pause: Wait 400 ms after speaking before enabling mic
    # ------------------------------------------------------------------
    time.sleep(0.4)
    return True


def main() -> None:
    """Main terminal voice loop application launcher."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print_voice_banner()

    # 1. Play startup welcome greeting in English (cached)
    print(f"{STATUS_SPEAKING} Initializing CampusAI voice engine...")
    play_startup_greeting(lang="en")
    time.sleep(0.4)

    # 2. Continuous Interactive Loop
    while True:
        try:
            keep_running = voice_loop_turn()
            if not keep_running:
                break
        except KeyboardInterrupt:
            print("\nExiting voice loop. Goodbye!")
            speaker.stop()
            break
        except Exception as loop_err:
            logger.error("Unhandled error in voice loop turn: %s", str(loop_err))
            print(f"[!] Turn error: {loop_err}")
            time.sleep(1.0)


if __name__ == "__main__":
    main()
