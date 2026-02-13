from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLM(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Generate response from LLM"""
        pass
    
    @abstractmethod
    def name(self) -> str:
        """Return model name"""
        pass
