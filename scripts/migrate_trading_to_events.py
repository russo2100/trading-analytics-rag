#!/usr/bin/env python3
"""
Migrate trading_events data to events table for RAG system

This script:
1. Reads trading_events from database
2. Converts them to IngestedEvent format
3. Inserts into events table for RAG retrieval
"""
import sys
import logging
import json
from pathlib import Path
from datetime import datetime
import sqlite3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_embedding_text(event: dict) -> str:
    """
    Create embedding text from trading event
    
    Args:
        event: Trading event dict
        
    Returns:
        Formatted text for embedding
    """
    parts = []
    
    # Basic info
    parts.append(f"Trading Decision on {event['timestamp']}")
    
    # Market data
    if event.get('price'):
        parts.append(f"Price: ${event['price']:.2f}")
    if event.get('rsi'):
        parts.append(f"RSI: {event['rsi']:.1f}")
    if event.get('trend_ltf'):
        parts.append(f"Trend LTF: {event['trend_ltf']}")
    if event.get('trend_htf'):
        parts.append(f"Trend HTF: {event['trend_htf']}")
    
    # Position
    if event.get('lots') is not None:
        parts.append(f"Position: {event['lots']} lots")
    if event.get('pnl_pct') is not None:
        parts.append(f"P&L: {event['pnl_pct']:.2f}%")
    
    # AI Decision
    if event.get('ai_signal'):
        parts.append(f"AI Signal: {event['ai_signal']}")
    if event.get('ai_confidence'):
        parts.append(f"Confidence: {event['ai_confidence']}%")
    if event.get('action'):
        parts.append(f"Action: {event['action']}")
    if event.get('reason'):
        parts.append(f"Reason: {event['reason']}")
    
    # Market conditions
    if event.get('sleeping_market'):
        parts.append(f"Sleeping Market: {event['sleeping_reason']}")
    if event.get('cooldown_active'):
        parts.append(f"Cooldown: {event['cooldown_remaining']} cycles")
    
    return ". ".join(parts)


def create_canonical_form(event: dict) -> dict:
    """
    Create canonical form from trading event
    
    Args:
        event: Trading event dict
        
    Returns:
        Canonical form dict
    """
    return {
        "event_id": event['event_id'],
        "session_id": event['session_id'],
        "timestamp": event['timestamp'],
        "cycle": event.get('cycle'),
        "market_data": {
            "price": event.get('price'),
            "rsi": event.get('rsi'),
            "trend_ltf": event.get('trend_ltf'),
            "trend_htf": event.get('trend_htf'),
        },
        "position": {
            "lots": event.get('lots'),
            "pnl_pct": event.get('pnl_pct'),
            "position_pnl_pct": event.get('position_pnl_pct'),
        },
        "decision": {
            "ai_signal": event.get('ai_signal'),
            "ai_confidence": event.get('ai_confidence'),
            "bias": event.get('bias'),
            "action": event.get('action'),
            "reason": event.get('reason'),
        },
        "market_conditions": {
            "sleeping_market": event.get('sleeping_market'),
            "sleeping_reason": event.get('sleeping_reason'),
            "cooldown_active": event.get('cooldown_active'),
        }
    }


def migrate_trading_events(limit: int = None):
    """
    Migrate trading_events to events table
    
    Args:
        limit: Optional limit on number of events to migrate
    """
    db_path = settings.sqlite_db_path
    
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return
    
    logger.info("=" * 60)
    logger.info("Migrating Trading Events to RAG Events Table")
    logger.info("=" * 60)
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if events table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
    if not cursor.fetchone():
        logger.error("Events table not found. Run 'python scripts/init_database.py' first")
        conn.close()
        return
    
    # Get trading events
    query = "SELECT * FROM trading_events ORDER BY timestamp DESC"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    trading_events = [dict(row) for row in cursor.fetchall()]
    
    logger.info(f"Found {len(trading_events)} trading events")
    
    if not trading_events:
        logger.warning("No trading events found")
        conn.close()
        return
    
    # Migrate events
    migrated_count = 0
    skipped_count = 0
    
    for event in trading_events:
        # Check if already exists
        cursor.execute("SELECT event_id FROM events WHERE event_id = ?", (event['event_id'],))
        if cursor.fetchone():
            skipped_count += 1
            continue
        
        # Create embedding text and canonical form
        embedding_text = create_embedding_text(event)
        canonical_form = create_canonical_form(event)
        
        # Insert into events table
        try:
            cursor.execute("""
                INSERT INTO events (
                    event_id, source, embedding_text, canonical_form,
                    authority, freshness, data_period_start, data_period_end
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event['event_id'],
                'logs',  # source
                embedding_text,
                json.dumps(canonical_form),
                0.9,  # authority (high for bot logs)
                event['timestamp'],  # freshness
                event['timestamp'],  # data_period_start
                event['timestamp']   # data_period_end
            ))
            migrated_count += 1
            
            if migrated_count % 100 == 0:
                logger.info(f"Migrated {migrated_count} events...")
                
        except Exception as e:
            logger.error(f"Error migrating event {event['event_id']}: {e}")
            continue
    
    # Commit changes
    conn.commit()
    
    # Verify migration
    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info("=" * 60)
    logger.info("Migration Complete")
    logger.info("=" * 60)
    logger.info(f"Migrated: {migrated_count} events")
    logger.info(f"Skipped (duplicates): {skipped_count} events")
    logger.info(f"Total events in database: {total_events}")
    logger.info("=" * 60)
    
    logger.info("\n✅ Next step: Build vector index")
    logger.info("   python scripts/build_vector_index.py")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate trading_events to events table for RAG"
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of events to migrate (for testing)'
    )
    
    args = parser.parse_args()
    
    try:
        migrate_trading_events(limit=args.limit)
    except Exception as e:
        logger.error(f"Error during migration: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
