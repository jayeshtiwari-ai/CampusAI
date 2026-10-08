"""
backend/agents/navigation.py - Specialized Navigation & Campus Directions Agent

Retrieves building locations and step-by-step directions using get_directions tool.
Returns structured output with steps[], map_id, qr_payload, and ui_action='show_map'.
"""

from typing import Dict, Any, Optional

from backend.database.db import get_directions, find_room
from backend.utils.logger import get_logger

logger = get_logger("campusai.agents.navigation")


class NavigationAgent:
    """Specialized agent for Campus Navigation and Location Guidance."""

    def handle(self, query: str, language: str = "en", entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle campus location or directions query."""
        clean_q = query.strip()
        q_lower = clean_q.lower()

        # Infer target destination name from entities or string search
        place_name = entities.get("room") if entities else None
        if not place_name:
            for candidate in ["Seminar Hall A", "Auditorium B", "Lab C-302", "Lab C-304", "Classroom C-201", "Principal Office", "Admissions Desk"]:
                if candidate.lower() in q_lower or candidate.split()[0].lower() in q_lower:
                    place_name = candidate
                    break

        if not place_name:
            # Fallback default place search if keyword matches room type
            if "hall" in q_lower:
                place_name = "Seminar Hall A"
            elif "auditorium" in q_lower:
                place_name = "Auditorium B"
            elif "lab" in q_lower or "computer" in q_lower:
                place_name = "Lab C-302 (AI Lab)"
            elif "principal" in q_lower or "office" in q_lower:
                place_name = "Principal Office"
            else:
                place_name = "Seminar Hall A"

        nav_data = get_directions(place_name)

        if not nav_data:
            return {
                "reply": "I could not find navigation directions for that location.",
                "agent": "navigation",
                "sources": [],
                "tools_used": ["get_directions"],
                "confident": False,
                "needs_human": True,
                "needs_clarification": False,
                "ui_action": "none",
                "data": {}
            }

        # Formulate reply text in user's language
        steps_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(nav_data["steps"])])
        
        if language in ["hi", "mr"]:
            reply_text = f"दिशा-निर्देश ({nav_data['place']}):\n{steps_str}"
        elif language == "hinglish":
            reply_text = f"Directions for {nav_data['place']}:\n{steps_str}\nAap kiosk screen par QR code scan karke map load kar sakte hain."
        else:
            reply_text = f"Directions to {nav_data['place']} ({nav_data['building']}, Floor {nav_data['floor']}):\n{steps_str}"

        return {
            "reply": reply_text,
            "agent": "navigation",
            "sources": ["DB:rooms"],
            "tools_used": ["get_directions"],
            "confident": True,
            "needs_human": False,
            "needs_clarification": False,
            "ui_action": "show_map",
            "data": nav_data
        }
