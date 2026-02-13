from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (e.g., 'Calculator')"""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for the LLM"""
        pass
        
    @abstractmethod
    def run(self, *args, **kwargs) -> str:
        """Execute the tool and return a string result"""
        pass
