from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import math
import logging

# We import only pipeline interface to avoid circular imports during type checking if possible
# But here we need actual functionality
from ..layer3_retrieval.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

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

class RetrievalTool(BaseTool):
    """Tool for searching knowledge base via RAG"""
    
    def __init__(self, pipeline: RAGPipeline):
        self.pipeline = pipeline
        
    @property
    def name(self) -> str:
        return "KnowledgeBase"
        
    @property
    def description(self) -> str:
        return "Useful for searching trading logs, market reports, and historical data. Input: a specific search query."

    def run(self, query: str) -> str:
        try:
            results = self.pipeline.retrieve(query, top_k=3)
            if not results:
                return "No relevant information found."
            return self.pipeline.format_context(results)
        except Exception as e:
            return f"Error searching knowledge base: {str(e)}"

class CalculatorTool(BaseTool):
    """Tool for basic mathematical calculations"""
    
    @property
    def name(self) -> str:
        return "Calculator"
        
    @property
    def description(self) -> str:
        return "Useful for performing mathematical calculations. Input: a mathematical expression string (e.g., '200 * 0.05')."

    def run(self, expression: str) -> str:
        try:
            # Safe evaluation of math expressions
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("__")
            }
            # Remove any potentially dangerous characters
            clean_expr = expression.replace('__', '').replace('import', '').replace('lambda', '')
            
            result = eval(clean_expr, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"Error calculating '{expression}': {str(e)}"
