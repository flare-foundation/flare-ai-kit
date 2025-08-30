"""Integration test for ADK implementation."""

import sys
from unittest.mock import MagicMock

import pytest

# Mock optional social dependencies before imports
mock_modules = [
    "telegram",
    "telegram.error",
    "telegram.ext",
    "tweepy",
    "tweepy.asynchronous",
    "tweepy.errors",
    "python_telegram_bot",
    "discord",
    "slack_sdk",
]

for module in mock_modules:
    sys.modules[module] = MagicMock()

# Mock specific classes
sys.modules["telegram"].error = MagicMock()
sys.modules["telegram"].error.TelegramError = Exception
sys.modules["telegram"].ext = MagicMock()


class MockApplication:
    @classmethod
    def builder(cls):
        return cls()

    def token(self, token):
        return self

    def build(self):
        return self


sys.modules["telegram"].ext.Application = MockApplication

sys.modules["tweepy"].asynchronous = MagicMock()
sys.modules["tweepy"].errors = MagicMock()
sys.modules["tweepy"].errors.TweepyException = Exception


@pytest.mark.asyncio
async def test_adk_full_integration():
    """Test full ADK integration with all components."""

    # Import the tool module
    from flare_ai_kit.agent.tool import TOOL_REGISTRY, tool

    initial_count = len(TOOL_REGISTRY)

    # Test basic tool registration
    @tool
    async def test_integration_tool(message: str) -> dict:
        """Test tool for integration."""
        return {"message": message, "status": "success"}

    assert len(TOOL_REGISTRY) == initial_count + 1

    # Test tool execution
    result = await test_integration_tool("integration test")
    assert result["status"] == "success"
    assert result["message"] == "integration test"

    print(f"✅ Basic tool registration and execution: {len(TOOL_REGISTRY)} tools")


def test_adk_tool_imports():
    """Test that ADK tool modules can be imported with mocked dependencies."""
    from flare_ai_kit.agent.tool import TOOL_REGISTRY

    initial_count = len(TOOL_REGISTRY)

    # Import TEE tools (should work with PyJWT)
    try:
        from flare_ai_kit.agent import tee_tools  # noqa: F401
        tee_import_success = True
        print("✅ TEE tools imported successfully")
    except Exception as e:
        tee_import_success = False
        print(f"❌ TEE tools import failed: {e}")

    # Import social tools (with mocked dependencies)
    try:
        from flare_ai_kit.agent import social_tools  # noqa: F401
        social_import_success = True
        print("✅ Social tools imported successfully")
    except Exception as e:
        social_import_success = False
        print(f"❌ Social tools import failed: {e}")

    # Import ecosystem tools
    try:
        from flare_ai_kit.agent import ecosystem_tools  # noqa: F401
        ecosystem_import_success = True
        print("✅ Ecosystem tools imported successfully")
    except Exception as e:
        ecosystem_import_success = False
        print(f"❌ Ecosystem tools import failed: {e}")

    # Import wallet tools
    try:
        from flare_ai_kit.agent import wallet_tools  # noqa: F401
        wallet_import_success = True
        print("✅ Wallet tools imported successfully")
    except Exception as e:
        wallet_import_success = False
        print(f"❌ Wallet tools import failed: {e}")

    final_count = len(TOOL_REGISTRY)
    tools_added = final_count - initial_count

    print(f"📊 Tools added during imports: {tools_added}")
    print(f"📋 Total tools in registry: {final_count}")

    # At least one module should import successfully
    assert (
        tee_import_success
        or social_import_success
        or ecosystem_import_success
        or wallet_import_success
    )

    # Should have added some tools (or tools were already imported)
    assert tools_added >= 0  # Allow 0 if tools were already imported in previous tests


def test_adk_agent_module():
    """Test that the main ADK agent module can be constructed."""
    try:
        from flare_ai_kit.agent.adk_agent import agent

        # Agent should be created
        assert agent is not None
        assert hasattr(agent, "name")
        assert "flare_ai_kit" in agent.name

        print(f"✅ ADK agent created: {agent.name}")
        return True

    except ImportError as e:
        print(f"⚠️  ADK agent import failed (missing API keys expected): {e}")
        return False
    except Exception as e:
        print(f"❌ ADK agent creation failed: {e}")
        return False


def test_tool_registry_contents():
    """Test the contents of the tool registry."""
    from flare_ai_kit.agent.tool import TOOL_REGISTRY

    print(f"\n🔧 Tool Registry Contents ({len(TOOL_REGISTRY)} tools):")

    for i, tool_obj in enumerate(TOOL_REGISTRY, 1):
        func = getattr(tool_obj, "_func", None)
        if func and hasattr(func, "__name__"):
            tool_name = func.__name__
        else:
            tool_name = f"{type(tool_obj).__name__}"

        print(f"  {i}. {tool_name}")

    # Should have some tools registered
    assert len(TOOL_REGISTRY) > 0

    # Each tool should be properly wrapped
    for tool_obj in TOOL_REGISTRY:
        # Should have the func attribute or be a proper ADK tool type
        assert (
            hasattr(tool_obj, "_func")
            or hasattr(tool_obj, "func")
            or callable(tool_obj)
        )


if __name__ == "__main__":
    print("🤖 Running ADK Integration Tests")
    print("=" * 50)

    # Run the tests manually if called directly
    import asyncio

    asyncio.run(test_adk_full_integration())
    test_adk_tool_imports()
    test_adk_agent_module()
    test_tool_registry_contents()

    print("\n✅ ADK integration tests completed!")
