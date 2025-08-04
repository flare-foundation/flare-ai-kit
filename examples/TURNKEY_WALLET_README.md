# Turnkey Wallet Integration for AI Agents

This documentation provides a comprehensive guide to the Turnkey SDK integration for non-custodial wallet functionality in AI agents on the Flare network.

## Overview

The Turnkey wallet integration enables AI agents to securely manage blockchain transactions with:

- **Non-custodial wallet management** - Private keys never leave the secure environment
- **Policy-based transaction enforcement** - Granular control over agent behavior
- **TEE (Trusted Execution Environment) integration** - Enhanced security for sensitive operations
- **Comprehensive audit logging** - Full transaction history and policy evaluation

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Agent      │────│ Agent Connector │────│ Turnkey Wallet  │
│                 │    │                 │    │                 │
│ - Justification │    │ - Policy Engine │    │ - Key Management│
│ - Risk Analysis │    │ - Permissions   │    │ - Transaction   │
│ - Confidence    │    │ - Rate Limiting │    │   Signing       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │ TEE Security    │    │ Flare Network   │
                       │ Manager         │    │                 │
                       │ - Attestation   │    │ - Transaction   │
                       │ - Encryption    │    │   Execution     │
                       │ - Audit Logs    │    │                 │
                       └─────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Installation

Add the wallet optional dependencies to your environment:

```bash
# Install with wallet support
uv sync --extra wallet

# Or manually install dependencies
uv add httpx cryptography eth-account pyjwt
```

### 2. Configuration

Set up your Turnkey configuration:

```python
from flare_ai_kit.wallet.turnkey_wallet import TurnkeySettings

settings = TurnkeySettings(
    organization_id="your_turnkey_org_id",
    api_public_key="your_api_public_key", 
    api_private_key="your_api_private_key"
)
```

### 3. Basic Usage

```python
import asyncio
from flare_ai_kit.wallet import TurnkeyWallet, PermissionEngine
from flare_ai_kit.agents.turnkey import TurnkeyAgentConnector, AgentWalletConfig

async def main():
    # Initialize wallet
    async with TurnkeyWallet(settings=settings) as wallet:
        
        # Create agent connector
        agent_connector = TurnkeyAgentConnector(wallet)
        
        # Register AI agent with policies
        config = AgentWalletConfig(
            agent_id="my_ai_agent",
            wallet_id="wallet_123",
            max_daily_spend=0.1,  # 0.1 ETH per day
            max_transaction_value=0.01,  # 0.01 ETH per transaction
            require_tee_attestation=True
        )
        
        await agent_connector.register_agent(config)
        
        # Execute agent transaction
        result = await agent_connector.execute_agent_transaction(
            agent_transaction,
            attestation_token="tee_token"
        )

asyncio.run(main())
```

## Core Components

### 1. Wallet Interface (`WalletInterface`)

Base interface for all wallet implementations:

```python
class WalletInterface(ABC):
    async def create_wallet(self, wallet_name: str) -> str
    async def get_address(self, wallet_id: str, derivation_path: str) -> WalletAddress
    async def sign_transaction(self, wallet_id: str, transaction: TransactionRequest) -> SignedTransaction
    async def export_wallet(self, wallet_id: str, password: str) -> Dict[str, Any]
    async def import_wallet(self, encrypted_wallet: Dict[str, Any], password: str) -> str
    async def list_wallets(self) -> List[str]
    async def delete_wallet(self, wallet_id: str) -> bool
```

### 2. Turnkey Wallet (`TurnkeyWallet`)

Main implementation of wallet functionality:

```python
from flare_ai_kit.wallet import TurnkeyWallet
from flare_ai_kit.wallet.turnkey_wallet import TurnkeySettings

# Create wallet instance
wallet = TurnkeyWallet(
    settings=TurnkeySettings(...),
    permission_engine=PermissionEngine(),
    tee_validator=VtpmValidation()
)

# Create a new wallet
wallet_id = await wallet.create_wallet("AI_Agent_Wallet")

# Get wallet address
address = await wallet.get_address(wallet_id)
print(f"Wallet address: {address.address}")

# Sign transaction (with policy enforcement)
signed_tx = await wallet.sign_transaction(wallet_id, transaction_request)
```

