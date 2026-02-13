from typing import List
from sentence_transformers import CrossEncoder
import logging
from .interfaces import BaseReranker
from .models import RetrievalResult

logger = logging.getLogger(__name__)

class CrossEncoderReranker(BaseReranker):
    """Reranks results using a Cross-Encoder model"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Args:
            model_name: HuggingFace model name for CrossEncoder
        """
        self.model_name = model_name
        self.model = CrossEncoder(model_name)
        logger.info(f"Initialized CrossEncoderReranker with {model_name}")
        
    def rerank(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Rerank limit number of results
        """
        if not results:
            return []
            
        logger.info(f"Reranking {len(results)} results for query: '{query[:50]}...'")
        
        # Prepare pairs for scoring
        pairs = [[query, res.content] for res in results]
        
        # Predict scores
        scores = self.model.predict(pairs)
        
        # Update scores and sort
        for i, res in enumerate(results):
            res.score = float(scores[i])
            
        # Sort by new score desc
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results
