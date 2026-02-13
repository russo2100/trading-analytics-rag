"""
Migrate trading_events → events table for RAG vector search.
Generates embedding_text from trading event fields.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
import json

project_root = Path(__file__).parent.parent
db_path = project_root / "data" / "metadata.db"


def create_embedding_text(event: dict) -> str:
    """Create searchable text from trading event."""
    parts = [
        f"Timestamp: {event['timestamp']}",
        f"Session: {event['session_id']}",
        f"Cycle: {event['cycle']}",
        f"Price: ${event['price']:.2f}" if event['price'] else "",
        f"RSI: {event['rsi']:.1f}" if event['rsi'] else "",
        f"Trend: {event['trend_ltf']}/{event['trend_htf']}" if event['trend_ltf'] else "",
        f"Action: {event['action']}",
        f"Reason: {event['reason']}" if event['reason'] else "",
        f"Signal: {event['ai_signal']}" if event['ai_signal'] else "",
        f"Confidence: {event['ai_confidence']}" if event['ai_confidence'] else "",
    ]
    return " | ".join([p for p in parts if p])


def migrate():
    """Migrate trading_events → events table."""
    print(f"📂 Migrating data from trading_events → events")
    print(f"📊 Database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Read trading_events
    cursor.execute("SELECT * FROM trading_events ORDER BY timestamp")
    trading_events = [dict(row) for row in cursor.fetchall()]
    print(f"✅ Loaded {len(trading_events)} trading events")
    
    # Check existing events
    cursor.execute("SELECT COUNT(*) FROM events")
    existing = cursor.fetchone()[0]
    if existing > 0:
        response = input(f"⚠️  events table has {existing} rows. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Aborted")
            return
        cursor.execute("DELETE FROM events")
        print(f"🗑️  Cleared {existing} existing events")
    
    # Migrate
    inserted = 0
    for te in trading_events:
        embedding_text = create_embedding_text(te)
        canonical_form = json.dumps({
            "event_id": te["event_id"],
            "session_id": te["session_id"],
            "timestamp": te["timestamp"],
            "action": te["action"],
            "price": te["price"],
            "reason": te["reason"]
        })
        
        cursor.execute("""
            INSERT INTO events (
                event_id, source, embedding_text, canonical_form,
                authority, freshness, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            te["event_id"],
            "trading_bot_log",
            embedding_text,
            canonical_form,
            1.0,  # authority: bot logs = ground truth
            te["timestamp"],
            datetime.now().isoformat()
        ))
        inserted += 1
    
    conn.commit()
    print(f"✅ Migrated {inserted} events")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM events")
    total = cursor.fetchone()[0]
    print(f"📊 events table now has {total} rows")
    
    conn.close()


if __name__ == "__main__":
    migrate()