### 3. Permission Engine (`PermissionEngine`)

Enforces transaction policies and limits:

```python
from flare_ai_kit.wallet.permissions import (
    PermissionEngine, 
    TransactionPolicy, 
    TimeWindow
)

# Create permission engine
engine = PermissionEngine()

# Define policy
policy = TransactionPolicy(
    name="conservative_policy",
    description="Conservative spending limits",
    max_transaction_value=Decimal("0.01"),  # 0.01 ETH max
    daily_spending_limit=Decimal("0.1"),    # 0.1 ETH per day
    time_windows=[
        TimeWindow(duration_minutes=60, max_transactions=5)
    ],
    allowed_hours_utc=[9, 10, 11, 12, 13, 14, 15, 16, 17],  # Business hours
    max_gas_price="50000000000"  # 50 gwei max
)

# Add policy
engine.add_policy(policy)

# Evaluate transaction
action, violations = await engine.evaluate_transaction(transaction, wallet_id)
```

### 4. Agent Connector (`TurnkeyAgentConnector`)

Manages AI agent registration and transaction execution:

```python
from flare_ai_kit.agents.turnkey import (
    TurnkeyAgentConnector,
    AgentWalletConfig,
    AgentTransaction
)

# Create connector
connector = TurnkeyAgentConnector(wallet)

# Configure agent
config = AgentWalletConfig(
    agent_id="yield_optimizer_v1",
    wallet_id=wallet_id,
    max_daily_spend=0.05,
    max_transaction_value=0.01,
    allowed_hours=list(range(9, 17)),  # 9 AM to 5 PM
    require_tee_attestation=True
)

# Register agent
await connector.register_agent(config)

# Create agent transaction
agent_tx = AgentTransaction(
    agent_id="yield_optimizer_v1",
    transaction_request=TransactionRequest(
        to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
        value="5000000000000000",  # 0.005 ETH
        chain_id=14  # Flare mainnet
    ),
    justification="Automated yield optimization",
    confidence_score=0.85,
    risk_assessment="Low risk - established protocol"
)

# Execute transaction
result = await connector.execute_agent_transaction(
    agent_tx,
    attestation_token="tee_attestation_token"
)
```

## Policy Configuration

### Transaction Limits

```python
policy = TransactionPolicy(
    name="strict_limits",
    max_transaction_value=Decimal("0.01"),  # Max per transaction
    daily_spending_limit=Decimal("0.1"),    # Max per day
    max_gas_price="50000000000",            # Max gas price (wei)
    max_gas_limit="200000"                  # Max gas limit
)
```

### Rate Limiting

```python
policy = TransactionPolicy(
    name="rate_limited",
    time_windows=[
        # Max 10 transactions per hour, 0.05 ETH total
        TimeWindow(duration_minutes=60, max_transactions=10, max_value=Decimal("0.05")),
        
        # Max 100 transactions per day, 0.5 ETH total  
        TimeWindow(duration_minutes=1440, max_transactions=100, max_value=Decimal("0.5"))
    ]
)
```

### Destination Control

```python
policy = TransactionPolicy(
    name="destination_control",
    # Only allow transactions to specific addresses
    allowed_destinations=[
        "0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
        "0x1234567890123456789012345678901234567890"
    ],
    # Block specific addresses
    blocked_destinations=[
        "0xbadaddress1234567890123456789012345678"
    ]
)
```

### Time-Based Restrictions

```python
policy = TransactionPolicy(
    name="business_hours",
    # Only allow transactions during business hours (UTC)
    allowed_hours_utc=[9, 10, 11, 12, 13, 14, 15, 16, 17],
    
    # Block contract interactions
    allow_contract_interactions=False
)
```

## TEE Security Integration

### TEE Attestation

