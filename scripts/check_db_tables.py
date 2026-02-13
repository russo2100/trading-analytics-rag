#!/usr/bin/env python3
"""Quick script to check database tables"""
import sqlite3

conn = sqlite3.connect('data/metadata.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables: {tables}")

# Check events table
if 'events' in tables:
    cursor.execute("SELECT COUNT(*) FROM events")
    count = cursor.fetchone()[0]
    print(f"Events count: {count}")
    
    # Show sample event
    cursor.execute("SELECT * FROM events LIMIT 1")
    print(f"Sample event: {cursor.fetchone()}")
else:
    print("⚠️ 'events' table not found!")

conn.close()
