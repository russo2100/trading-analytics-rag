"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """Global settings loaded from .env file"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # API Keys
    openrouter_api_key: str = ""
    eia_api_key: str = ""
    weather_api_key: str = ""
    
    # OpenRouter settings
    openrouter_model: str = "anthropic/claude-3.5-sonnet"  # Default LLM
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Paths
    raw_data_path: Path = Path("./data/raw")
    processed_data_path: Path = Path("./data/processed")
    vector_index_path: Path = Path("./data/vector_index")
    
    # Storage
    sqlite_db_path: Path = Path("./data/metadata.db")
    use_redis: bool = False
    
    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Logging
    log_level: str = "INFO"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        self.processed_data_path.mkdir(parents=True, exist_ok=True)
        self.vector_index_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
