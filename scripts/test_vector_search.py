#!/usr/bin/env python3
"""
Test vector search functionality

Interactive script to test vector search with different queries
"""
import sys
import logging
from pathlib import Path
import json

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


def load_and_display_event(event_id: str, metadata_store: MetadataStore):
    """Load and display full event details"""
    event = metadata_store.get_event(event_id)
    if event:
        print(f"\n{'='*60}")
        print(f"Event ID: {event['event_id']}")
        print(f"Source: {event['source']}")
        print(f"Authority: {event['authority']:.2f}")
        print(f"Freshness: {event['freshness']}")
        print(f"\nEmbedding Text:")
        print(f"{event['embedding_text'][:500]}...")
        print(f"\nCanonical Form:")
        canonical = json.loads(event['canonical_form'])
        print(json.dumps(canonical, indent=2)[:500])
        print(f"{'='*60}")


def test_search(vector_store: VectorStore, metadata_store: MetadataStore):
    """Interactive search testing"""
    print("\n" + "="*60)
    print("Vector Search Test Interface")
    print("="*60)
    print(f"Index contains {vector_store.index.ntotal} vectors")
    print(f"Model: {vector_store.model_name}")
    print(f"Dimension: {vector_store.dimension}")
    print("\nCommands:")
    print("  - Enter a search query")
    print("  - 'stats' - Show index statistics")
    print("  - 'detail <event_id>' - Show full event details")
    print("  - 'quit' - Exit")
    print("="*60)
    
    while True:
        try:
            query = input("\n🔍 Query: ").strip()
            
            if not query:
                continue
            
            if query.lower() == 'quit':
                break
            
            if query.lower() == 'stats':
                stats = vector_store.get_stats()
                print("\nIndex Statistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                continue
            
            if query.lower().startswith('detail '):
                event_id = query.split(' ', 1)[1]
                load_and_display_event(event_id, metadata_store)
                continue
            
            # Parse optional parameters
            top_k = 5
            source_filter = None
            
            if '|' in query:
                parts = query.split('|')
                query = parts[0].strip()
                
                for part in parts[1:]:
                    part = part.strip()
                    if part.startswith('k='):
                        top_k = int(part[2:])
                    elif part.startswith('source='):
                        source_filter = part[7:]
            
            # Perform search
            filter_metadata = {'source': source_filter} if source_filter else None
            results = vector_store.search(query, top_k=top_k, filter_metadata=filter_metadata)
            
            if not results:
                print("❌ No results found")
                continue
            
            # Display results
            print(f"\n📊 Found {len(results)} results:")
            print("-" * 60)
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Score: {result['score']:.4f} | Distance: {result['distance']:.4f}")
                print(f"   Event ID: {result['event_id']}")
                print(f"   Source: {result['metadata'].get('source', 'N/A')}")
                print(f"   Authority: {result['metadata'].get('authority', 'N/A'):.2f}")
                print(f"   Freshness: {result['metadata'].get('freshness', 'N/A')}")
                
                # Load embedding text from metadata store
                event = metadata_store.get_event(result['event_id'])
                if event:
                    text = event['embedding_text']
                    # Show first 150 chars
                    preview = text[:150] + "..." if len(text) > 150 else text
                    print(f"   Preview: {preview}")
            
            print("-" * 60)
            print(f"\nTip: Use 'detail {results[0]['event_id']}' to see full event")
            print("Tip: Add filters like '| k=10' or '| source=logs'")
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Search error: {e}", exc_info=True)


def run_predefined_tests(vector_store: VectorStore, metadata_store: MetadataStore):
    """Run predefined test queries"""
    test_queries = [
        ("trading decision buy", 5),
        ("market price RSI indicator", 3),
        ("profit and loss", 3),
        ("AI signal confidence", 5),
        ("session daily trades", 3),
    ]
    
    print("\n" + "="*60)
    print("Running Predefined Test Queries")
    print("="*60)
    
    for query, top_k in test_queries:
        print(f"\n🔍 Query: '{query}' (top_k={top_k})")
        print("-" * 60)
        
        results = vector_store.search(query, top_k=top_k)
        
        if not results:
            print("❌ No results found")
            continue
        
        for i, result in enumerate(results, 1):
            print(f"{i}. Score: {result['score']:.4f} | Event: {result['event_id'][:16]}...")
            print(f"   Source: {result['metadata'].get('source', 'N/A')}")
            
            # Load preview
            event = metadata_store.get_event(result['event_id'])
            if event:
                text = event['embedding_text']
                preview = text[:100] + "..." if len(text) > 100 else text
                print(f"   Preview: {preview}")
        
        print()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test vector search functionality"
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    parser.add_argument(
        '--query',
        type=str,
        help='Single query to test'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='Number of results to return'
    )
    
    args = parser.parse_args()
    
    # Check if index exists
    if not settings.vector_index_path.exists():
        logger.error(f"Vector index not found at {settings.vector_index_path}")
        logger.info("Run 'python scripts/build_vector_index.py' first")
        sys.exit(1)
    
    # Load vector store
    logger.info("Loading vector store...")
    vector_store = VectorStore()
    vector_store.load()
    
    # Load metadata store
    logger.info("Loading metadata store...")
    metadata_store = MetadataStore()
    
    if args.query:
        # Single query mode
        print(f"\n🔍 Query: '{args.query}'")
        results = vector_store.search(args.query, top_k=args.top_k)
        
        print(f"\n📊 Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result['score']:.4f}")
            print(f"   Event ID: {result['event_id']}")
            print(f"   Source: {result['metadata'].get('source', 'N/A')}")
            
            event = metadata_store.get_event(result['event_id'])
            if event:
                text = event['embedding_text']
                preview = text[:150] + "..." if len(text) > 150 else text
                print(f"   Preview: {preview}")
    
    elif args.interactive:
        # Interactive mode
        test_search(vector_store, metadata_store)
    
    else:
        # Run predefined tests
        run_predefined_tests(vector_store, metadata_store)
        
        # Ask if user wants interactive mode
        print("\n" + "="*60)
        response = input("Enter interactive mode? (y/N): ")
        if response.lower() == 'y':
            test_search(vector_store, metadata_store)
    
    metadata_store.close()
    logger.info("Done!")


if __name__ == "__main__":
    main()
