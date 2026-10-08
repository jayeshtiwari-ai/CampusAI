"""
backend/config.py - Configuration management for CampusAI.

Loads configuration settings from environment variables and .env file.
Validates critical environment variables such as GROQ_API_KEY.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Initialize logging
logger = logging.getLogger("campusai.config")

# Project Root Directory (CampusAI/)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Load environment variables from .env file at project root if present
ENV_PATH: Path = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
    logger.info("Loaded configuration from %s", ENV_PATH)
else:
    load_dotenv()
    logger.info("No explicit .env file found at %s; relying on environment variables.", ENV_PATH)


class Settings:
    """Application Settings dataclass with environment fallbacks and validation."""

    def __init__(self) -> None:
        # LLM & STT settings (Groq)
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
        self.GROQ_LLM_MODEL: str = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile").strip()
        self.GROQ_STT_MODEL: str = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo").strip()

        # Vector RAG Embeddings & Search parameters
        self.EMBED_MODEL: str = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small").strip()
        self.RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
        self.RAG_MIN_SCORE: float = float(os.getenv("RAG_MIN_SCORE", "0.5"))

        # Telegram Escalation Notifications
        self.TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()

        # College Metadata & Server Network Settings
        self.COLLEGE_NAME: str = os.getenv("COLLEGE_NAME", "CampusAI Engineering College").strip()
        self.HOST: str = os.getenv("HOST", "0.0.0.0").strip()
        self.PORT: int = int(os.getenv("PORT", "8000"))

        # TTS Voices
        self.VOICE_EN: str = os.getenv("VOICE_EN", "en-IN-NeerjaNeural").strip()
        self.VOICE_HI: str = os.getenv("VOICE_HI", "hi-IN-SwaraNeural").strip()
        self.VOICE_HINGLISH: str = os.getenv("VOICE_HINGLISH", "hi-IN-SwaraNeural").strip()
        self.VOICE_MR: str = os.getenv("VOICE_MR", "mr-IN-AarohiNeural").strip()

        # Core Directory Paths
        self.BASE_DIR: Path = BASE_DIR
        self.KNOWLEDGE_BASE_DIR: Path = BASE_DIR / "knowledge_base"
        self.DATABASE_DIR: Path = BASE_DIR / "backend" / "database"
        self.KIOSK_UI_DIR: Path = BASE_DIR / "kiosk_ui"

    def validate(self, require_groq_key: bool = True) -> None:
        """
        Validate critical environment variables.
        
        Args:
            require_groq_key: If True, raises ValueError if GROQ_API_KEY is unset or default placeholder.
        """
        invalid_placeholders = ["", "gsk_your_groq_api_key_here", "YOUR_GROQ_API_KEY"]
        if require_groq_key and (not self.GROQ_API_KEY or self.GROQ_API_KEY in invalid_placeholders):
            error_msg = (
                "\n"
                "========================================================================\n"
                "[ERROR] GROQ_API_KEY is missing or invalid in your environment / .env file!\n"
                "Please get a free Groq API key from https://console.groq.com and set:\n"
                "  GROQ_API_KEY=gsk_your_actual_key_here\n"
                "in your CampusAI/.env file.\n"
                "========================================================================"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Configuration validated successfully for college: %s", self.COLLEGE_NAME)


# Global settings singleton instance
settings = Settings()
