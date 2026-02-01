"""
Data loaders for all sources
Responsibility: Fetch raw data, return as dict (no normalization here)
"""
import json
import httpx
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

from ..config import settings

logger = logging.getLogger(__name__)


async def load_jsonl_logs(file_path: Path) -> List[Dict]:
    """
    Load JSONL logs from trading bot
    
    Args:
        file_path: Path to .jsonl file
        
    Returns:
        List of raw log entries (dict)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If invalid JSONL format
    """
    if not file_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {file_path}")
    
    logs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                log_entry = json.loads(line)
                logs.append(log_entry)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON at line {line_num}: {e}")
                continue
    
    logger.info(f"Loaded {len(logs)} log entries from {file_path}")
    return logs


async def fetch_eia_storage(api_key: Optional[str] = None) -> Dict:
    """
    Fetch latest Natural Gas storage data from EIA API
    
    API Doc: https://www.eia.gov/opendata/
    Endpoint: /v2/natural-gas/stor/wsum/data
    
    Args:
        api_key: EIA API key (uses settings.eia_api_key if None)
        
    Returns:
        Raw API response dict with storage data
        
    Raises:
        httpx.HTTPError: If API request fails
    """
    api_key = api_key or settings.eia_api_key
    if not api_key:
        raise ValueError("EIA API key not configured. Set EIA_API_KEY in .env")
    
    # EIA Natural Gas Weekly Storage API
    url = "https://api.eia.gov/v2/natural-gas/stor/wsum/data"
    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",  # Storage level
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 1,  # Latest week only
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Fetched EIA storage data: {data.get('response', {}).get('total', 0)} records")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"EIA API request failed: {e}")
            raise


async def fetch_weather_forecast(
    location: str = "US Northeast",
    api_key: Optional[str] = None
) -> Dict:
    """
    Fetch weather forecast for Natural Gas demand centers
    
    Uses Open-Meteo API (free, no key required) or OpenWeatherMap
    
    Args:
        location: Weather location (default: US Northeast for NG demand)
        api_key: Weather API key if using paid service
        
    Returns:
        Raw weather API response dict
        
    Raises:
        httpx.HTTPError: If API request fails
    """
    # OPTION 1: Open-Meteo (free, no key)
    # Henry Hub coordinates (Louisiana, NG trading hub)
    lat, lon = 29.95, -90.07
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_min,temperature_2m_max",
        "forecast_days": 7,
        "timezone": "America/Chicago",
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Fetched weather forecast: {len(data.get('daily', {}).get('time', []))} days")
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Weather API request failed: {e}")
            raise


async def fetch_news_rss(source: str = "eia") -> List[Dict]:
    """
    Fetch news from RSS feeds
    
    Args:
        source: News source ('eia', 'investing', etc.)
        
    Returns:
        List of news items (dict with title, link, published, summary)
        
    Raises:
        Exception: If RSS feed fetch fails
    """
    import feedparser
    
    RSS_FEEDS = {
        "eia": "https://www.eia.gov/rss/todayinenergy.xml",
        # Add more sources as needed
    }
    
    feed_url = RSS_FEEDS.get(source)
    if not feed_url:
        raise ValueError(f"Unknown news source: {source}. Available: {list(RSS_FEEDS.keys())}")
    
    try:
        feed = feedparser.parse(feed_url)
        
        news_items = []
        for entry in feed.entries[:10]:  # Latest 10 items
            news_items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
            })
        
        logger.info(f"Fetched {len(news_items)} news items from {source}")
        return news_items
        
    except Exception as e:
        logger.error(f"RSS feed fetch failed for {source}: {e}")
        raise


# FALLBACK: Cached data when API fails
async def load_cached_eia_data() -> Optional[Dict]:
    """
    Load last successful EIA fetch from cache
    Used as fallback when API is unavailable
    
    Returns:
        Cached EIA data or None if no cache exists
    """
    cache_path = settings.processed_data_path / "eia_cache.json"
    
    if not cache_path.exists():
        logger.warning("No cached EIA data found")
        return None
    
    try:
        with open(cache_path, 'r') as f:
            cached = json.load(f)
            
        # Check cache age
        cache_time = datetime.fromisoformat(cached.get("cached_at", ""))
        age_days = (datetime.now() - cache_time).days
        
        if age_days > 7:
            logger.warning(f"Cached EIA data is {age_days} days old (stale)")
        
        logger.info(f"Using cached EIA data from {cache_time}")
        return cached.get("data")
        
    except Exception as e:
        logger.error(f"Failed to load cached EIA data: {e}")
        return None


async def save_eia_cache(data: Dict):
    """
    Save EIA data to cache for fallback
    
    Args:
        data: EIA API response to cache
    """
    cache_path = settings.processed_data_path / "eia_cache.json"
    
    cached = {
        "cached_at": datetime.now().isoformat(),
        "data": data,
    }
    
    try:
        with open(cache_path, 'w') as f:
            json.dump(cached, f, indent=2)
        logger.info(f"Saved EIA data to cache: {cache_path}")
    except Exception as e:
        logger.error(f"Failed to save EIA cache: {e}")