```python
from flare_ai_kit.wallet.tee_security import TEESecurityManager

# Create TEE security manager
tee_manager = TEESecurityManager()

# Create secure operation
secure_op = await tee_manager.create_secure_operation(
    operation_type="ai_transaction",
    operation_data={
        "agent_id": "agent_001",
        "transaction_value": "0.01",
        "destination": "0x742d35Cc..."
    },
    attestation_token="tee_attestation_token"
)

# Validate operation integrity
is_valid = await tee_manager.verify_operation_integrity(secure_op)
```

### Secure Data Encryption

```python
# Encrypt sensitive data within TEE
encrypted_data = await tee_manager.encrypt_sensitive_data(
    data=b"sensitive_private_key_material",
    attestation_token="tee_token",
    additional_data=b"context_specific_data"
)

# Decrypt data (requires valid TEE context)
decrypted_data = await tee_manager.decrypt_sensitive_data(
    encrypted_data=encrypted_data,
    attestation_token="tee_token",
    additional_data=b"context_specific_data"
)
```

## Monitoring and Audit

### Transaction History

```python
# Get agent transaction history
history = await connector.get_transaction_history(
    agent_id="yield_optimizer_v1",
    limit=50
)

for tx in history:
    print(f"Hash: {tx['transaction_hash']}")
    print(f"Value: {tx['value']} ETH")
    print(f"Confidence: {tx['confidence_score']}")
    print(f"TEE Attested: {tx['tee_attested']}")
```

### Agent Status

```python
# Get comprehensive agent status
status = await connector.get_agent_status("yield_optimizer_v1")

print(f"Agent: {status['agent_id']}")
print(f"Total transactions: {status['statistics']['total_transactions']}")
print(f"Total value: {status['statistics']['total_value_eth']} ETH")
print(f"Average confidence: {status['statistics']['avg_confidence_score']}")
```

### Policy Violations

```python
# Evaluate transaction for violations
action, violations = await engine.evaluate_transaction(transaction, wallet_id)

if violations:
    for violation in violations:
        print(f"Policy: {violation.policy_name}")
        print(f"Type: {violation.violation_type}")
        print(f"Description: {violation.description}")
        print(f"Action: {violation.suggested_action}")
```

## Security Best Practices

### 1. Environment Variables

Store sensitive configuration in environment variables:

```bash
export TURNKEY_ORGANIZATION_ID="your_org_id"
export TURNKEY_API_PUBLIC_KEY="your_public_key"
export TURNKEY_API_PRIVATE_KEY="your_private_key"
```

### 2. Policy Layering

Implement multiple layers of policies:

```python
# Base security policy
base_policy = TransactionPolicy(
    name="base_security",
    max_transaction_value=Decimal("0.01"),
    daily_spending_limit=Decimal("0.1")
)

# Agent-specific policy  
agent_policy = TransactionPolicy(
    name="agent_specific",
    allowed_hours_utc=[9, 10, 11, 12, 13, 14, 15, 16, 17],
    max_gas_price="30000000000"
)

engine.add_policy(base_policy)
engine.add_policy(agent_policy)
```

### 3. TEE Validation

Always validate TEE attestation for sensitive operations:

```python
if config.require_tee_attestation:
    if not await wallet.validate_tee_attestation(attestation_token):
        raise SecurityError("Invalid TEE attestation")
```

### 4. Transaction Justification

Require meaningful justifications from AI agents:

```python
if not agent_transaction.justification.strip():
    raise ValueError("Transaction justification is required")

if agent_transaction.confidence_score < 0.7:
    raise ValueError("Agent confidence too low for execution")
```

## Error Handling

### Common Error Scenarios

```python
try:
    result = await connector.execute_agent_transaction(agent_tx, attestation_token)
    
except PermissionError as e:
    # Policy violation
    print(f"Transaction denied by policy: {e}")
    
except ValueError as e:
    # Invalid agent configuration or transaction
    print(f"Invalid request: {e}")
    
except RuntimeError as e:
    # Turnkey API or network error
    print(f"System error: {e}")
    
except Exception as e:
    # Unexpected error
    print(f"Unexpected error: {e}")
```

