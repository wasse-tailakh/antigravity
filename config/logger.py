"""Unified logging system for Antigravity project."""

import logging
import sys
from pathlib import Path
from typing import Optional

class LoggerSetup:
    """Centralized logging configuration for the entire project."""
    
    _initialized = False
    _log_level = logging.INFO
    
    @classmethod
    def setup(cls, 
              name: str = "antigravity",
              level: int = logging.INFO,
              log_file: Optional[Path] = None,
              console: bool = True) -> logging.Logger:
        """
        Setup a logger with consistent formatting.
        
        Args:
            name: Logger name (typically module name)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional file path for logging to file
            console: Whether to log to console (default: True)
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
            
        logger.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console handler
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        cls._initialized = True
        cls._log_level = level
        
        return logger
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get or create a logger with the default configuration.
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            Logger instance
        """
        if not cls._initialized:
            cls.setup()
        
        return logging.getLogger(name)


# Convenience function
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return LoggerSetup.get_logger(name)
