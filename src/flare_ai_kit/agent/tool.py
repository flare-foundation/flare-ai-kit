import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from google.adk.tools import FunctionTool, LongRunningFunctionTool

RT = TypeVar("RT")  # Return type
# ToolUnion = FunctionTool
TOOL_REGISTRY: list[Any] = []


def tool(func: Callable[..., RT]) -> Callable[..., RT]:
    """
    Decorator to register a function as a Gemini-compatible ADK tool.
    Automatically wraps async functions using LongRunningFunctionTool,
    and sync functions using FunctionTool.
    """
    is_async = inspect.iscoroutinefunction(func)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"[ADK TOOL] Calling {func.__name__} with args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)

    # Choose appropriate wrapper
    tool_obj = (
        LongRunningFunctionTool(func=func) if is_async else FunctionTool(func=func)
    )

    TOOL_REGISTRY.append(tool_obj)
    return cast("Callable[..., RT]", wrapper)
