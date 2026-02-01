"""
In-memory semantic cache
Responsibility: Cache frequent queries to reduce LLM/embedding calls
"""
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SemanticCache:
    """Simple in-memory cache with TTL (Redis replacement for MVP)"""
    
    def __init__(self, ttl_minutes: int = 30):
        """
        Initialize cache
        
        Args:
            ttl_minutes: Time-to-live for cached entries (default: 30 min)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        logger.info(f"Initialized SemanticCache (TTL={ttl_minutes} min)")
    
    def _hash_query(self, query: str) -> str:
        """Generate cache key from query"""
        return hashlib.md5(query.encode()).hexdigest()
    
    def get(self, query: str) -> Optional[Any]:
        """
        Retrieve cached result
        
        Args:
            query: Query string
            
        Returns:
            Cached result or None if miss/expired
        """
        cache_key = self._hash_query(query)
        
        if cache_key not in self.cache:
            return None
        
        entry = self.cache[cache_key]
        
        # Check TTL
        if datetime.now() - entry["timestamp"] > self.ttl:
            del self.cache[cache_key]
            logger.debug(f"Cache expired: {query[:50]}...")
            return None
        
        logger.debug(f"Cache hit: {query[:50]}...")
        return entry["result"]
    
    def set(self, query: str, result: Any):
        """
        Store result in cache
        
        Args:
            query: Query string
            result: Result to cache
        """
        cache_key = self._hash_query(query)
        
        self.cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now(),
        }
        
        logger.debug(f"Cached result for: {query[:50]}...")
    
    def clear(self):
        """Clear all cached entries"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "ttl_minutes": self.ttl.total_seconds() / 60,
        }
