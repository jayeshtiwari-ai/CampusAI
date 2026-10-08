"""
backend/utils/language.py - Multilingual Language Detection Helper

Detects user query language (en, hi, mr, hinglish) based on Unicode script analysis
and Hinglish / Marathi dictionary keyword matching.
"""

import re


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
