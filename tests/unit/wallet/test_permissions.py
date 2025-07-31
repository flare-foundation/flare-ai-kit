"""Tests for wallet permissions and policy engine."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from flare_ai_kit.wallet.base import TransactionRequest
from flare_ai_kit.wallet.permissions import (
    PermissionEngine,
    PolicyAction,
    TimeWindow,
    TransactionPolicy,
)


@pytest.fixture
def permission_engine():
    """Create a permission engine for testing."""
    return PermissionEngine()


@pytest.fixture
def basic_policy():
    """Create a basic transaction policy."""
    return TransactionPolicy(
        name="basic_test_policy",
        description="Basic policy for testing",
        max_transaction_value=Decimal("0.1"),
        daily_spending_limit=Decimal("1.0"),
        time_windows=[
            TimeWindow(
                duration_minutes=60, max_transactions=5, max_value=Decimal("0.5")
            )
        ],
    )


@pytest.fixture
def sample_transaction():
    """Create a sample transaction request."""
    return TransactionRequest(
        to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
        value="50000000000000000",  # 0.05 ETH in wei
        chain_id=1,
    )


class TestTransactionPolicy:
    """Test TransactionPolicy model."""

    def test_create_basic_policy(self):
        """Test creating a basic policy."""
        policy = TransactionPolicy(
            name="test_policy",
            description="Test description",
            max_transaction_value=Decimal("1.0"),
        )

        assert policy.name == "test_policy"
        assert policy.description == "Test description"
        assert policy.max_transaction_value == Decimal("1.0")
        assert policy.enabled is True

    def test_create_policy_with_time_windows(self):
        """Test creating policy with time windows."""
        time_window = TimeWindow(
            duration_minutes=60, max_transactions=10, max_value=Decimal("2.0")
        )

        policy = TransactionPolicy(
            name="time_limited_policy",
            description="Policy with time limits",
            time_windows=[time_window],
        )

        assert len(policy.time_windows) == 1
        assert policy.time_windows[0].duration_minutes == 60
        assert policy.time_windows[0].max_transactions == 10
        assert policy.time_windows[0].max_value == Decimal("2.0")


class TestPermissionEngine:
    """Test PermissionEngine functionality."""

    def test_add_policy(self, permission_engine, basic_policy):
        """Test adding a policy to the engine."""
        permission_engine.add_policy(basic_policy)

        policies = permission_engine.list_policies()
        assert "basic_test_policy" in policies

    def test_remove_policy(self, permission_engine, basic_policy):
        """Test removing a policy from the engine."""
        permission_engine.add_policy(basic_policy)

        result = permission_engine.remove_policy("basic_test_policy")
        assert result is True

        policies = permission_engine.list_policies()
        assert "basic_test_policy" not in policies

    def test_remove_nonexistent_policy(self, permission_engine):
        """Test removing a policy that doesn't exist."""
        result = permission_engine.remove_policy("nonexistent_policy")
        assert result is False

    def test_get_policy(self, permission_engine, basic_policy):
        """Test retrieving a policy by name."""
        permission_engine.add_policy(basic_policy)

        retrieved_policy = permission_engine.get_policy("basic_test_policy")
        assert retrieved_policy is not None
        assert retrieved_policy.name == "basic_test_policy"

    def test_get_nonexistent_policy(self, permission_engine):
        """Test retrieving a policy that doesn't exist."""
        policy = permission_engine.get_policy("nonexistent_policy")
        assert policy is None


