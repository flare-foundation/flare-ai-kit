"""Unit tests for Stargate connector."""

from unittest.mock import patch

import pytest

from flare_ai_kit.common import StargateError
from flare_ai_kit.ecosystem.applications.stargate import Stargate
from flare_ai_kit.ecosystem.settings import EcosystemSettings


@pytest.fixture
def settings():
    """Create a valid EcosystemSettings for testing."""
    return EcosystemSettings(
        wallet_address="0x1234567890123456789012345678901234567890",
        private_key="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        web3_provider_url="https://flare-api.flare.network/ext/C/rpc",
        max_retries=3,
    )


@pytest.mark.asyncio
async def test_stargate_initialization(settings):
    """Test successful initialization of Stargate connector."""
    with patch("flare_ai_kit.ecosystem.flare.AsyncWeb3"):
        stargate = await Stargate.create(settings)

        assert stargate.FLARE_ENDPOINT_ID == 30295
        # Verify addresses are loaded from settings
        assert stargate.settings.contracts.flare.stargate_eth_oft is not None
        assert stargate.settings.contracts.flare.stargate_usdc_oft is not None
        assert stargate.settings.contracts.flare.stargate_usdt_oft is not None


@pytest.mark.asyncio
async def test_get_oft_address(settings):
    """Test getting OFT token addresses."""
    with patch("flare_ai_kit.ecosystem.flare.AsyncWeb3"):
        stargate = await Stargate.create(settings)

        # Valid tokens
        assert (
            stargate.get_oft_address("ETH")
            == "0x8e8539e4CcD69123c623a106773F2b0cbbc58746"
        )
        assert (
            stargate.get_oft_address("USDC")
            == "0x77C71633C34C3784ede189d74223122422492a0f"
        )
        assert (
            stargate.get_oft_address("USDT")
            == "0x1C10CC06DC6D35970d1D53B2A23c76ef370d4135"
        )

        # Case insensitive
        assert stargate.get_oft_address("eth") == stargate.get_oft_address("ETH")

        # Invalid token
        with pytest.raises(StargateError, match="Unsupported token"):
            stargate.get_oft_address("BTC")


@pytest.mark.asyncio
async def test_get_chain_endpoint(settings):
    """Test getting chain endpoint IDs."""
    with patch("flare_ai_kit.ecosystem.flare.AsyncWeb3"):
        stargate = await Stargate.create(settings)

        # Valid chains
        assert stargate.get_chain_endpoint("ethereum") == 30101
        assert stargate.get_chain_endpoint("arbitrum") == 30110
        assert stargate.get_chain_endpoint("base") == 30184

        # Case insensitive
        assert stargate.get_chain_endpoint("ETHEREUM") == 30101

        # Invalid chain
        with pytest.raises(StargateError, match="Unsupported chain"):
            stargate.get_chain_endpoint("solana")


@pytest.mark.asyncio
async def test_get_supported_tokens(settings):
    """Test getting supported tokens."""
    with patch("flare_ai_kit.ecosystem.flare.AsyncWeb3"):
        stargate = await Stargate.create(settings)

        tokens = stargate.get_supported_tokens()

        assert "ETH" in tokens
        assert "USDC" in tokens
        assert "USDT" in tokens
        assert len(tokens) == 3


@pytest.mark.asyncio
async def test_get_supported_chains(settings):
    """Test getting supported chains."""
    with patch("flare_ai_kit.ecosystem.flare.AsyncWeb3"):
        stargate = await Stargate.create(settings)

        chains = stargate.get_supported_chains()

        assert "ethereum" in chains
        assert "arbitrum" in chains
        assert "base" in chains
        assert len(chains) == 10


@pytest.mark.asyncio
async def test_get_bridge_info(settings):
    """Test getting bridge info."""
    with patch("flare_ai_kit.ecosystem.flare.AsyncWeb3"):
        stargate = await Stargate.create(settings)

        info = stargate.get_bridge_info()

        assert info["network"] == "Flare"
        assert info["endpoint_id"] == 30295
        assert info["token_messaging"] == "0x45d417612e177672958dC0537C45a8f8d754Ac2E"
        assert info["treasurer"] == "0x090194F1EEDc134A680e3b488aBB2D212dba8c01"
        assert "ETH" in info["supported_tokens"]
        assert "arbitrum" in info["supported_chains"]
