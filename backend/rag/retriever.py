"""
backend/rag/retriever.py - FAISS Vector Retriever & Query Rewriter

Loads FAISS vector index and metadata, rewrites Hinglish/multilingual queries
to English search terms, and retrieves relevant document chunks with cosine similarity scores.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import faiss
import numpy as np

from backend.config import settings
from backend.rag.embeddings import get_embedding_manager
from backend.llm.model import GroqLLM
from backend.utils.logger import get_logger

logger = get_logger("campusai.rag.retriever")

DATA_INDEX_DIR: Path = settings.BASE_DIR / "data" / "index"
INDEX_FILE_PATH: Path = DATA_INDEX_DIR / "faiss_index.bin"
METADATA_FILE_PATH: Path = DATA_INDEX_DIR / "chunks_metadata.json"


class FAISSRetriever:
    """Retriever class for FAISS similarity search over embedded knowledge base chunks."""

    def __init__(self) -> None:
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []
        self.embed_mgr = get_embedding_manager()
        self.llm = GroqLLM()
        self.load_index()

    def load_index(self) -> bool:
        """Load FAISS index binary and metadata JSON from data/index/."""
        if not INDEX_FILE_PATH.exists() or not METADATA_FILE_PATH.exists():
            logger.warning("FAISS index or metadata missing. Run 'python -m backend.rag.ingest' first.")
            return False

        try:
            logger.info("Loading FAISS index from %s...", INDEX_FILE_PATH)
            self.index = faiss.read_index(str(INDEX_FILE_PATH))

            with open(METADATA_FILE_PATH, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

            logger.info("FAISS index loaded successfully with %d vectors.", self.index.ntotal)
            return True
        except Exception as e:
            logger.error("Failed to load FAISS index: %s", str(e))
            return False

    def rewrite_query_to_english(self, raw_query: str) -> str:
        """
        Use LLM to rewrite Hinglish/Hindi/Marathi query into a clear English search query.
        """
        # If query is short and strictly ascii english, return as-is
        if len(raw_query.strip().split()) <= 4 and raw_query.isascii():
            return raw_query.strip()

        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a search query optimizer for a college knowledge base. "
                    "Translate and rewrite the user's question into 1 clear, concise English search phrase. "
                    "Output ONLY the English search phrase and nothing else."
                )
            },
            {"role": "user", "content": raw_query}
        ]

        try:
            english_query = self.llm.chat(messages=prompt, temperature=0.1)
            logger.info("Rewrote query '%s' -> '%s'", raw_query, english_query)
            return english_query
        except Exception as err:
            logger.warning("Query rewriting failed: %s. Using raw query.", str(err))
            return raw_query

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top_k document chunks matching the query with cosine similarity scores.

        Args:
            query: User input text query (multilingual / Hinglish / English).
            top_k: Maximum number of chunks to return.
            category_filter: Optional category folder filter.

        Returns:
            List of chunk metadata dictionaries with attached 'score' field.
        """
        if self.index is None or not self.metadata:
            if not self.load_index():
                return []

        clean_query = query.strip()
        if not clean_query:
            return []

        # 1. Obtain query embeddings for original query and rewritten query
        rewritten_query = self.rewrite_query_to_english(clean_query)
        queries_to_embed = [clean_query]
        if rewritten_query.lower() != clean_query.lower():
            queries_to_embed.append(rewritten_query)

        candidate_chunks: Dict[str, Dict[str, Any]] = {}

        for q_text in queries_to_embed:
            q_vec = self.embed_mgr.embed_query(q_text)
            q_matrix = np.expand_dims(q_vec, axis=0)

            # Perform FAISS search (IP on normalized vectors = cosine similarity)
            fetch_k = min(top_k * 3, self.index.ntotal)
            scores, indices = self.index.search(q_matrix, fetch_k)

            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.metadata):
                    continue

                chunk_meta = dict(self.metadata[idx])
                sim_score = float(score)
                chunk_meta["score"] = round(sim_score, 4)

                # Filter by category if requested
                if category_filter and chunk_meta.get("category") != category_filter:
                    continue

                c_id = chunk_meta["chunk_id"]
                # Keep highest score if chunk found in multiple query searches
                if c_id not in candidate_chunks or sim_score > candidate_chunks[c_id]["score"]:
                    candidate_chunks[c_id] = chunk_meta

        # Sort candidates by score descending
        sorted_chunks = sorted(candidate_chunks.values(), key=lambda x: x["score"], reverse=True)
        return sorted_chunks[:top_k]


# Global retriever singleton instance helper
_retriever_instance: Optional[FAISSRetriever] = None

def get_retriever() -> FAISSRetriever:
    """Get global cached FAISSRetriever instance."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = FAISSRetriever()
    return _retriever_instance
