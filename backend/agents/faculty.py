"""
backend/agents/faculty.py - Specialized Faculty & Staff Agent

Handles room/lab/hall availability queries, faculty directory lookups,
and cabin locations using parameterized SQL tool functions.
"""

from typing import Dict, Any, List, Optional

from backend.database.db import room_free_now, find_faculty, find_room
from backend.llm.model import GroqLLM
from backend.utils.logger import get_logger

logger = get_logger("campusai.agents.faculty")


class FacultyAgent:
    """Specialized agent for Faculty and Room Availability queries."""

    def __init__(self) -> None:
        self.llm = GroqLLM()

    def handle(self, query: str, language: str = "en", entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle faculty or room availability query."""
        clean_q = query.strip()
        q_lower = clean_q.lower()
        tools_used = []
        sources = ["DB:rooms", "DB:faculty"]
        db_context = ""

        # 1. Room / Hall Availability Check
        if any(k in q_lower for k in ["free", "empty", "available", "booking", "occupied"]):
            target_room = entities.get("room") if entities else None
            if not target_room:
                # Infer room name from query
                for r_name in ["Seminar Hall A", "Auditorium B", "Lab C-302", "Classroom C-201"]:
                    if r_name.lower() in q_lower or r_name.split()[0].lower() in q_lower:
                        target_room = r_name
                        break
                if not target_room:
                    target_room = "Seminar Hall A"

            status_res = room_free_now(target_room)
            tools_used.append("room_free_now")
            db_context += f"ROOM AVAILABILITY RESULT:\n{status_res['reason']}\n\n"

        # 2. Faculty Directory Search
        elif any(k in q_lower for k in ["dr.", "prof", "hod", "cabin", "email", "phone"]):
            fac_name = entities.get("faculty_name") if entities else clean_q
            fac_list = find_faculty(fac_name)
            if fac_list:
                tools_used.append("find_faculty")
                snippets = [f"- {f['designation']} {f['name']} ({f['department']}): Cabin {f['cabin']}, Email: {f['email']}, Phone: {f['phone']}" for f in fac_list]
                db_context += "FACULTY DIRECTORY RECORDS:\n" + "\n".join(snippets) + "\n\n"

        if not db_context.strip():
            return {
                "reply": "I don't have verified room or faculty information for that request.",
                "agent": "faculty",
                "sources": sources,
                "tools_used": tools_used,
                "confident": False,
                "needs_human": True,
                "needs_clarification": False,
                "ui_action": "none"
            }

        prompt = [
            {
                "role": "system",
                "content": (
                    "You are the Faculty & Staff Support Specialist at CampusAI.\n"
                    "Provide a direct, polite answer in " + language + " (max 3 sentences) using ONLY the context.\n\n"
                    "CONTEXT:\n" + db_context
                )
            },
            {"role": "user", "content": clean_q}
        ]

        try:
            reply = self.llm.chat(messages=prompt, temperature=0.1, max_tokens=250)
            return {
                "reply": reply,
                "agent": "faculty",
                "sources": sources,
                "tools_used": tools_used,
                "confident": True,
                "needs_human": False,
                "needs_clarification": False,
                "ui_action": "none"
            }
        except Exception:
            return {
                "reply": "I don't have verified room or faculty details for that.",
                "agent": "faculty",
                "sources": sources,
                "tools_used": tools_used,
                "confident": False,
                "needs_human": True,
                "needs_clarification": False,
                "ui_action": "none"
            }
