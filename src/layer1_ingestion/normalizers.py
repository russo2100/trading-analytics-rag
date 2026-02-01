"""
Normalizers: Convert raw data to canonical form (IngestedEvent)
Responsibility: Transform source-specific formats → Pydantic models
"""
import os
from datetime import datetime, timezone
from typing import Dict, Optional
import logging

from .models import (
    IngestedEvent,
    EIAStorageData,
    WeatherForecast,
    NewsItem,
)

logger = logging.getLogger(__name__)


# Authority scores (source reliability: 0-1)
AUTHORITY_SCORES = {
    "logs": 0.80,      # Bot logs (medium-high: reflects actual market state)
    "eia": 1.00,       # EIA (highest: official government data)
    "weather": 0.90,   # Weather API (high: meteorological models)
    "news": 0.60,      # News RSS (medium: subject to bias)
    "oi": 0.85,        # Open Interest (high: exchange data)
}


def normalize_bot_log(raw_log: Dict) -> IngestedEvent:
    """
    Normalize trading bot log entry to IngestedEvent
    
    Args:
        raw_log: Raw JSONL log entry from bot
        
    Returns:
        IngestedEvent with normalized data
        
    Example raw_log:
    {
        "timestamp": "2026-01-20T08:50:45.534384+03:00",
        "cycle": 1,
        "input_state": {"price": 3.591, "rsi": 70.47, "trend": "FLAT"},
        "decision": {"ai_signal": "HOLD", "ai_confidence": 75}
    }
    """
    # Parse timestamp
    timestamp_str = raw_log.get("timestamp", "")
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
    except ValueError:
        logger.warning(f"Invalid timestamp: {timestamp_str}, using now()")
        timestamp = datetime.now(timezone.utc)
    
    # Extract canonical form
    canonical_form = {
        "cycle": raw_log.get("cycle"),
        "price": raw_log.get("input_state", {}).get("price"),
        "rsi": raw_log.get("input_state", {}).get("rsi"),
        "trend": raw_log.get("input_state", {}).get("trend"),
        "lots": raw_log.get("input_state", {}).get("lots", 0),
        "pnl_pct": raw_log.get("input_state", {}).get("pnl_pct", 0.0),
        "ai_signal": raw_log.get("decision", {}).get("ai_signal"),
        "ai_confidence": raw_log.get("decision", {}).get("ai_confidence"),
        "action": raw_log.get("decision", {}).get("action"),
        "reason": raw_log.get("decision", {}).get("reason", ""),
    }
    
    # Generate embedding text (what will be semantically searched)
    embedding_text = (
        f"Trading cycle {canonical_form['cycle']}: "
        f"Price {canonical_form['price']}, RSI {canonical_form['rsi']}, "
        f"Trend {canonical_form['trend']}, Signal {canonical_form['ai_signal']}, "
        f"Confidence {canonical_form['ai_confidence']}%, "
        f"Reason: {canonical_form['reason']}"
    )
    if os.getenv("DEBUG_INGEST") == "1": print("DEBUG canonical_form:", canonical_form) 
    

    
    return IngestedEvent(
        event_id="",  
        source="trading_bot",  # ✅ ОТДЕЛЬНО!
        canonical_form=canonical_form,
        embedding_text=embedding_text,
        metadata={
            "authority": AUTHORITY_SCORES["logs"],
            "freshness": timestamp,
            "data_period": None,
        }
    )



