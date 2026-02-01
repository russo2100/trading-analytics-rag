#!/usr/bin/env python3
"""
Trading logs ingestion script (специализированный для trading_events таблицы).

Импортирует bot logs (JSONL v1/v2) в SQLite: trading_events, sessions, trades.
НЕ использует RAG-pipeline (VectorStore/MetadataStore).

Usage:
    python scripts/ingest_trading_logs.py --source data/raw/shadow_agents_log_20260130.jsonl
    python scripts/ingest_trading_logs.py --source data/raw/22.01.2026.jsonl --format v1
    python scripts/ingest_trading_logs.py --source data/raw/*.jsonl --batch
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import glob

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.layer1_ingestion.normalizers import (
    normalize_bot_log_v1,
    normalize_bot_log_v2,
    extract_trade_from_event
)
from src.layer1_ingestion.id_generators import generate_session_id


class TradingLogIngester:
    """Specialized ingester for trading logs (не RAG-pipeline)."""
    
    def __init__(self, db_path: str = "data/metadata.db"):
        self.db_path = db_path
        self.conn: sqlite3.Connection = None  # type: ignore
        
    def connect(self):
        """Connect to SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        print(f"✅ Connected to {self.db_path}")
        
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def _ensure_connected(self):
        """Ensure database connection is active."""
        if self.conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
    
    def detect_format(self, log_path: str) -> str:
        """
        Auto-detect log format (v1 or v2).
        
        v1: has account_snapshot
        v2: has sleeping_market
        """
        with open(log_path, 'r', encoding='utf-8') as f:  # ← ИСПРАВЛЕНИЕ
            first_line = f.readline()
            if not first_line:
                raise ValueError(f"Empty file: {log_path}")
            
            event = json.loads(first_line)
            
            if "sleeping_market" in event or "daily_trades_count" in event:
                return "v2"
            elif "account_snapshot" in event:
                return "v1"
            else:
                print(f"⚠️  Unknown format, defaulting to v2")
                return "v2"

    
    def load_jsonl(self, log_path: str) -> List[Dict[str, Any]]:
        """Load JSONL file."""
        events = []
        with open(log_path, 'r', encoding='utf-8') as f:  # ← ИСПРАВЛЕНИЕ
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Line {line_num}: Invalid JSON: {e}")
                    continue
        
        return events

    
    def normalize_events(self, events: List[Dict], format_version: str) -> List[Dict]:  # ← ДОЛЖЕН БЫТЬ ВНУТРИ КЛАССА
        """Normalize raw events to trading_events schema."""
        normalized = []
        normalizer = normalize_bot_log_v2 if format_version == "v2" else normalize_bot_log_v1
        
        for raw_event in events:
            try:
                norm_event = normalizer(raw_event)
                normalized.append(norm_event)
            except Exception as e:
                print(f"⚠️  Normalization failed: {e}")
                continue
        
        return normalized
    
    def insert_events(self, events: List[Dict]) -> int:
        """Insert trading_events into database (batch)."""
        self._ensure_connected()
        
        if not events:
            return 0
        
        fields = list(events[0].keys())
        placeholders = ', '.join(['?' for _ in fields])
        query = f"""
            INSERT OR IGNORE INTO trading_events ({', '.join(fields)})
            VALUES ({placeholders})
        """
        
        cursor = self.conn.cursor()
        inserted = 0
        
        for event in events:
            try:
                values = [event[f] for f in fields]
                cursor.execute(query, values)
                if cursor.rowcount > 0:
                    inserted += 1
            except sqlite3.IntegrityError:
                continue
            except Exception as e:
                print(f"⚠️  Insert failed: {e}")
                continue
        
        self.conn.commit()
        return inserted
    
    def insert_trades(self, events: List[Dict]) -> int:
        """Extract and insert trades from events."""
        self._ensure_connected()
        
        trades = []
        for event in events:
            trade = extract_trade_from_event(event)
            if trade:
                trades.append(trade)
        
        if not trades:
            return 0
        
        fields = list(trades[0].keys())
        placeholders = ', '.join(['?' for _ in fields])
        query = f"""
            INSERT OR IGNORE INTO trades ({', '.join(fields)})
            VALUES ({placeholders})
        """
        
        cursor = self.conn.cursor()
        inserted = 0
        
        for trade in trades:
            try:
                values = [trade[f] for f in fields]
                cursor.execute(query, values)
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"⚠️  Trade insert failed: {e}")
                continue
        
        self.conn.commit()
        return inserted
    
    def upsert_session(self, events: List[Dict]):
        """Create or update session record."""
        self._ensure_connected()
        
        if not events:
            print("   ⚠️  No events to process for sessions")
            return
        
        print(f"   Processing {len(events)} events for sessions...")
        
        # Group events by session_id
        sessions = {}
        for event in events:
            sid = event["session_id"]
            if sid not in sessions:
                sessions[sid] = {
                    "events": [],
                    "trades_count": 0
                }
            sessions[sid]["events"].append(event)
            
            # Считать trades только если action не NULL и не NOOP
            action = event.get("action")
            if action is not None and action != "NOOP" and action != "":
                sessions[sid]["trades_count"] += 1
        
        print(f"   Found {len(sessions)} unique sessions: {list(sessions.keys())}")
        
        # Upsert each session
        cursor = self.conn.cursor()
        
        for session_id, data in sessions.items():
            evs = data["events"]
            
            # Extract session metadata
            timestamps = [e["timestamp"] for e in evs]
            first_ts = min(timestamps)
            last_ts = max(timestamps)
            
            total_cycles = len(evs)
            total_trades = data["trades_count"]
            
            initial_lots = evs[0].get("lots", 0)
            final_lots = evs[-1].get("lots", 0)
            
            initial_pnl = evs[0].get("pnl_pct", 0.0)
            final_pnl = evs[-1].get("pnl_pct", 0.0)
            
            sleeping_cycles = sum(1 for e in evs if e.get("sleeping_market"))
            cooldown_cycles = sum(1 for e in evs if e.get("cooldown_active"))
            
            # Parse date from timestamp (исправление для ISO format с timezone)
            from datetime import datetime
            date = datetime.fromisoformat(first_ts.replace('Z', '+00:00')).date()
            
            # Upsert query
            query = """
                INSERT INTO sessions (
                    session_id, date, first_timestamp, last_timestamp,
                    total_cycles, total_trades,
                    initial_lots, final_lots, initial_pnl_pct, final_pnl_pct,
                    sleeping_market_cycles, cooldown_cycles
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_timestamp = excluded.last_timestamp,
                    total_cycles = excluded.total_cycles,
                    total_trades = excluded.total_trades,
                    final_lots = excluded.final_lots,
                    final_pnl_pct = excluded.final_pnl_pct,
                    sleeping_market_cycles = excluded.sleeping_market_cycles,
                    cooldown_cycles = excluded.cooldown_cycles
            """
            
            try:
                cursor.execute(query, (
                    session_id, date, first_ts, last_ts,
                    total_cycles, total_trades,
                    initial_lots, final_lots, initial_pnl, final_pnl,
                    sleeping_cycles, cooldown_cycles
                ))
                print(f"      {session_id}: {total_cycles} cycles, {total_trades} trades")
            except Exception as e:
                print(f"      ⚠️  Failed to upsert session {session_id}: {e}")
                import traceback
                traceback.print_exc()
        
        self.conn.commit()
        print(f"   ✅ Committed {len(sessions)} sessions to database")






