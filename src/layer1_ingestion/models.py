"""
Pydantic models for ingestion layer
CONTRACT: Inputs → IngestedEvent (normalized, deduplicated)
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal, Optional
import hashlib


class IngestMessage(BaseModel):
    """Raw input from any data source"""
    source: Literal["logs", "eia", "weather", "news", "oi"]
    timestamp: datetime
    raw_data: dict
    metadata: dict = Field(default_factory=dict)


class IngestedEvent(BaseModel):
    """Normalized, deduplicated event ready for storage"""
    event_id: str  # MD5 hash of (source + timestamp + canonical_form)
    source: str
    canonical_form: dict  # Normalized structure (source-specific)
    embedding_text: str  # What will be embedded (concatenated fields)
    
    metadata: dict = Field(default_factory=dict)
    # metadata должен содержать:
    # - authority: float (0-1, source reliability)
    # - freshness: datetime (when this data was generated)
    # - data_period: tuple (start_time, end_time) or None
    
    @field_validator("event_id", mode="before")
    @classmethod
    def generate_event_id(cls, v, info):
        """Auto-generate event_id if not provided"""
        if v:
            return v

        data = info.data

        # Не ломаем контракт: если каких-то полей нет, используем безопасные дефолты.
        source = data.get("source", "unknown")
        timestamp = data.get("timestamp", "")
        canonical_form = data.get("canonical_form", "")

        hash_input = f"{source}{timestamp}{canonical_form}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    
    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v):
        """Ensure required metadata fields exist"""
        required = ["authority", "freshness"]
        for field in required:
            if field not in v:
                raise ValueError(f"Missing required metadata field: {field}")
        
        # Validate authority range
        if not 0 <= v["authority"] <= 1:
            raise ValueError("authority must be between 0 and 1")
        
        # Validate freshness is datetime
        if not isinstance(v["freshness"], datetime):
            raise ValueError("freshness must be datetime")
        
        return v


class EIAStorageData(BaseModel):
    """Canonical form for EIA storage data"""
    storage_level: float = Field(..., ge=0, le=1, description="Storage as fraction (0-1)")
    storage_bcf: float = Field(..., description="Storage in billion cubic feet")
    five_year_avg: float = Field(..., description="5-year average for comparison")
    change_from_last_week: float = Field(..., description="Change in BCF")
    timestamp: datetime


class WeatherForecast(BaseModel):
    """Canonical form for weather data"""
    location: str = "US Northeast"  # NG demand center
    temperature_celsius: float
    is_extreme: bool = Field(..., description="Is temperature extreme? (<-5C or >35C)")
    forecast_period: tuple[datetime, datetime]  # (start, end)
    confidence: float = Field(..., ge=0, le=1)


class NewsItem(BaseModel):
    """Canonical form for news"""
    headline: str
    summary: str
    sentiment_score: float = Field(..., ge=-1, le=1, description="-1 (bearish) to +1 (bullish)")
    source_name: str
    url: Optional[str] = None
    published_at: datetime
