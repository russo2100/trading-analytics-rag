#!/usr/bin/env python3
import sys
import asyncio
from pathlib import Path
import os

root_dir = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root_dir))

from src.layer1_ingestion.loaders import load_jsonl_logs
from src.layer1_ingestion.normalizers import normalize_bot_log
from src.layer2_storage.embed import embed_pipeline

async def main():
    os.makedirs("artifacts", exist_ok=True)

    logs = await load_jsonl_logs(Path("data/raw/21.01.2026.jsonl"))
    events = [normalize_bot_log(log) for log in logs[:50]]
    print(f"Ingested {len(events)} events")

    index_path = "artifacts/trading.faiss"
    embed_pipeline(events, index_path)
    print(f"✅ Layer2 OK: {index_path}")

if __name__ == "__main__":
    asyncio.run(main())
