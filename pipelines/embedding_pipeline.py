"""
Embedding Pipeline - Converts text reviews to semantic embeddings

Uses SentenceTransformers for efficient text encoding
"""

import logging
import threading
from typing import List, Tuple
import numpy as np
import os

logger = logging.getLogger(__name__)

# Global singleton for lazy loading
_embedding_model = None
_lock = threading.Lock()


class EmbeddingPipeline:
    """Handles text embedding for semantic analysis"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model.

        Args:
            model_name: HuggingFace model name for embeddings
                - 'all-MiniLM-L6-v2': Fast, lightweight (384 dims)
                - 'all-mpnet-base-v2': High quality but slower (768 dims)
                - 'all-distilroberta-v1': Good balance (768 dims)
        """
        logger.info(f"Loading embedding model: {model_name}")
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Encode texts to embeddings.

        Args:
            texts: List of text strings to encode
            batch_size: Batch size for processing

        Returns:
            NumPy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([]).reshape(0, self.embedding_dim)

        logger.info(f"Encoding {len(texts)} texts with batch_size={batch_size}")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        logger.info(f"Encoding complete. Shape: {embeddings.shape}")
        return embeddings

    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode single text to embedding.

        Args:
            text: Single text string

        Returns:
            NumPy array of shape (embedding_dim,)
        """
        return self.model.encode(text, convert_to_numpy=True)

    def similarity(self, embeddings1: np.ndarray, embeddings2: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between embedding sets.

        Args:
            embeddings1: Array of shape (n, embedding_dim)
            embeddings2: Array of shape (m, embedding_dim)

        Returns:
            Similarity matrix of shape (n, m)
        """
        from sklearn.metrics.pairwise import cosine_similarity
        return cosine_similarity(embeddings1, embeddings2)

    def get_most_similar(
        self,
        query_embedding: np.ndarray,
        embeddings: np.ndarray,
        top_k: int = 5
    ) -> Tuple[List[int], List[float]]:
        """
        Find most similar embeddings to query.

        Args:
            query_embedding: Query embedding
            embeddings: Pool of embeddings to search
            top_k: Number of top similar to return

        Returns:
            Tuple of (indices, similarity_scores)
        """
        similarities = self.similarity(
            query_embedding.reshape(1, -1),
            embeddings
        )[0]
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_scores = similarities[top_indices]
        return top_indices.tolist(), top_scores.tolist()


# Global instance for easy access
_embedding_model = None


def get_embedding_pipeline(model_name: str | None = None) -> EmbeddingPipeline:
    """Lazy load embedding model"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingPipeline(model_name or os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    return _embedding_model