### Policy Violation Handling

```python
action, violations = await engine.evaluate_transaction(transaction, wallet_id)

if action == PolicyAction.DENY:
    # Transaction completely blocked
    raise PermissionError(f"Transaction denied: {violations}")
    
elif action == PolicyAction.REQUIRE_APPROVAL:
    # Manual approval needed
    approval_request = create_approval_request(transaction, violations)
    await submit_for_approval(approval_request)
    
elif action == PolicyAction.ALLOW:
    # Transaction can proceed
    await execute_transaction(transaction)
```

## Performance Considerations

### 1. Connection Pooling

Use connection pooling for high-throughput scenarios:

```python
# Configure HTTP client with connection limits
wallet = TurnkeyWallet(
    settings=settings,
    http_client_config={
        "limits": {"max_connections": 100, "max_keepalive_connections": 20},
        "timeout": 30.0
    }
)
```

### 2. Policy Evaluation Caching

Cache policy evaluations for repeated similar transactions:

```python
# Implement caching layer
from functools import lru_cache

@lru_cache(maxsize=1000)
def evaluate_cached_policy(transaction_hash, policy_hash):
    return engine.evaluate_transaction(transaction, wallet_id)
```

### 3. Batch Operations

Group multiple operations where possible:

```python
# Batch wallet creation
wallet_ids = await asyncio.gather(*[
    wallet.create_wallet(f"agent_wallet_{i}")
    for i in range(10)
])
```

## Troubleshooting

### Common Issues

1. **TEE Attestation Failures**
   - Ensure TEE environment is properly configured
   - Verify attestation token format and signature
   - Check token expiration

2. **Policy Violations**
   - Review transaction against all active policies
   - Check time-based restrictions
   - Verify gas price and limit settings

3. **Turnkey API Errors**
   - Verify API credentials and organization ID
   - Check network connectivity
   - Review rate limiting and quotas

4. **Transaction Signing Failures**
   - Ensure wallet has sufficient permissions
   - Verify private key format and accessibility
   - Check derivation path configuration

### Debugging

Enable debug logging:

```python
import structlog

# Configure debug logging
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # DEBUG level
    logger_factory=structlog.dev.ConsoleLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
# Run all wallet tests
uv run python -m pytest tests/unit/wallet/ -v

# Run agent tests
uv run python -m pytest tests/unit/agents/test_turnkey.py -v

# Run with coverage
uv run python -m pytest tests/unit/wallet/ --cov=flare_ai_kit.wallet
```

### Integration Testing

Use the provided integration example:

```bash
# Run the integration demo
uv run python examples/03_turnkey_wallet_integration.py
```

## Production Deployment

### 1. Environment Configuration

```bash
# Production environment variables
export TURNKEY_ORGANIZATION_ID="prod_org_id"
export TURNKEY_API_BASE_URL="https://api.turnkey.com"
export FLARE_NETWORK_RPC_URL="https://flare-api.flare.network/ext/bc/C/rpc"
export TEE_ATTESTATION_ENDPOINT="https://confidentialcomputing.googleapis.com"
```

### 2. Monitoring Setup

```python
# Add monitoring and alerting
import structlog
from flare_ai_kit.wallet.monitoring import WalletMonitor

monitor = WalletMonitor(
    alert_thresholds={
        "transaction_failures": 5,  # Alert after 5 failures
        "policy_violations": 10,    # Alert after 10 violations
        "daily_spend_limit": 0.8    # Alert at 80% of daily limit
    }
)

# Register monitor with connector
connector.add_monitor(monitor)
```

### 3. Backup and Recovery

```python
# Export wallet configurations
configs = {}
for agent_id in await connector.list_registered_agents():
    configs[agent_id] = await connector.get_agent_status(agent_id)

# Store configurations securely
await secure_storage.store("agent_configs", configs)
```

This integration provides a robust, secure foundation for AI agents to interact with the Flare blockchain while maintaining strict security controls and comprehensive audit trails.