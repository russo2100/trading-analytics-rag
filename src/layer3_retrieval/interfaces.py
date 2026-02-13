from abc import ABC, abstractmethod
from typing import List
from .models import SearchQuery, RetrievalResult

class BaseRetriever(ABC):
    """Abstract base class for all retrieval strategies"""
    
    @abstractmethod
    def search(self, query: SearchQuery) -> List[RetrievalResult]:
        """Execute search based on query parameters"""
        pass
    
    @abstractmethod
    def name(self) -> str:
        """Return retriever name"""
        pass

class BaseReranker(ABC):
    """Abstract base class for reranking strategies"""
    
    @abstractmethod
    def rerank(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Rerank initial retrieval results"""
        pass
