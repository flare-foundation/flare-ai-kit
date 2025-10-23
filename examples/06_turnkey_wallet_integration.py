"""
Turnkey Wallet Integration Example.

This example demonstrates how to use the Turnkey wallet integration
for AI agents to securely manage blockchain transactions on Flare.

Features demonstrated:
- Wallet creation and management
- AI agent registration with policies
- Transaction signing with permission enforcement
- TEE attestation validation
- Secure audit logging
"""

import asyncio
import os
from decimal import Decimal
from typing import Any

from flare_ai_kit.agents.turnkey import (
    AgentTransaction,
    AgentWalletConfig,
    TurnkeyAgentConnector,
)
from flare_ai_kit.tee.validation import VtpmValidation
from flare_ai_kit.wallet import PermissionEngine, TransactionPolicy, TurnkeyWallet
from flare_ai_kit.wallet.base import TransactionRequest
from flare_ai_kit.wallet.permissions import TimeWindow
from flare_ai_kit.wallet.tee_security import TEESecurityManager
from flare_ai_kit.wallet.turnkey_wallet import TurnkeySettings


async def setup_turnkey_wallet() -> TurnkeyWallet:
    """Set up Turnkey wallet with proper configuration."""
    print("🔧 Setting up Turnkey wallet...")

    # Configure Turnkey settings (in production, use environment variables)
    settings = TurnkeySettings(
        organization_id=os.getenv("TURNKEY_ORGANIZATION_ID", "demo_org_id"),
        api_public_key=os.getenv("TURNKEY_API_PUBLIC_KEY", "demo_public_key"),
        api_private_key=os.getenv("TURNKEY_API_PRIVATE_KEY", "demo_private_key"),
    )

    # Create permission engine with default policies
    permission_engine = PermissionEngine()

    # Add a restrictive default policy for security
    default_policy = TransactionPolicy(
        name="default_security_policy",
        description="Default restrictive policy for all transactions",
        max_transaction_value=Decimal("0.01"),  # 0.01 ETH max per transaction
        daily_spending_limit=Decimal("0.1"),  # 0.1 ETH max per day
        time_windows=[
            TimeWindow(
                duration_minutes=60, max_transactions=10, max_value=Decimal("0.05")
            ),
            TimeWindow(
                duration_minutes=1440, max_transactions=100, max_value=Decimal("0.1")
            ),
        ],
        allowed_hours_utc=list(range(6, 22)),  # 6 AM to 10 PM UTC only
        max_gas_price="50000000000",  # 50 gwei max
        max_gas_limit="200000",
    )

    permission_engine.add_policy(default_policy)

    # Create TEE validator for secure operations
    tee_validator = VtpmValidation()

    # Initialize wallet
    wallet = TurnkeyWallet(
        settings=settings,
        permission_engine=permission_engine,
        tee_validator=tee_validator,
    )

    print("✅ Turnkey wallet configured successfully")
    return wallet


async def create_demo_wallet(wallet: TurnkeyWallet) -> tuple[str, str]:
    """Create a demo wallet for the AI agent."""
    print("\n💼 Creating demo wallet...")

    try:
        wallet_id = await wallet.create_wallet("AI_Agent_Demo_Wallet")
        print(f"✅ Wallet created with ID: {wallet_id}")

        # Get the wallet address
        address_info = await wallet.get_address(wallet_id)
        print(f"📍 Wallet address: {address_info.address}")
        print(f"📍 Derivation path: {address_info.derivation_path}")
    except Exception as e:
        print(f"❌ Failed to create wallet: {e}")
        # For demo purposes, return mock values
        return "demo_wallet_id", "0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b"
    else:
        return wallet_id, address_info.address


async def register_ai_agent(
    agent_connector: TurnkeyAgentConnector, wallet_id: str
) -> AgentWalletConfig:
    """Register an AI agent with specific permissions."""
    print("\n🤖 Registering AI agent...")

    # Configure agent with conservative limits
    agent_config = AgentWalletConfig(
        agent_id="yield_optimizer_v1",
        wallet_id=wallet_id,
        max_daily_spend=0.05,  # 0.05 ETH per day
        max_transaction_value=0.01,  # 0.01 ETH per transaction
        allowed_hours=list(range(9, 17)),  # 9 AM to 5 PM UTC only
        require_tee_attestation=True,
    )

    success = await agent_connector.register_agent(agent_config)

    if success:
        print(f"✅ Agent '{agent_config.agent_id}' registered successfully")
        print(f"   📊 Max daily spend: {agent_config.max_daily_spend} ETH")
        print(f"   📊 Max transaction value: {agent_config.max_transaction_value} ETH")
        print(f"   🕒 Allowed hours: {agent_config.allowed_hours}")
        print(f"   🔒 TEE attestation required: {agent_config.require_tee_attestation}")
    else:
        print("❌ Failed to register AI agent")

    return agent_config if success else None


