"""Permission and policy enforcement system for wallet operations."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from .base import TransactionRequest


class PolicyAction(str, Enum):
    """Actions that can be taken by policies."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class TimeWindow(BaseModel):
    """Represents a time window for rate limiting."""

    duration_minutes: int = Field(gt=0, description="Duration in minutes")
    max_transactions: int = Field(gt=0, description="Maximum transactions allowed")
    max_value: Decimal | None = Field(None, description="Maximum total value in ETH")


class TransactionPolicy(BaseModel):
    """Policy for transaction validation and limits."""

    name: str
    description: str
    enabled: bool = True

    # Value limits
    max_transaction_value: Decimal | None = Field(
        None, description="Max value per transaction in ETH"
    )
    daily_spending_limit: Decimal | None = Field(
        None, description="Daily spending limit in ETH"
    )

    # Rate limiting
    time_windows: list["TimeWindow"] = []

    # Destination restrictions
    allowed_destinations: list[str] | None = Field(
        None, description="Allowed destination addresses"
    )
    blocked_destinations: list[str] = Field(
        default_factory=list, description="Blocked destination addresses"
    )

    # Contract interaction restrictions
    allow_contract_interactions: bool = True
    allowed_contracts: list[str] | None = Field(
        None, description="Allowed contract addresses"
    )

    # Time-based restrictions
    allowed_hours_utc: list[int] | None = Field(
        None, description="Allowed hours (0-23 UTC)"
    )

    # Gas restrictions
    max_gas_price: str | None = Field(None, description="Maximum gas price in wei")
    max_gas_limit: str | None = Field(None, description="Maximum gas limit")


class PolicyViolation(BaseModel):
    """Represents a policy violation."""

    policy_name: str
    violation_type: str
    description: str
    suggested_action: PolicyAction


class TransactionHistory(BaseModel):
    """Track transaction history for rate limiting."""

    transaction_hash: str
    timestamp: datetime
    value: Decimal
    destination: str
    gas_used: str | None = None