def normalize_eia_data(raw_eia: Dict) -> IngestedEvent:
    """
    Normalize EIA storage API response to IngestedEvent
    
    Args:
        raw_eia: Raw EIA API response
        
    Returns:
        IngestedEvent with EIAStorageData in canonical_form
        
    Example raw_eia:
    {
        "response": {
            "data": [{
                "period": "2026-01-15",
                "value": 2850,  # BCF
                "area": "Total Lower 48",
                ...
            }]
        }
    }
    """
    try:
        data = raw_eia.get("response", {}).get("data", [])[0]
    except (KeyError, IndexError):
        raise ValueError("Invalid EIA API response format")
    
    # Parse data
    storage_bcf = float(data.get("value", 0))
    period_str = data.get("period", "")
    period_date = datetime.strptime(period_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    # Normalize to 0-1 scale (approximate: NG storage range ~1500-4000 BCF)
    storage_level = (storage_bcf - 1500) / (4000 - 1500)
    storage_level = max(0.0, min(1.0, storage_level))  # Clamp to [0, 1]
    
    # Calculate 5-year average (placeholder: needs historical data)
    five_year_avg = 3200  # BCF (approximate winter average)
    change_from_avg = storage_bcf - five_year_avg
    
    # Create canonical form
    canonical = EIAStorageData(
        storage_level=storage_level,
        storage_bcf=storage_bcf,
        five_year_avg=five_year_avg,
        change_from_last_week=0.0,  # TODO: Calculate from previous week
        timestamp=period_date,
    )
    
    embedding_text = (
        f"EIA Natural Gas storage: {storage_bcf:.0f} BCF ({storage_level:.1%} of capacity), "
        f"{'below' if change_from_avg < 0 else 'above'} 5-year average by {abs(change_from_avg):.0f} BCF. "
        f"Period: {period_str}"
    )
    
    return IngestedEvent(
        event_id="",
        source="eia",
        canonical_form=canonical.model_dump(),
        embedding_text=embedding_text,
        metadata={
            "authority": AUTHORITY_SCORES["eia"],
            "freshness": period_date,
            "data_period": (period_date, period_date),  # Weekly snapshot
        }
    )


def normalize_weather_data(raw_weather: Dict) -> IngestedEvent:
    """
    Normalize weather API response to IngestedEvent
    
    Args:
        raw_weather: Raw Open-Meteo API response
        
    Returns:
        IngestedEvent with WeatherForecast in canonical_form
        
    Example raw_weather:
    {
        "daily": {
            "time": ["2026-01-22", "2026-01-23", ...],
            "temperature_2m_min": [-5.2, -8.1, ...],
            "temperature_2m_max": [2.3, 0.5, ...]
        }
    }
    """
    try:
        daily = raw_weather.get("daily", {})
        times = daily.get("time", [])
        temp_mins = daily.get("temperature_2m_min", [])
        temp_maxs = daily.get("temperature_2m_max", [])
    except KeyError:
        raise ValueError("Invalid weather API response format")
    
    if not times or not temp_mins:
        raise ValueError("No weather data in response")
    
    # Take first forecast day (today)
    forecast_date_str = times[0]
    temp_min = temp_mins[0]
    temp_max = temp_maxs[0]
    
    forecast_date = datetime.strptime(forecast_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    # Determine if extreme weather (< -5°C or > 35°C)
    is_extreme = temp_min < -5 or temp_max > 35
    
    # Create canonical form
    canonical = WeatherForecast(
        location="US Northeast",
        temperature_celsius=temp_min,
        is_extreme=is_extreme,
        forecast_period=(forecast_date, forecast_date),
        confidence=0.85,  # Meteorological model confidence
    )
    
    embedding_text = (
        f"Weather forecast for NG demand region: "
        f"Temperature {temp_min:.1f}°C to {temp_max:.1f}°C. "
        f"{'EXTREME COLD' if temp_min < -5 else 'Normal temperature'}. "
        f"Date: {forecast_date_str}"
    )
    
    return IngestedEvent(
        event_id="",
        source="weather",
        canonical_form=canonical.model_dump(),
        embedding_text=embedding_text,
        metadata={
            "authority": AUTHORITY_SCORES["weather"],
            "freshness": datetime.now(timezone.utc),
            "data_period": (forecast_date, forecast_date),
        }
    )


def normalize_news_item(raw_news: Dict, sentiment_score: Optional[float] = None) -> IngestedEvent:
    """
    Normalize news RSS item to IngestedEvent
    
    Args:
        raw_news: Raw RSS feed entry
        sentiment_score: Pre-calculated sentiment (-1 to +1), None = neutral
        
    Returns:
        IngestedEvent with NewsItem in canonical_form
        
    Example raw_news:
    {
        "title": "Arctic blast to hit US Northeast, gas demand surge expected",
        "link": "https://eia.gov/...",
        "published": "Wed, 20 Jan 2026 14:30:00 GMT",
        "summary": "..."
    }
    """
    title = raw_news.get("title", "")
    link = raw_news.get("link", "")
    summary = raw_news.get("summary", "")
    published_str = raw_news.get("published", "")
    
    # Parse published date
    try:
        from email.utils import parsedate_to_datetime
        published_at = parsedate_to_datetime(published_str)
    except:
        logger.warning(f"Invalid published date: {published_str}, using now()")
        published_at = datetime.now(timezone.utc)
    
    # Sentiment analysis (simple keyword-based for MVP, LLM later)
    if sentiment_score is None:
        sentiment_score = _calculate_simple_sentiment(title + " " + summary)
    
    canonical = NewsItem(
        headline=title,
        summary=summary,
        sentiment_score=sentiment_score,
        source_name="EIA Today in Energy",  # TODO: Dynamic source detection
        url=link,
        published_at=published_at,
    )
    
    embedding_text = (
        f"News: {title}. "
        f"{'BULLISH' if sentiment_score > 0.3 else 'BEARISH' if sentiment_score < -0.3 else 'NEUTRAL'} sentiment. "
        f"Summary: {summary[:200]}"  # First 200 chars
    )
    
    return IngestedEvent(
        event_id="",
        source="news",
        canonical_form=canonical.model_dump(),
        embedding_text=embedding_text,
        metadata={
            "authority": AUTHORITY_SCORES["news"],
            "freshness": published_at,
            "data_period": None,
        }
    )


def _calculate_simple_sentiment(text: str) -> float:
    """
    Simple keyword-based sentiment (MVP, replace with LLM in Phase 2)
    
    Args:
        text: News headline + summary
        
    Returns:
        Sentiment score (-1 to +1)
    """
    text_lower = text.lower()
    
    # Bullish keywords for NG
    bullish = ["surge", "demand", "cold", "arctic", "shortage", "rally", "bullish", "rise", "increase"]
    # Bearish keywords
    bearish = ["warm", "surplus", "oversupply", "bearish", "decline", "fall", "decrease", "glut"]
    
    bullish_count = sum(1 for keyword in bullish if keyword in text_lower)
    bearish_count = sum(1 for keyword in bearish if keyword in text_lower)
    
    if bullish_count + bearish_count == 0:
        return 0.0  # Neutral
    
    # Normalize to [-1, +1]
    sentiment = (bullish_count - bearish_count) / (bullish_count + bearish_count)
    return sentiment


# Добавить в конец существующего файла normalizers.py

"""
Trading log normalizers for bot logs (v1/v2 formats).
"""

from typing import Dict, Any, Optional
from datetime import datetime
from .id_generators import (
    generate_event_id,
    generate_session_id,
    parse_iso_timestamp,
    extract_lots_from_action,
    extract_lots_before_after
)


def normalize_bot_log_v1(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize bot log v1 format (decisions_20260129.jsonl, 22.01.2026.jsonl).
    
    v1 format has:
    - cycle, timestamp, price, rsi, action (МОЖЕТ ОТСУТСТВОВАТЬ!), reason
    - account_snapshot with pnl_today
    - NO event_id, NO session_id
    
    Args:
        event: Raw log entry from JSONL
        
    Returns:
        Normalized dict ready for trading_events table
    """
    timestamp = parse_iso_timestamp(event["timestamp"])
    cycle = event.get("cycle", 0)
    
    # Generate IDs
    event_id = generate_event_id(timestamp, cycle)
    session_id = generate_session_id(timestamp)
    
    # Extract account_snapshot (if exists)
    snapshot = event.get("account_snapshot", {})
    pnl_today = snapshot.get("pnl_today", {})
    
    # ИСПРАВЛЕНИЕ: action может отсутствовать в старых v1 логах
    # Попробуем разные варианты имени поля
    action = event.get("action") or event.get("decision") or event.get("trade_action") or "NOOP"
    
    # Normalize to trading_events schema
    normalized = {
        "event_id": event_id,
        "session_id": session_id,
        "timestamp": timestamp.isoformat(),
        "cycle": cycle,
        
        # Market data
        "price": event.get("price"),
        "rsi": event.get("rsi"),
        "trend_ltf": event.get("trend_ltf"),
        "trend_htf": event.get("trend_htf"),
        "trend_override": event.get("trend_override", ""),
        
        # Position state
        "lots": event.get("lots", 0),
        "pnl_pct": event.get("pnl_pct", 0.0),
        "position_pnl_pct": event.get("pnl_pct", 0.0),  # v1 uses pnl_pct
        
        # AI decision
        "ai_signal": event.get("ai_signal") or event.get("signal"),  # fallback
        "ai_confidence": event.get("ai_confidence") or event.get("confidence"),
        "bias": event.get("bias"),
        "action": action,  # ← ИСПОЛЬЗУЕМ fallback
        "reason": event.get("reason"),
        
        # v2 fields (defaults for v1)
        "sleeping_market": False,
        "sleeping_reason": None,
        "cooldown_active": False,
        "cooldown_remaining": 0,
        "adaptive_sl_multiplier": None,
        "sl_level": None,
        
        # Daily limits (v1 doesn't have these)
        "daily_trades_count": 0,
        "daily_pnl_total": pnl_today.get("net_pnl_rub", 0.0),
        "daily_trades_remaining": None,
        "daily_limit_blocked": False,
        
        # Timing
        "minutes_to_clearing": event.get("minutes_to_clearing"),
        "holding_hours": event.get("holding_hours", 0.0),
        "forced_entry": event.get("forced_entry", False),
        "consecutive_signals": event.get("consecutive_signals", 0),
        "avg_confidence": event.get("avg_confidence", 0.0),
    }
    
    return normalized



def normalize_bot_log_v2(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize bot log v2 format (shadow_agents_log_20260130.jsonl).
    
    v2 format has:
    - All v1 fields
    - sleeping_market, cooldown_active, daily_trades_count
    - NO account_snapshot, NO event_id
    
    Args:
        event: Raw log entry from JSONL
        
    Returns:
        Normalized dict ready for trading_events table
    """
    timestamp = parse_iso_timestamp(event["timestamp"])
    cycle = event.get("cycle", 0)
    
    # Generate IDs
    event_id = generate_event_id(timestamp, cycle)
    session_id = generate_session_id(timestamp)
    
    # Normalize to trading_events schema (v2 is superset of v1)
    normalized = {
        "event_id": event_id,
        "session_id": session_id,
        "timestamp": timestamp.isoformat(),
        "cycle": cycle,
        
        # Market data
        "price": event.get("price"),
        "rsi": event.get("rsi"),
        "trend_ltf": event.get("trend_ltf"),
        "trend_htf": event.get("trend_htf"),
        "trend_override": event.get("trend_override", ""),
        
        # Position state
        "lots": event.get("lots", 0),
        "pnl_pct": event.get("pnl_pct", 0.0),
        "position_pnl_pct": event.get("position_pnl_pct", 0.0),
        
        # AI decision
        "ai_signal": event.get("ai_signal"),
        "ai_confidence": event.get("ai_confidence"),
        "bias": event.get("bias"),
        "action": event.get("action"),
        "reason": event.get("reason"),
        
        # v2-specific fields
        "sleeping_market": event.get("sleeping_market", False),
        "sleeping_reason": event.get("sleeping_reason"),
        "cooldown_active": event.get("cooldown_active", False),
        "cooldown_remaining": event.get("cooldown_remaining", 0),
        "adaptive_sl_multiplier": event.get("adaptive_sl_multiplier"),
        "sl_level": event.get("sl_level"),
        
        # Daily limits
        "daily_trades_count": event.get("daily_trades_count", 0),
        "daily_pnl_total": event.get("daily_pnl_total", 0.0),
        "daily_trades_remaining": event.get("daily_trades_remaining"),
        "daily_limit_blocked": event.get("daily_limit_blocked", False),
        
        # Timing
        "minutes_to_clearing": event.get("minutes_to_clearing"),
        "holding_hours": event.get("holding_hours", 0.0),
        "forced_entry": event.get("forced_entry", False),
        "consecutive_signals": event.get("consecutive_signals", 0),
        "avg_confidence": event.get("avg_confidence", 0.0),
    }
    
    return normalized


def extract_trade_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract trade record from normalized event (if action != NOOP).
    
    Args:
        event: Normalized trading_event dict
        
    Returns:
        Trade dict or None if action is NOOP or None
    """
    action = event.get("action")  # Может быть None!
    
    # ДОБАВИТЬ ЭТУ ПРОВЕРКУ ↓
    if action is None or action == "NOOP":
        return None
    
    lots_before = event.get("lots", 0)
    lots_before_calc, lots_after = extract_lots_before_after(action, lots_before)
    lots_changed = extract_lots_from_action(action, lots_before)
    
    trade = {
        "trade_id": event["event_id"],  # Same as parent event
        "event_id": event["event_id"],
        "session_id": event["session_id"],
        "timestamp": event["timestamp"],
        "action": action,
        "lots_before": lots_before,
        "lots_after": lots_after,
        "lots_changed": lots_changed,
        "price_usd": event.get("price"),
        "reason": event.get("reason"),
        "signal": event.get("ai_signal"),
        "confidence": event.get("ai_confidence"),
        "realized_pnl_rub": None,  # Not in bot logs
        "unrealized_pnl_rub": None,
        "fees_rub": None,
    }
    
    return trade

def normalize_bot_log_v1_legacy(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize bot log v1 LEGACY format (22.01.2026.jsonl).
    
    Structure:
    - timestamp, cycle
    - input_state: { price, rsi, trend, lots, pnl_pct, holding_hours, minutes_to_clearing, bias }
    - decision: { ai_signal, ai_confidence, action, reason, rules, forced_entry, consecutive_signals, avg_confidence }
    
    Args:
        event: Raw log entry from JSONL
        
    Returns:
        Normalized dict ready for trading_events table
    """
    timestamp = parse_iso_timestamp(event["timestamp"])
    cycle = event.get("cycle", 0)
    
    # Generate IDs
    event_id = generate_event_id(timestamp, cycle)
    session_id = generate_session_id(timestamp)
    
    # Extract nested structures
    input_state = event.get("input_state", {})
    decision = event.get("decision", {})
    rules = decision.get("rules", {})
    
    # Normalize to trading_events schema
    normalized = {
        "event_id": event_id,
        "session_id": session_id,
        "timestamp": timestamp.isoformat(),
        "cycle": cycle,
        
        # Market data (from input_state)
        "price": input_state.get("price"),
        "rsi": input_state.get("rsi"),
        "trend_ltf": input_state.get("trend"),  # FLAT/UPTREND/DOWNTREND
        "trend_htf": "NEUTRAL",  # Not in legacy format
        "trend_override": "",
        
        # Position state (from input_state)
        "lots": input_state.get("lots", 0),
        "pnl_pct": input_state.get("pnl_pct", 0.0),
        "position_pnl_pct": input_state.get("pnl_pct", 0.0),
        
        # AI decision (from decision)
        "ai_signal": decision.get("ai_signal"),
        "ai_confidence": decision.get("ai_confidence"),
        "bias": input_state.get("bias") or rules.get("bias"),
        "action": decision.get("action"),  # ← ЗДЕСЬ action!
        "reason": decision.get("reason"),
        
        # v2 fields (defaults for v1 legacy)
        "sleeping_market": False,
        "sleeping_reason": None,
        "cooldown_active": False,
        "cooldown_remaining": 0,
        "adaptive_sl_multiplier": None,
        "sl_level": None,
        
        # Daily limits (v1 legacy doesn't have)
        "daily_trades_count": 0,
        "daily_pnl_total": 0.0,
        "daily_trades_remaining": None,
        "daily_limit_blocked": False,
        
        # Timing (from input_state and decision)
        "minutes_to_clearing": input_state.get("minutes_to_clearing"),
        "holding_hours": input_state.get("holding_hours", 0.0),
        "forced_entry": decision.get("forced_entry", False),
        "consecutive_signals": decision.get("consecutive_signals", 0),
        "avg_confidence": decision.get("avg_confidence", 0.0),
    }
    
    return normalized
