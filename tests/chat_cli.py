"""
tests/chat_cli.py - Terminal Chat Client for CampusAI

Interactive terminal CLI to chat with the CampusAI receptionist backend.
Supports commands: /reset, /quit, /exit.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uuid
import requests
from typing import Optional

BASE_URL = "http://127.0.0.1:8000"


def print_banner() -> None:
    """Print CLI welcome banner."""
    print("==================================================================")
    print("               CampusAI Receptionist CLI Client                   ")
    print("==================================================================")
    print("Commands:")
    print("  /reset  - Clear session history")
    print("  /quit   - Exit the chat CLI")
    print("  /exit   - Exit the chat CLI")
    print("==================================================================\n")


def check_health() -> bool:
    """Verify backend server health."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            print(f"[✓] Connected to CampusAI Backend ({data.get('college')})")
            print(f"    Model: {data.get('model')}")
            print(f"    Uptime: {data.get('uptime_seconds')}s\n")
            return True
        else:
            print(f"[✗] Server returned status code {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print(f"[✗] Could not connect to CampusAI backend at {BASE_URL}.")
        print("    Ensure the uvicorn server is running: uvicorn backend.main:app --reload\n")
        return False


def reset_session(session_id: str) -> None:
    """Send reset session request to backend."""
    try:
        res = requests.post(f"{BASE_URL}/chat/reset", json={"session_id": session_id}, timeout=5.0)
        if res.status_code == 200:
            print(f"\n[System] Session history reset successfully for ID: {session_id}\n")
        else:
            print(f"\n[System] Reset failed with status code {res.status_code}\n")
    except Exception as e:
        print(f"\n[System] Failed to send reset request: {e}\n")


def chat_loop() -> None:
    """Main CLI chat loop."""
    print_banner()
    if not check_health():
        sys.exit(1)

    session_id = str(uuid.uuid4())
    print(f"Active Session ID: {session_id}\n")

    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["/quit", "/exit"]:
                print("Exiting CampusAI Chat CLI. Goodbye!")
                break

            if user_input.lower() == "/reset":
                reset_session(session_id)
                session_id = str(uuid.uuid4())
                print(f"New Session ID: {session_id}\n")
                continue

            # Send chat request
            payload = {
                "session_id": session_id,
                "message": user_input
            }
            response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=20.0)

            if response.status_code == 200:
                data = response.json()
                reply = data.get("reply", "")
                lang = data.get("language_detected", "unknown")
                print(f"\nCampusAI ({lang}) > {reply}\n")
            else:
                print(f"\n[Error] Server returned status code {response.status_code}: {response.text}\n")

        except KeyboardInterrupt:
            print("\nExiting CLI...")
            break
        except Exception as err:
            print(f"\n[Error] Failed to communicate with server: {err}\n")


if __name__ == "__main__":
    chat_loop()
