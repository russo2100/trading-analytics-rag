"""
FAISS Vector Store wrapper
Responsibility: Store and search embeddings with metadata support
"""
import faiss
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import logging
import pickle
import json
from datetime import datetime

from sentence_transformers import SentenceTransformer
from ..config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for semantic search with metadata support"""
    
    def __init__(self, embedding_model: Optional[str] = None, use_gpu: bool = False):
        """
        Initialize vector store
        
        Args:
            embedding_model: SentenceTransformer model name
                Default: settings.embedding_model
            use_gpu: Use GPU for FAISS operations (requires faiss-gpu)
        """
        self.model_name = embedding_model or settings.embedding_model
        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.use_gpu = use_gpu
        
        # Initialize FAISS index (Flat L2 for MVP, IVF for large scale)
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Move to GPU if requested
        if use_gpu and faiss.get_num_gpus() > 0:
            self.index = faiss.index_cpu_to_all_gpus(self.index)
            logger.info("FAISS index moved to GPU")
        
        # Mapping: FAISS index position → event_id
        self.event_ids: List[str] = []
        
        # Metadata storage: event_id → metadata dict
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Initialized VectorStore with model={self.model_name}, dim={self.dimension}")
    
    def add_events(
        self, 
        event_ids: List[str], 
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Add events to vector store
        
        Args:
            event_ids: List of event IDs
            texts: List of embedding texts (same length as event_ids)
            metadata: Optional list of metadata dicts for each event
        """
        if len(event_ids) != len(texts):
            raise ValueError("event_ids and texts must have same length")
        
        if metadata and len(metadata) != len(event_ids):
            raise ValueError("metadata must have same length as event_ids")
        
        if not texts:
            logger.warning("No texts to add")
            return
        
        # Generate embeddings in batches for efficiency
        logger.info(f"Generating embeddings for {len(texts)} events...")
        embeddings = self.model.encode(
            texts, 
            show_progress_bar=len(texts) > 100,
            batch_size=32,
            convert_to_numpy=True
        )
        embeddings = embeddings.astype('float32')
        
        # Normalize embeddings for cosine similarity (optional)
        # faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings)
        self.event_ids.extend(event_ids)
        
        # Store metadata
        if metadata:
            for event_id, meta in zip(event_ids, metadata):
                self.metadata[event_id] = meta
        
        logger.info(f"Added {len(texts)} events to vector store (total: {self.index.ntotal})")
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar events
        
        Args:
            query: Query text
            top_k: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"source": "logs"})
            
        Returns:
            List of dicts with keys: event_id, score, metadata
            score = 1 / (1 + L2_distance) (normalized to 0-1)
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], show_progress_bar=False)
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search FAISS (retrieve more if filtering)
        search_k = top_k * 3 if filter_metadata else top_k
        search_k = min(search_k, self.index.ntotal)
        
        distances, indices = self.index.search(query_embedding, search_k)
        
        # Convert to result dicts
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.event_ids):
                continue
            
            event_id = self.event_ids[idx]
            
            # Apply metadata filters
            if filter_metadata:
                event_meta = self.metadata.get(event_id, {})
                if not self._matches_filter(event_meta, filter_metadata):
                    continue
            
            # Convert L2 distance to similarity score (0-1 range)
            similarity = 1.0 / (1.0 + float(dist))
            
            result = {
                "event_id": event_id,
                "score": similarity,
                "distance": float(dist),
                "metadata": self.metadata.get(event_id, {})
            }
            results.append(result)
            
            # Stop if we have enough results
            if len(results) >= top_k:
                break
        
        logger.debug(f"Vector search: query='{query[:50]}...' returned {len(results)} results")
        return results
    
    def _matches_filter(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if metadata matches all filter criteria"""
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    def get_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get event metadata by ID
        
        Args:
            event_id: Event ID to retrieve
            
        Returns:
            Dict with event_id and metadata, or None if not found
        """
        if event_id not in self.event_ids:
            return None
        
        return {
            "event_id": event_id,
            "metadata": self.metadata.get(event_id, {})
        }
    
    def save(self, index_path: Optional[Path] = None):
        """
        Save FAISS index and event_id mapping to disk
        
        Args:
            index_path: Directory to save index (default: settings.vector_index_path)
        """
        index_path = index_path or settings.vector_index_path
        index_path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index (move to CPU first if on GPU)
        faiss_file = index_path / "faiss.index"
        if self.use_gpu and faiss.get_num_gpus() > 0:
            cpu_index = faiss.index_gpu_to_cpu(self.index)
            faiss.write_index(cpu_index, str(faiss_file))
        else:
            faiss.write_index(self.index, str(faiss_file))
        
        # Save event_id mapping
        mapping_file = index_path / "event_ids.pkl"
        with open(mapping_file, 'wb') as f:
            pickle.dump(self.event_ids, f)
        
        # Save metadata
        metadata_file = index_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, default=str)
        
        # Save index info
        info_file = index_path / "index_info.json"
        info = {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "total_vectors": self.index.ntotal,
            "created_at": datetime.now().isoformat(),
            "use_gpu": self.use_gpu
        }
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2)
        
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
        metadata_file = index_path / "metadata.json"
        
        if not faiss_file.exists() or not mapping_file.exists():
            logger.warning(f"Index files not found in {index_path}")
            return
        
        # Load FAISS index
        self.index = faiss.read_index(str(faiss_file))
        
        # Move to GPU if requested
        if self.use_gpu and faiss.get_num_gpus() > 0:
            self.index = faiss.index_cpu_to_all_gpus(self.index)
            logger.info("FAISS index moved to GPU")
        
        # Load event_id mapping
        with open(mapping_file, 'rb') as f:
            self.event_ids = pickle.load(f)
        
        # Load metadata if exists
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        
        logger.info(f"Loaded vector store from {index_path} ({self.index.ntotal} vectors)")
    
    def clear(self):
        """Clear all vectors from index"""
        self.index.reset()
        self.event_ids.clear()
        self.metadata.clear()
        logger.info("Cleared vector store")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics
        
        Returns:
            Dict with statistics about the vector store
        """
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "model_name": self.model_name,
            "use_gpu": self.use_gpu,
            "has_metadata": len(self.metadata) > 0,
            "metadata_count": len(self.metadata)
        }
