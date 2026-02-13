import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import settings
from src.layer2_storage.vector_store import VectorStore
from src.layer2_storage.metadata_store import MetadataStore
from src.layer3_retrieval.pipeline import RAGPipeline
from src.layer4_generation.llm import OpenRouterClient
from src.layer5_agents.tools import RetrievalTool, CalculatorTool
from src.layer5_agents.agent import ReActAgent
from src.layer5_agents.tools import RetrievalTool, CalculatorTool, SessionQueryTool


logging.basicConfig(level=logging.INFO)
# Silence verbose loggers
logging.getLogger("src.layer2_storage").setLevel(logging.WARNING)
logging.getLogger("src.layer3_retrieval").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def test_agent():
    print("="*50)
    logger.info("Initializing Stack...")
    
    # L2
    vs = VectorStore()
    ms = MetadataStore()
    if settings.vector_index_path.exists():
        vs.load()
    else:
        logger.warning("Vector Index not found. Mocking or failing gracefully.")
    
    # L3
    rag_pipeline = RAGPipeline(vs, ms)
    
    # L4
    if not settings.openrouter_api_key:
        logger.warning("\n⚠️ OPENROUTER_API_KEY missing. Agent will likely fail or output mocks.\n")
    llm = OpenRouterClient()
    
    # L5 Tools
    tools = [
        RetrievalTool(rag_pipeline),
        CalculatorTool(),
        SessionQueryTool()
    ]
    
    # Agent
    agent = ReActAgent(llm=llm, tools=tools, max_steps=10)
    
    print("🤖 Agent Activated. Ready for complex queries.")
    print("="*50)
    
    # Scenario: Multi-step reasoning
    # 1. Retrieve info about trading session
    # 2. Calculate something based on it (simulated)
    
    query = "Find the trading session on 2026-01-30. If the total PnL was positive, multiply it by 10. If negative, divide by 2."
    
    print(f"\nUser Query: {query}\n")
    
    try:
        response = agent.run(query)
        print(f"\n🤖 Final Answer:\n{response}")
    except Exception as e:
        logger.error(f"Agent crashed: {e}")
        
    print("\n" + "="*50)

if __name__ == "__main__":
    test_agent()
