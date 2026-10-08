"""
check_setup.py - CampusAI Environment Verification Script

Verifies:
1. Python version (3.11 recommended)
2. All required third-party Python packages
3. ffmpeg installation in PATH
4. Groq API Key connectivity and response test
5. Audio input/output devices (microphones/speakers)
"""

import sys
import shutil
import logging
import time
from typing import List, Tuple, Dict, Any

# Ensure stdout handles UTF-8 encoding safely on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("check_setup")


# Safe ASCII / Unicode printable status tags
TAG_OK = "[OK]"
TAG_WARN = "[WARN]"
TAG_FAIL = "[FAIL]"


def print_header(title: str) -> None:
    """Print formatted section header."""
    print(f"\n--- {title} ---")


def check_python_version() -> bool:
    """Check if running Python version meets requirements."""
    print_header("1. Checking Python Version")
    major, minor, micro = sys.version_info[:3]
    version_str = f"{major}.{minor}.{micro}"
    logger.info("Detected Python version: %s", version_str)

    if major == 3 and minor == 11:
        print(f"{TAG_OK} Python version {version_str} (Target 3.11 matched)")
        return True
    elif major == 3 and minor >= 10:
        print(f"{TAG_WARN} Python version {version_str} (Recommended: 3.11, Compatible: >=3.10)")
        return True
    else:
        print(f"{TAG_FAIL} Python version {version_str} is incompatible. Please use Python 3.11.")
        return False


def check_package_imports() -> bool:
    """Check if all required dependencies can be imported successfully."""
    print_header("2. Verifying Required Packages")
    required_modules = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("multipart", "python-multipart"),
        ("dotenv", "python-dotenv"),
        ("pydantic", "Pydantic"),
        ("groq", "Groq Client"),
        ("sentence_transformers", "Sentence-Transformers"),
        ("faiss", "FAISS Vector DB"),
        ("pypdf", "PyPDF"),
        ("docx", "python-docx"),
        ("edge_tts", "Edge TTS"),
        ("sounddevice", "SoundDevice"),
        ("numpy", "NumPy"),
        ("webrtcvad", "WebRTC VAD"),
        ("pydub", "PyDub"),
        ("qrcode", "QRCode"),
        ("requests", "Requests"),
        ("websockets", "WebSockets"),
        ("pytest", "PyTest"),
    ]

    all_passed = True
    for module_name, display_name in required_modules:
        try:
            __import__(module_name)
            print(f"{TAG_OK} {display_name:<25} ({module_name})")
        except ImportError as e:
            print(f"{TAG_FAIL} {display_name:<25} FAILED to import: {e}")
            all_passed = False

    return all_passed


def check_ffmpeg() -> bool:
    """Verify that ffmpeg binary is installed and present in system PATH."""
    print_header("3. Checking ffmpeg Binary")
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"{TAG_OK} ffmpeg found in PATH: {ffmpeg_path}")
        return True
    else:
        print(f"{TAG_FAIL} ffmpeg was NOT found in system PATH!")
        print("    Please install ffmpeg and add its 'bin' directory to system environment PATH.")
        return False


def check_groq_api() -> bool:
    """Perform a live test call against Groq API with exponential backoff retry."""
    print_header("4. Testing Groq API Key & LLM Connectivity")
    try:
        from backend.config import settings
        try:
            settings.validate(require_groq_key=True)
        except ValueError as val_err:
            print(f"{TAG_FAIL} Groq Key Configuration Error:\n{val_err}")
            return False

        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        model_name = settings.GROQ_LLM_MODEL
        
        logger.info("Initiating Groq LLM ping with model: %s", model_name)

        max_retries = 3
        backoff_sec = 2.0
        
        for attempt in range(1, max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are CampusAI reception system test script."},
                        {"role": "user", "content": "Respond with 'CampusAI Online'"}
                    ],
                    max_tokens=20,
                    temperature=0.1,
                )
                reply = response.choices[0].message.content.strip()
                print(f"{TAG_OK} Groq API call succeeded!")
                print(f"    Model: {model_name}")
                print(f"    Response: \"{reply}\"")
                return True
            except Exception as req_err:
                logger.warning("Groq API call attempt %d failed: %s", attempt, req_err)
                if attempt < max_retries:
                    print(f"{TAG_WARN} Groq rate limit / network error. Retrying in {backoff_sec} seconds...")
                    time.sleep(backoff_sec)
                    backoff_sec *= 2.0
                else:
                    print(f"{TAG_FAIL} Groq API call failed after {max_retries} attempts: {req_err}")
                    return False

    except Exception as outer_err:
        print(f"{TAG_FAIL} Unexpected error checking Groq API: {outer_err}")
        return False


def check_audio_devices() -> bool:
    """Query and list available microphone and speaker hardware devices."""
    print_header("5. Listing Audio Input/Output Devices")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        if not devices:
            print(f"{TAG_WARN} No audio devices found on this system.")
            return False

        print(f"Total audio devices detected: {len(devices)}")
        input_count = 0
        output_count = 0

        for idx, dev in enumerate(devices):
            max_in = dev.get("max_input_channels", 0)
            max_out = dev.get("max_output_channels", 0)
            name = dev.get("name", "Unknown")
            sample_rate = dev.get("default_samplerate", 44100)

            dev_type = []
            if max_in > 0:
                dev_type.append(f"IN: {max_in} ch")
                input_count += 1
            if max_out > 0:
                dev_type.append(f"OUT: {max_out} ch")
                output_count += 1

            type_str = ", ".join(dev_type) if dev_type else "No Channels"
            print(f"  [{idx}] {name} ({type_str}, {int(sample_rate)} Hz)")

        print(f"{TAG_OK} Audio subsystem verified (Inputs: {input_count}, Outputs: {output_count})")
        return True

    except Exception as e:
        print(f"{TAG_FAIL} Audio device listing failed: {e}")
        return False


def main() -> None:
    """Run full setup verification checklist."""
    print("==========================================================")
    print("            CampusAI Setup Verification Checklist         ")
    print("==========================================================")

    results: Dict[str, bool] = {
        "Python Version": check_python_version(),
        "Package Imports": check_package_imports(),
        "ffmpeg Binary": check_ffmpeg(),
        "Groq API Test": check_groq_api(),
        "Audio Devices": check_audio_devices(),
    }

    print("\n==========================================================")
    print("                    Verification Summary                  ")
    print("==========================================================")

    all_passed = True
    for item, passed in results.items():
        status = f"{TAG_OK} PASSED" if passed else f"{TAG_FAIL} FAILED"
        print(f"  {item:<25}: {status}")
        if not passed:
            all_passed = False

    print("==========================================================")
    if all_passed:
        print(" SUCCESS: CampusAI development environment is fully operational!")
    else:
        print(" ATTENTION: Some setup checks failed. Please fix the marked items.")
    print("==========================================================\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
