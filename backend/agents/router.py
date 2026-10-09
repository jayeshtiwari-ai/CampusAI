"""
backend/agents/router.py - Multi-Agent Intent Classifier & Router

Classifies user queries into:
- User Type: parent, student, faculty, visitor, unknown
- Target Agent: admission, student, faculty, navigation, reception, escalation
- Extracted Entities & Confidence score

Uses Groq LLM in JSON mode with keyword-based fallback logic.
"""

import json
import re
from typing import Dict, Any, Optional

from backend.llm.model import GroqLLM, LLMUnavailable
from backend.utils.language import detect_language
from backend.utils.logger import get_logger

logger = get_logger("campusai.agents.router")


def fallback_keyword_routing(user_query: str) -> Dict[str, Any]:
    """
    Fallback keyword-based routing rules when LLM classification is unavailable.
    """
    q_lower = user_query.lower()
    lang = detect_language(user_query)

    # Escalation / Personal case
    if any(k in q_lower for k in ["mere marks", "my marks", "my score", "mera percentile", "cutoff clear", "मेरे अंक", "मेरे मार्क्स"]):
        return {
            "intent": "personal_case_escalation",
            "user_type": "visitor",
            "agent": "escalation",
            "language": lang,
            "entities": {},
            "confidence": 0.95
        }

    # Navigation keywords
    if any(k in q_lower for k in ["where is", "kahan", "kaise jayein", "directions", "location", "path", "map", "room", "hall", "lab", "कहाँ", "कहां", "किधर", "मार्ग", "दिशा", "इमारत", "मजला", "कुठे"]):
        return {
            "intent": "navigation_inquiry",
            "user_type": "visitor",
            "agent": "navigation",
            "language": lang,
            "entities": {},
            "confidence": 0.85
        }

    # Admission & Fee keywords
    if any(k in q_lower for k in ["fee", "fees", "tuition", "admission", "dakhila", "eligibility", "documents", "cutoff", "scholarship", "प्रवेश", "फीस", "शुल्क", "पात्रता", "दाखिला", "छात्रवृत्ति"]):
        return {
            "intent": "admission_fee_inquiry",
            "user_type": "parent" if any(k in q_lower for k in ["fees", "fee", "फीस", "शुल्क"]) else "visitor",
            "agent": "admission",
            "language": lang,
            "entities": {},
            "confidence": 0.85
        }

    # Faculty & Room Booking keywords
    if any(k in q_lower for k in ["hod", "professor", "dr.", "cabin", "room free", "hall free", "meeting", "प्राध्यापक", "प्रोफेसर", "केबिन", "विभाग प्रमुख"]):
        return {
            "intent": "faculty_room_inquiry",
            "user_type": "faculty",
            "agent": "faculty",
            "language": lang,
            "entities": {},
            "confidence": 0.85
        }

    # Student Timetable / Exam keywords
    if any(k in q_lower for k in ["timetable", "exam", "schedule", "test", "class", "lecture", "hall ticket", "समयसारणी", "टाइमटेबल", "परीक्षा", "क्लास"]):
        return {
            "intent": "student_schedule_inquiry",
            "user_type": "student",
            "agent": "student",
            "language": lang,
            "entities": {},
            "confidence": 0.85
        }

    # General Reception default
    return {
        "intent": "general_reception",
        "user_type": "visitor",
        "agent": "reception",
        "language": lang,
        "entities": {},
        "confidence": 0.70
    }


class RouterAgent:
    """Agent responsible for classifying intent and routing queries to specialized agents."""

    def __init__(self) -> None:
        self.llm = GroqLLM()

    def route_query(self, user_query: str, session_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify user query and return routing decision dictionary.

        Returns:
            Dictionary: {intent, user_type, agent, language, entities, confidence}
        """
        clean_query = user_query.strip()
        detected_lang = detect_language(clean_query)

        system_prompt = (
            "You are the Intelligent Router for CampusAI College Reception System.\n"
            "Classify the incoming user query and return JSON ONLY.\n\n"
            "TARGET AGENT OPTIONS:\n"
            "- 'admission' : Fees, course eligibility, application dates, documents, scholarships.\n"
            "- 'student'   : Class timetable, exam schedule, notices, library.\n"
            "- 'faculty'   : Faculty cabins, room/lab/hall availability, faculty contacts.\n"
            "- 'navigation': Directions, building location, finding rooms or halls.\n"
            "- 'reception' : General greetings, general college queries.\n"
            "- 'escalation': Personal marks evaluation, complaint, or sensitive cases.\n\n"
            "USER TYPE OPTIONS: 'parent', 'student', 'faculty', 'visitor', 'unknown'\n\n"
            'OUTPUT STRICT JSON SCHEMA:\n'
            '{\n'
            '  "intent": "string",\n'
            '  "user_type": "string",\n'
            '  "agent": "admission|student|faculty|navigation|reception|escalation",\n'
            '  "language": "' + detected_lang + '",\n'
            '  "entities": {"course": null, "room": null, "faculty_name": null},\n'
            '  "confidence": 0.95\n'
            '}'
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Query: {clean_query}"}
        ]

        try:
            raw_res = self.llm.chat(messages=messages, temperature=0.1, json_mode=True, max_tokens=300)
            res_json = json.loads(raw_res)

            # Ensure valid agent string
            valid_agents = {"admission", "student", "faculty", "navigation", "reception", "escalation"}
            if res_json.get("agent") not in valid_agents:
                res_json["agent"] = "reception"

            res_json["language"] = detected_lang
            logger.info("Router Decision -> Agent: '%s' | UserType: '%s' | Intent: '%s'",
                        res_json.get("agent"), res_json.get("user_type"), res_json.get("intent"))
            return res_json

        except (LLMUnavailable, json.JSONDecodeError, Exception) as err:
            logger.warning("Router LLM failed: %s. Using keyword fallback.", str(err))
            fallback_res = fallback_keyword_routing(clean_query)
            return fallback_res


# Global Router instance helper
_router_instance: Optional[RouterAgent] = None

def get_router() -> RouterAgent:
    """Get global cached RouterAgent instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = RouterAgent()
    return _router_instance
