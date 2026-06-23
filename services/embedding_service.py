"""
Embedding service layer.

Handles text encoding, caching, and vector operations with configurable
model selection and device management.
"""

from __future__ import annotations

import logging
import threading
from typing import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing text embeddings."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Initialize embedding model (singleton pattern)."""
        import os
        
        self.model_name = settings.embedding.model_name
        self.batch_size = settings.embedding.batch_size
        self.device = settings.embedding.device
        
        # Ensure cache directory exists
        cache_dir = settings.embedding.cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"Using cache directory: {cache_dir}")
        
        logger.info(
            f"Initializing EmbeddingService with model: {self.model_name}, "
            f"device: {self.device}"
        )
        
        try:
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=cache_dir,
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(
                f"Cannot load embedding model '{self.model_name}'. "
                f"Check internet connection and disk space."
            )
        
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.embedding_dim}")
    
    @classmethod
    def get_instance(cls) -> EmbeddingService:
        """Get singleton instance of EmbeddingService."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """
        Encode a batch of texts to embeddings.
        
        Args:
            texts: List of text strings to encode
            
        Returns:
            Array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([]).reshape(0, self.embedding_dim)
        
        logger.debug(f"Encoding {len(texts)} texts with batch_size={self.batch_size}")
        
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        
        logger.debug(f"Encoding complete. Shape: {embeddings.shape}")
        return embeddings
    
    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text to embedding.
        
        Args:
            text: Single text string
            
        Returns:
            Array of shape (embedding_dim,)
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def similarity(
        self,
        embeddings1: np.ndarray,
        embeddings2: np.ndarray,
    ) -> np.ndarray:
        """
        Compute cosine similarity between two sets of embeddings.
        
        Args:
            embeddings1: Array of shape (n, embedding_dim)
            embeddings2: Array of shape (m, embedding_dim)
            
        Returns:
            Similarity matrix of shape (n, m)
        """
        return cosine_similarity(embeddings1, embeddings2)
    
    def find_similar(
        self,
        query_embedding: np.ndarray,
        embeddings: np.ndarray,
        top_k: int = 5,
    ) -> tuple[list[int], list[float]]:
        """
        Find most similar embeddings to query.
        
        Args:
            query_embedding: Query embedding of shape (embedding_dim,)
            embeddings: Pool of embeddings of shape (n, embedding_dim)
            top_k: Number of top similar to return
            
        Returns:
            Tuple of (indices, similarity_scores)
        """
        similarities = self.similarity(
            query_embedding.reshape(1, -1),
            embeddings,
        )[0]
        
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_scores = similarities[top_indices]
        
        return top_indices.tolist(), top_scores.tolist()


def get_embedding_service() -> EmbeddingService:
    """Convenience function to get EmbeddingService singleton."""
    return EmbeddingService.get_instance()
