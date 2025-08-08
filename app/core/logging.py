import logging
import sys
from typing import Any, Optional


def initialize_logging() -> None:
    """Initialize application logging"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def log_info(logger: logging.Logger, message: str, **kwargs: Any) -> None:
    logger.info(message, extra=kwargs)


def log_debug(logger: logging.Logger, message: str, **kwargs: Any) -> None:
    logger.debug(message, extra=kwargs)


def log_warning(
    logger: logging.Logger, message: str, exc_info: Optional[Exception] = None, **kwargs: Any
) -> None:
    logger.warning(message, exc_info=exc_info, extra=kwargs)


def log_error(
    logger: logging.Logger, message: str, exc_info: Optional[Exception] = None, **kwargs: Any
) -> None:
    logger.error(message, exc_info=exc_info, extra=kwargs)
