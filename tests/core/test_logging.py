import logging
from unittest.mock import Mock, patch
from app.core.logging import initialize_logging, log_info, log_debug


def test_initialize_logging():
    """Test that logging gets initialized"""
    with patch("logging.basicConfig") as mock_config:
        initialize_logging()
        mock_config.assert_called_once()


def test_log_functions_call_logger():
    """Test that log functions call logger methods"""
    mock_logger = Mock()

    log_info(mock_logger, "test message", extra_param="value")
    log_debug(mock_logger, "debug message")

    mock_logger.info.assert_called_once_with(
        "test message", extra={"extra_param": "value"}
    )
    mock_logger.debug.assert_called_once_with("debug message", extra={})
