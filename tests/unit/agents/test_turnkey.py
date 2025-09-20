"""Tests for Turnkey agent connector."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from flare_ai_kit.agents.turnkey import (
    AgentTransaction,
    AgentWalletConfig,
    TurnkeyAgentConnector,
)
from flare_ai_kit.wallet.base import SignedTransaction, TransactionRequest
from flare_ai_kit.wallet.turnkey_wallet import TurnkeyWallet


@pytest.fixture
def mock_turnkey_wallet():
    """Create mock TurnkeyWallet."""
    wallet = MagicMock(spec=TurnkeyWallet)
    wallet.permission_engine = MagicMock()
    wallet.permission_engine.add_policy = MagicMock()
    wallet.permission_engine.remove_policy = MagicMock()
    wallet.sign_transaction = AsyncMock()
    wallet.validate_tee_attestation = AsyncMock(return_value=True)
    return wallet


@pytest.fixture
def agent_connector(mock_turnkey_wallet):
    """Create TurnkeyAgentConnector for testing."""
    return TurnkeyAgentConnector(mock_turnkey_wallet)


@pytest.fixture
def agent_config():
    """Create sample agent configuration."""
    return AgentWalletConfig(
        agent_id="test_agent_001",
        wallet_id="test_wallet_001",
        max_daily_spend=0.5,
        max_transaction_value=0.1,
        allowed_hours=list(range(9, 18)),  # 9 AM to 6 PM
        require_tee_attestation=True,
    )


@pytest.fixture
def sample_agent_transaction():
    """Create sample agent transaction."""
    return AgentTransaction(
        agent_id="test_agent_001",
        transaction_request=TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="50000000000000000",  # 0.05 ETH
            chain_id=1,
        ),
        justification="Automated DeFi yield optimization",
        confidence_score=0.85,
        risk_assessment="Low risk - established protocol",
    )


class TestAgentWalletConfig:
    """Test AgentWalletConfig model."""

    def test_create_basic_config(self):
        """Test creating basic agent configuration."""
        config = AgentWalletConfig(agent_id="test_agent", wallet_id="test_wallet")

        assert config.agent_id == "test_agent"
        assert config.wallet_id == "test_wallet"
        assert config.max_daily_spend == 0.1  # Default
        assert config.max_transaction_value == 0.01  # Default
        assert config.require_tee_attestation is True  # Default

    def test_create_custom_config(self):
        """Test creating custom agent configuration."""
        config = AgentWalletConfig(
            agent_id="custom_agent",
            wallet_id="custom_wallet",
            max_daily_spend=1.0,
            max_transaction_value=0.25,
            allowed_hours=[9, 10, 11, 12, 13, 14, 15, 16, 17],
            require_tee_attestation=False,
        )

        assert config.max_daily_spend == 1.0
        assert config.max_transaction_value == 0.25
        assert config.allowed_hours == [9, 10, 11, 12, 13, 14, 15, 16, 17]
        assert config.require_tee_attestation is False


class TestAgentTransaction:
    """Test AgentTransaction model."""

    def test_create_agent_transaction(self, sample_agent_transaction):
        """Test creating agent transaction."""
        assert sample_agent_transaction.agent_id == "test_agent_001"
        assert sample_agent_transaction.confidence_score == 0.85
        assert (
            sample_agent_transaction.justification
            == "Automated DeFi yield optimization"
        )
        assert (
            sample_agent_transaction.risk_assessment
            == "Low risk - established protocol"
        )

    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        # Valid confidence score
        transaction = AgentTransaction(
            agent_id="test_agent",
            transaction_request=TransactionRequest(
                to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
                value="1000000000000000000",
                chain_id=1,
            ),
            justification="Test transaction",
            confidence_score=0.75,
            risk_assessment="Medium risk",
        )

        assert transaction.confidence_score == 0.75

        # Invalid confidence scores should raise validation error
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            AgentTransaction(
                agent_id="test_agent",
                transaction_request=TransactionRequest(
                    to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
                    value="1000000000000000000",
                    chain_id=1,
                ),
                justification="Test transaction",
                confidence_score=1.5,  # Invalid: > 1.0
                risk_assessment="Medium risk",
            )


class TestTurnkeyAgentConnector:
    """Test TurnkeyAgentConnector functionality."""

    @pytest.mark.asyncio
    async def test_register_agent(self, agent_connector, agent_config):
        """Test agent registration."""
        result = await agent_connector.register_agent(agent_config)

        assert result is True
        assert agent_config.agent_id in agent_connector.agent_configs

        # Verify policy was added
        agent_connector.wallet.permission_engine.add_policy.assert_called_once()

    @pytest.mark.asyncio
    async def test_unregister_agent(self, agent_connector, agent_config):
        """Test agent unregistration."""
        # First register the agent
        await agent_connector.register_agent(agent_config)

        # Then unregister
        result = await agent_connector.unregister_agent(agent_config.agent_id)

        assert result is True
        assert agent_config.agent_id not in agent_connector.agent_configs

        # Verify policy was removed
        agent_connector.wallet.permission_engine.remove_policy.assert_called()

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_agent(self, agent_connector):
        """Test unregistering non-existent agent."""
        result = await agent_connector.unregister_agent("nonexistent_agent")

        assert result is False

    @pytest.mark.asyncio
    async def test_execute_agent_transaction_success(
        self, agent_connector, agent_config, sample_agent_transaction
    ):
        """Test successful agent transaction execution."""
        # Register agent first
        await agent_connector.register_agent(agent_config)

        # Mock successful transaction signing

        signed_tx = SignedTransaction(
            transaction_hash="0x123abc...",
            signed_transaction="0xf86c...",
            raw_transaction="0xf86c...",
        )
        agent_connector.wallet.sign_transaction.return_value = signed_tx

        # Execute transaction
        result = await agent_connector.execute_agent_transaction(
            sample_agent_transaction, attestation_token="valid_token"
        )

        assert result["success"] is True
        assert result["transaction_hash"] == "0x123abc..."
        assert len(agent_connector.transaction_log) == 1

        # Verify wallet methods were called
        agent_connector.wallet.validate_tee_attestation.assert_called_once_with(
            "valid_token"
        )
        agent_connector.wallet.sign_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_transaction_unregistered_agent(
        self, agent_connector, sample_agent_transaction
    ):
        """Test executing transaction with unregistered agent."""
        result = await agent_connector.execute_agent_transaction(
            sample_agent_transaction
        )

        assert result["success"] is False
        assert "not registered" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_transaction_missing_tee_attestation(
        self, agent_connector, agent_config, sample_agent_transaction
    ):
        """Test executing transaction without required TEE attestation."""
        # Register agent with TEE requirement
        await agent_connector.register_agent(agent_config)

        # Execute without attestation token
        result = await agent_connector.execute_agent_transaction(
            sample_agent_transaction
        )

        assert result["success"] is False
        assert "TEE attestation required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_transaction_invalid_tee_attestation(
        self, agent_connector, agent_config, sample_agent_transaction
    ):
        """Test executing transaction with invalid TEE attestation."""
        # Register agent
        await agent_connector.register_agent(agent_config)

        # Mock invalid attestation
        agent_connector.wallet.validate_tee_attestation.return_value = False

        result = await agent_connector.execute_agent_transaction(
            sample_agent_transaction, attestation_token="invalid_token"
        )

        assert result["success"] is False
        assert "Invalid TEE attestation" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_transaction_low_confidence(
        self, agent_connector, agent_config
    ):
        """Test executing transaction with low confidence score."""
        # Register agent
        await agent_connector.register_agent(agent_config)

        # Create low confidence transaction
        low_confidence_tx = AgentTransaction(
            agent_id="test_agent_001",
            transaction_request=TransactionRequest(
                to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
                value="50000000000000000",
                chain_id=1,
            ),
            justification="Test transaction",
            confidence_score=0.3,  # Below threshold
            risk_assessment="High risk",
        )

        result = await agent_connector.execute_agent_transaction(
            low_confidence_tx, attestation_token="valid_token"
        )

        assert result["success"] is False
        assert "confidence" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_transaction_value_exceeds_limit(
        self, agent_connector, agent_config
    ):
        """Test executing transaction that exceeds agent value limit."""
        # Register agent
        await agent_connector.register_agent(agent_config)

        # Create transaction exceeding limit
        large_tx = AgentTransaction(
            agent_id="test_agent_001",
            transaction_request=TransactionRequest(
                to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
                value="200000000000000000",  # 0.2 ETH (exceeds 0.1 ETH limit)
                chain_id=1,
            ),
            justification="Large transaction",
            confidence_score=0.9,
            risk_assessment="Low risk",
        )

        result = await agent_connector.execute_agent_transaction(
            large_tx, attestation_token="valid_token"
        )

        assert result["success"] is False
        assert "exceeds agent limit" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_transaction_empty_justification(
        self, agent_connector, agent_config
    ):
        """Test executing transaction with empty justification."""
        # Register agent
        await agent_connector.register_agent(agent_config)

        # Create transaction with empty justification
        empty_justification_tx = AgentTransaction(
            agent_id="test_agent_001",
            transaction_request=TransactionRequest(
                to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
                value="50000000000000000",
                chain_id=1,
            ),
            justification="",  # Empty justification
            confidence_score=0.8,
            risk_assessment="Low risk",
        )

        result = await agent_connector.execute_agent_transaction(
            empty_justification_tx, attestation_token="valid_token"
        )

        assert result["success"] is False
        assert "justification is required" in result["error"]

    @pytest.mark.asyncio
    async def test_get_agent_status(self, agent_connector, agent_config):
        """Test getting agent status."""
        # Register agent
        await agent_connector.register_agent(agent_config)

        status = await agent_connector.get_agent_status(agent_config.agent_id)

        assert status is not None
        assert status["agent_id"] == agent_config.agent_id
        assert status["wallet_id"] == agent_config.wallet_id
        assert status["is_registered"] is True
        assert "statistics" in status
        assert "config" in status

    @pytest.mark.asyncio
    async def test_get_agent_status_nonexistent(self, agent_connector):
        """Test getting status for non-existent agent."""
        status = await agent_connector.get_agent_status("nonexistent_agent")

        assert status is None

    @pytest.mark.asyncio
    async def test_list_registered_agents(self, agent_connector, agent_config):
        """Test listing registered agents."""
        # Initially empty
        agents = await agent_connector.list_registered_agents()
        assert len(agents) == 0

        # Register agent
        await agent_connector.register_agent(agent_config)

        agents = await agent_connector.list_registered_agents()
        assert len(agents) == 1
        assert agent_config.agent_id in agents

    @pytest.mark.asyncio
    async def test_get_transaction_history(
        self, agent_connector, agent_config, sample_agent_transaction
    ):
        """Test getting transaction history."""
        # Register agent and execute transaction
        await agent_connector.register_agent(agent_config)

        # Mock successful transaction

        signed_tx = SignedTransaction(
            transaction_hash="0x123abc...",
            signed_transaction="0xf86c...",
            raw_transaction="0xf86c...",
        )
        agent_connector.wallet.sign_transaction.return_value = signed_tx

        await agent_connector.execute_agent_transaction(
            sample_agent_transaction, attestation_token="valid_token"
        )

        # Get transaction history
        history = await agent_connector.get_transaction_history()
        assert len(history) == 1
        assert history[0]["agent_id"] == agent_config.agent_id
        assert history[0]["transaction_hash"] == "0x123abc..."

        # Get history filtered by agent
        agent_history = await agent_connector.get_transaction_history(
            agent_id=agent_config.agent_id
        )
        assert len(agent_history) == 1

    @pytest.mark.asyncio
    async def test_update_agent_config(self, agent_connector, agent_config):
        """Test updating agent configuration."""
        # Register agent
        await agent_connector.register_agent(agent_config)

        # Create updated config
        updated_config = AgentWalletConfig(
            agent_id=agent_config.agent_id,
            wallet_id=agent_config.wallet_id,
            max_daily_spend=1.0,  # Increased limit
            max_transaction_value=0.25,  # Increased limit
            allowed_hours=list(range(24)),  # 24/7 operation
            require_tee_attestation=False,
        )

        result = await agent_connector.update_agent_config(
            agent_config.agent_id, updated_config
        )

        assert result is True
        assert (
            agent_connector.agent_configs[agent_config.agent_id].max_daily_spend == 1.0
        )
        assert (
            agent_connector.agent_configs[agent_config.agent_id].max_transaction_value
            == 0.25
        )

        # Verify old policy was removed and new policy was added
        assert agent_connector.wallet.permission_engine.remove_policy.call_count >= 1
        assert (
            agent_connector.wallet.permission_engine.add_policy.call_count >= 2
        )  # Initial + update

    @pytest.mark.asyncio
    async def test_update_nonexistent_agent_config(self, agent_connector, agent_config):
        """Test updating configuration for non-existent agent."""
        result = await agent_connector.update_agent_config(
            "nonexistent_agent", agent_config
        )

        assert result is False
