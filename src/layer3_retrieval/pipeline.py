from typing import List, Optional
import logging
from ..layer2_storage.vector_store import VectorStore
from ..layer2_storage.metadata_store import MetadataStore
from .models import SearchQuery, RetrievalResult, RetrievalType
from .retrievers import VectorRetriever, KeywordRetriever, HybridRetriever
from .reranking import CrossEncoderReranker

logger = logging.getLogger(__name__)

class RAGPipeline:
    """Main entry point for Layer 3 Retrieval"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        metadata_store: MetadataStore,
        embedding_model: Optional[str] = None,
        rerank_model: Optional[str] = None
    ):
        """
        Args:
            vector_store: Initialized VectorStore
            metadata_store: Initialized MetadataStore
            embedding_model: Name of sentence-transformer model (optional override)
            rerank_model: Name of cross-encoder model (optional override)
        """
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        
        # Initialize component retrievers
        self.vector_retriever = VectorRetriever(vector_store, metadata_store)
        self.keyword_retriever = KeywordRetriever(metadata_store)
        
        # Initialize hybrid retriever
        self.hybrid_retriever = HybridRetriever(
            self.vector_retriever, 
            self.keyword_retriever
        )
        
        # Initialize reranker
        self.reranker = CrossEncoderReranker(
            model_name=rerank_model or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        
        logger.info("RAG Pipeline initialized")

    def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[dict] = None
    ) -> List[RetrievalResult]:
        """
        Full retrieval pipeline: Hybrid Search -> Reranking
        """
        logger.info(f"Pipeline executing for: '{query}'")
        
        # 1. Expand Query (Future: multiple variations)
        search_query = SearchQuery(
            text=query,
            top_k=top_k * 3, # Retrieve more candidates for reranking
            filters=filters
        )
        
        # 2. Hybrid Retrieval
        candidates = self.hybrid_retriever.search(search_query)
        logger.info(f"Retrieved {len(candidates)} candidates")
        
        # 3. Reranking
        final_results = self.reranker.rerank(query, candidates)
        
        # 4. Return top K
        return final_results[:top_k]

    def format_context(self, results: List[RetrievalResult]) -> str:
        """
        Format results into a context string for LLM
        """
        context_parts = []
        for i, res in enumerate(results, 1):
            source = res.metadata.get("source", "unknown")
            date = res.metadata.get("freshness", "unknown_date")
            
            # Context block format
            block = f"""[Document {i}]
Source: {source}
Date: {date}
Content: {res.content}
"""
            context_parts.append(block)
            
        return "\n\n".join(context_parts)
