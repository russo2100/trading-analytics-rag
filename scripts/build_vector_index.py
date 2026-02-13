#!/usr/bin/env python3
"""
Build vector index from database events

This script:
1. Loads events from SQLite metadata store
2. Generates embeddings using SentenceTransformer
3. Builds FAISS index
4. Saves index to disk
"""
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
import sqlite3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.layer2_storage.vector_store import VectorStore
from src.layer2_storage.metadata_store import MetadataStore
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_events_from_db(
    db_path: Path,
    source_filter: str = None,
    limit: int = None
) -> List[Dict[str, Any]]:
    """
    Load events from SQLite database
    
    Args:
        db_path: Path to SQLite database
        source_filter: Optional source filter (e.g., 'logs', 'eia')
        limit: Optional limit on number of events
        
    Returns:
        List of event dicts
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM events"
    params = []
    
    if source_filter:
        query += " WHERE source = ?"
        params.append(source_filter)
    
    query += " ORDER BY freshness DESC"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    events = [dict(row) for row in rows]
    conn.close()
    
    logger.info(f"Loaded {len(events)} events from database")
    return events


def build_vector_index(
    db_path: Path = None,
    source_filter: str = None,
    limit: int = None,
    use_gpu: bool = False
):
    """
    Build vector index from database events
    
    Args:
        db_path: Path to SQLite database (default: settings.sqlite_db_path)
        source_filter: Optional source filter
        limit: Optional limit on number of events
        use_gpu: Use GPU for FAISS operations
    """
    db_path = db_path or settings.sqlite_db_path
    
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        logger.info("Run 'python scripts/init_database.py' first")
        return
    
    logger.info("=" * 60)
    logger.info("Building Vector Index")
    logger.info("=" * 60)
    
    # Load events from database
    logger.info(f"Loading events from {db_path}...")
    events = load_events_from_db(db_path, source_filter, limit)
    
    if not events:
        logger.warning("No events found in database")
        return
    
    # Extract data for vector store
    event_ids = [e['event_id'] for e in events]
    texts = [e['embedding_text'] for e in events]
    metadata = [
        {
            'source': e['source'],
            'authority': e['authority'],
            'freshness': e['freshness'],
            'data_period_start': e.get('data_period_start'),
            'data_period_end': e.get('data_period_end')
        }
        for e in events
    ]
    
    # Initialize vector store
    logger.info(f"Initializing vector store (GPU: {use_gpu})...")
    vector_store = VectorStore(use_gpu=use_gpu)
    
    # Add events to vector store
    logger.info("Generating embeddings and building index...")
    vector_store.add_events(event_ids, texts, metadata)
    
    # Save index
    logger.info("Saving index to disk...")
    vector_store.save()
    
    # Print statistics
    stats = vector_store.get_stats()
    logger.info("=" * 60)
    logger.info("Index Statistics")
    logger.info("=" * 60)
    logger.info(f"Total vectors: {stats['total_vectors']}")
    logger.info(f"Dimension: {stats['dimension']}")
    logger.info(f"Model: {stats['model_name']}")
    logger.info(f"GPU enabled: {stats['use_gpu']}")
    logger.info(f"Metadata count: {stats['metadata_count']}")
    logger.info(f"Index path: {settings.vector_index_path}")
    logger.info("=" * 60)
    
    # Test search
    logger.info("\nTesting search functionality...")
    test_query = "trading decision"
    results = vector_store.search(test_query, top_k=3)
    
    logger.info(f"\nTest query: '{test_query}'")
    logger.info(f"Top {len(results)} results:")
    for i, result in enumerate(results, 1):
        logger.info(f"\n{i}. Event ID: {result['event_id']}")
        logger.info(f"   Score: {result['score']:.4f}")
        logger.info(f"   Source: {result['metadata'].get('source', 'N/A')}")
        logger.info(f"   Authority: {result['metadata'].get('authority', 'N/A')}")
    
    logger.info("\n✅ Vector index built successfully!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build FAISS vector index from database events"
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        default=settings.sqlite_db_path,
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--source',
        type=str,
        help='Filter by source (logs, eia, weather, news)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of events to index'
    )
    parser.add_argument(
        '--gpu',
        action='store_true',
        help='Use GPU for FAISS operations (requires faiss-gpu)'
    )
    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Rebuild index even if it exists'
    )
    
    args = parser.parse_args()
    
    # Check if index already exists
    if settings.vector_index_path.exists() and not args.rebuild:
        logger.warning(f"Index already exists at {settings.vector_index_path}")
        logger.info("Use --rebuild to rebuild the index")
        
        response = input("Continue and rebuild? (y/N): ")
        if response.lower() != 'y':
            logger.info("Aborted")
            return
    
    try:
        build_vector_index(
            db_path=args.db_path,
            source_filter=args.source,
            limit=args.limit,
            use_gpu=args.gpu
        )
    except Exception as e:
        logger.error(f"Error building index: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
