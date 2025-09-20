"""Generic for ADK tools."""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import structlog
from google.adk.tools import FunctionTool, LongRunningFunctionTool

logger = structlog.get_logger(__name__)


RT = TypeVar("RT")  # Return type
TOOL_REGISTRY: list[Any] = []


def adk_tool(func: Callable[..., RT]) -> Callable[..., RT]:  # noqa: UP047
    """
    Decorator to register a function as a Gemini-compatible ADK tool.

    Automatically wraps async functions using LongRunningFunctionTool,
    and sync functions using FunctionTool.
    """
    is_async = inspect.iscoroutinefunction(func)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.info("adk_tool", func=func.__name__, args=args, kwargs=kwargs)
        return func(*args, **kwargs)

    tool_obj = (
        LongRunningFunctionTool(func=func) if is_async else FunctionTool(func=func)
    )

    TOOL_REGISTRY.append(tool_obj)
    return cast("Callable[..., RT]", wrapper)
