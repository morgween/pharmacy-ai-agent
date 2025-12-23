"""centralized logging configuration for pharmacy ai agent"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    configure structured logging for the application

    args:
        log_level: logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: optional path to log file (creates parent directories if needed)

    returns:
        configured logger instance
    """
    # format with timestamp, module, level, file location, and message
    log_format = (
        '%(asctime)s - %(name)s - %(levelname)s - '
        '%(filename)s:%(lineno)d - %(message)s'
    )

    # date format for timestamps
    date_format = '%Y-%m-%d %H:%M:%S'

    # configure handlers
    handlers = [logging.StreamHandler(sys.stdout)]

    # add file handler if log file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
        handlers.append(file_handler)

    # configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True  # override any existing configuration
    )

    # return logger for caller
    logger = logging.getLogger(__name__)
    logger.info(f"logging initialized at {log_level} level")

    if log_file:
        logger.info(f"logging to file: {log_file}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    get a logger instance for a specific module

    args:
        name: module name (typically __name__)

    returns:
        logger instance
    """
    return logging.getLogger(name)
