"""
Structured logging utilities for Flare AI Kit.

Provides standardized logging configuration and utilities for consistent
logging across all modules. Automatically masks sensitive data and provides
structured context information.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import LoggerFactory

from .exceptions import FlareAIKitError


def configure_logging(level: str = "INFO") -> None:
    """
    Configure structured logging for the Flare AI Kit.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(colors=True)
            if sys.stderr.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger for the given module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structured logger

    """
    return structlog.get_logger(name)


def mask_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Mask sensitive data in logging context.

    Args:
        data: Dictionary containing potentially sensitive data

    Returns:
        Dictionary with sensitive values masked

    """
    sensitive_keys = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "key",
        "api_key",
        "private_key",
        "privatekey",
        "mnemonic",
        "seed",
        "auth",
        "authorization",
        "credential",
        "cred",
        "access_token",
        "refresh_token",
        "bearer",
        "jwt",
        "session",
        "cookie",
    }

    masked_data = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            masked_data[key] = "***MASKED***"  # type: ignore[assignment]
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value)  # type: ignore[arg-type]
        else:
            masked_data[key] = value
    return masked_data  # type: ignore[return-value]


def log_exception(
    logger: structlog.BoundLogger,
    exception: Exception,
    message: str,
    context: dict[str, Any] | None = None,
    level: str = "error",
    **kwargs: Any,
) -> None:
    """
    Log an exception with structured context.

    Args:
        logger: Structured logger instance
        exception: Exception to log
        message: Log message
        context: Additional context (sensitive data will be masked)
        level: Log level (debug, info, warning, error, critical)
        **kwargs: Additional keyword arguments to include in the log

    """
    log_context = mask_sensitive_data(context or {})
    log_context.update(mask_sensitive_data(kwargs))

    if isinstance(exception, FlareAIKitError):
        log_context.update(
            {
                "error_code": exception.error_code,
                "exception_context": exception.context,
            }
        )

    getattr(logger, level)(
        message,
        exception=str(exception),
        exception_type=type(exception).__name__,
        **log_context,
        exc_info=True,
    )


def log_operation_start(
    logger: structlog.BoundLogger,
    operation: str,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Log the start of an operation.

    Args:
        logger: Structured logger instance
        operation: Operation name
        context: Additional context (sensitive data will be masked)

    """
    log_context = mask_sensitive_data(context or {})
    logger.info("Starting %s", operation, operation=operation, **log_context)


def log_operation_success(
    logger: structlog.BoundLogger,
    operation: str,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Log successful completion of an operation.

    Args:
        logger: Structured logger instance
        operation: Operation name
        context: Additional context (sensitive data will be masked)

    """
    log_context = mask_sensitive_data(context or {})
    logger.info("Completed %s", operation, operation=operation, **log_context)


def log_operation_failure(
    logger: structlog.BoundLogger,
    operation: str,
    error: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Log failure of an operation.

    Args:
        logger: Structured logger instance
        operation: Operation name
        error: Exception that caused the failure
        context: Additional context (sensitive data will be masked)

    """
    log_exception(logger, error, "Failed %s", context, "error", operation=operation)
