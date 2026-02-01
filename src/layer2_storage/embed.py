"""
Layer2: Embeddings + FAISS Index
"""
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List
from src.layer1_ingestion.models import IngestedEvent
import os

# Global model (384 dim)
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_pipeline(events: List[IngestedEvent], index_path: str) -> str:
    """IngestedEvent[] → FAISS index"""
    
    if not events:
        raise ValueError("No events to embed")
    
    # 1. Extract texts + metadata IDs
    texts = [e.embedding_text for e in events]
    ids = [e.event_id for e in events]
    
    print(f"Embedding {len(texts)} events...")
    
    # 2. Generate embeddings (batch)
    embeddings = model.encode(texts, batch_size=32)

    
    # 3. FAISS Index (FlatL2 — exact search)
    d = embeddings.shape[1]  # 384
    index = faiss.IndexFlatL2(d)
    index.add(embeddings.astype('float32'))
    
    # 4. Save index + metadata
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)
    
    # Save metadata (event_ids)
    meta_path = index_path.replace('.faiss', '.jsonl')
    with open(meta_path, 'w', encoding='utf-8') as f:
        for event_id in ids:
            f.write(f"{event_id}\n")
    
    print(f"✅ Saved index: {index_path} (dim={d}, ntotal={index.ntotal})")
    print(f"   Metadata: {meta_path}")
    
    return index_path
