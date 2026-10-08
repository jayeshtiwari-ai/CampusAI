"""
setup_project.py - CampusAI Directory Structure Generator

Creates the full project directory tree and empty __init__.py files
for the CampusAI college reception AI robot project.
"""

import logging
from pathlib import Path
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("setup_project")

# Root directory of CampusAI project
ROOT_DIR = Path(__file__).resolve().parent

# Directory tree specification
DIRECTORIES: List[Path] = [
    ROOT_DIR / "backend",
    ROOT_DIR / "backend" / "api",
    ROOT_DIR / "backend" / "agents",
    ROOT_DIR / "backend" / "rag",
    ROOT_DIR / "backend" / "speech",
    ROOT_DIR / "backend" / "llm",
    ROOT_DIR / "backend" / "database",
    ROOT_DIR / "backend" / "utils",
    ROOT_DIR / "knowledge_base" / "admission",
    ROOT_DIR / "knowledge_base" / "academics",
    ROOT_DIR / "knowledge_base" / "departments",
    ROOT_DIR / "knowledge_base" / "notices",
    ROOT_DIR / "knowledge_base" / "facilities",
    ROOT_DIR / "kiosk_ui",
    ROOT_DIR / "dashboard",
    ROOT_DIR / "robot" / "esp32",
    ROOT_DIR / "tests",
]

# Python package directories requiring __init__.py files
INIT_PACKAGE_DIRS: List[Path] = [
    ROOT_DIR / "backend",
    ROOT_DIR / "backend" / "api",
    ROOT_DIR / "backend" / "agents",
    ROOT_DIR / "backend" / "rag",
    ROOT_DIR / "backend" / "speech",
    ROOT_DIR / "backend" / "llm",
    ROOT_DIR / "backend" / "database",
    ROOT_DIR / "backend" / "utils",
    ROOT_DIR / "tests",
]

# Placeholder files to ensure initial structure completeness
PLACEHOLDER_FILES: List[Path] = [
    ROOT_DIR / "backend" / "api" / "chat.py",
    ROOT_DIR / "backend" / "api" / "voice.py",
    ROOT_DIR / "backend" / "api" / "robot.py",
    ROOT_DIR / "backend" / "api" / "escalation.py",
    ROOT_DIR / "backend" / "api" / "admin.py",
    ROOT_DIR / "backend" / "agents" / "router.py",
    ROOT_DIR / "backend" / "agents" / "receptionist.py",
    ROOT_DIR / "backend" / "agents" / "admission.py",
    ROOT_DIR / "backend" / "agents" / "student.py",
    ROOT_DIR / "backend" / "agents" / "faculty.py",
    ROOT_DIR / "backend" / "agents" / "navigation.py",
    ROOT_DIR / "backend" / "agents" / "escalation.py",
    ROOT_DIR / "backend" / "rag" / "loader.py",
    ROOT_DIR / "backend" / "rag" / "embeddings.py",
    ROOT_DIR / "backend" / "rag" / "retriever.py",
    ROOT_DIR / "backend" / "rag" / "ingest.py",
    ROOT_DIR / "backend" / "speech" / "stt.py",
    ROOT_DIR / "backend" / "speech" / "tts.py",
    ROOT_DIR / "backend" / "speech" / "vad.py",
    ROOT_DIR / "backend" / "llm" / "model.py",
    ROOT_DIR / "backend" / "llm" / "prompts.py",
    ROOT_DIR / "backend" / "database" / "db.py",
    ROOT_DIR / "backend" / "database" / "schema.sql",
    ROOT_DIR / "backend" / "database" / "seed.py",
    ROOT_DIR / "backend" / "utils" / "logger.py",
    ROOT_DIR / "backend" / "utils" / "fallback.py",
]


def create_structure() -> None:
    """Create all required directories, package __init__.py files, and module placeholders."""
    logger.info("Initializing CampusAI folder structure under: %s", ROOT_DIR)
    
    # Create directories
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info("Directory created/verified: %s", directory.relative_to(ROOT_DIR))

    # Create __init__.py files in Python package directories
    for package_dir in INIT_PACKAGE_DIRS:
        init_file = package_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            logger.info("Created __init__.py in: %s", package_dir.relative_to(ROOT_DIR))

    # Create empty module placeholders if they don't exist
    for file_path in PLACEHOLDER_FILES:
        if not file_path.exists():
            file_path.touch()
            logger.info("Created module placeholder: %s", file_path.relative_to(ROOT_DIR))

    logger.info("CampusAI project setup completed successfully.")


if __name__ == "__main__":
    create_structure()
