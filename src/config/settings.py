from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # API Keys
    binance_api_key: str = Field(default_factory=lambda: os.getenv("BINANCE_API_KEY", ""))
    binance_api_secret: str = Field(default_factory=lambda: os.getenv("BINANCE_API_SECRET", ""))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    
    # Social Media APIs
    twitter_api_key: str = Field(default_factory=lambda: os.getenv("TWITTER_API_KEY", ""))
    twitter_api_secret: str = Field(default_factory=lambda: os.getenv("TWITTER_API_SECRET", ""))
    twitter_access_token: str = Field(default_factory=lambda: os.getenv("TWITTER_ACCESS_TOKEN", ""))
    twitter_access_token_secret: str = Field(default_factory=lambda: os.getenv("TWITTER_ACCESS_TOKEN_SECRET", ""))
    reddit_client_id: str = Field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID", ""))
    reddit_client_secret: str = Field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET", ""))
    reddit_user_agent: str = Field(default_factory=lambda: os.getenv("REDDIT_USER_AGENT", "CryptoTradingBot/1.0"))
    
    # Telegram
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    
    # Redis
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    
    # Trading Parameters
    max_position_size: float = Field(default=1000.0)
    risk_per_trade: float = Field(default=0.02)
    target_weekly_return: float = Field(default=2.0)
    max_concurrent_positions: int = Field(default=3)
    
    # Analysis Parameters
    analysis_interval_hours: int = Field(default=4)
    sentiment_update_minutes: int = Field(default=30)
    technical_timeframes: List[str] = Field(default=["1h", "4h", "1d"])
    
    # Crypto pairs to analyze
    target_symbols: List[str] = Field(default=[
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT",
        "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT"
    ])
    
    # Technical indicators
    technical_indicators: Dict[str, Dict] = Field(default={
        "RSI": {"period": 14, "oversold": 30, "overbought": 70},
        "MACD": {"fast": 12, "slow": 26, "signal": 9},
        "BB": {"period": 20, "std": 2},
        "EMA": {"periods": [9, 21, 50, 200]},
        "ATR": {"period": 14},
        "STOCH": {"k_period": 14, "d_period": 3, "smooth_k": 3}
    })
    
    # Sentiment sources
    sentiment_sources: Dict[str, List[str]] = Field(default={
        "twitter": ["@elonmusk", "@APompliano", "@CryptoHayes", "@VitalikButerin"],
        "reddit": ["r/cryptocurrency", "r/bitcoin", "r/ethtrader", "r/binance"],
        "news": ["coindesk.com", "cointelegraph.com", "decrypt.co", "theblock.co"]
    })
    
    # Risk management
    stop_loss_percentage: float = Field(default=0.05)  # 5% stop loss
    take_profit_percentage: float = Field(default=0.10)  # 10% take profit
    trailing_stop_percentage: float = Field(default=0.03)  # 3% trailing stop
    
    # AI Model settings
    gpt_model: str = Field(default="gpt-4-turbo-preview")
    claude_model: str = Field(default="claude-3-opus-20240229")
    temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=4000)
    
    # Environment
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = Field(default=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()