import sys
import logging
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import settings
from src.layer2_storage.vector_store import VectorStore
from src.layer2_storage.metadata_store import MetadataStore
from src.layer3_retrieval.pipeline import RAGPipeline
from src.layer4_generation.llm import OpenRouterClient
from src.layer4_generation.generator import RAGGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_full_rag():
    logger.info("Initializing Storage Layer (L2)...")
    vs = VectorStore()
    ms = MetadataStore()
    
    if not settings.vector_index_path.exists():
        logger.error("Vector index not found! Run scripts/build_vector_index.py first.")
        return
        
    vs.load()
    
    logger.info("Initializing Retrieval Layer (L3)...")
    pipeline = RAGPipeline(vs, ms)
    
    logger.info("Initializing Generation Layer (L4)...")
    if not settings.openrouter_api_key:
        logger.warning("\n⚠️ OPENROUTER_API_KEY not found in .env! Generation will use mock/error.\n")
        
    llm = OpenRouterClient()
    generator = RAGGenerator(pipeline, llm)
    
    # Test queries
    queries = [
        "Why did the bot enter a SHORT position on 2026-01-30?",
        "Summarize the market conditions for the last session.",
        "What is the current trend based on the logs?"
    ]
    
    print("\n" + "="*50)
    print(" RAG GENERATION TEST ")
    print("="*50 + "\n")
    
    for q in queries:
        print(f"QUERY: {q}")
        print("-" * 30)
        
        try:
            answer = generator.generate_answer(q)
            print(f"\nANSWER:\n{answer}")
        except Exception as e:
            print(f"❌ Error during generation: {e}")
            
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    test_full_rag()
