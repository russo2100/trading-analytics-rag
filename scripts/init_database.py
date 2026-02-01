#!/usr/bin/env python3
"""
Initialize database schema for EventHorizon DAG system.

Creates SQLite database and applies schema.sql (RAG + Trading tables).

Usage:
    python scripts/init_database.py
    python scripts/init_database.py --db data/metadata.db --force
"""

import argparse
import sqlite3
import sys
from pathlib import Path

def init_database(db_path: str, schema_path: str, force: bool = False):
    """
    Initialize database with schema.
    
    Args:
        db_path: Path to SQLite database
        schema_path: Path to schema.sql
        force: If True, drop existing tables before creating
    """
    db_file = Path(db_path)
    schema_file = Path(schema_path)
    
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_path}")
        sys.exit(1)
    
    # Check if DB already exists
    if db_file.exists() and not force:
        print(f"⚠️  Database already exists: {db_path}")
        print("   Use --force to recreate tables")
        response = input("   Continue without dropping tables? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    # Read schema
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Connect to DB
    print(f"📂 Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop tables if force mode
    if force:
        print("🗑️  Dropping existing tables...")
        drop_tables = [
            "daily_pnl", "broker_trades", "trades", "trading_events", "sessions",
            "events_fts", "query_stats", "events"
        ]
        for table in drop_tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"   Dropped: {table}")
            except sqlite3.Error as e:
                print(f"   ⚠️  {table}: {e}")
        conn.commit()
    
    # Apply schema
    print("📋 Applying schema...")
    try:
        cursor.executescript(schema_sql)
        conn.commit()
        print("✅ Schema applied successfully!")
    except sqlite3.Error as e:
        print(f"❌ Schema error: {e}")
        conn.rollback()
        sys.exit(1)
    
    # Verify tables
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n📊 Created {len(tables)} tables:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   • {table}: {count} rows")
    
    conn.close()
    print(f"\n✅ Database ready: {db_path}")


def main():
    parser = argparse.ArgumentParser(description="Initialize EventHorizon database")
    parser.add_argument(
        "--db",
        default="data/metadata.db",
        help="Path to SQLite database (default: data/metadata.db)"
    )
    parser.add_argument(
        "--schema",
        default="src/layer2_storage/schema.sql",
        help="Path to schema.sql (default: src/layer2_storage/schema.sql)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop existing tables before creating (DESTRUCTIVE!)"
    )
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    init_database(args.db, args.schema, args.force)


if __name__ == "__main__":
    main()
