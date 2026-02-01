"""
Layer 2: Storage & Indexing

CONTRACT: IngestedEvent → Persistent storage (FAISS + SQLite + Cache)

Components:
- vector_store.py: FAISS vector database wrapper
- metadata_store.py: SQLite metadata database wrapper
- cache.py: In-memory semantic cache
- schema.sql: SQLite table definitions
"""

from .vector_store import VectorStore
from .metadata_store import MetadataStore
from .cache import SemanticCache

__all__ = [
    "VectorStore",
    "MetadataStore",
    "SemanticCache",
]
