"""
backend/utils/phrases.py - CampusAI Standard Spoken Phrases & Latency Hiding Fillers

Contains localized pre-defined phrases (EN, HI, MR, Hinglish) for:
- Initial greeting on startup
- Clarification when audio is quiet/unclear ("did_not_catch")
- Out of Knowledge Base refusal ("no_info")
- Handoff / Department connection ("connect_dept")
- Goodbye greetings ("goodbye")
- Offline operation warning ("offline_mode")
- Long response truncation tail ("long_answer_tail")
- Random filler phrases to hide system latency without repeating back-to-back
"""

import os
import random
from pathlib import Path
from typing import Dict, List, Optional

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("campusai.utils.phrases")

AUDIO_CACHE_DIR: Path = settings.BASE_DIR / "data" / "audio_cache"

# Standard system phrases across supported languages
PHRASES: Dict[str, Dict[str, str]] = {
    "greeting": {
        "en": "Hello! Welcome to our college. How can I help you?",
        "hi": "नमस्कार! हमारे कॉलेज में आपका स्वागत है। मैं आपकी क्या मदद कर सकता हूँ?",
        "hinglish": "Hello! Humare college mein aapka swagat hai. Main aapki kya help kar sakta hoon?",
        "mr": "नमस्कार! आमच्या कॉलेजमध्ये आपले स्वागत आहे. मी तुम्हाला कशी मदत करू शकेन?",
    },
    "did_not_catch": {
        "en": "Sorry, I did not catch that. Please speak again.",
        "hi": "माफ़ कीजिये, मैं समझ नहीं पाया। कृपया फिर से बोलिये।",
        "hinglish": "Sorry, main samajh nahi paya. Kripya fir se boliye.",
        "mr": "माफ करा, मला ते ऐकू आले नाही. कृपया पुन्हा बोला.",
    },
    "no_info": {
        "en": "I don't have verified information for that right now.",
        "hi": "मेरे पास इसके लिए अभी सत्यापित जानकारी नहीं है।",
        "hinglish": "Mere paas iski abhi verified jankari nahi hai.",
        "mr": "माझ्याकडे यासाठी सध्या पडताळलेली माहिती नाही.",
    },
    "connect_dept": {
        "en": "Would you like me to connect you with the concerned department?",
        "hi": "क्या आप चाहेंगे कि मैं आपको संबंधित विभाग से जोड़ूँ?",
        "hinglish": "Kya aap chahenge ki main aapko department se connect karoon?",
        "mr": "तुम्हाला मी संबंधित विभागाशी जोडलेले आवडेल का?",
    },
    "goodbye": {
        "en": "Goodbye! Have a great day.",
        "hi": "धन्यवाद! आपका दिन शुभ हो।",
        "hinglish": "Thank you! Aapka din accha rahe. Goodbye!",
        "mr": "धन्यवाद! आपका दिवस चांगला जावो.",
    },
    "offline_mode": {
        "en": "I am operating in offline mode right now.",
        "hi": "मैं अभी ऑफ़लाइन मोड में काम कर रहा हूँ।",
        "hinglish": "Main abhi offline mode mein kaam kar raha hoon.",
        "mr": "मी आता ऑफलाइन मोडमध्ये काम करत आहे.",
    },
    "long_answer_tail": {
        "en": "I can send the rest to your phone.",
        "hi": "बाकी की जानकारी मैं आपके फोन पर भेज सकता हूँ।",
        "hinglish": "Baki details main aapke phone par bheja sakta hoon.",
        "mr": "मी उर्वरित माहिती तुमच्या फोनवर पाठवू शकतो.",
    }
}

# Latency hiding filler phrases by language
FILLERS: Dict[str, List[str]] = {
    "en": [
        "Sure, let me check that for you.",
        "Give me a second to find that information.",
        "Looking up the college records now.",
        "Let me verify that detail."
    ],
    "hi": [
        "एक मिनट, मैं चेक करता हूँ।",
        "जी, मैं जानकारी खोज रहा हूँ।",
        "बस एक पल रुकिए, मैं रिकॉर्ड्स देख रहा हूँ।",
        "ज़रूर, मैं अभी पता लगाता हूँ।"
    ],
    "hinglish": [
        "Ek minute, main check karta hoon.",
        "Sure, main jankari nikal raha hoon.",
        "Bas ek second, details dekh raha hoon.",
        "Ha, main check karke batata hoon."
    ],
    "mr": [
        "एक मिनिट, मी तपासतो.",
        "मी माहिती शोधत आहे.",
        "कृपया एक क्षण थांबा, मी रेकॉर्ड पाहत आहे.",
        "होय, मी लगेच माहिती काढतो."
    ]
}

# Track last used filler per language to prevent consecutive duplicates
_last_filler_indices: Dict[str, int] = {}


def get_phrase(phrase_key: str, lang: str = "en", department: Optional[str] = None) -> str:
    """
    Retrieve standard spoken phrase text for a given key and language.

    Args:
        phrase_key: Key name (e.g. 'greeting', 'did_not_catch', 'no_info', 'connect_dept', 'goodbye', 'offline_mode').
        lang: Target language code ('en', 'hi', 'hinglish', 'mr').
        department: Optional department name to populate 'connect_dept'.

    Returns:
        Formatted phrase string.
    """
    lang_code = (lang or "en").lower().strip()
    if lang_code not in ["en", "hi", "hinglish", "mr"]:
        lang_code = "en"

    phrase_entry = PHRASES.get(phrase_key, {})
    text = phrase_entry.get(lang_code, phrase_entry.get("en", ""))

    if phrase_key == "connect_dept" and department:
        if lang_code == "hi":
            text = f"क्या आप चाहेंगे कि मैं आपको {department} विभाग से जोड़ूँ?"
        elif lang_code == "hinglish":
            text = f"Kya aap chahenge ki main aapko {department} department se connect karoon?"
        elif lang_code == "mr":
            text = f"तुम्हाला मी {department} विभागाशी जोडलेले आवडेल का?"
        else:
            text = f"Would you like me to connect you with the {department} department?"

    return text


def get_random_filler(lang: str = "en") -> str:
    """
    Get a random latency-hiding filler phrase for the given language.
    Guarantees that the same filler phrase is never picked twice in a row.

    Args:
        lang: Target language code.

    Returns:
        Filler phrase string.
    """
    lang_code = (lang or "en").lower().strip()
    if lang_code not in FILLERS:
        lang_code = "en"

    options = FILLERS[lang_code]
    last_idx = _last_filler_indices.get(lang_code, -1)

    valid_indices = [i for i in range(len(options)) if i != last_idx]
    chosen_idx = random.choice(valid_indices)

    _last_filler_indices[lang_code] = chosen_idx
    return options[chosen_idx]


def precache_all_phrases() -> None:
    """Pre-synthesize and store static standard phrases as cached MP3 files."""
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Audio cache directory initialized at: %s", str(AUDIO_CACHE_DIR))
