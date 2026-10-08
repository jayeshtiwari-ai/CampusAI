"""
backend/agents/__init__.py - CampusAI Multi-Agent Orchestrator

Routes visitor queries via RouterAgent to specialized domain agents (Admission, Student,
Faculty, Navigation, Receptionist, Escalation), maintains session topic memory for follow-ups,
and strictly validates tool outputs to prevent hallucinations.
"""

from typing import Dict, Any, Optional

from backend.agents.router import get_router
from backend.agents.admission import AdmissionAgent
from backend.agents.student import StudentAgent
from backend.agents.faculty import FacultyAgent
from backend.agents.navigation import NavigationAgent
from backend.agents.receptionist import ReceptionistAgent
from backend.utils.logger import get_logger

logger = get_logger("campusai.agents.orchestrator")

# In-Memory Session Topic Tracking for Follow-Up Context (session_id -> last_topic_meta)
session_topic_memory: Dict[str, Dict[str, Any]] = {}


class MultiAgentOrchestrator:
    """Master Orchestrator class managing intent routing and specialized agent execution."""

    def __init__(self) -> None:
        self.router = get_router()
        self.admission_agent = AdmissionAgent()
        self.student_agent = StudentAgent()
        self.faculty_agent = FacultyAgent()
        self.navigation_agent = NavigationAgent()
        self.receptionist_agent = ReceptionistAgent()

    def handle_query(
        self,
        user_query: str,
        session_id: str,
        language: Optional[str] = None,
        user_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate complete query flow:
        Route -> Select Agent -> Execute -> Validate Output -> Return Standardized Result.
        """
        clean_q = user_query.strip()
        q_lower = clean_q.lower()

        # Handle follow-up context (e.g. "and its fees?", "where is that room?")
        previous_context = session_topic_memory.get(session_id, {})
        if previous_context and any(f_word in q_lower for f_word in ["and its", "uske", "iska", "vahan", "there"]):
            logger.info("Detected follow-up question. Reusing previous topic agent: '%s'", previous_context.get("agent"))
            routing_decision = previous_context
        else:
            # Route query via RouterAgent
            routing_decision = self.router.route_query(clean_q)

        target_agent = routing_decision.get("agent", "reception")
        detected_lang = language or routing_decision.get("language", "en")
        entities = routing_decision.get("entities", {})

        logger.info(
            "Orchestrator dispatching query to Agent: '%s' (Lang: '%s', Session: '%s')",
            target_agent, detected_lang, session_id
        )

        result: Dict[str, Any] = {}

        # Dispatch to specialized agent
        if target_agent == "admission":
            result = self.admission_agent.handle(clean_q, language=detected_lang, entities=entities)
        elif target_agent == "student":
            result = self.student_agent.handle(clean_q, language=detected_lang, entities=entities)
        elif target_agent == "faculty":
            result = self.faculty_agent.handle(clean_q, language=detected_lang, entities=entities)
        elif target_agent == "navigation":
            result = self.navigation_agent.handle(clean_q, language=detected_lang, entities=entities)
        elif target_agent == "escalation":
            if detected_lang in ["hi", "mr"]:
                reply_msg = "माफ करा, वैयक्तिक मूल्यमापन आणि विशेष प्रकरणांसाठी मानवी कर्मचार्‍यांची आवश्यकता आहे. मी तुमचा कॉल प्रवेश विभागात हस्तांतरित करत आहे."
            elif detected_lang == "hinglish":
                reply_msg = "Personal mark evaluation human staff handle karte hain. Main aapko admissions office human staff se connect kar raha hoon."
            else:
                reply_msg = "Personal evaluation and specific marks cases require human staff verification. Connecting you to human staff."

            result = {
                "reply": reply_msg,
                "agent": "escalation",
                "sources": [],
                "tools_used": [],
                "confident": False,
                "needs_human": True,
                "needs_clarification": False,
                "ui_action": "none"
            }
        else:  # 'reception' default
            rag_res = self.receptionist_agent.process_query(clean_q, language=detected_lang)
            result = {
                "reply": rag_res.get("answer", "I don't have verified information for that."),
                "agent": "reception",
                "sources": rag_res.get("sources", []),
                "tools_used": [],
                "confident": rag_res.get("confident", True),
                "needs_human": rag_res.get("needs_human", False),
                "needs_clarification": rag_res.get("needs_clarification", False),
                "ui_action": "none"
            }

        # Store topic context for future follow-up queries
        session_topic_memory[session_id] = {
            "agent": target_agent,
            "entities": entities,
            "intent": routing_decision.get("intent")
        }

        # Strict validation step: Ensure required standardized keys exist
        result.setdefault("reply", "I don't have verified information for that.")
        result.setdefault("agent", target_agent)
        result.setdefault("sources", [])
        result.setdefault("tools_used", [])
        result.setdefault("confident", True)
        result.setdefault("needs_human", False)
        result.setdefault("needs_clarification", False)
        result.setdefault("ui_action", "none")

        return result


# Global Orchestrator instance helper
_orchestrator_instance: Optional[MultiAgentOrchestrator] = None

def get_orchestrator() -> MultiAgentOrchestrator:
    """Get global cached MultiAgentOrchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = MultiAgentOrchestrator()
    return _orchestrator_instance
