"""AI Music Composer - An intelligent system for generating musical compositions."""

__version__ = "0.1.0"

from .config import get_config, get_database_url, get_default_bpm, get_openai_api_key

__all__ = ["get_config", "get_database_url", "get_openai_api_key", "get_default_bpm"]
