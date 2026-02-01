#!/usr/bin/env python3
"""
Check database contents (replaces sqlite3 CLI for Windows).

Usage:
    python scripts/check_database.py
    python scripts/check_database.py --db data/metadata.db
"""

import argparse
import sqlite3
from pathlib import Path


def check_database(db_path: str):
    """Display database statistics."""
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"📊 Database: {db_path}\n")
    
    # Count tables
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"📋 Tables ({len(tables)}):")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   • {table}: {count:,} rows")
    
    # Trading events by session
    print("\n📅 Events by session:")
    cursor.execute("""
        SELECT 
            session_id,
            COUNT(*) as events,
            SUM(CASE WHEN action IS NOT NULL AND action != 'NOOP' THEN 1 ELSE 0 END) as trades,
            MIN(timestamp) as first,
            MAX(timestamp) as last
        FROM trading_events
        GROUP BY session_id
        ORDER BY session_id DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()  # ← ИСПРАВЛЕНИЕ: сначала fetch, потом итерация
    for row in rows:
        print(f"   {row['session_id']}: {row['events']} events, {row['trades']} trades")
        print(f"      {row['first']} → {row['last']}")
    
    # Sessions summary
    print("\n🎯 Sessions summary:")
    cursor.execute("""
        SELECT 
            session_id,
            date,
            total_cycles,
            total_trades,
            final_lots,
            ROUND(final_pnl_pct, 2) as pnl
        FROM sessions
        ORDER BY date DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()  # ← ИСПРАВЛЕНИЕ
    if not rows:
        print("   (empty)")
    else:
        for row in rows:
            print(f"   {row['date']} ({row['session_id']}): "
                  f"{row['total_cycles']} cycles, {row['total_trades']} trades, "
                  f"lots={row['final_lots']}, pnl={row['pnl']}%")
    
    # Check for NULL actions
    print("\n⚠️  Data quality checks:")
    cursor.execute("SELECT COUNT(*) FROM trading_events WHERE action IS NULL")
    null_actions = cursor.fetchone()[0]
    print(f"   • NULL actions: {null_actions}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM trading_events 
        GROUP BY event_id 
        HAVING COUNT(*) > 1
    """)
    duplicates = len(cursor.fetchall())
    print(f"   • Duplicate event_ids: {duplicates}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM trades t
        LEFT JOIN trading_events e ON t.event_id = e.event_id
        WHERE e.event_id IS NULL
    """)
    orphaned = cursor.fetchone()[0]
    print(f"   • Orphaned trades: {orphaned}")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Check database contents")
    parser.add_argument("--db", default="data/metadata.db", help="Database path")
    args = parser.parse_args()
    
    check_database(args.db)


if __name__ == "__main__":
    main()
