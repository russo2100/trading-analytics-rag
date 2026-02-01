"""
FAISS Vector Store wrapper
Responsibility: Store and search embeddings
"""
import faiss
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import logging
import pickle

from sentence_transformers import SentenceTransformer
from ..config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for semantic search"""
    
    def __init__(self, embedding_model: Optional[str] = None):
        """
        Initialize vector store
        
        Args:
            embedding_model: SentenceTransformer model name
                Default: settings.embedding_model
        """
        self.model_name = embedding_model or settings.embedding_model
        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # Initialize FAISS index (Flat L2 for MVP, IVF for large scale)
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Mapping: FAISS index position → event_id
        self.event_ids: List[str] = []
        
        logger.info(f"Initialized VectorStore with model={self.model_name}, dim={self.dimension}")
    
    def add_events(self, event_ids: List[str], texts: List[str]):
        """
        Add events to vector store
        
        Args:
            event_ids: List of event IDs
            texts: List of embedding texts (same length as event_ids)
        """
        if len(event_ids) != len(texts):
            raise ValueError("event_ids and texts must have same length")
        
        if not texts:
            logger.warning("No texts to add")
            return
        
        # Generate embeddings
        embeddings = self.model.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings).astype('float32')
        
        # Add to FAISS index
        self.index.add(embeddings)
        self.event_ids.extend(event_ids)
        
        logger.info(f"Added {len(texts)} events to vector store (total: {self.index.ntotal})")
    
    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Search for similar events
        
        Args:
            query: Query text
            top_k: Number of results to return
            
        Returns:
            List of (event_id, similarity_score) tuples
            similarity_score = 1 / (1 + L2_distance) (normalized to 0-1)
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], show_progress_bar=False)
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search FAISS
        distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        # Convert to (event_id, score) tuples
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.event_ids):
                continue
            
            event_id = self.event_ids[idx]
            # Convert L2 distance to similarity score (0-1 range)
            similarity = 1.0 / (1.0 + float(dist))
            results.append((event_id, similarity))
        
        logger.debug(f"Vector search: query='{query[:50]}...' returned {len(results)} results")
        return results
    
    def save(self, index_path: Optional[Path] = None):
        """
        Save FAISS index and event_id mapping to disk
        
        Args:
            index_path: Directory to save index (default: settings.vector_index_path)
        """
        index_path = index_path or settings.vector_index_path
        index_path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss_file = index_path / "faiss.index"
        faiss.write_index(self.index, str(faiss_file))
        
        # Save event_id mapping
        mapping_file = index_path / "event_ids.pkl"
        with open(mapping_file, 'wb') as f:
            pickle.dump(self.event_ids, f)
        
        logger.info(f"Saved vector store to {index_path} ({self.index.ntotal} vectors)")
    
    def load(self, index_path: Optional[Path] = None):
        """
        Load FAISS index and event_id mapping from disk
        
        Args:
            index_path: Directory to load index from
        """
        index_path = index_path or settings.vector_index_path
        
        faiss_file = index_path / "faiss.index"
        mapping_file = index_path / "event_ids.pkl"
        
        if not faiss_file.exists() or not mapping_file.exists():
            logger.warning(f"Index files not found in {index_path}")
            return
        
        # Load FAISS index
        self.index = faiss.read_index(str(faiss_file))
        
        # Load event_id mapping
        with open(mapping_file, 'rb') as f:
            self.event_ids = pickle.load(f)
        
        logger.info(f"Loaded vector store from {index_path} ({self.index.ntotal} vectors)")
    
    def clear(self):
        """Clear all vectors from index"""
        self.index.reset()
        self.event_ids.clear()
        logger.info("Cleared vector store")
