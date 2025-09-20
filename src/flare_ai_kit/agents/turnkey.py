"""Turnkey agent connector for AI-driven wallet operations."""

import asyncio
import time
from decimal import Decimal
from typing import Any

import structlog
from pydantic import BaseModel, Field

from flare_ai_kit.tee.validation import VtpmValidation
from flare_ai_kit.wallet import TransactionPolicy, TurnkeyWallet
from flare_ai_kit.wallet.base import TransactionRequest
from flare_ai_kit.wallet.permissions import TimeWindow

logger = structlog.get_logger(__name__)


class AgentWalletConfig(BaseModel):
    """Configuration for agent wallet operations."""

    agent_id: str = Field(description="Unique identifier for the AI agent")
    wallet_id: str = Field(description="Associated wallet ID")
    max_daily_spend: float = Field(
        default=0.1, description="Maximum daily spending in ETH"
    )
    max_transaction_value: float = Field(
        default=0.01, description="Maximum per-transaction value in ETH"
    )
    allowed_hours: list[int] = Field(
        default_factory=lambda: list(range(24)),
        description="Allowed operation hours (UTC)",
    )
    require_tee_attestation: bool = Field(
        default=True, description="Require TEE attestation for operations"
    )


class AgentTransaction(BaseModel):
    """Represents a transaction initiated by an AI agent."""

    agent_id: str
    transaction_request: TransactionRequest
    justification: str = Field(
        description="AI agent's justification for the transaction"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Agent's confidence in the transaction"
    )
    risk_assessment: str = Field(description="Agent's risk assessment")


