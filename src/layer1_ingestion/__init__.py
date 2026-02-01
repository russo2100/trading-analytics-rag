"""
Layer 1: Ingestion & Normalization

CONTRACT: Raw data sources → IngestedEvent (normalized, deduplicated)
"""
from .models import (
    IngestMessage,
    IngestedEvent,
    EIAStorageData,
    WeatherForecast,
    NewsItem,
)
from .loaders import (
    load_jsonl_logs,
    fetch_eia_storage,
    fetch_weather_forecast,
)
from .normalizers import (
    normalize_bot_log,
    normalize_eia_data,
    normalize_weather_data,
    normalize_news_item,
)
from .deduplication import (
    deduplicate_events,
    validate_event_integrity,  # FIX: добавить сюда
)

__all__ = [
    # Models
    "IngestMessage",
    "IngestedEvent",
    "EIAStorageData",
    "WeatherForecast",
    "NewsItem",
    # Loaders
    "load_jsonl_logs",
    "fetch_eia_storage",
    "fetch_weather_forecast",
    # Normalizers
    "normalize_bot_log",
    "normalize_eia_data",
    "normalize_weather_data",
    "normalize_news_item",
    # Deduplication
    "deduplicate_events",
    "validate_event_integrity",
]