class TestPolicyEvaluation:
    """Test policy evaluation logic."""

    @pytest.mark.asyncio
    async def test_transaction_allowed(
        self, permission_engine, basic_policy, sample_transaction
    ):
        """Test transaction that should be allowed."""
        permission_engine.add_policy(basic_policy)

        action, violations = await permission_engine.evaluate_transaction(
            sample_transaction, "test_wallet"
        )

        assert action == PolicyAction.ALLOW
        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_transaction_exceeds_value_limit(
        self, permission_engine, basic_policy
    ):
        """Test transaction that exceeds value limit."""
        permission_engine.add_policy(basic_policy)

        large_transaction = TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="200000000000000000",  # 0.2 ETH (exceeds 0.1 ETH limit)
            chain_id=1,
        )

        action, violations = await permission_engine.evaluate_transaction(
            large_transaction, "test_wallet"
        )

        assert action == PolicyAction.DENY
        assert len(violations) > 0
        assert any(v.violation_type == "max_transaction_value" for v in violations)

    @pytest.mark.asyncio
    async def test_blocked_destination(self, permission_engine):
        """Test transaction to blocked destination."""
        blocked_address = "0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b"
        policy = TransactionPolicy(
            name="blocked_dest_policy",
            description="Policy with blocked destinations",
            blocked_destinations=[blocked_address],
        )
        permission_engine.add_policy(policy)

        transaction = TransactionRequest(
            to=blocked_address,
            value="10000000000000000",  # 0.01 ETH
            chain_id=1,
        )

        action, violations = await permission_engine.evaluate_transaction(
            transaction, "test_wallet"
        )

        assert action == PolicyAction.DENY
        assert len(violations) > 0
        assert any(v.violation_type == "blocked_destination" for v in violations)

    @pytest.mark.asyncio
    async def test_allowed_destinations_only(self, permission_engine):
        """Test transaction with allowed destinations restriction."""
        allowed_address = "0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b"
        disallowed_address = "0x1234567890123456789012345678901234567890"

        policy = TransactionPolicy(
            name="allowed_dest_policy",
            description="Policy with allowed destinations only",
            allowed_destinations=[allowed_address],
        )
        permission_engine.add_policy(policy)

        # Test allowed destination
        allowed_transaction = TransactionRequest(
            to=allowed_address, value="10000000000000000", chain_id=1
        )

        action, violations = await permission_engine.evaluate_transaction(
            allowed_transaction, "test_wallet"
        )

        assert action == PolicyAction.ALLOW
        assert len(violations) == 0

        # Test disallowed destination
        disallowed_transaction = TransactionRequest(
            to=disallowed_address, value="10000000000000000", chain_id=1
        )

        action, violations = await permission_engine.evaluate_transaction(
            disallowed_transaction, "test_wallet"
        )

        assert action == PolicyAction.DENY
        assert any(v.violation_type == "destination_not_allowed" for v in violations)

    @pytest.mark.asyncio
    async def test_contract_interaction_blocked(self, permission_engine):
        """Test blocking contract interactions."""
        policy = TransactionPolicy(
            name="no_contracts_policy",
            description="Policy that blocks contract interactions",
            allow_contract_interactions=False,
        )
        permission_engine.add_policy(policy)

        contract_transaction = TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="10000000000000000",
            data="0xa9059cbb000000000000000000000000742d35cc6634c0532925a3b8d8c8ee7c9e92bb1b",
            chain_id=1,
        )

        action, violations = await permission_engine.evaluate_transaction(
            contract_transaction, "test_wallet"
        )

        assert action == PolicyAction.DENY
        assert any(
            v.violation_type == "contract_interaction_blocked" for v in violations
        )

    @pytest.mark.asyncio
    async def test_time_restrictions(self, permission_engine):
        """Test time-based restrictions."""
        # Only allow transactions during specific hours
        policy = TransactionPolicy(
            name="time_restricted_policy",
            description="Policy with time restrictions",
            allowed_hours_utc=[9, 10, 11, 12, 13, 14, 15, 16, 17],  # 9 AM to 5 PM UTC
        )
        permission_engine.add_policy(policy)

        transaction = TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="10000000000000000",
            chain_id=1,
        )

        # Use proper mocking with patch

        with patch("flare_ai_kit.wallet.permissions.datetime") as mock_datetime:
            # Make the mock datetime.now() return our test datetime
            mock_datetime.now.return_value = datetime(2024, 1, 1, 2, 0, 0, tzinfo=UTC)
            # Make sure UTC is available on the mock
            mock_datetime.UTC = UTC

            action, violations = await permission_engine.evaluate_transaction(
                transaction, "test_wallet"
            )

            assert action == PolicyAction.DENY
            assert any(v.violation_type == "time_restriction" for v in violations)

        # Test during allowed hours (10 AM)
        with patch("flare_ai_kit.wallet.permissions.datetime") as mock_datetime:
            # Make the mock datetime.now() return our test datetime
            mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
            # Make sure UTC is available on the mock
            mock_datetime.UTC = UTC

            action, violations = await permission_engine.evaluate_transaction(
                transaction, "test_wallet"
            )

            assert action == PolicyAction.ALLOW
            assert not any(v.violation_type == "time_restriction" for v in violations)

    @pytest.mark.asyncio
    async def test_gas_restrictions(self, permission_engine):
        """Test gas price and limit restrictions."""
        policy = TransactionPolicy(
            name="gas_restricted_policy",
            description="Policy with gas restrictions",
            max_gas_price="30000000000",  # 30 gwei
            max_gas_limit="100000",
        )
        permission_engine.add_policy(policy)

        # Test high gas price (should require approval)
        high_gas_transaction = TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="10000000000000000",
            gas_price="50000000000",  # 50 gwei (above limit)
            gas_limit="80000",
            chain_id=1,
        )

        action, violations = await permission_engine.evaluate_transaction(
            high_gas_transaction, "test_wallet"
        )

        assert action == PolicyAction.REQUIRE_APPROVAL
        assert any(v.violation_type == "gas_price_too_high" for v in violations)

        # Test high gas limit (should require approval)
        high_gas_limit_transaction = TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="10000000000000000",
            gas_price="20000000000",  # 20 gwei (within limit)
            gas_limit="150000",  # Above limit
            chain_id=1,
        )

        action, violations = await permission_engine.evaluate_transaction(
            high_gas_limit_transaction, "test_wallet"
        )

        assert action == PolicyAction.REQUIRE_APPROVAL
        assert any(v.violation_type == "gas_limit_too_high" for v in violations)


class TestTransactionHistory:
    """Test transaction history and rate limiting."""

    def test_record_transaction(self, permission_engine, sample_transaction):
        """Test recording a transaction."""
        initial_count = len(permission_engine.transaction_history)

        permission_engine.record_transaction("0x123abc", sample_transaction)

        assert len(permission_engine.transaction_history) == initial_count + 1

        recorded_tx = permission_engine.transaction_history[-1]
        assert recorded_tx.transaction_hash == "0x123abc"
        assert recorded_tx.destination == sample_transaction.to
        assert recorded_tx.value == Decimal(sample_transaction.value) / Decimal(10**18)

    def test_daily_spending_calculation(self, permission_engine):
        """Test daily spending calculation."""
        # Record some transactions
        transactions = [
            (
                "0x1",
                TransactionRequest(to="0x123", value="100000000000000000", chain_id=1),
            ),  # 0.1 ETH
            (
                "0x2",
                TransactionRequest(to="0x123", value="200000000000000000", chain_id=1),
            ),  # 0.2 ETH
            (
                "0x3",
                TransactionRequest(to="0x123", value="150000000000000000", chain_id=1),
            ),  # 0.15 ETH
        ]

        for tx_hash, tx in transactions:
            permission_engine.record_transaction(tx_hash, tx)

        daily_spent = permission_engine._calculate_daily_spending("test_wallet")
        expected = Decimal("0.45")  # 0.1 + 0.2 + 0.15

        assert daily_spent == expected