class PermissionEngine:
    """Engine for evaluating transaction permissions and policies."""

    def __init__(self) -> None:
        self.policies: list[TransactionPolicy] = []
        self.transaction_history: list[TransactionHistory] = []

    def add_policy(self, policy: TransactionPolicy) -> None:
        """Add a new policy to the engine."""
        self.policies.append(policy)

    def remove_policy(self, policy_name: str) -> bool:
        """Remove a policy by name."""
        initial_count = len(self.policies)
        self.policies = [p for p in self.policies if p.name != policy_name]
        return len(self.policies) < initial_count

    def get_policy(self, policy_name: str) -> TransactionPolicy | None:
        """Get a policy by name."""
        return next((p for p in self.policies if p.name == policy_name), None)

    def list_policies(self) -> list[str]:
        """List all policy names."""
        return [p.name for p in self.policies]

    async def evaluate_transaction(
        self, transaction: TransactionRequest, wallet_id: str
    ) -> tuple[PolicyAction, list[PolicyViolation]]:
        """
        Evaluate a transaction against all policies.

        Returns:
            Tuple of (action, violations) where action is the most restrictive
            action required and violations is a list of all policy violations.

        """
        violations: list[PolicyViolation] = []
        most_restrictive_action = PolicyAction.ALLOW

        for policy in self.policies:
            if not policy.enabled:
                continue

            policy_violations = await self._evaluate_policy(
                transaction, policy, wallet_id
            )
            violations.extend(policy_violations)

            # Determine most restrictive action
            if policy_violations:
                if any(
                    v.suggested_action == PolicyAction.DENY for v in policy_violations
                ):
                    most_restrictive_action = PolicyAction.DENY
                elif most_restrictive_action != PolicyAction.DENY and any(
                    v.suggested_action == PolicyAction.REQUIRE_APPROVAL
                    for v in policy_violations
                ):
                    most_restrictive_action = PolicyAction.REQUIRE_APPROVAL

        return most_restrictive_action, violations

    async def _evaluate_policy(  # noqa: C901
        self, transaction: TransactionRequest, policy: TransactionPolicy, wallet_id: str
    ) -> list[PolicyViolation]:
        """Evaluate a transaction against a single policy."""
        violations: list[PolicyViolation] = []

        # Check transaction value limits
        if policy.max_transaction_value is not None:
            tx_value = Decimal(transaction.value) / Decimal(
                10**18
            )  # Convert wei to ETH
            if tx_value > policy.max_transaction_value:
                violations.append(
                    PolicyViolation(
                        policy_name=policy.name,
                        violation_type="max_transaction_value",
                        description=f"{tx_value} exceeds tx value"
                        f"limit {policy.max_transaction_value}",
                        suggested_action=PolicyAction.DENY,
                    )
                )

        # Check daily spending limits
        if policy.daily_spending_limit is not None:
            daily_spent = self._calculate_daily_spending(wallet_id)
            tx_value = Decimal(transaction.value) / Decimal(10**18)
            if daily_spent + tx_value > policy.daily_spending_limit:
                violations.append(
                    PolicyViolation(
                        policy_name=policy.name,
                        violation_type="daily_spending_limit",
                        description=f"Transaction would exceed daily limit."
                        f"Spent: {daily_spent}, Limit: {policy.daily_spending_limit}",
                        suggested_action=PolicyAction.DENY,
                    )
                )

        # Check destination restrictions
        if policy.blocked_destinations and transaction.to.lower() in [
            addr.lower() for addr in policy.blocked_destinations
        ]:
            violations.append(
                PolicyViolation(
                    policy_name=policy.name,
                    violation_type="blocked_destination",
                    description=f"Transaction to blocked destination: {transaction.to}",
                    suggested_action=PolicyAction.DENY,
                )
            )

        if policy.allowed_destinations and transaction.to.lower() not in [
            addr.lower() for addr in policy.allowed_destinations
        ]:
            violations.append(
                PolicyViolation(
                    policy_name=policy.name,
                    violation_type="destination_not_allowed",
                    description=f"Tx to non-whitelisted dest: {transaction.to}",
                    suggested_action=PolicyAction.DENY,
                )
            )

        # Check contract interaction restrictions
        if not policy.allow_contract_interactions and transaction.data:
            violations.append(
                PolicyViolation(
                    policy_name=policy.name,
                    violation_type="contract_interaction_blocked",
                    description="Contract interactions are not allowed by this policy",
                    suggested_action=PolicyAction.DENY,
                )
            )

        # Check time-based restrictions
        if policy.allowed_hours_utc is not None:
            current_hour = datetime.now(UTC).hour
            if current_hour not in policy.allowed_hours_utc:
                violations.append(
                    PolicyViolation(
                        policy_name=policy.name,
                        violation_type="time_restriction",
                        description=f"Transactions not allowed at {current_hour} UTC",
                        suggested_action=PolicyAction.DENY,
                    )
                )

        # Check gas restrictions
        if (
            policy.max_gas_price
            and transaction.gas_price
            and int(transaction.gas_price) > int(policy.max_gas_price)
        ):
            violations.append(
                PolicyViolation(
                    policy_name=policy.name,
                    violation_type="gas_price_too_high",
                    description=f"Gas price {transaction.gas_price} exceeds"
                    f"limit {policy.max_gas_price}",
                    suggested_action=PolicyAction.REQUIRE_APPROVAL,
                )
            )

        if (
            policy.max_gas_limit
            and transaction.gas_limit
            and int(transaction.gas_limit) > int(policy.max_gas_limit)
        ):
            violations.append(
                PolicyViolation(
                    policy_name=policy.name,
                    violation_type="gas_limit_too_high",
                    description=f"{transaction.gas_limit} exceeds"
                    f"limit {policy.max_gas_limit}",
                    suggested_action=PolicyAction.REQUIRE_APPROVAL,
                )
            )

        # Check rate limiting
        for window in policy.time_windows:
            violations.extend(
                self._check_rate_limit(transaction, policy, window, wallet_id)
            )

        return violations

    def _calculate_daily_spending(self, _: str) -> Decimal:
        """Calculate total spending in the last 24 hours."""
        cutoff = datetime.now(UTC) - timedelta(days=1)
        daily_transactions = [
            tx for tx in self.transaction_history if tx.timestamp > cutoff
        ]
        total = sum(tx.value for tx in daily_transactions)
        return total if isinstance(total, Decimal) else Decimal(str(total))

    def _check_rate_limit(
        self,
        transaction: TransactionRequest,
        policy: TransactionPolicy,
        window: TimeWindow,
        _: str,
    ) -> list[PolicyViolation]:
        """Check if transaction violates rate limiting rules."""
        violations: list[PolicyViolation] = []
        cutoff = datetime.now(UTC) - timedelta(minutes=window.duration_minutes)

        recent_transactions = [
            tx for tx in self.transaction_history if tx.timestamp > cutoff
        ]

        # Check transaction count
        if len(recent_transactions) >= window.max_transactions:
            violations.append(
                PolicyViolation(
                    policy_name=policy.name,
                    violation_type="rate_limit_transactions",
                    description=(
                        f"Too many transactions in {window.duration_minutes} "
                        f"minutes. Limit: {window.max_transactions}"
                    ),
                    suggested_action=PolicyAction.DENY,
                )
            )

        # Check total value
        if window.max_value is not None:
            total_value = sum(tx.value for tx in recent_transactions)
            tx_value = Decimal(transaction.value) / Decimal(10**18)
            if total_value + tx_value > window.max_value:
                violations.append(
                    PolicyViolation(
                        policy_name=policy.name,
                        violation_type="rate_limit_value",
                        description=(
                            f"Total value in {window.duration_minutes} minutes "
                            f"would exceed limit {window.max_value} ETH"
                        ),
                        suggested_action=PolicyAction.DENY,
                    )
                )

        return violations

    def record_transaction(
        self, transaction_hash: str, transaction: TransactionRequest
    ) -> None:
        """Record a completed transaction for future policy evaluation."""
        history_entry = TransactionHistory(
            transaction_hash=transaction_hash,
            timestamp=datetime.now(UTC),
            value=Decimal(transaction.value) / Decimal(10**18),  # Convert to ETH
            destination=transaction.to,
            gas_used=transaction.gas_limit,
        )
        self.transaction_history.append(history_entry)

        # Keep only last 30 days of history
        cutoff = datetime.now(UTC) - timedelta(days=30)
        self.transaction_history = [
            tx for tx in self.transaction_history if tx.timestamp > cutoff
        ]
