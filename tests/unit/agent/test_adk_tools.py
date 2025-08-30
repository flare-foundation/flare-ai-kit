"""Unit tests for ADK tool decorators and functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Test the core tool decorator
def test_tool_decorator():
    """Test that the @tool decorator properly registers functions."""
    from flare_ai_kit.agent.tool import TOOL_REGISTRY, tool

    initial_count = len(TOOL_REGISTRY)

    @tool
    async def test_async_function(param: str) -> str:
        """Test async function."""
        return f"Hello {param}"

    @tool
    def test_sync_function(param: int) -> int:
        """Test sync function."""
        return param * 2

    # Should have added 2 tools
    assert len(TOOL_REGISTRY) == initial_count + 2

    # Check that tools were wrapped properly
    latest_tools = TOOL_REGISTRY[-2:]
    assert hasattr(latest_tools[0], "_func") or hasattr(latest_tools[0], "func")
    assert hasattr(latest_tools[1], "_func") or hasattr(latest_tools[1], "func")


class TestEcosystemTools:
    """Test ecosystem tool functions."""

    @pytest.mark.asyncio
    @patch("flare_ai_kit.agent.ecosystem_tools.FtsoV2")
    @patch("flare_ai_kit.agent.ecosystem_tools.EcosystemSettings")
    async def test_get_ftso_price(self, mock_settings, mock_ftso_class):
        """Test FTSO price retrieval tool."""
        from flare_ai_kit.agent.ecosystem_tools import get_ftso_price

        # Mock the FtsoV2 instance
        mock_ftso = AsyncMock()
        mock_ftso.get_latest_price.return_value = 45123.45
        mock_ftso_class.create = AsyncMock(return_value=mock_ftso)

        result = await get_ftso_price("BTC/USD", "01")

        assert result["status"] == "success"
        assert result["feed_name"] == "BTC/USD"
        assert result["price"] == 45123.45
        assert result["category"] == "01"

        mock_ftso.get_latest_price.assert_called_once()

    @pytest.mark.asyncio
    @patch("flare_ai_kit.agent.ecosystem_tools.Flare")
    @patch("flare_ai_kit.agent.ecosystem_tools.EcosystemSettings")
    async def test_check_flr_balance(self, mock_settings, mock_flare_class):
        """Test FLR balance check tool."""
        from flare_ai_kit.agent.ecosystem_tools import check_flr_balance

        # Mock the Flare instance
        mock_flare = AsyncMock()
        mock_flare.check_balance.return_value = 1000.5
        mock_flare_class.return_value = mock_flare

        address = "0x1234567890123456789012345678901234567890"
        result = await check_flr_balance(address)

        assert result["status"] == "success"
        assert result["address"] == address
        assert result["balance"] == 1000.5
        assert result["currency"] == "FLR"


class TestTeeTools:
    """Test TEE tool functions."""

    @pytest.mark.asyncio
    @patch("flare_ai_kit.agent.tee_tools.VtpmAttestation")
    async def test_get_attestation_token(self, mock_attestation_class):
        """Test attestation token generation."""
        from flare_ai_kit.agent.tee_tools import get_attestation_token

        # Mock the VtpmAttestation instance
        mock_attestation = MagicMock()
        mock_attestation.get_token.return_value = (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."
        )
        mock_attestation_class.return_value = mock_attestation

        nonces = ["test_nonce_123", "test_nonce_456"]
        result = await get_attestation_token(nonces, simulate=True)

        assert result["status"] == "success"
        assert result["nonces_count"] == 2
        assert result["simulated"] == True
        assert result["token_type"] == "OIDC"
        assert "token" in result

    @pytest.mark.asyncio
    async def test_create_secure_nonces(self):
        """Test secure nonce generation."""
        from flare_ai_kit.agent.tee_tools import create_secure_nonces

        result = await create_secure_nonces(count=3, length=25)

        assert result["status"] == "success"
        assert result["count"] == 3
        assert result["length"] == 25
        assert len(result["nonces"]) == 3
        assert all(len(nonce) == 25 for nonce in result["nonces"])

    @pytest.mark.asyncio
    async def test_check_tee_environment(self):
        """Test TEE environment check."""
        from flare_ai_kit.agent.tee_tools import check_tee_environment

        with patch("pathlib.Path.exists", return_value=False):
            with patch("os.getenv", return_value=None):
                result = await check_tee_environment()

                assert result["status"] == "success"
                assert result["environment"] == "standard"
                assert result["tee_socket_exists"] == False
                assert result["confidential_space"] == False


class TestWalletTools:
    """Test wallet tool functions."""

    @pytest.mark.asyncio
    @patch("flare_ai_kit.agent.wallet_tools.TurnkeyWallet")
    @patch("flare_ai_kit.agent.wallet_tools.TurnkeySettings")
    async def test_create_wallet(self, mock_settings, mock_wallet_class):
        """Test wallet creation tool."""
        from flare_ai_kit.agent.wallet_tools import create_wallet

        # Mock the TurnkeyWallet instance
        mock_wallet = AsyncMock()
        mock_wallet.create_wallet.return_value = "wallet_123"
        mock_wallet_class.return_value.__aenter__.return_value = mock_wallet

        result = await create_wallet("Test Wallet")

        assert result["status"] == "success"
        assert result["wallet_name"] == "Test Wallet"
        assert result["wallet_id"] == "wallet_123"

    @pytest.mark.asyncio
    async def test_create_transaction_policy(self):
        """Test transaction policy creation."""
        from flare_ai_kit.agent.wallet_tools import create_transaction_policy

        result = await create_transaction_policy(
            policy_name="test_policy",
            description="Test policy for unit tests",
            max_transaction_value=10.0,
            daily_spending_limit=100.0,
        )

        assert result["status"] == "success"
        assert result["policy_name"] == "test_policy"
        assert result["enabled"] == True


class TestSocialTools:
    """Test social media tool functions."""

    @pytest.mark.asyncio
    @patch("flare_ai_kit.agent.social_tools.TelegramClient")
    @patch("flare_ai_kit.agent.social_tools.SocialSettings")
    async def test_send_telegram_message(self, mock_settings, mock_telegram_class):
        """Test Telegram message sending."""
        from flare_ai_kit.agent.social_tools import send_telegram_message

        # Mock the TelegramClient instance
        mock_telegram = AsyncMock()
        mock_telegram.send_message.return_value = True
        mock_telegram.is_configured = True
        mock_telegram_class.return_value = mock_telegram

        result = await send_telegram_message("@testchannel", "Hello World!")

        assert result["status"] == "success"
        assert result["success"] == True
        assert result["platform"] == "telegram"
        assert result["configured"] == True

    @pytest.mark.asyncio
    async def test_format_social_update(self):
        """Test social media formatting."""
        from flare_ai_kit.agent.social_tools import format_social_update

        result = await format_social_update(
            title="Test Update",
            description="This is a test update",
            hashtags=["test", "demo"],
            platform="general",
        )

        assert result["status"] == "success"
        assert "Test Update" in result["message"]
        assert "#test" in result["message"]
        assert "#demo" in result["message"]
        assert result["platform"] == "general"


@pytest.mark.asyncio
async def test_tool_error_handling():
    """Test that tools handle errors gracefully."""
    from flare_ai_kit.agent.ecosystem_tools import get_ftso_price

    # Test with invalid parameters that would cause an error
    with patch("flare_ai_kit.agent.ecosystem_tools.FtsoV2") as mock_ftso_class:
        mock_ftso_class.create = AsyncMock(side_effect=Exception("Connection failed"))

        result = await get_ftso_price("INVALID/PAIR", "99")

        assert result["status"] == "error"
        assert "error" in result
        assert result["price"] == 0.0
