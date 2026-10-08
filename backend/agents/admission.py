"""
backend/agents/admission.py - Specialized Admission Agent

Handles parent and visitor inquiries regarding course fees, eligibility,
admission deadlines, required documents, and scholarships.
Combines SQL tool queries with RAG document retrieval.
"""

from typing import Dict, Any, List, Optional

from backend.database.db import get_course_fees, get_admission_dates, latest_notices
from backend.rag.retriever import get_retriever
from backend.llm.model import GroqLLM, LLMUnavailable
from backend.utils.logger import get_logger

logger = get_logger("campusai.agents.admission")


class AdmissionAgent:
    """Specialized agent for Admission and Fee queries."""

    def __init__(self) -> None:
        self.retriever = get_retriever()
        self.llm = GroqLLM()

    def handle(self, query: str, language: str = "en", entities: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle admission or fee query using DB tool lookups and RAG document grounding.
        """
        clean_q = query.strip()
        tools_used = []
        sources = []
        db_context = ""

        # 1. Check SQL Database for Course Fees if fee keyword is present
        if any(k in clean_q.lower() for k in ["fee", "fees", "tuition", "cost", "kitni"]):
            course_name = entities.get("course") if entities else None
            fee_rows = get_course_fees(course_name)
            if fee_rows:
                tools_used.append("get_course_fees")
                sources.append("DB:fees")
                fee_snippets = [
                    f"- Course: {r['course_name']} ({r['code']}) | Total Fee: INR {r['total_fee']:,.2f}/year (Tuition: INR {r['tuition_fee']:,.2f})"
                    for r in fee_rows
                ]
                db_context += "STRUCTURED FEE DATABASE RECORDS:\n" + "\n".join(fee_snippets) + "\n\n"

        # 2. Check RAG Document Store
        chunks = self.retriever.retrieve(clean_q, top_k=3)
        qualifying_chunks = [c for c in chunks if c.get("score", 0.0) >= 0.45]

        for c in qualifying_chunks:
            src = c.get("source", "doc")
            if src not in sources:
                sources.append(src)
            db_context += f"DOCUMENT [{src}]:\n{c.get('text')}\n\n"

        # If neither DB nor RAG found data, refuse strictly
        if not db_context.strip():
            refusal_text = (
                "Mere paas iski verified jankari nahi hai. Kripya main office se contact karein."
                if language == "hinglish"
                else "I don't have verified information for that admission detail."
            )
            return {
                "reply": refusal_text,
                "agent": "admission",
                "sources": [],
                "tools_used": tools_used,
                "confident": False,
                "needs_human": True,
                "needs_clarification": False,
                "ui_action": "none"
            }

        # Synthesize answer using LLM
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are the Admission & Fees Specialist at CampusAI Engineering College.\n"
                    "Provide a brief, clear, and polite answer (max 3 sentences) in the user's language (" + language + ").\n"
                    "Base your answer ONLY on the provided context.\n\n"
                    "CONTEXT:\n" + db_context
                )
            },
            {"role": "user", "content": clean_q}
        ]

        try:
            reply = self.llm.chat(messages=prompt, temperature=0.3, max_tokens=300)
            return {
                "reply": reply,
                "agent": "admission",
                "sources": sources,
                "tools_used": tools_used,
                "confident": True,
                "needs_human": False,
                "needs_clarification": False,
                "ui_action": "none"
            }
        except Exception as err:
            logger.error("AdmissionAgent LLM error: %s", str(err))
            return {
                "reply": "I don't have verified information for that.",
                "agent": "admission",
                "sources": sources,
                "tools_used": tools_used,
                "confident": False,
                "needs_human": True,
                "needs_clarification": False,
                "ui_action": "none"
            }
