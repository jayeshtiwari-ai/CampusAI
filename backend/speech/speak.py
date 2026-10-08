"""
backend/speech/speak.py - Laptop Speaker Audio Output & Pipelined TTS Engine

Features:
1. Speaker class using pygame.mixer for MP3 playback
2. Pipelined sentence TTS (Producer/Consumer Queue): synthesizes sentence N+1 in a
   background thread while sentence N is playing out loud.
3. Time To First Audio (TTFA) optimization.
4. Offline fallback using pyttsx3 when edge-tts or internet is unavailable.
5. Instant cached startup greeting ("Hello! Welcome to our college. How can I help you?").
6. Immediate stop() functionality for user interrupts.
"""

import os
import sys
import time
import queue
import re
import threading
import tempfile
import asyncio
from pathlib import Path
from typing import List, Optional, Tuple

import pygame
import pyttsx3

from backend.config import settings
from backend.speech.tts import get_tts, clean_text_for_tts, limit_sentences, split_into_sentences, CACHE_DIR
from backend.utils.phrases import get_phrase
from backend.utils.logger import get_logger

logger = get_logger("campusai.speech.speak")


def speak_pyttsx3_fallback(text: str) -> None:
    """Fallback offline TTS engine using pyttsx3 when network/edge-tts fails."""
    logger.warning("Using pyttsx3 offline fallback for: '%s'", text[:40])
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.say(text)
        engine.runAndWait()
    except Exception as err:
        logger.error("pyttsx3 offline engine error: %s", str(err))


class Speaker:
    """
    Speaker audio output manager.
    Supports pipelined sentence playback via pygame.mixer, immediate stop interrupt,
    and offline TTS fallback.
    """

    def __init__(self) -> None:
        self._is_speaking_flag: bool = False
        self._stop_requested: bool = False
        self.tts = get_tts()
        self._init_mixer()

    def _init_mixer(self) -> None:
        """Initialize pygame mixer for MP3 audio playback."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
                logger.info("Pygame mixer initialized successfully.")
        except Exception as err:
            logger.error("Failed to initialize pygame mixer: %s", str(err))

    @property
    def is_speaking(self) -> bool:
        """Returns True if the speaker is currently playing audio or processing sentences."""
        if self._is_speaking_flag:
            return True
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                return True
        except Exception:
            pass
        return False

    def stop(self) -> None:
        """Immediately stop current playback and clear all queued sentences."""
        self._stop_requested = True
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception as err:
            logger.error("Error stopping pygame mixer playback: %s", str(err))
        self._is_speaking_flag = False
        logger.info("Speaker playback stopped by interrupt signal.")

    def speak(self, text: str, lang: str = "en") -> float:
        """
        Synthesize and play speech out loud using sentence-level pipelining.
        Synthesizes sentence N+1 while sentence N plays out loud.

        Args:
            text: Text string to speak out loud.
            lang: Language code ('en', 'hi', 'mr', 'hinglish').

        Returns:
            TTFA (Time to First Audio) in seconds.
        """
        self._stop_requested = False
        
        # 1. Clean & sentence-limit text
        clean_str = clean_text_for_tts(text)
        if not clean_str:
            return 0.0

        limited_str = limit_sentences(clean_str, max_sentences=4, lang=lang)
        sentences = split_into_sentences(limited_str)
        if not sentences:
            return 0.0

        self._is_speaking_flag = True
        audio_queue: queue.Queue = queue.Queue()
        voice = self.tts.get_voice_for_language(lang)

        # 2. Background Producer Thread for Pipelined Synthesis
        def _producer():
            for idx, sentence in enumerate(sentences):
                if self._stop_requested:
                    break

                # Attempt async synthesis using edge-tts
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    mp3_bytes = loop.run_until_complete(self.tts.synthesize(sentence, language=lang))
                    loop.close()
                except Exception as synth_err:
                    logger.warning("Sentence %d synthesis error: %s", idx, str(synth_err))
                    mp3_bytes = b""

                if self._stop_requested:
                    break

                if mp3_bytes:
                    # Write to temp MP3 file for pygame playback
                    temp_file = os.path.join(tempfile.gettempdir(), f"campusai_pipe_{idx}_{int(time.time()*1000)}.mp3")
                    with open(temp_file, "wb") as f:
                        f.write(mp3_bytes)
                    audio_queue.put((temp_file, False, sentence))
                else:
                    # Mark sentence for offline pyttsx3 fallback
                    audio_queue.put((None, True, sentence))

            # Sentinel to indicate end of queue
            audio_queue.put(None)

        producer_thread = threading.Thread(target=_producer, daemon=True)
        t_start = time.time()
        ttfa: float = 0.0
        first_audio_recorded = False

        producer_thread.start()

        # 3. Main Consumer Loop for Immediate Sentence Playback
        try:
            while True:
                if self._stop_requested:
                    break

                try:
                    item = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    if not producer_thread.is_alive() and audio_queue.empty():
                        break
                    continue

                if item is None or self._stop_requested:
                    break

                temp_file, is_offline, sentence_text = item

                if not first_audio_recorded:
                    ttfa = time.time() - t_start
                    first_audio_recorded = True

                if is_offline:
                    speak_pyttsx3_fallback(sentence_text)
                else:
                    self._play_mp3_file(temp_file)
                    # Cleanup temp MP3 file
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except OSError:
                            pass

                audio_queue.task_done()

        finally:
            self._is_speaking_flag = False

        return ttfa if ttfa > 0 else (time.time() - t_start)

    def _play_mp3_file(self, file_path: str) -> None:
        """Play a single MP3 file via pygame.mixer and wait until completion."""
        if not file_path or not os.path.exists(file_path):
            return

        try:
            self._init_mixer()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                if self._stop_requested:
                    pygame.mixer.music.stop()
                    break
                pygame.time.Clock().tick(20)

        except Exception as play_err:
            logger.error("Error playing MP3 file '%s': %s", file_path, str(play_err))


# Global Speaker instance singleton
_speaker_instance: Optional[Speaker] = None

def get_speaker() -> Speaker:
    """Get global Speaker instance."""
    global _speaker_instance
    if _speaker_instance is None:
        _speaker_instance = Speaker()
    return _speaker_instance


def speak(text: str, lang: str = "en") -> float:
    """Convenience helper to speak text via global Speaker instance."""
    speaker = get_speaker()
    return speaker.speak(text, lang=lang)


def play_startup_greeting(lang: str = "en") -> None:
    """
    Speak startup welcome greeting ("Hello! Welcome to our college. How can I help you?").
    Caches audio under data/audio_cache/ for instant startup playback.
    """
    speaker = get_speaker()
    greeting_text = get_phrase("greeting", lang=lang)

    print(f"\n[CampusAI Spoken Greeting] > \"{greeting_text}\"\n")
    speaker.speak(greeting_text, lang=lang)