class TurnkeyAgentConnector:
    """Connector for AI agents to interact with Turnkey wallets securely."""

    def __init__(
        self,
        turnkey_wallet: TurnkeyWallet,
        tee_validator: VtpmValidation | None = None,
    ) -> None:
        self.wallet = turnkey_wallet
        self.tee_validator = tee_validator or VtpmValidation()
        self.agent_configs: dict[str, AgentWalletConfig] = {}
        self.transaction_log: list[dict[str, Any]] = []

    async def register_agent(self, config: AgentWalletConfig) -> bool:
        """
        Register an AI agent with wallet access configuration.

        Args:
            config: Agent wallet configuration

        Returns:
            True if registration successful

        """
        logger.info(
            "Registering AI agent", agent_id=config.agent_id, wallet_id=config.wallet_id
        )

        # Create restrictive policies for the agent
        agent_policy = TransactionPolicy(
            name=f"agent_{config.agent_id}_policy",
            description=f"Automated policy for AI agent {config.agent_id}",
            max_transaction_value=Decimal(str(config.max_transaction_value)),
            daily_spending_limit=Decimal(str(config.max_daily_spend)),
            allowed_hours_utc=config.allowed_hours,
            allowed_destinations=None,
            allowed_contracts=None,
            max_gas_price=None,
            max_gas_limit=None,
            time_windows=[
                TimeWindow(
                    duration_minutes=60,
                    max_transactions=10,
                    max_value=Decimal(str(config.max_transaction_value * 5)),
                ),
                TimeWindow(
                    duration_minutes=1440,
                    max_transactions=100,
                    max_value=Decimal(str(config.max_daily_spend)),
                ),
            ],
        )

        # Add policy to permission engine
        self.wallet.permission_engine.add_policy(agent_policy)

        # Store agent configuration
        self.agent_configs[config.agent_id] = config

        logger.info("AI agent registered successfully", agent_id=config.agent_id)
        return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an AI agent and remove its policies.

        Args:
            agent_id: Agent identifier

        Returns:
            True if unregistration successful

        """
        logger.info("Unregistering AI agent", agent_id=agent_id)

        if agent_id not in self.agent_configs:
            logger.warning("Agent not found for unregistration", agent_id=agent_id)
            return False

        # Remove agent policy
        policy_name = f"agent_{agent_id}_policy"
        self.wallet.permission_engine.remove_policy(policy_name)

        # Remove agent configuration
        del self.agent_configs[agent_id]

        logger.info("AI agent unregistered successfully", agent_id=agent_id)
        return True

    async def execute_agent_transaction(  # noqa: PLR0911
        self,
        agent_transaction: AgentTransaction,
        attestation_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a transaction initiated by an AI agent.

        Args:
            agent_transaction: Transaction request from AI agent
            attestation_token: Optional TEE attestation token

        Returns:
            Transaction result with status and details

        """
        agent_id = agent_transaction.agent_id
        logger.info(
            "Processing agent transaction",
            agent_id=agent_id,
            to=agent_transaction.transaction_request.to,
            value=agent_transaction.transaction_request.value,
        )

        # Verify agent is registered
        if agent_id not in self.agent_configs:
            error_msg = f"Agent {agent_id} is not registered"
            logger.error("unregistered_agent_transaction", agent_id=agent_id)
            return {"success": False, "error": error_msg}

        config = self.agent_configs[agent_id]

        # Validate TEE attestation if required
        if config.require_tee_attestation:
            if not attestation_token:
                error_msg = "TEE attestation required but not provided"
                logger.error("missing_tee_attestation", agent_id=agent_id)
                return {"success": False, "error": error_msg}

            if not await self.wallet.validate_tee_attestation(attestation_token):
                error_msg = "Invalid TEE attestation"
                logger.error("invalid_tee_attestation", agent_id=agent_id)
                return {"success": False, "error": error_msg}

        # Additional agent-specific validations
        validation_result = await self._validate_agent_transaction(
            agent_transaction, config
        )
        if not validation_result["valid"]:
            logger.error(
                "agent_transaction_validation_failed",
                agent_id=agent_id,
                reason=validation_result["reason"],
            )
            return {"success": False, "error": validation_result["reason"]}

        try:
            # Execute transaction through wallet
            signed_tx = await self.wallet.sign_transaction(
                config.wallet_id, agent_transaction.transaction_request
            )

            # Log transaction for audit
            log_entry = {
                "timestamp": asyncio.get_event_loop().time(),
                "agent_id": agent_id,
                "transaction_hash": signed_tx.transaction_hash,
                "to": agent_transaction.transaction_request.to,
                "value": agent_transaction.transaction_request.value,
                "justification": agent_transaction.justification,
                "confidence_score": agent_transaction.confidence_score,
                "risk_assessment": agent_transaction.risk_assessment,
                "tee_attested": attestation_token is not None,
            }
            self.transaction_log.append(log_entry)

            logger.info(
                "Agent transaction executed successfully",
                agent_id=agent_id,
                tx_hash=signed_tx.transaction_hash,
            )

        except PermissionError as e:
            logger.exception(
                "agent_transaction_denied", agent_id=agent_id, error=str(e)
            )
            return {"success": False, "error": f"Transaction denied: {e}"}

        except Exception as e:
            logger.exception(
                "agent_transaction_failed", agent_id=agent_id, error=str(e)
            )
            return {"success": False, "error": f"Transaction failed: {e}"}
        else:
            return {
                "success": True,
                "transaction_hash": signed_tx.transaction_hash,
                "signed_transaction": signed_tx.signed_transaction,
            }

    async def _validate_agent_transaction(
        self, agent_transaction: AgentTransaction, config: AgentWalletConfig
    ) -> dict[str, Any]:
        """
        Perform agent-specific transaction validation.

        Args:
            agent_transaction: Transaction to validate
            config: Agent configuration

        Returns:
            Validation result

        """
        # Check confidence threshold
        min_confidence = 0.7  # Configurable threshold
        if agent_transaction.confidence_score < min_confidence:
            return {
                "valid": False,
                "reason": (
                    f"Agent confidence {agent_transaction.confidence_score} "
                    f"below threshold {min_confidence}"
                ),
            }

        # Validate justification is provided
        if not agent_transaction.justification.strip():
            return {"valid": False, "reason": "Transaction justification is required"}

        # Check transaction value against agent limits
        tx_value = (
            float(agent_transaction.transaction_request.value) / 10**18
        )  # Convert wei to ETH
        if tx_value > config.max_transaction_value:
            return {
                "valid": False,
                "reason": (
                    f"Transaction value {tx_value} ETH exceeds agent limit "
                    f"{config.max_transaction_value} ETH"
                ),
            }

        # Additional risk-based validations could be added here
        # For example, checking the risk assessment content

        return {"valid": True, "reason": ""}

    async def get_agent_status(self, agent_id: str) -> dict[str, Any] | None:
        """
        Get status and statistics for an AI agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent status information or None if not found

        """
        if agent_id not in self.agent_configs:
            return None

        config = self.agent_configs[agent_id]

        # Calculate agent transaction statistics
        agent_transactions = [
            tx for tx in self.transaction_log if tx["agent_id"] == agent_id
        ]
        total_transactions = len(agent_transactions)
        total_value = sum(float(tx["value"]) / 10**18 for tx in agent_transactions)

        # Get recent transaction activity (last 24 hours)
        recent_cutoff = time.time() - 86400  # 24 hours ago
        recent_transactions = [
            tx for tx in agent_transactions if tx["timestamp"] > recent_cutoff
        ]

        return {
            "agent_id": agent_id,
            "wallet_id": config.wallet_id,
            "is_registered": True,
            "config": config.model_dump(),
            "statistics": {
                "total_transactions": total_transactions,
                "total_value_eth": total_value,
                "recent_transactions_24h": len(recent_transactions),
                "avg_confidence_score": sum(
                    tx["confidence_score"] for tx in agent_transactions
                )
                / max(total_transactions, 1),
            },
        }

    async def list_registered_agents(self) -> list[str]:
        """
        List all registered agent IDs.

        Returns:
            List of registered agent IDs

        """
        return list(self.agent_configs.keys())

    async def get_transaction_history(
        self, agent_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get transaction history for agents.

        Args:
            agent_id: Optional agent ID to filter by
            limit: Maximum number of transactions to return

        Returns:
            List of transaction log entries

        """
        transactions = self.transaction_log

        if agent_id:
            transactions = [tx for tx in transactions if tx["agent_id"] == agent_id]

        # Sort by timestamp (most recent first) and apply limit
        transactions = sorted(transactions, key=lambda x: x["timestamp"], reverse=True)
        return transactions[:limit]

    async def update_agent_config(
        self, agent_id: str, new_config: AgentWalletConfig
    ) -> bool:
        """
        Update configuration for a registered agent.

        Args:
            agent_id: Agent identifier
            new_config: Updated configuration

        Returns:
            True if update successful

        """
        if agent_id not in self.agent_configs:
            logger.error(
                "Cannot update config for unregistered agent", agent_id=agent_id
            )
            return False

        # Remove old policy
        old_policy_name = f"agent_{agent_id}_policy"
        self.wallet.permission_engine.remove_policy(old_policy_name)

        # Create new policy with updated config
        new_policy = TransactionPolicy(
            name=f"agent_{agent_id}_policy",
            description=f"Updated policy for AI agent {agent_id}",
            max_transaction_value=Decimal(str(new_config.max_transaction_value)),
            daily_spending_limit=Decimal(str(new_config.max_daily_spend)),
            allowed_hours_utc=new_config.allowed_hours,
            allowed_destinations=None,
            allowed_contracts=None,
            max_gas_price=None,
            max_gas_limit=None,
            time_windows=[
                TimeWindow(
                    duration_minutes=60,
                    max_transactions=10,
                    max_value=Decimal(str(new_config.max_transaction_value * 5)),
                ),
                TimeWindow(
                    duration_minutes=1440,
                    max_transactions=100,
                    max_value=Decimal(str(new_config.max_daily_spend)),
                ),
            ],
        )

        # Add new policy
        self.wallet.permission_engine.add_policy(new_policy)

        # Update stored configuration
        self.agent_configs[agent_id] = new_config

        logger.info("Agent configuration updated", agent_id=agent_id)
        return True
