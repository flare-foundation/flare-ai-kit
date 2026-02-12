# SparkDEX Connector

The SparkDEX connector enables AI agents to swap tokens on SparkDEX V3, a Uniswap V3 fork deployed on Flare Network.

## Quick Start

```python
import asyncio
from flare_ai_kit.ecosystem.applications.sparkdex import SparkDEX, FEE_MEDIUM
from flare_ai_kit.ecosystem.settings import EcosystemSettings

async def swap_example():
    # Initialize connector
    settings = EcosystemSettings()
    sparkdex = await SparkDEX.create(settings)
    
    # Execute a swap
    tx_hash = await sparkdex.swap_exact_input_single(
        token_in="0xTokenInAddress",
        token_out="0xTokenOutAddress",
        fee=FEE_MEDIUM,  # 0.3% fee tier
        recipient="0xYourAddress",
        amount_in=1000000000000000000,  # 1 token (18 decimals)
        amount_out_minimum=900000000000000000,  # Min 0.9 tokens out (10% slippage)
        deadline=int(time.time()) + 3600,  # 1 hour from now
    )
    print(f"Swap successful: {tx_hash}")

asyncio.run(swap_example())
```

## Features

### Swap Functions

#### `swap_exact_input_single()`
Swap an exact amount of input tokens for as many output tokens as possible.

**Parameters:**
- `token_in` (str): Address of input token
- `token_out` (str): Address of output token  
- `fee` (int): Pool fee tier (500/3000/10000)
- `recipient` (str): Address to receive output tokens
- `amount_in` (int): Exact input amount in wei
- `amount_out_minimum` (int): Minimum output amount (slippage protection)
- `deadline` (int): Unix timestamp deadline
- `sqrt_price_limit_x96` (int, optional): Price limit (default: 0 = no limit)

**Returns:** Transaction hash (str)

**Example:**
```python
# Swap 100 USDT for minimum 95 USDC (5% slippage)
tx_hash = await sparkdex.swap_exact_input_single(
    token_in="0xUSDT_ADDRESS",
    token_out="0xUSDC_ADDRESS",
    fee=FEE_LOW,  # 0.05% fee for stablecoin pairs
    recipient=sparkdex.address,
    amount_in=100_000000,  # 100 USDT (6 decimals)
    amount_out_minimum=95_000000,  # Min 95 USDC
    deadline=int(time.time()) + 1800,  # 30 min
)
```

#### `swap_exact_output_single()`
Swap as few input tokens as possible to receive an exact amount of output tokens.

**Parameters:**
- `token_in` (str): Address of input token
- `token_out` (str): Address of output token
- `fee` (int): Pool fee tier (500/3000/10000)
- `recipient` (str): Address to receive output tokens
- `amount_out` (int): Exact output amount desired in wei
- `amount_in_maximum` (int): Maximum input amount willing to spend
- `deadline` (int): Unix timestamp deadline
- `sqrt_price_limit_x96` (int, optional): Price limit

**Returns:** Transaction hash (str)

**Example:**
```python
# Buy exactly 1 ETH, spending at most 2000 USDC
tx_hash = await sparkdex.swap_exact_output_single(
    token_in="0xUSDC_ADDRESS",
    token_out="0xWETH_ADDRESS",
    fee=FEE_MEDIUM,  # 0.3% fee
    recipient=sparkdex.address,
    amount_out=1_000000000000000000,  # Exactly 1 ETH
    amount_in_maximum=2000_000000,  # Max 2000 USDC
    deadline=int(time.time()) + 1800,
)
```

### Query Functions

#### `get_factory_address()`
Get the SparkDEX V3 factory contract address.

**Returns:** Factory address (ChecksumAddress)

```python
factory = await sparkdex.get_factory_address()
print(f"Factory: {factory}")
```

#### `get_weth9_address()`
Get the WETH9 (Wrapped FLR) contract address.

**Returns:** WETH9 address (ChecksumAddress)

```python
weth9 = await sparkdex.get_weth9_address()
print(f"Wrapped FLR: {weth9}")
```

## Fee Tiers

SparkDEX V3 uses three fee tiers for different token pairs:

| Constant | Basis Points | Percentage | Best For |
|----------|--------------|------------|----------|
| `FEE_LOW` | 500 | 0.05% | Stablecoin pairs (USDC/USDT) |
| `FEE_MEDIUM` | 3000 | 0.3% | Most pairs (ETH/USDC) |
| `FEE_HIGH` | 10000 | 1% | Exotic/volatile pairs |

```python
from flare_ai_kit.ecosystem.applications.sparkdex import FEE_LOW, FEE_MEDIUM, FEE_HIGH
```

## Configuration

The connector requires SparkDEX router address in your `.env`:

