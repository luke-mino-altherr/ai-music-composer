"""Centralized configuration for AI Music Composer.

This module provides a single source of truth for all configuration values,
environment variables, and secrets used throughout the application.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    """Neo4j database configuration."""

    host: str = "localhost"
    port: int = 7687
    username: str = "neo4j"
    password: str = "musiccomposer"
    scheme: str = "bolt"

    @property
    def url(self) -> str:
        """Get the complete database URL."""
        return (
            f"{self.scheme}://{self.username}:{self.password}@{self.host}:{self.port}"
        )


@dataclass
class LLMConfig:
    """LLM and AI configuration."""

    openai_api_key: Optional[str] = None
    openai_organization_id: Optional[str] = None
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30


@dataclass
class MIDIConfig:
    """MIDI system configuration."""

    default_bpm: float = 120.0
    default_velocity: int = 100
    default_channel: int = 0
    default_duration: float = 0.5
    max_sequence_loops: int = 1000

    # Timing precision settings
    timing_precision_ms: float = 1.0  # Millisecond precision for scheduling
    scheduling_lookahead_beats: float = 0.1  # How far ahead to schedule events


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Module-specific log levels
    midi_log_level: str = "INFO"
    sequencer_log_level: str = "INFO"
    transport_log_level: str = "INFO"
    llm_log_level: str = "INFO"
    database_log_level: str = "INFO"


@dataclass
class AppConfig:
    """Main application configuration."""

    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    midi: MIDIConfig = field(default_factory=MIDIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Application metadata
    app_name: str = "AI Music Composer"
    version: str = "0.1.0"
    debug: bool = False

    def __post_init__(self):
        """Load environment variables and validate configuration."""
        self._load_from_environment()
        self._validate_config()

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        # Load .env file if it exists
        load_dotenv()

        # Database configuration
        self.database.host = os.getenv("NEO4J_HOST", self.database.host)
        self.database.port = int(os.getenv("NEO4J_PORT", str(self.database.port)))
        self.database.username = os.getenv("NEO4J_USERNAME", self.database.username)
        self.database.password = os.getenv("NEO4J_PASSWORD", self.database.password)
        self.database.scheme = os.getenv("NEO4J_SCHEME", self.database.scheme)

        # LLM configuration
        self.llm.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.llm.openai_organization_id = os.getenv("OPENAI_ORGANIZATION_ID")
        self.llm.model_name = os.getenv("OPENAI_MODEL_NAME", self.llm.model_name)
        self.llm.temperature = float(
            os.getenv("OPENAI_TEMPERATURE", str(self.llm.temperature))
        )
        self.llm.max_tokens = int(
            os.getenv("OPENAI_MAX_TOKENS", str(self.llm.max_tokens))
        )
        self.llm.timeout = int(os.getenv("OPENAI_TIMEOUT", str(self.llm.timeout)))

        # MIDI configuration
        self.midi.default_bpm = float(
            os.getenv("MIDI_DEFAULT_BPM", str(self.midi.default_bpm))
        )
        self.midi.default_velocity = int(
            os.getenv("MIDI_DEFAULT_VELOCITY", str(self.midi.default_velocity))
        )
        self.midi.default_channel = int(
            os.getenv("MIDI_DEFAULT_CHANNEL", str(self.midi.default_channel))
        )
        self.midi.default_duration = float(
            os.getenv("MIDI_DEFAULT_DURATION", str(self.midi.default_duration))
        )
        self.midi.max_sequence_loops = int(
            os.getenv("MIDI_MAX_SEQUENCE_LOOPS", str(self.midi.max_sequence_loops))
        )
        self.midi.timing_precision_ms = float(
            os.getenv("MIDI_TIMING_PRECISION_MS", str(self.midi.timing_precision_ms))
        )
        self.midi.scheduling_lookahead_beats = float(
            os.getenv(
                "MIDI_SCHEDULING_LOOKAHEAD_BEATS",
                str(self.midi.scheduling_lookahead_beats),
            )
        )

        # Logging configuration
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level).upper()
        self.logging.midi_log_level = os.getenv(
            "MIDI_LOG_LEVEL", self.logging.midi_log_level
        ).upper()
        self.logging.sequencer_log_level = os.getenv(
            "SEQUENCER_LOG_LEVEL", self.logging.sequencer_log_level
        ).upper()
        self.logging.transport_log_level = os.getenv(
            "TRANSPORT_LOG_LEVEL", self.logging.transport_log_level
        ).upper()
        self.logging.llm_log_level = os.getenv(
            "LLM_LOG_LEVEL", self.logging.llm_log_level
        ).upper()
        self.logging.database_log_level = os.getenv(
            "DATABASE_LOG_LEVEL", self.logging.database_log_level
        ).upper()

        # Application settings
        self.debug = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes", "on")

    def _validate_config(self):
        """Validate configuration values."""
        # Validate MIDI settings
        if not (60.0 <= self.midi.default_bpm <= 300.0):
            raise ValueError(
                f"Invalid MIDI BPM: {self.midi.default_bpm}. Must be between 60-300."
            )

        if not (0 <= self.midi.default_velocity <= 127):
            raise ValueError(
                f"Invalid MIDI velocity: {self.midi.default_velocity}. Must be between 0-127."
            )

        if not (0 <= self.midi.default_channel <= 15):
            raise ValueError(
                f"Invalid MIDI channel: {self.midi.default_channel}. Must be between 0-15."
            )

        # Validate LLM settings
        if self.llm.temperature < 0.0 or self.llm.temperature > 2.0:
            raise ValueError(
                f"Invalid LLM temperature: {self.llm.temperature}. Must be between 0.0-2.0."
            )

        # Validate logging levels
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        for level_name, level_value in [
            ("LOG_LEVEL", self.logging.level),
            ("MIDI_LOG_LEVEL", self.logging.midi_log_level),
            ("SEQUENCER_LOG_LEVEL", self.logging.sequencer_log_level),
            ("TRANSPORT_LOG_LEVEL", self.logging.transport_log_level),
            ("LLM_LOG_LEVEL", self.logging.llm_log_level),
            ("DATABASE_LOG_LEVEL", self.logging.database_log_level),
        ]:
            if level_value not in valid_log_levels:
                raise ValueError(
                    f"Invalid {level_name}: {level_value}. Must be one of {valid_log_levels}."
                )


# Global configuration instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config


def reload_config():
    """Reload configuration from environment variables."""
    global config
    config = AppConfig()
    return config


# Convenience functions for common configuration access
def get_database_url() -> str:
    """Get the Neo4j database URL."""
    return config.database.url


def get_openai_api_key() -> Optional[str]:
    """Get the OpenAI API key."""
    return config.llm.openai_api_key


def get_default_bpm() -> float:
    """Get the default BPM for MIDI sequences."""
    return config.midi.default_bpm


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return config.debug
