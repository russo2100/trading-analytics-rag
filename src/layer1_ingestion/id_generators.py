"""
ID generation utilities for trading events.
Deterministic ID generation to prevent duplicates on re-import.
"""

from datetime import datetime
import re
from typing import Optional


def generate_event_id(timestamp: datetime, cycle: int) -> str:
    """
    Generate deterministic event_id from timestamp and cycle.
    
    Format: YYYYMMDD_cycle_unixtime
    Example: 20260130_242_1738245052
    
    Args:
        timestamp: Event timestamp
        cycle: Cycle number from bot log
        
    Returns:
        Unique event_id string
    """
    date_str = timestamp.strftime("%Y%m%d")
    unix_time = int(timestamp.timestamp())
    return f"{date_str}_{cycle}_{unix_time}"


def generate_session_id(timestamp: datetime) -> str:
    """
    Generate session_id from timestamp (date-based).
    
    Format: YYYYMMDD
    Example: 20260130
    
    Args:
        timestamp: Any timestamp within the session
        
    Returns:
        Session ID string
    """
    return timestamp.strftime("%Y%m%d")


def extract_lots_from_action(action: str, lots_before: int = 0) -> int:
    """
    Extract lots_changed from action string.
    
    Examples:
        BUY3 -> +3
        SELL1 -> -1
        SELLALL -> -lots_before
        CLOSE_SHORT -> 0 (position flip, not a net change)
        NOOP -> 0
    
    Args:
        action: Action string from bot log (может быть None!)
        lots_before: Current position size (needed for SELLALL)
        
    Returns:
        Net change in lots (positive = buy, negative = sell)
    """
    # ДОБАВИТЬ ЭТУ ПРОВЕРКУ ↓
    if action is None or action == "":
        return 0
    
    action = action.upper().strip()
    
    # NOOP
    if action == "NOOP":
        return 0
    
    # SELLALL/BUYALL
    if action == "SELLALL":
        return -lots_before
    if action == "BUYALL":
        return lots_before  # Rare case
    
    # BUY/SELL with numbers
    buy_match = re.match(r"BUY(\d+)", action)
    if buy_match:
        return int(buy_match.group(1))
    
    sell_match = re.match(r"SELL(\d+)", action)
    if sell_match:
        return -int(sell_match.group(1))
    
    # CLOSE_SHORT/CLOSE_LONG (from CSV)
    if action in ("CLOSE_SHORT", "CLOSE_LONG"):
        return 0
    
    # Unknown action
    return 0



def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """
    Parse ISO timestamp from bot logs (with timezone).
    
    Examples:
        2026-01-30T11:18:55.951960+03:00
        2026-01-29T16:32:28.877753+03:00
    
    Args:
        timestamp_str: ISO format timestamp string
        
    Returns:
        datetime object (timezone-aware)
    """
    # Remove microseconds and timezone for SQLite compatibility
    # SQLite doesn't support timezone-aware timestamps natively
    dt = datetime.fromisoformat(timestamp_str)
    # Convert to UTC or remove timezone
    return dt.replace(tzinfo=None)


def extract_lots_before_after(action: str, lots_current: int) -> tuple[int, int]:
    """
    Calculate lots_before and lots_after based on action and current position.
    
    Args:
        action: Action string (BUY3, SELL1, etc.)
        lots_current: Current position BEFORE action
        
    Returns:
        (lots_before, lots_after) tuple
    """
    lots_changed = extract_lots_from_action(action, lots_current)
    lots_before = lots_current
    lots_after = lots_current + lots_changed
    
    return lots_before, lots_after