```bash
# Already configured for Flare Mainnet
ECOSYSTEM__CONTRACTS__FLARE__SPARKDEX_SWAP_ROUTER=0x8a1E35F5c98C4E85B36B7B253222eE17773b2781

# For Coston2 testnet (if available)
ECOSYSTEM__CONTRACTS__COSTON2__SPARKDEX_SWAP_ROUTER=0xYourTestnetAddress
```

## Prerequisites

Before swapping, ensure:

1. **FLR Balance** - For gas fees (~0.01 FLR per swap)
2. **Token Balance** - Sufficient input token amount
3. **Token Approval** - Approve SparkDEX router to spend your tokens:

```python
from flare_ai_kit.common import load_abi

# Get ERC20 contract
token_contract = sparkdex.w3.eth.contract(
    address=sparkdex.w3.to_checksum_address(token_address),
    abi=load_abi("ERC20"),
)

# Approve router
approve_tx = await token_contract.functions.approve(
    router_address,
    amount_to_approve
).transact({'from': sparkdex.address})
```

## Error Handling

```python
from flare_ai_kit.common import FlareTxError, FlareTxRevertedError

try:
    tx_hash = await sparkdex.swap_exact_input_single(...)
except AttributeError as e:
    print("SparkDEX not initialized - use SparkDEX.create()")
except ValueError as e:
    print("Account not configured - set ECOSYSTEM__ACCOUNT_ADDRESS")
except FlareTxRevertedError as e:
    print(f"Transaction reverted: {e}")
    # Common causes:
    # - Insufficient token approval
    # - Slippage too low (amount_out_minimum too high)
    # - Deadline expired
    # - Pool doesn't exist for this fee tier
except FlareTxError as e:
    print(f"Transaction failed: {e}")
```

## Best Practices

### 1. **Set Appropriate Slippage**

```python
# Calculate slippage tolerance
input_amount = 1000000000000000000  # 1 token
slippage_percent = 1.0  # 1% slippage

min_output = int(expected_output * (1 - slippage_percent / 100))

await sparkdex.swap_exact_input_single(
    amount_in=input_amount,
    amount_out_minimum=min_output,  # 1% slippage protection
    ...
)
```

### 2. **Use Reasonable Deadlines**

```python
import time

# 10 minutes from now
deadline = int(time.time()) + 600

# For production: adjust based on network congestion
deadline = int(time.time()) + 1800  # 30 minutes
```

### 3. **Choose Correct Fee Tier**

```python
# Check which fee tier has the most liquidity on SparkDEX UI
# before executing large swaps

# Stablecoins: Use FEE_LOW (0.05%)
await sparkdex.swap_exact_input_single(
    token_in=USDC,
    token_out=USDT,
    fee=FEE_LOW,
    ...
)

# Most pairs: Use FEE_MEDIUM (0.3%)
await sparkdex.swap_exact_input_single(
    token_in=WETH,
    token_out=USDC,
    fee=FEE_MEDIUM,
    ...
)
```

### 4. **Test with Small Amounts First**

```python
# Test with 0.1 tokens before swapping large amounts
test_amount = 100000000000000000  # 0.1 token (18 decimals)

tx_hash = await sparkdex.swap_exact_input_single(
    amount_in=test_amount,
    ...
)
```

## Architecture

The connector extends the `Flare` base class and uses:
- **Web3** for blockchain interactions
- **Structlog** for logging
- **EcosystemSettings** for configuration

```
SparkDEX
  ├── Inherits from: Flare
  ├── Contract: SparkDEX V3 SwapRouter
  ├── ABI: SparkDEXRouter.json (Uniswap V3 compatible)
  └── Network: Flare Mainnet (Contract: 0x8a1E...2781)
```

## Contract Addresses

### Flare Mainnet

| Contract | Address | Description |
|----------|---------|-------------|
| SwapRouter | [`0x8a1E35F5c98C4E85B36B7B253222eE17773b2781`](https://flarescan.com/address/0x8a1E35F5c98C4E85B36B7B253222eE17773b2781) | V3 Swap Router |
| Factory | `0x8A2578d23d4C532cC9A98FaD91C0523f5efDE652` | V3 Factory |
| WETH9 | `0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d` | Wrapped FLR |

## Testing

Run unit tests:

```bash
uv run pytest tests/unit/ecosystem/applications/test_sparkdex.py -v
```

## Examples

See [`examples/sparkdex_swap.py`](../../examples/sparkdex_swap.py) for a complete working example.

## References

- [SparkDEX Documentation](https://docs.sparkdex.ai/)
- [Uniswap V3 Core](https://docs.uniswap.org/contracts/v3/overview)
- [FlareScan - SparkDEX Router](https://flarescan.com/address/0x8a1E35F5c98C4E85B36B7B253222eE17773b2781)

