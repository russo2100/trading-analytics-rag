from typing import List, Dict, Any, Optional
import logging
from ..layer2_storage.vector_store import VectorStore
from ..layer2_storage.metadata_store import MetadataStore
from .interfaces import BaseRetriever
from .models import SearchQuery, RetrievalResult, RetrievalType

logger = logging.getLogger(__name__)

class VectorRetriever(BaseRetriever):
    """Retrieves documents using dense vector similarity search"""
    
    def __init__(self, vector_store: VectorStore, metadata_store: Optional[MetadataStore] = None):
        """
        Args:
            vector_store: Initialized VectorStore from Layer 2
            metadata_store: Optional MetadataStore for retrieving full content
        """
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        self.name_val = "VectorRetriever"

    def search(self, query: SearchQuery) -> List[RetrievalResult]:
        """Execute semantic search"""
        if not query.text:
            return []
            
        logger.info(f"Vector search for: '{query.text}' (top_k={query.top_k})")
        
        # Execute search in Layer 2
        raw_results = self.vector_store.search(
            query=query.text,
            top_k=query.top_k,
            filter_metadata=query.filters
        )
        
        results = []
        for r in raw_results:
            # Filter by score threshold
            if r["score"] < query.min_score:
                continue
                
            # Get full content if metadata store is available
            event_id = r["event_id"]
            content = r["metadata"].get("content", "") # Fallback
            full_meta = r["metadata"].copy()
            
            if self.metadata_store:
                event = self.metadata_store.get_event(event_id)
                if event:
                    # Use embedding text as content
                    content = event.get("embedding_text", "")
                    full_meta.update(event) # Merge full metadata
            
            if not content:
                 content = f"Event {event_id}"

            results.append(RetrievalResult(
                event_id=event_id,
                content=str(content),
                score=r["score"],
                metadata=full_meta,
                source_type=RetrievalType.VECTOR
            ))
            
        return results

    def name(self) -> str:
        return self.name_val

class KeywordRetriever(BaseRetriever):
    """Retrieves documents using BM25 keyword search (via SQLite FTS5)"""
    
    def __init__(self, metadata_store: MetadataStore):
        self.metadata_store = metadata_store
        self.name_val = "KeywordRetriever"
        
    def search(self, query: SearchQuery) -> List[RetrievalResult]:
        if not query.text:
            return []
            
        logger.info(f"Keyword search for: '{query.text}' (top_k={query.top_k})")
        
        # FTS5 Match
        # To make it more robust, we might want to sanitize query or split into terms
        # Simple implementation: use query as is
        fts_query = query.text.replace('"', '""') # Basic sanitization
        
        raw_rows = self.metadata_store.search_text(fts_query, limit=query.top_k)
        
        results = []
        for row in raw_rows:
            # FTS rank is usually smaller is better (negative or close to 0)
            # We normalize crudely
            rank_score = 1.0  # Placeholder, real score requires normalization
            
            results.append(RetrievalResult(
                event_id=row["event_id"],
                content=row.get("embedding_text", ""),
                score=rank_score,
                metadata=dict(row),
                source_type=RetrievalType.KEYWORD
            ))
            
        return results

    def name(self) -> str:
        return self.name_val

class HybridRetriever(BaseRetriever):
    """Combines Vector and Keyword search using Reciprocal Rank Fusion (RRF)"""
    
    def __init__(self, vector_retriever: VectorRetriever, keyword_retriever: KeywordRetriever):
        self.vector = vector_retriever
        self.keyword = keyword_retriever
        self.name_val = "HybridRetriever"
        
    def search(self, query: SearchQuery) -> List[RetrievalResult]:
        # 1. Run both retrievers
        vec_results = self.vector.search(query)
        kw_results = self.keyword.search(query)
        
        # 2. RRF Algorithm
        # score = 1 / (k + rank)
        k = 60
        scores = {}
        content_map = {}
        meta_map = {}
        
        # Process Vector Results
        for rank, res in enumerate(vec_results):
            if res.event_id not in scores:
                scores[res.event_id] = 0.0
                content_map[res.event_id] = res.content
                meta_map[res.event_id] = res.metadata
            
            scores[res.event_id] += 1.0 / (k + rank + 1)
            
        # Process Keyword Results
        for rank, res in enumerate(kw_results):
            if res.event_id not in scores:
                scores[res.event_id] = 0.0
                content_map[res.event_id] = res.content
                meta_map[res.event_id] = res.metadata
            
            scores[res.event_id] += 1.0 / (k + rank + 1)
            
        # 3. Create final results
        final_results = []
        for event_id, score in scores.items():
            final_results.append(RetrievalResult(
                event_id=event_id,
                content=content_map[event_id],
                score=score, 
                metadata=meta_map[event_id],
                source_type=RetrievalType.HYBRID
            ))
            
        # Sort by RRF score desc
        final_results.sort(key=lambda x: x.score, reverse=True)
        
        return final_results[:query.top_k]

    def name(self) -> str:
        return self.name_val
