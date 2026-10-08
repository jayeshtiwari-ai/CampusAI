"""
backend/agents/receptionist.py - CampusAI Receptionist Agent with Confidence Gating

Coordinates query processing by combining:
1. Personal case classifier
2. FAISS vector retrieval
3. Score threshold confidence gating (RAG_MIN_SCORE)
4. Groq LLM JSON mode grounded answer generation with source citations
"""

import json
import re
from typing import Dict, List, Any, Optional

from backend.config import settings
from backend.rag.retriever import get_retriever
from backend.llm.model import GroqLLM, LLMUnavailable
from backend.utils.logger import get_logger

logger = get_logger("campusai.agents.receptionist")


def is_personal_case(query: str) -> bool:
    """
    Classify whether a user query asks for personal evaluation, individual marks eligibility,
    or personal case status that cannot be answered automatically.
    """
    q_lower = query.lower()
    
    # Key patterns indicating personal evaluation or individual case inquiries
    personal_patterns = [
        r"mere\s+marks", r"mera\s+score", r"mera\s+cutoff", r"mera\s+percentile",
        r"my\s+marks", r"my\s+score", r"my\s+percentage", r"my\s+rank", r"my\s+case",
        r"mere\s+\d+%", r"my\s+\d+%", r"mera\s+\d+%",
        r"will\s+i\s+get\s+admission", r"kya\s+mujhe\s+admission\s+milega",
        r"kya\s+mera\s+admission\s+hoga", r"mujhe\s+branch\s+milegi",
        r"is\s+my\s+percentage\s+enough", r"eligible\0\s+hoon\s+kya"
    ]

    for pattern in personal_patterns:
        if re.search(pattern, q_lower):
            logger.info("Query flagged as personal case query: '%s'", query)
            return True
            
    return False


class ReceptionistAgent:
    """Receptionist Agent implementing confidence gating and grounded RAG responses."""

    def __init__(self) -> None:
        self.retriever = get_retriever()
        self.llm = GroqLLM()
        self.min_score_threshold = settings.RAG_MIN_SCORE

    def process_query(
        self,
        user_query: str,
        language: str = "en",
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a visitor query through personal classification, RAG retrieval,
        confidence gating, and LLM grounded answer synthesis.

        Returns:
            Dictionary with keys: answer, confident, sources, needs_human,
            needs_clarification, clarifying_question, reason.
        """
        clean_query = user_query.strip()

        # Step 1: Detect Personal Case Queries
        if is_personal_case(clean_query):
            if language in ["hi", "mr"]:
                personal_reply = "व्यक्तिगत गुणपत्रक आणि पात्रतेची तपासणी मानवी प्रवेश अधिकार्‍यांकडून केली जाते. मी तुमचा कॉल संबंधित विभागात हस्तांतरित करत आहे."
            elif language == "hinglish":
                personal_reply = "Personal evaluation aur individual marks case human staff handle karte hain. Main aapko admissions office human staff se connect kar raha hoon."
            else:
                personal_reply = "Individual mark evaluation and personal eligibility cases require human staff verification. Connecting you to human staff."

            return {
                "answer": personal_reply,
                "confident": False,
                "sources": [],
                "needs_clarification": False,
                "clarifying_question": None,
                "needs_human": True,
                "reason": "Flagged as personal case question requiring human evaluation."
            }

        # Step 2: Retrieve Relevant Knowledge Base Chunks
        retrieved_chunks = self.retriever.retrieve(
            query=clean_query,
            top_k=settings.RAG_TOP_K
        )

        logger.info(
            "Retrieved %d candidate chunks for query '%s'",
            len(retrieved_chunks), clean_query
        )

        # Step 3: Confidence Gating - Filter by RAG_MIN_SCORE
        qualifying_chunks = [c for c in retrieved_chunks if c.get("score", 0.0) >= self.min_score_threshold]
        
        logger.info(
            "Confidence Gating: %d / %d chunks passed threshold (>= %.2f)",
            len(qualifying_chunks), len(retrieved_chunks), self.min_score_threshold
        )

        # If NO chunks pass confidence threshold, REFUSE TO ANSWER (Zero Hallucination)
        if not qualifying_chunks:
            if language in ["hi", "mr"]:
                refusal_text = "माझ्याकडे याची अधिकृत माहिती नाही. कृपया मुख्य कार्यालयाशी संपर्क साधा."
            elif language == "hinglish":
                refusal_text = "Mere paas iski verified jankari nahi hai. Kripya main office se contact karein."
            else:
                refusal_text = "I don't have verified information for that. Please check with the main office."

            highest_score = retrieved_chunks[0]["score"] if retrieved_chunks else 0.0
            return {
                "answer": refusal_text,
                "confident": False,
                "sources": [],
                "needs_clarification": False,
                "clarifying_question": None,
                "needs_human": True,
                "reason": f"No retrieved chunks met minimum confidence threshold ({highest_score:.4f} < {self.min_score_threshold:.2f})."
            }

        # Step 4: Prepare Grounded Context & System Prompt
        context_snippets = []
        source_files = set()
        for idx, chunk in enumerate(qualifying_chunks, start=1):
            src = chunk.get("source", "unknown")
            source_files.add(src)
            context_snippets.append(f"--- Document Source [{idx}]: {src} ---\n{chunk.get('text')}")

        context_str = "\n\n".join(context_snippets)

        system_prompt = (
            f"You are the official AI Receptionist at {settings.COLLEGE_NAME}.\n"
            "STRICT GROUNDING INSTRUCTIONS:\n"
            "1. Answer ONLY using facts from the VERIFIED CONTEXT provided below.\n"
            "2. NEVER invent, extrapolate, or add outside facts not present in the context.\n"
            "3. Cite the exact source filename(s) in your answer if relevant.\n"
            "4. Respond in the user's language/script (Language code: " + language + ").\n"
            "5. OUTPUT STRICT JSON ONLY with the following keys:\n"
            '   {\n'
            '     "answer": "string",\n'
            '     "confident": true,\n'
            '     "sources": ["filename.md"],\n'
            '     "needs_clarification": false,\n'
            '     "clarifying_question": null,\n'
            '     "needs_human": false,\n'
            '     "reason": "string"\n'
            '   }\n\n'
            f"VERIFIED CONTEXT:\n{context_str}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Question ({language}): {clean_query}"}
        ]

        # Step 5: Call LLM in JSON mode
        try:
            raw_response = self.llm.chat(messages=messages, temperature=0.2, json_mode=True, max_tokens=1000)
            res_json = json.loads(raw_response)
            
            # Ensure sources list is present
            if "sources" not in res_json or not res_json["sources"]:
                res_json["sources"] = list(source_files)

            return {
                "answer": res_json.get("answer", "I don't have verified information for that."),
                "confident": res_json.get("confident", True),
                "sources": res_json.get("sources", list(source_files)),
                "needs_clarification": res_json.get("needs_clarification", False),
                "clarifying_question": res_json.get("clarifying_question", None),
                "needs_human": res_json.get("needs_human", False),
                "reason": res_json.get("reason", "Answer grounded in verified knowledge base context.")
            }

        except (LLMUnavailable, json.JSONDecodeError, Exception) as err:
            logger.error("Error generating grounded response: %s", str(err))
            return {
                "answer": "I don't have verified information for that.",
                "confident": False,
                "sources": list(source_files),
                "needs_clarification": False,
                "clarifying_question": None,
                "needs_human": True,
                "reason": f"Error parsing grounded response: {str(err)}"
            }
