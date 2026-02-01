#!/usr/bin/env python3
"""Test normalizer on sample event."""

import json
import sys
sys.path.insert(0, ".")

from src.layer1_ingestion.normalizers import normalize_bot_log_v1_legacy

# Sample event from 22.01.2026.jsonl
sample = {
    "timestamp": "2026-01-20T08:50:45.534384+03:00",
    "cycle": 1,
    "input_state": {
        "price": 3.591,
        "rsi": 70.47,
        "trend": "FLAT",
        "lots": 0,
        "pnl_pct": 0.0,
        "holding_hours": 0.0,
        "minutes_to_clearing": 999,
        "bias": "NEUTRAL"
    },
    "decision": {
        "ai_signal": "HOLD",
        "ai_confidence": 75,
        "action": "NOOP",
        "reason": "Waiting. B:0.60 S:0.40 RSI:70.5",
        "rules": {
            "bias": "NEUTRAL",
            "risk_mode": "CONSERVATIVE"
        },
        "forced_entry": False,
        "consecutive_signals": 0,
        "avg_confidence": 0.0
    }
}

print("Testing normalize_bot_log_v1_legacy()...\n")

try:
    normalized = normalize_bot_log_v1_legacy(sample)
    
    print("✅ Normalization successful!")
    print(f"\nKey fields:")
    print(f"  event_id: {normalized['event_id']}")
    print(f"  session_id: {normalized['session_id']}")
    print(f"  action: {normalized['action']}")
    print(f"  ai_signal: {normalized['ai_signal']}")
    print(f"  price: {normalized['price']}")
    print(f"  lots: {normalized['lots']}")
    
    print(f"\nFull normalized event:")
    print(json.dumps(normalized, indent=2, default=str))
    
except Exception as e:
    print(f"❌ Normalization failed: {e}")
    import traceback
    traceback.print_exc()
