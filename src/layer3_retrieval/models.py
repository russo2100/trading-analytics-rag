from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class RetrievalType(str, Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"

@dataclass
class RetrievalResult:
    """Standardized result from any retrieval strategy"""
    event_id: str
    content: str
    score: float  # Normalized 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_type: RetrievalType = RetrievalType.VECTOR
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
            "source_type": self.source_type.value
        }

@dataclass
class SearchQuery:
    """Structured search query"""
    text: str
    top_k: int = 5
    filters: Optional[Dict[str, Any]] = None
    min_score: float = 0.0
    strategy: RetrievalType = RetrievalType.HYBRID
