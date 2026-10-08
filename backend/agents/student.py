"""
backend/agents/student.py - Specialized Student Agent

Handles student queries regarding class timetables, exam schedules,
announcements, and library timings.
Includes student verification flag stub for Phase 8 authentication.
"""

from typing import Dict, Any, List, Optional

from backend.database.db import get_timetable, get_exam_schedule, latest_notices
from backend.rag.retriever import get_retriever
from backend.llm.model import GroqLLM
from backend.utils.logger import get_logger

logger = get_logger("campusai.agents.student")


class StudentAgent:
    """Specialized agent for Student academic and schedule queries."""

    def __init__(self) -> None:
        self.retriever = get_retriever()
        self.llm = GroqLLM()

    def handle(self, query: str, language: str = "en", entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle timetable, exam, or notice query."""
        clean_q = query.strip()
        q_lower = clean_q.lower()
        tools_used = []
        sources = []
        db_context = ""

        # 1. Exam schedule lookup
        if any(k in q_lower for k in ["exam", "test", "mid-sem", "paper", "date sheet"]):
            course = entities.get("course", "") if entities else ""
            exams = get_exam_schedule(course)
            if exams:
                tools_used.append("get_exam_schedule")
                sources.append("DB:exams")
                snippets = [f"- Subject: {e['subject']} ({e['course']}) | Date: {e['exam_date']} at {e['start_time']} in {e['room_name']}" for e in exams]
                db_context += "EXAM SCHEDULE RECORDS:\n" + "\n".join(snippets) + "\n\n"

        # 2. Timetable lookup
        elif any(k in q_lower for k in ["timetable", "schedule", "class", "lecture"]):
            class_name = entities.get("course", "B.Tech CSE") if entities else "B.Tech CSE"
            tt = get_timetable(class_name)
            if tt:
                tools_used.append("get_timetable")
                sources.append("DB:timetable")
                snippets = [f"- {t['day']} {t['start_time']}-{t['end_time']}: {t['subject']} ({t['room_name']})" for t in tt]
                db_context += "TIMETABLE RECORDS:\n" + "\n".join(snippets) + "\n\n"

        # 3. Notices lookup
        elif any(k in q_lower for k in ["notice", "announcement", "news"]):
            notices = latest_notices(3)
            if notices:
                tools_used.append("latest_notices")
                sources.append("DB:notices")
                snippets = [f"- [{n['date']}] {n['title']}: {n['body']}" for n in notices]
                db_context += "LATEST NOTICES:\n" + "\n".join(snippets) + "\n\n"

        # 4. Document RAG fallback
        chunks = self.retriever.retrieve(clean_q, top_k=3)
        qualifying = [c for c in chunks if c.get("score", 0.0) >= 0.45]
        for c in qualifying:
            src = c.get("source", "doc")
            if src not in sources:
                sources.append(src)
            db_context += f"DOCUMENT [{src}]:\n{c.get('text')}\n\n"

        if not db_context.strip():
            return {
                "reply": "I don't have verified schedule information for that query.",
                "agent": "student",
                "sources": [],
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
                    "You are the Student Services Specialist at CampusAI.\n"
                    "Provide a brief, clear response in " + language + " (max 3 sentences) based ONLY on context.\n\n"
                    "CONTEXT:\n" + db_context
                )
            },
            {"role": "user", "content": clean_q}
        ]

        try:
            reply = self.llm.chat(messages=prompt, temperature=0.2, max_tokens=300)
            return {
                "reply": reply,
                "agent": "student",
                "sources": sources,
                "tools_used": tools_used,
                "confident": True,
                "needs_human": False,
                "needs_clarification": False,
                "ui_action": "none"
            }
        except Exception:
            return {
                "reply": "I don't have verified schedule information for that.",
                "agent": "student",
                "sources": sources,
                "tools_used": tools_used,
                "confident": False,
                "needs_human": True,
                "needs_clarification": False,
                "ui_action": "none"
            }
