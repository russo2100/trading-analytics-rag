"""
Unit tests for VectorStore
"""
import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil

from src.layer2_storage.vector_store import VectorStore


@pytest.fixture
def temp_index_path():
    """Create temporary directory for index"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_events():
    """Sample events for testing"""
    return {
        'event_ids': ['event_1', 'event_2', 'event_3'],
        'texts': [
            'Trading bot made a BUY decision based on RSI indicator',
            'Market price increased to 3.50 USD with high volume',
            'AI signal confidence is 85% for SELL action'
        ],
        'metadata': [
            {'source': 'logs', 'authority': 0.95},
            {'source': 'logs', 'authority': 0.90},
            {'source': 'logs', 'authority': 0.92}
        ]
    }


class TestVectorStore:
    """Test VectorStore functionality"""
    
    def test_initialization(self):
        """Test VectorStore initialization"""
        store = VectorStore()
        
        assert store.model_name is not None
        assert store.dimension > 0
        assert store.index.ntotal == 0
        assert len(store.event_ids) == 0
        assert len(store.metadata) == 0
    
    def test_add_events(self, sample_events):
        """Test adding events to vector store"""
        store = VectorStore()
        
        store.add_events(
            sample_events['event_ids'],
            sample_events['texts'],
            sample_events['metadata']
        )
        
        assert store.index.ntotal == 3
        assert len(store.event_ids) == 3
        assert len(store.metadata) == 3
        assert store.event_ids == sample_events['event_ids']
    
    def test_add_events_without_metadata(self, sample_events):
        """Test adding events without metadata"""
        store = VectorStore()
        
        store.add_events(
            sample_events['event_ids'],
            sample_events['texts']
        )
        
        assert store.index.ntotal == 3
        assert len(store.metadata) == 0
    
    def test_add_events_validation(self, sample_events):
        """Test validation of add_events parameters"""
        store = VectorStore()
        
        # Mismatched lengths
        with pytest.raises(ValueError):
            store.add_events(
                sample_events['event_ids'][:2],
                sample_events['texts']
            )
        
        # Mismatched metadata length
        with pytest.raises(ValueError):
            store.add_events(
                sample_events['event_ids'],
                sample_events['texts'],
                sample_events['metadata'][:2]
            )
    
    def test_search(self, sample_events):
        """Test vector search"""
        store = VectorStore()
        store.add_events(
            sample_events['event_ids'],
            sample_events['texts'],
            sample_events['metadata']
        )
        
        # Search for similar events
        results = store.search("trading decision buy", top_k=2)
        
        assert len(results) <= 2
        assert all('event_id' in r for r in results)
        assert all('score' in r for r in results)
        assert all('distance' in r for r in results)
        assert all('metadata' in r for r in results)
        
        # Scores should be between 0 and 1
        assert all(0 <= r['score'] <= 1 for r in results)
        
        # Results should be sorted by score (descending)
        scores = [r['score'] for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_search_with_filter(self, sample_events):
        """Test search with metadata filters"""
        store = VectorStore()
        
        # Add events with different sources
        event_ids = ['e1', 'e2', 'e3']
        texts = ['trading log', 'weather data', 'news article']
        metadata = [
            {'source': 'logs'},
            {'source': 'weather'},
            {'source': 'news'}
        ]
        
        store.add_events(event_ids, texts, metadata)
        
        # Search with filter
        results = store.search(
            "trading",
            top_k=10,
            filter_metadata={'source': 'logs'}
        )
        
        # Should only return logs
        assert all(r['metadata']['source'] == 'logs' for r in results)
    
    def test_search_empty_index(self):
        """Test search on empty index"""
        store = VectorStore()
        results = store.search("test query")
        
        assert results == []
    
    def test_get_by_id(self, sample_events):
        """Test getting event by ID"""
        store = VectorStore()
        store.add_events(
            sample_events['event_ids'],
            sample_events['texts'],
            sample_events['metadata']
        )
        
        # Get existing event
        result = store.get_by_id('event_1')
        assert result is not None
        assert result['event_id'] == 'event_1'
        assert result['metadata']['source'] == 'logs'
        
        # Get non-existing event
        result = store.get_by_id('non_existing')
        assert result is None
    
    def test_save_and_load(self, sample_events, temp_index_path):
        """Test saving and loading index"""
        # Create and populate store
        store1 = VectorStore()
        store1.add_events(
            sample_events['event_ids'],
            sample_events['texts'],
            sample_events['metadata']
        )
        
        # Save
        store1.save(temp_index_path)
        
        # Check files exist
        assert (temp_index_path / "faiss.index").exists()
        assert (temp_index_path / "event_ids.pkl").exists()
        assert (temp_index_path / "metadata.json").exists()
        assert (temp_index_path / "index_info.json").exists()
        
        # Load into new store
        store2 = VectorStore()
        store2.load(temp_index_path)
        
        # Verify loaded data
        assert store2.index.ntotal == 3
        assert store2.event_ids == sample_events['event_ids']
        assert len(store2.metadata) == 3
        
        # Test search on loaded index
        results = store2.search("trading decision", top_k=1)
        assert len(results) > 0
    
    def test_clear(self, sample_events):
        """Test clearing the index"""
        store = VectorStore()
        store.add_events(
            sample_events['event_ids'],
            sample_events['texts'],
            sample_events['metadata']
        )
        
        assert store.index.ntotal == 3
        
        store.clear()
        
        assert store.index.ntotal == 0
        assert len(store.event_ids) == 0
        assert len(store.metadata) == 0
    
    def test_get_stats(self, sample_events):
        """Test getting statistics"""
        store = VectorStore()
        store.add_events(
            sample_events['event_ids'],
            sample_events['texts'],
            sample_events['metadata']
        )
        
        stats = store.get_stats()
        
        assert stats['total_vectors'] == 3
        assert stats['dimension'] > 0
        assert stats['model_name'] is not None
        assert stats['has_metadata'] is True
        assert stats['metadata_count'] == 3
    
    def test_batch_operations(self):
        """Test batch operations with many events"""
        store = VectorStore()
        
        # Create 100 events
        event_ids = [f'event_{i}' for i in range(100)]
        texts = [f'Sample text number {i} for testing' for i in range(100)]
        metadata = [{'source': 'test', 'index': i} for i in range(100)]
        
        store.add_events(event_ids, texts, metadata)
        
        assert store.index.ntotal == 100
        assert len(store.event_ids) == 100
        
        # Search should work
        results = store.search("sample text", top_k=10)
        assert len(results) == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
