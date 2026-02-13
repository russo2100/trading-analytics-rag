from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseAgent(ABC):
    """Abstract base class for agents"""
    
    @abstractmethod
    def run(self, query: str) -> str:
        """Execute agent workflow for a query"""
        pass