async def simulate_tee_operation(_tee_manager: TEESecurityManager) -> str:
    """Simulate a TEE secure operation."""
    print("\n🔐 Simulating TEE secure operation...")

    # Mock TEE attestation token (in production, this comes from the TEE)
    mock_attestation_token = (
        "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiJkZW1vX3RlZSIsImlzcyI6Imh0dHBzOi8vY29uZmlkZW50aWFsY29tcHV0aW5nLmdvb2dsZWFwaXMuY29tIiwiaWF0IjoxNjk5OTk5OTk5fQ."
        "mock_signature"
    )

    try:
        # This would normally validate against real TEE attestation
        print("⚠️  Note: Using mock TEE attestation for demo purposes")

        # In production, this would create a secure operation

        print("✅ TEE operation simulated (would validate in production)")
    except Exception as e:
        print(f"❌ TEE operation failed: {e}")
        print("   Using mock attestation for demo purposes")
        return mock_attestation_token
    else:
        return mock_attestation_token


async def execute_ai_transaction(
    agent_connector: TurnkeyAgentConnector,
    agent_config: AgentWalletConfig,
    attestation_token: str,
) -> dict[str, Any]:
    """Execute a transaction initiated by the AI agent."""
    print("\n💸 Executing AI agent transaction...")

    # Create a sample transaction request
    transaction_request = TransactionRequest(
        to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",  # Demo recipient
        value="5000000000000000",  # 0.005 ETH in wei
        gas_limit="21000",
        gas_price="20000000000",  # 20 gwei
        chain_id=14,  # Flare mainnet
    )

    # Create agent transaction with justification and risk assessment
    agent_transaction = AgentTransaction(
        agent_id=agent_config.agent_id,
        transaction_request=transaction_request,
        justification=(
            "Automated yield optimization - moving funds to higher yield protocol"
        ),
        confidence_score=0.85,
        risk_assessment="Low risk - established DeFi protocol with 99.9% uptime",
    )

    print("📝 Transaction details:")
    print(f"   To: {transaction_request.to}")
    print(f"   Value: {float(transaction_request.value) / 10**18} ETH")
    print(f"   Agent confidence: {agent_transaction.confidence_score}")
    print(f"   Justification: {agent_transaction.justification}")

    try:
        # Execute the transaction
        result = await agent_connector.execute_agent_transaction(
            agent_transaction, attestation_token=attestation_token
        )

        if result["success"]:
            print("✅ Transaction executed successfully!")
            print(f"   📋 Transaction hash: {result['transaction_hash']}")
            print(f"   📋 Signed transaction: {result['signed_transaction'][:50]}...")
        else:
            print(f"❌ Transaction failed: {result['error']}")
    except Exception as e:
        print(f"❌ Transaction execution error: {e}")
        return {"success": False, "error": str(e)}
    else:
        return result


