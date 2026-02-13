"""
Layer 4: Generation
Responsibility: Generate answers using LLM based on retrieved context.
"""
from .interfaces import BaseLLM
from .llm import OpenRouterClient
from .generator import RAGGenerator
from .prompts import TRADING_ANALYST_SYSTEM, format_rag_prompt

__all__ = [
    "BaseLLM", 
    "OpenRouterClient", 
    "RAGGenerator",
    "TRADING_ANALYST_SYSTEM",
    "format_rag_prompt"
]
