"""
Centralized logging configuration with Sentry integration.

This module provides a unified way to configure logging across the application,
integrating with Sentry for error tracking and log aggregation.
"""
import logging
import os
import sys
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


def setup_logging(
        level: str = "INFO",
        sentry_dsn: Optional[str] = None,
        environment: Optional[str] = None,
        enable_sentry: bool = True
) -> None:
    """
    Configure logging for the application with Sentry integration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        sentry_dsn: Sentry DSN URL. If not provided, will read from SENTRY_DSN env var
        environment: Environment name (e.g., 'production', 'staging', 'development')
        enable_sentry: Whether to enable Sentry integration
    """
    # Configure basic logging
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create a formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Initialize Sentry if enabled
    if enable_sentry:
        # Get Sentry DSN from parameter or environment variable
        dsn = sentry_dsn or os.getenv('SENTRY_DSN')

        if dsn:
            # Get environment from parameter or environment variable
            env = environment or os.getenv('SENTRY_ENVIRONMENT', 'production')

            # Configure Sentry logging integration
            # This will capture logs at ERROR level and above as breadcrumbs
            # and send them to Sentry
            sentry_logging = LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors and above as events
            )

            sentry_sdk.init(
                dsn=dsn,
                environment=env,
                integrations=[sentry_logging],
                traces_sample_rate=0.1,  # Sample 10% of transactions for performance monitoring
                profiles_sample_rate=0.1,  # Sample 10% for profiling
                # Set release if available
                release=os.getenv('SENTRY_RELEASE', None),
                # Send default PII (personally identifiable information)
                send_default_pii=False,
                # Attach stack traces to pure messages
                attach_stacktrace=True,
                # Maximum breadcrumbs
                max_breadcrumbs=50,
            )

            logging.info(f"Sentry initialized successfully for environment: {env}")
        else:
            logging.warning(
                "Sentry DSN not provided. Logging will work locally only. "
                "Set SENTRY_DSN environment variable to enable Sentry integration."
            )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def capture_exception(exception: Exception, **extra_data) -> None:
    """
    Manually capture an exception and send it to Sentry.

    Args:
        exception: The exception to capture
        **extra_data: Additional context data to attach to the event
    """
    if extra_data:
        # Use new isolation_scope API for Sentry SDK 2.x
        with sentry_sdk.isolation_scope() as scope:
            for key, value in extra_data.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exception)
    else:
        sentry_sdk.capture_exception(exception)


def capture_message(message: str, level: str = "info", **extra_data) -> None:
    """
    Manually capture a message and send it to Sentry.

    Args:
        message: The message to capture
        level: Message level (debug, info, warning, error, fatal)
        **extra_data: Additional context data to attach to the event
    """
    # Type casting for Sentry SDK literal type
    from typing import Literal
    sentry_level: Literal["fatal", "critical", "error", "warning", "info", "debug"] = level  # type: ignore

    if extra_data:
        # Use new isolation_scope API for Sentry SDK 2.x
        with sentry_sdk.isolation_scope() as scope:
            for key, value in extra_data.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=sentry_level)
    else:
        sentry_sdk.capture_message(message, level=sentry_level)


def add_breadcrumb(message: str, category: str = "default", level: str = "info", **data) -> None:
    """
    Add a breadcrumb to the current scope.
    Breadcrumbs are a trail of events that happened before an error.

    Args:
        message: Breadcrumb message
        category: Breadcrumb category (e.g., 'http', 'db', 'ui')
        level: Breadcrumb level
        **data: Additional data to attach
    """
    sentry_sdk.add_breadcrumb(
        category=category,
        message=message,
        level=level,
        data=data
    )
