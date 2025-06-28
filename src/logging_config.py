"""Centralized logging configuration for AI Music Composer.

This module provides a single point for configuring logging across the entire
application following Python logging best practices.
"""

import logging
import logging.config
import sys
from typing import Any, Dict, Optional

try:
    from .config import get_config
except ImportError:
    # Handle case when run as script
    from config import get_config


def get_logging_config() -> Dict[str, Any]:
    """Get the logging configuration dictionary.

    Returns:
        Dictionary suitable for logging.config.dictConfig()
    """
    config = get_config()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": config.logging.format,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {"format": "%(levelname)s - %(name)s - %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "ai_music_composer.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "ai_music_composer_errors.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "midi_generator": {
                "level": config.logging.midi_log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "midi_generator.midi_controller": {
                "level": config.logging.midi_log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "midi_generator.sequencer": {
                "level": config.logging.sequencer_log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "midi_generator.transport": {
                "level": config.logging.transport_log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "llm_composer": {
                "level": config.logging.llm_log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "database": {
                "level": config.logging.database_log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": config.logging.level,
            "handlers": ["console", "file", "error_file"],
        },
    }


def setup_logging(log_config: Optional[Dict[str, Any]] = None) -> None:
    """Set up logging configuration for the application.

    Args:
        log_config: Optional custom logging configuration. If None, uses default.
    """
    if log_config is None:
        log_config = get_logging_config()

    logging.config.dictConfig(log_config)

    # Log the initialization
    logger = logging.getLogger(__name__)
    logger.info("Logging configuration initialized")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    This is the recommended way to get loggers throughout the application.

    Args:
        name: Logger name, typically __name__ from the calling module

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def configure_module_logger(
    module_name: str, level: Optional[str] = None
) -> logging.Logger:
    """Configure a logger for a specific module.

    Args:
        module_name: Name of the module (e.g., 'midi_generator.sequencer')
        level: Optional log level override

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(module_name)

    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    return logger


def set_log_level(logger_name: str, level: str) -> None:
    """Dynamically change log level for a specific logger.

    Args:
        logger_name: Name of the logger to modify
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.info(f"Log level changed to {level.upper()} for {logger_name}")


def get_debug_logger(name: str) -> logging.Logger:
    """Get a logger configured for debug output.

    Useful for temporary debugging during development.

    Args:
        name: Logger name

    Returns:
        Logger configured for debug output
    """
    logger = logging.getLogger(f"debug.{name}")
    logger.setLevel(logging.DEBUG)

    # Add a simple console handler if it doesn't exist
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("DEBUG - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# Context manager for temporary log level changes
class temporary_log_level:
    """Context manager for temporarily changing log level.

    Usage:
        with temporary_log_level('midi_generator', 'DEBUG'):
            # Code that needs debug logging
            pass
    """

    def __init__(self, logger_name: str, level: str):
        """Initialize the temporary log level context manager.

        Args:
            logger_name: Name of the logger to modify
            level: Log level to temporarily set
        """
        self.logger_name = logger_name
        self.new_level = level
        self.original_level = None

    def __enter__(self):
        """Enter the context manager and set temporary log level.

        Returns:
            The logger instance with the new level set
        """
        logger = logging.getLogger(self.logger_name)
        self.original_level = logger.level
        logger.setLevel(getattr(logging, self.new_level.upper(), logging.INFO))
        return logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and restore original log level.

        Args:
            exc_type: Exception type if any
            exc_val: Exception value if any
            exc_tb: Exception traceback if any
        """
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(self.original_level)
