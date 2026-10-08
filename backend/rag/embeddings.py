"""
backend/rag/embeddings.py - Vector Embedding Manager for CampusAI

Generates normalized vector embeddings using sentence-transformers (intfloat/multilingual-e5-small).
Enforces required 'passage: ' and 'query: ' prefixes for e5 embeddings.
"""

import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("campusai.rag.embeddings")


class EmbeddingManager:
    """Singleton Embedding Manager for sentence-transformers models."""

    _instance = None

    def __new__(cls, model_name: str = None):
        if cls._instance is None:
            cls._instance = super(EmbeddingManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = None) -> None:
        if self._initialized:
            return

        self.model_name = model_name or settings.EMBED_MODEL
        logger.info("Initializing SentenceTransformer model: %s", self.model_name)
        
        # Load transformer model
        self.model = SentenceTransformer(self.model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info("SentenceTransformer loaded. Vector dimension: %d", self.embedding_dim)
        
        self._initialized = True

    def embed_passages(self, texts: List[str]) -> np.ndarray:
        """
        Embed document passage chunks with 'passage: ' prefix.

        Args:
            texts: List of raw document chunk texts.

        Returns:
            Normalized 2D numpy array of shape (N, dim) with float32 type.
        """
        if not texts:
            return np.empty((0, self.embedding_dim), dtype=np.float32)

        # Apply e5 prefix for passages
        prefixed_texts = [f"passage: {t.strip()}" for t in texts]
        
        logger.info("Embedding %d passage chunks...", len(prefixed_texts))
        embeddings = self.model.encode(
            prefixed_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query_text: str) -> np.ndarray:
        """
        Embed a single search query with 'query: ' prefix.

        Args:
            query_text: User search query string.

        Returns:
            Normalized 1D numpy array of shape (dim,) with float32 type.
        """
        clean_query = query_text.strip()
        prefixed_query = f"query: {clean_query}"
        
        embedding = self.model.encode(
            prefixed_query,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embedding.astype(np.float32)


# Global singleton instance function
def get_embedding_manager() -> EmbeddingManager:
    """Get global cached EmbeddingManager instance."""
    return EmbeddingManager()
