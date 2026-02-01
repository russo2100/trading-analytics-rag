"""
Deduplication logic for IngestedEvents
Responsibility: Remove duplicate events, resolve conflicts
"""
from typing import List, Dict, Tuple
from collections import defaultdict
import logging

from .models import IngestedEvent

logger = logging.getLogger(__name__)


def deduplicate_events(
    events: List[IngestedEvent],
    conflict_strategy: str = "keep_latest"
) -> Tuple[List[IngestedEvent], Dict]:
    """
    Remove duplicate events by event_id
    
    Args:
        events: List of IngestedEvent objects
        conflict_strategy: How to resolve conflicts
            - "keep_latest": Keep event with most recent freshness
            - "keep_first": Keep first occurrence (FIFO)
            - "keep_highest_authority": Keep event with highest authority score
            
    Returns:
        Tuple of:
        - Deduplicated list of events
        - Stats dict: {"total": int, "duplicates_removed": int, "conflicts": int}
        
    Example:
        events = [event1, event2_duplicate, event3]
        deduplicated, stats = deduplicate_events(events)
        # stats = {"total": 3, "duplicates_removed": 1, "conflicts": 0}
    """
    if not events:
        return [], {"total": 0, "duplicates_removed": 0, "conflicts": 0}
    
    # Group events by event_id
    event_groups = defaultdict(list)
    for event in events:
        event_groups[event.event_id].append(event)
    
    # Resolve conflicts and pick one event per ID
    deduplicated = []
    conflicts_count = 0
    
    for event_id, group in event_groups.items():
        if len(group) == 1:
            # No duplicates
            deduplicated.append(group[0])
        else:
            # Duplicates found, resolve conflict
            conflicts_count += 1
            selected_event = _resolve_conflict(group, conflict_strategy)
            deduplicated.append(selected_event)
            
            logger.warning(
                f"Conflict detected for event_id={event_id}: "
                f"{len(group)} versions found, kept {conflict_strategy} strategy"
            )
    
    stats = {
        "total": len(events),
        "unique": len(deduplicated),
        "duplicates_removed": len(events) - len(deduplicated),
        "conflicts": conflicts_count,
    }
    
    logger.info(
        f"Deduplication complete: {stats['total']} events → "
        f"{stats['unique']} unique ({stats['duplicates_removed']} duplicates removed, "
        f"{stats['conflicts']} conflicts resolved)"
    )
    
    return deduplicated, stats


def _resolve_conflict(
    conflicting_events: List[IngestedEvent],
    strategy: str
) -> IngestedEvent:
    """
    Resolve conflict when multiple events have same event_id but different data
    
    Args:
        conflicting_events: List of events with same event_id
        strategy: Conflict resolution strategy
        
    Returns:
        Selected event based on strategy
    """
    if strategy == "keep_latest":
        # Keep event with most recent freshness timestamp
        return max(
            conflicting_events,
            key=lambda e: e.metadata.get("freshness")
        )
    
    elif strategy == "keep_first":
        # Keep first occurrence (order in list)
        return conflicting_events[0]
    
    elif strategy == "keep_highest_authority":
        # Keep event with highest authority score
        return max(
            conflicting_events,
            key=lambda e: e.metadata.get("authority", 0.0)
        )
    
    else:
        logger.warning(f"Unknown conflict strategy: {strategy}, defaulting to keep_latest")
        return conflicting_events[0]


def detect_near_duplicates(
    events: List[IngestedEvent],
    similarity_threshold: float = 0.95
) -> List[Tuple[str, str, float]]:
    """
    Detect near-duplicate events (same content, different event_id)
    
    This can happen if timestamps differ slightly or metadata changes.
    Useful for audit and data quality checks.
    
    Args:
        events: List of IngestedEvent objects
        similarity_threshold: Cosine similarity threshold (0-1)
        
    Returns:
        List of (event_id1, event_id2, similarity_score) tuples
        
    Note: This is expensive (O(n²)), use only for periodic audits
    """
    from difflib import SequenceMatcher
    
    near_duplicates = []
    
    for i, event1 in enumerate(events):
        for event2 in events[i+1:]:
            # Skip if same event_id (already handled by deduplicate_events)
            if event1.event_id == event2.event_id:
                continue
            
            # Compare embedding_text similarity
            similarity = SequenceMatcher(
                None,
                event1.embedding_text,
                event2.embedding_text
            ).ratio()
            
            if similarity >= similarity_threshold:
                near_duplicates.append((
                    event1.event_id,
                    event2.event_id,
                    similarity
                ))
                logger.warning(
                    f"Near-duplicate detected: {event1.event_id[:8]} vs "
                    f"{event2.event_id[:8]} (similarity: {similarity:.2%})"
                )
    
    return near_duplicates


def validate_event_integrity(event: IngestedEvent) -> bool:
    """
    Validate that IngestedEvent has all required fields and consistent data
    
    Args:
        event: IngestedEvent to validate
        
    Returns:
        True if valid, False otherwise (logs errors)
    """
    # Check event_id exists and is valid hash
    if not event.event_id or len(event.event_id) != 32:
        logger.error(f"Invalid event_id: {event.event_id}")
        return False
    
    # Check metadata has required fields
    required_metadata = ["authority", "freshness"]
    for field in required_metadata:
        if field not in event.metadata:
            logger.error(f"Missing metadata field: {field} in event {event.event_id}")
            return False
    
    # Check authority score range
    authority = event.metadata.get("authority", 0)
    if not 0 <= authority <= 1:
        logger.error(f"Invalid authority score: {authority} (must be 0-1)")
        return False
    
    # Check embedding_text is not empty
    if not event.embedding_text or len(event.embedding_text.strip()) == 0:
        logger.error(f"Empty embedding_text in event {event.event_id}")
        return False
    
    # Check canonical_form is not empty
    if not event.canonical_form or not isinstance(event.canonical_form, dict):
        logger.error(f"Invalid canonical_form in event {event.event_id}")
        return False
    
    return True
