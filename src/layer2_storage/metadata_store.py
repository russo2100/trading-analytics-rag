"""
SQLite Metadata Store wrapper
Responsibility: Store structured metadata, enable filtering queries
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

from ..config import settings
from ..layer1_ingestion.models import IngestedEvent

logger = logging.getLogger(__name__)


class MetadataStore:
    """SQLite-based metadata store"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize metadata store
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or settings.sqlite_db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return dict-like rows
        
        self._init_schema()
        logger.info(f"Initialized MetadataStore at {self.db_path}")
    
    def _init_schema(self):
        """Initialize database schema from schema.sql"""
        schema_file = Path(__file__).parent / "schema.sql"
        
        if not schema_file.exists():
            logger.error(f"schema.sql not found at {schema_file}")
            return
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        self.conn.executescript(schema_sql)
        self.conn.commit()
        logger.info("Database schema initialized")
    
    def insert_event(self, event: IngestedEvent):
        """
        Insert IngestedEvent into database
        
        Args:
            event: IngestedEvent to store
        """
        cursor = self.conn.cursor()
        
        # Extract data_period
        data_period = event.metadata.get("data_period")
        data_period_start = data_period[0] if data_period else None
        data_period_end = data_period[1] if data_period else None
        
        cursor.execute("""
            INSERT OR REPLACE INTO events (
                event_id, source, embedding_text, canonical_form,
                authority, freshness, data_period_start, data_period_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.source,
            event.embedding_text,
            json.dumps(event.canonical_form),
            event.metadata["authority"],
            event.metadata["freshness"],
            data_period_start,
            data_period_end,
        ))
        
        self.conn.commit()
    
    def bulk_insert_events(self, events: List[IngestedEvent]):
        """Bulk insert events (faster than individual inserts)"""
        cursor = self.conn.cursor()
        
        data = []
        for event in events:
            data_period = event.metadata.get("data_period")
            data_period_start = data_period[0] if data_period else None
            data_period_end = data_period[1] if data_period else None
            
            data.append((
                event.event_id,
                event.source,
                event.embedding_text,
                json.dumps(event.canonical_form),
                event.metadata["authority"],
                event.metadata["freshness"],
                data_period_start,
                data_period_end,
            ))
        
        cursor.executemany("""
            INSERT OR REPLACE INTO events (
                event_id, source, embedding_text, canonical_form,
                authority, freshness, data_period_start, data_period_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        
        self.conn.commit()
        logger.info(f"Bulk inserted {len(events)} events")
    
    def get_event(self, event_id: str) -> Optional[Dict]:
        """Retrieve event by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def search_metadata(
        self,
        source: Optional[str] = None,
        min_authority: Optional[float] = None,
        freshness_hours: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search events by metadata filters
        
        Args:
            source: Filter by source ('eia', 'logs', etc.)
            min_authority: Minimum authority score
            freshness_hours: Only events within last N hours
            limit: Max results
            
        Returns:
            List of event dicts
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        if min_authority is not None:
            query += " AND authority >= ?"
            params.append(min_authority)
        
        if freshness_hours is not None:
            query += " AND freshness >= datetime('now', ? || ' hours')"
            params.append(-freshness_hours)
        
        query += " ORDER BY freshness DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]

    def search_text(self, query_text: str, limit: int = 10) -> List[Dict]:
        """
        Full-text search using SQLite FTS5
        Returns list of events matching keywords, sorted by rank
        """
        cursor = self.conn.cursor()
        
        # Safe FTS query using parameters
        # We search in events_fts virtual table which is linked to events
        sql = """
            SELECT e.*, fts.rank 
            FROM events e
            JOIN events_fts fts ON e.rowid = fts.rowid
            WHERE events_fts MATCH ?
            ORDER BY fts.rank
            LIMIT ?
        """
        
        try:
            # FTS5 expects query syntax, simple words work fine
            # For more complex queries, might need sanitization
            cursor.execute(sql, (query_text, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS search failed for '{query_text}': {e}")
            return []

    
    def count_events(self, source: Optional[str] = None) -> int:
        """Count total events (optionally by source)"""
        cursor = self.conn.cursor()
        
        if source:
            cursor.execute("SELECT COUNT(*) FROM events WHERE source = ?", (source,))
        else:
            cursor.execute("SELECT COUNT(*) FROM events")
        
        return cursor.fetchone()[0]
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("Closed MetadataStore connection")