def main():
    parser = argparse.ArgumentParser(description="Ingest trading bot logs into SQLite")
    parser.add_argument("--source", required=True, help="Path to JSONL file or glob pattern")
    parser.add_argument("--format", choices=["v1_legacy", "v1", "v2", "auto"], default="auto", help="Log format version")
    parser.add_argument("--db", default="data/metadata.db", help="SQLite database path")
    parser.add_argument("--batch", action="store_true", help="Process multiple files (glob pattern)")
    
    args = parser.parse_args()
    
    # Expand glob pattern
    if args.batch or "*" in args.source:
        files = glob.glob(args.source)
        if not files:
            print(f"❌ No files match pattern: {args.source}")
            sys.exit(1)
    else:
        files = [args.source]
    
    print(f"📂 Processing {len(files)} file(s)...")
    
    ingester = TradingLogIngester(args.db)
    ingester.connect()
    
    total_events = 0
    total_trades = 0
    
    for file_path in files:
        print(f"\n📄 {file_path}")
        
        # Auto-detect format
        if args.format == "auto":
            format_version = ingester.detect_format(file_path)
        else:
            format_version = args.format
        
        print(f"   Format: {format_version}")
        
        # Load and normalize
        raw_events = ingester.load_jsonl(file_path)
        normalized = ingester.normalize_events(raw_events, format_version)
        
        print(f"   Loaded: {len(raw_events)} raw → {len(normalized)} normalized")
        
        # Insert into DB
        inserted_events = ingester.insert_events(normalized)
        inserted_trades = ingester.insert_trades(normalized)
        
        print(f"   Inserted: {inserted_events} events, {inserted_trades} trades")
        
        # ← ДОБАВЬ ЭТИ 3 СТРОКИ ↓
        print(f"   Updating sessions...")
        ingester.upsert_session(normalized)
        print(f"   ✅ Sessions updated!")
        
        total_events += inserted_events
        total_trades += inserted_trades
    
    ingester.close()
    
    print(f"\n✅ Complete! Total: {total_events} events, {total_trades} trades")


if __name__ == "__main__":
    main()



def detect_format(self, log_path: str) -> str:
    """
    Auto-detect log format (v1_legacy, v1, v2).
    
    v1_legacy: has input_state + decision (nested structure) - 22.01.2026
    v1: has account_snapshot (flat structure) - 29.01.2026
    v2: has sleeping_market, daily_trades_count - 30.01.2026
    """
    with open(log_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        if not first_line:
            raise ValueError(f"Empty file: {log_path}")
        
        event = json.loads(first_line)
        
        # Check for v2 markers
        if "sleeping_market" in event or "daily_trades_count" in event:
            return "v2"
        
        # Check for v1 markers
        if "account_snapshot" in event:
            return "v1"
        
        # Check for v1_legacy markers (nested structure)
        if "input_state" in event and "decision" in event:
            return "v1_legacy"
        
        # Default to v2 (newest format)
        print(f"⚠️  Cannot determine format, defaulting to v2: {log_path}")
        return "v2"

def normalize_events(self, events: List[Dict], format_version: str) -> List[Dict]:
    """Normalize raw events to trading_events schema."""
    normalized = []
    
    # Select normalizer based on format
    if format_version == "v2":
        normalizer = normalize_bot_log_v2
    elif format_version == "v1_legacy":
        from src.layer1_ingestion.normalizers import normalize_bot_log_v1_legacy
        normalizer = normalize_bot_log_v1_legacy
    else:  # v1
        normalizer = normalize_bot_log_v1
    
    for raw_event in events:
        try:
            norm_event = normalizer(raw_event)
            normalized.append(norm_event)
        except Exception as e:
            print(f"⚠️  Normalization failed: {e}")
            continue
    
    return normalized


if __name__ == "__main__":
    main()
