from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import math
import logging

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
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("__")
            }
            clean_expr = expression.replace('__', '').replace('import', '').replace('lambda', '')
            result = eval(clean_expr, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"Error calculating '{expression}': {str(e)}"


class SessionQueryTool(BaseTool):
    """Query aggregated session data (total_trades, final_pnl_pct)"""
    
    def __init__(self, db_path: str = "data/metadata.db"):
        self.db_path = db_path
    
    @property
    def name(self) -> str:
        return "SessionQuery"
    
    @property
    def description(self) -> str:
        return "Query trading session statistics. Input: session_id (YYYYMMDD)."
    
    def run(self, session_id: str) -> str:
        """Execute session query"""
        session_id = session_id.strip().replace("-", "").replace(" ", "")
        
        if not (len(session_id) == 8 and session_id.isdigit()):
            return f"ERROR: Invalid session_id format. Expected YYYYMMDD (e.g., 20260130), got: '{session_id}'"
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT session_id, total_trades, final_pnl_pct, 
                    total_cycles, first_timestamp, last_timestamp
                FROM sessions 
                WHERE session_id = ?
            """, (session_id,))
            
            row = cur.fetchone()
            
            if row is None:
                cur.execute("SELECT session_id FROM sessions ORDER BY session_id DESC LIMIT 5")
                available = [r[0] for r in cur.fetchall()]
                return f"ERROR: Session '{session_id}' not found. Available: {', '.join(available)}"
            
            sid, trades, pnl, cycles, first_ts, last_ts = row
            result = (
                f"Session {sid}:\n"
                f"- Total trades: {trades}\n"
                f"- Final PnL: {pnl:.2f}%\n"
                f"- Total cycles: {cycles}\n"
                f"- Duration: {first_ts[:16]} → {last_ts[:16]}"
            )
            conn.close()
            return result
            
        except Exception as e:
            return f"ERROR: Database query failed: {str(e)}"

