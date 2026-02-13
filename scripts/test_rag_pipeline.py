import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import settings
from src.layer2_storage.vector_store import VectorStore
from src.layer2_storage.metadata_store import MetadataStore
from src.layer3_retrieval.pipeline import RAGPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pipeline():
    logger.info("Initializing Storage Layer...")
    vs = VectorStore()
    ms = MetadataStore()
    
    # Check if index exists
    if not settings.vector_index_path.exists():
        logger.error("Vector index not found! Run scripts/build_vector_index.py first.")
        return
        
    vs.load()
    
    logger.info("Initializing Retrieval Layer (RAG Pipeline)...")
    pipeline = RAGPipeline(vs, ms)
    
    # Test queries
    queries = [
        "What is the trend for crude oil prices?",
        "Show me trading activity on 2026-01-30",
        "Explain the reasoning for selling on downtrend"
    ]
    
    for q in queries:
        print(f"\nQUERY: {q}")
        print("-" * 50)
        
        results = pipeline.retrieve(q, top_k=3)
        context = pipeline.format_context(results)
        
        print(f"✅ Found {len(results)} relevant chunks:")
        print(context)
        print("-" * 50)

if __name__ == "__main__":
    test_pipeline()
