#!/usr/bin/env python3
"""
Inspect structure of JSONL log files.

Usage:
    python scripts/inspect_logs.py data/raw/22.01.2026.jsonl
    python scripts/inspect_logs.py data/raw/decisions_20260129.jsonl
"""

import json
import sys

log_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/22.01.2026.jsonl"

print(f"📄 Inspecting: {log_path}\n")

with open(log_path, 'r', encoding='utf-8') as f:  # ← ИСПРАВЛЕНИЕ: добавлен encoding
    # Read first 3 events
    for i in range(3):
        line = f.readline()
        if not line:
            break
        
        event = json.loads(line)
        print(f"=== Event {i+1} ===")
        print(f"Keys: {list(event.keys())}")
        print(f"action: {repr(event.get('action'))}")
        print(f"decision: {repr(event.get('decision'))}")
        print(f"trade_action: {repr(event.get('trade_action'))}")
        print(f"ai_signal: {repr(event.get('ai_signal'))}")
        print(f"signal: {repr(event.get('signal'))}")
        
        # Print full event (first 800 chars)
        event_str = json.dumps(event, indent=2, ensure_ascii=False)
        print(f"\nFull event (truncated):\n{event_str[:800]}")
        print("-" * 60)
