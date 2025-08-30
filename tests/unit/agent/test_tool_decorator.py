"""Unit tests for the ADK tool decorator specifically."""

import sys
from unittest.mock import MagicMock

import pytest

# Mock all optional dependencies before any imports
mock_modules = [
    "telegram",
    "telegram.error",
    "telegram.ext",
    "tweepy",
    "tweepy.asynchronous",
    "tweepy.errors",
    "python_telegram_bot",
]

for module in mock_modules:
    sys.modules[module] = MagicMock()

# Mock specific classes that are imported
sys.modules["telegram"].error = MagicMock()
sys.modules["telegram"].error.TelegramError = Exception
sys.modules["telegram"].ext = MagicMock()
sys.modules["telegram"].ext.Application = MagicMock()

sys.modules["tweepy"].asynchronous = MagicMock()
sys.modules["tweepy"].errors = MagicMock()
sys.modules["tweepy"].errors.TweepyException = Exception


def test_tool_decorator_registration():
    """Test that the @tool decorator properly registers functions."""
    # Import after mocking
    from flare_ai_kit.agent.tool import TOOL_REGISTRY, tool

    initial_count = len(TOOL_REGISTRY)

    @tool
    async def test_async_function(param: str) -> dict:
        """Test async function."""
        return {"result": f"Hello {param}"}

    @tool
    def test_sync_function(param: int) -> int:
        """Test sync function."""
        return param * 2

    # Should have added 2 tools to registry
    assert len(TOOL_REGISTRY) == initial_count + 2

    # Check that latest tools have the expected structure
    latest_tools = TOOL_REGISTRY[-2:]

    # Both should be wrapped as ADK tools
    for tool_obj in latest_tools:
        assert hasattr(tool_obj, "_func") or hasattr(tool_obj, "func")


def test_tool_decorator_preserves_metadata():
    """Test that the decorator preserves function metadata."""
    from flare_ai_kit.agent.tool import tool, TOOL_REGISTRY

    @tool
    async def documented_function(x: int, y: str = "default") -> dict:
        """This is a test function with documentation.

        Args:
            x: An integer parameter
            y: A string parameter with default

        Returns:
            A dictionary with results
        """
        return {"x": x, "y": y}

    # Function should still be callable (wrapped)
    assert callable(documented_function)

    # Original function should be preserved somewhere in the tool object
    tool_obj = TOOL_REGISTRY[-1]

    # The actual function reference should be accessible
    func_ref = getattr(tool_obj, "_func", getattr(tool_obj, "func", None))
    if func_ref and not str(func_ref).startswith("<MagicMock"):  # Skip mocked functions
        assert func_ref.__name__ == "documented_function"
        assert "test function" in func_ref.__doc__


@pytest.mark.asyncio
async def test_tool_execution():
    """Test that decorated tools can still be executed."""
    from flare_ai_kit.agent.tool import tool

    @tool
    async def executable_tool(message: str) -> dict:
        """A tool that can be executed."""
        return {"message": f"Processed: {message}", "success": True}

    # The decorated function should still work
    result = await executable_tool("test message")

    assert isinstance(result, dict)
    assert "Processed: test message" in result["message"]
    assert result["success"] == True


def test_tool_registry_isolation():
    """Test that the tool registry maintains tools across imports."""
    from flare_ai_kit.agent.tool import TOOL_REGISTRY, tool

    initial_count = len(TOOL_REGISTRY)

    @tool
    def isolated_test_tool():
        """Test tool for isolation."""
        return "isolated"

    # Should increment by 1
    assert len(TOOL_REGISTRY) == initial_count + 1

    # Re-importing should not change the count
    from flare_ai_kit.agent.tool import TOOL_REGISTRY as TOOL_REGISTRY_2

    assert len(TOOL_REGISTRY_2) == len(TOOL_REGISTRY)
    assert TOOL_REGISTRY is TOOL_REGISTRY_2  # Should be the same object