async def demonstrate_policy_enforcement(
    agent_connector: TurnkeyAgentConnector,
    agent_config: AgentWalletConfig,
    attestation_token: str,
) -> None:
    """Demonstrate policy enforcement by attempting violating transactions."""
    print("\n🚫 Demonstrating policy enforcement...")

    # Test 1: Transaction exceeding value limit
    print("\n📊 Test 1: Transaction exceeding value limit")
    large_transaction = AgentTransaction(
        agent_id=agent_config.agent_id,
        transaction_request=TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="20000000000000000",  # 0.02 ETH (exceeds 0.01 ETH limit)
            chain_id=14,
        ),
        justification="Large yield optimization move",
        confidence_score=0.9,
        risk_assessment="Medium risk - large transaction",
    )

    result = await agent_connector.execute_agent_transaction(
        large_transaction, attestation_token
    )
    if not result["success"]:
        print(f"✅ Policy correctly blocked large transaction: {result['error']}")
    else:
        print("❌ Policy should have blocked this transaction")

    # Test 2: Low confidence transaction
    print("\n📊 Test 2: Low confidence transaction")
    low_confidence_tx = AgentTransaction(
        agent_id=agent_config.agent_id,
        transaction_request=TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="5000000000000000",  # 0.005 ETH
            chain_id=14,
        ),
        justification="Uncertain yield opportunity",
        confidence_score=0.4,  # Low confidence
        risk_assessment="High risk - unverified protocol",
    )

    result = await agent_connector.execute_agent_transaction(
        low_confidence_tx, attestation_token
    )
    if not result["success"]:
        print(
            f"✅ Policy correctly blocked low confidence transaction: {result['error']}"
        )
    else:
        print("❌ Policy should have blocked this transaction")

    # Test 3: Missing justification
    print("\n📊 Test 3: Missing justification")
    no_justification_tx = AgentTransaction(
        agent_id=agent_config.agent_id,
        transaction_request=TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="5000000000000000",
            chain_id=14,
        ),
        justification="",  # Empty justification
        confidence_score=0.8,
        risk_assessment="Low risk",
    )

    result = await agent_connector.execute_agent_transaction(
        no_justification_tx, attestation_token
    )
    if not result["success"]:
        print(
            "✅ Policy correctly blocked transaction without justification: "
            f"{result['error']}"
        )
    else:
        print("❌ Policy should have blocked this transaction")


async def show_agent_status_and_history(
    agent_connector: TurnkeyAgentConnector, agent_id: str
) -> None:
    """Display agent status and transaction history."""
    print("\n📊 Agent Status and Transaction History")

    # Get agent status
    status = await agent_connector.get_agent_status(agent_id)
    if status:
        print(f"\n🤖 Agent: {status['agent_id']}")
        print(f"   💼 Wallet ID: {status['wallet_id']}")
        print(f"   📊 Total transactions: {status['statistics']['total_transactions']}")
        print(f"   💰 Total value: {status['statistics']['total_value_eth']:.6f} ETH")
        avg_confidence = status["statistics"]["avg_confidence_score"]
        print(f"   📈 Average confidence: {avg_confidence:.2f}")
        recent_24h = status["statistics"]["recent_transactions_24h"]
        print(f"   🕒 Recent transactions (24h): {recent_24h}")

    # Get transaction history
    history = await agent_connector.get_transaction_history(agent_id=agent_id, limit=10)

    if history:
        print("\n📜 Recent Transaction History:")
        for i, tx in enumerate(history[:5], 1):
            print(f"   {i}. Hash: {tx['transaction_hash']}")
            print(f"      Value: {float(tx['value']):.6f} ETH")
            print(f"      Confidence: {tx['confidence_score']}")
            print(f"      TEE Attested: {tx['tee_attested']}")
    else:
        print("   No transaction history found")


async def main() -> None:
    """Main demonstration function."""
    print("🚀 Turnkey Wallet Integration Demo")
    print("=" * 50)

    try:
        # 1. Set up Turnkey wallet
        wallet = await setup_turnkey_wallet()

        # 2. Create demo wallet
        wallet_id, _wallet_address = await create_demo_wallet(wallet)

        # 3. Set up TEE security manager
        tee_manager = TEESecurityManager()

        # 4. Create agent connector
        agent_connector = TurnkeyAgentConnector(wallet)

        # 5. Register AI agent
        agent_config = await register_ai_agent(agent_connector, wallet_id)

        if not agent_config:
            print("❌ Cannot continue without registered agent")
            return

        # 6. Simulate TEE operation
        attestation_token = await simulate_tee_operation(tee_manager)

        # 7. Execute valid AI transaction
        await execute_ai_transaction(agent_connector, agent_config, attestation_token)

        # 8. Demonstrate policy enforcement
        await demonstrate_policy_enforcement(
            agent_connector, agent_config, attestation_token
        )

        # 9. Show agent status and history
        await show_agent_status_and_history(agent_connector, agent_config.agent_id)

        # 10. List all registered agents
        agents = await agent_connector.list_registered_agents()
        print(f"\n📋 All registered agents: {agents}")

        # 11. Cleanup
        print("\n🧹 Cleaning up...")
        await agent_connector.unregister_agent(agent_config.agent_id)
        print("✅ Agent unregistered")

        # Close wallet connection
        await wallet.__aexit__(None, None, None)
        print("✅ Wallet connection closed")

        print("\n🎉 Demo completed successfully!")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
