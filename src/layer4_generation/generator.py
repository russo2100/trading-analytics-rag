import logging
from typing import Optional, List
from .interfaces import BaseLLM
from .prompts import TRADING_ANALYST_SYSTEM, format_rag_prompt
# Import RAGPipeline only for type hinting to avoid circular imports at runtime if possible, 
# but for now we need it for dependency injection.
from ..layer3_retrieval.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

class RAGGenerator:
    """
    RAG Generation Orchestrator
    Combines Retrieval (Layer 3) + Generation (Layer 4)
    """
    
    def __init__(self, retrieval_pipeline: RAGPipeline, llm_client: BaseLLM):
        self.retrieval = retrieval_pipeline
        self.llm = llm_client
        self.max_context_tokens = 6000 # Leave room for answer (model limit usually 8k-128k)
        
    def generate_answer(self, query: str, conversation_history: Optional[List[dict]] = None) -> str:
        """
        End-to-end RAG process:
        1. Retrieve context
        2. Format prompt
        3. Generate answer
        """
        logger.info(f"Generating answer for: '{query}'")
        
        # 1. Retrieve
        results = self.retrieval.retrieve(query, top_k=5)
        
        if not results:
            logger.warning("No relevant context found.")
            return "I couldn't find any relevant information in the database to answer your question."
            
        # Format context
        context_str = self.retrieval.format_context(results)
        
        # 2. Manage Token Limit (Simple Truncation)
        # Approx 4 chars per token
        if len(context_str) / 4 > self.max_context_tokens:
            logger.warning("Context too long, truncating...")
            context_str = context_str[:self.max_context_tokens * 4] + "...(truncated)"
            
        # 3. Construct Prompt
        full_prompt = format_rag_prompt(query, context_str)
        
        # 4. Generate with LLM
        logger.info("Sending prompt to LLM...")
        answer = self.llm.generate(
            prompt=full_prompt,
            system_prompt=TRADING_ANALYST_SYSTEM,
            temperature=0.3, # Low temp for factual answers
            max_tokens=2000
        )
        
        return answer
