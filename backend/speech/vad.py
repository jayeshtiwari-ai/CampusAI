"""
backend/speech/vad.py - Voice Activity Detection (VAD) Audio Recorder

Captures audio from laptop microphone using sounddevice and webrtcvad.
Detects speech onset, auto-stops after ~1.0s of silence, enforces 15s max limit,
and ignores noise clips shorter than 0.4s.
"""

import sys
import time
import io
import wave
import numpy as np
import sounddevice as sd
import webrtcvad

from backend.utils.logger import get_logger

logger = get_logger("campusai.speech.vad")


def create_wav_bytes(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Pack raw 16-bit PCM audio bytes into a standard WAV container format."""
    out_buffer = io.BytesIO()
    with wave.open(out_buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit = 2 bytes per sample
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return out_buffer.getvalue()


def record_until_silence(
    sample_rate: int = 16000,
    frame_duration_ms: int = 30,
    silence_duration_sec: float = 1.0,
    max_record_sec: float = 15.0,
    min_audio_sec: float = 0.4
) -> bytes:
    """
    Record audio from microphone until silence is detected via WebRTC VAD.

    Args:
        sample_rate: Audio sampling frequency (16000 Hz recommended).
        frame_duration_ms: Audio chunk duration for VAD evaluation (10, 20, or 30 ms).
        silence_duration_sec: Continuous silence threshold before stopping (default: 1.0s).
        max_record_sec: Hard cutoff maximum recording length (default: 15.0s).
        min_audio_sec: Minimum valid speech duration to return (default: 0.4s).

    Returns:
        WAV audio file bytes or empty bytes if silent/discarded.
    """
    vad = webrtcvad.Vad(mode=3)  # Aggressive mode for speech detection

    frame_bytes = int(sample_rate * (frame_duration_ms / 1000.0) * 2)  # 16-bit mono = 2 bytes/sample
    samples_per_frame = int(sample_rate * (frame_duration_ms / 1000.0))

    silence_frames_needed = int(silence_duration_sec * 1000.0 / frame_duration_ms)
    max_frames = int(max_record_sec * 1000.0 / frame_duration_ms)
    min_frames = int(min_audio_sec * 1000.0 / frame_duration_ms)

    print("\n[VAD] Waiting for speech... Speak into microphone now.")

    speech_detected = False
    consecutive_silence = 0
    recorded_pcm_frames = []

    def audio_callback(indata, frames, time_info, status):
        pass

    try:
        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=samples_per_frame
        )
        stream.start()
        start_time = time.time()

        frame_count = 0
        while frame_count < max_frames:
            pcm_chunk, overflow = stream.read(samples_per_frame)
            raw_bytes = pcm_chunk.tobytes()

            if len(raw_bytes) != frame_bytes:
                continue

            frame_count += 1
            is_speech = vad.is_speech(raw_bytes, sample_rate)

            if is_speech:
                if not speech_detected:
                    speech_detected = True
                    logger.info("Speech onset detected.")
                consecutive_silence = 0
                recorded_pcm_frames.append(raw_bytes)
            else:
                if speech_detected:
                    consecutive_silence += 1
                    recorded_pcm_frames.append(raw_bytes)
                    if consecutive_silence >= silence_frames_needed:
                        logger.info("Silence threshold (%.1fs) reached. Stopping recording.", silence_duration_sec)
                        break

            # Print terminal progress indicator
            if speech_detected:
                recorded_sec = (len(recorded_pcm_frames) * frame_duration_ms) / 1000.0
                bar_len = min(20, int(recorded_sec * 2))
                bar = "█" * bar_len + "░" * (20 - bar_len)
                sys.stdout.write(f"\rListening... [{bar}] {recorded_sec:.1f}s")
                sys.stdout.flush()

        stream.stop()
        stream.close()
        print()  # Newline after indicator

    except Exception as mic_err:
        logger.error("Microphone error during VAD recording: %s", str(mic_err))
        print(f"[!] Microphone error: {mic_err}")
        return b""

    if not speech_detected or len(recorded_pcm_frames) < min_frames:
        logger.info("No valid speech recorded or audio clip too short (< %.1fs).", min_audio_sec)
        print("[!] No speech detected or recording too short.")
        return b""

    full_pcm = b"".join(recorded_pcm_frames)
    wav_bytes = create_wav_bytes(full_pcm, sample_rate=sample_rate, channels=1)
    logger.info("VAD recording complete. Total size: %d bytes (%.2fs)", len(wav_bytes), len(full_pcm)/(sample_rate*2))
    return wav_bytes
