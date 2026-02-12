# Stargate Connector

The Stargate connector provides information about cross-chain bridging capabilities on Flare Network using Stargate Finance.

## Overview

Stargate is a fully composable omnichain bridge built on LayerZero. It enables cross-chain transfers of assets between Flare and other major blockchains with unified liquidity and instant guaranteed finality.

## Contract Information

| Item | Value |
|------|-------|
| **Token Messaging** | `0x45d417612e177672958dC0537C45a8f8d754Ac2E` |
| **Treasurer** | `0x090194F1EEDc134A680e3b488aBB2D212dba8c01` |
| **Flare Endpoint ID** | `30295` |
| **Network** | Flare Mainnet |

## Supported Tokens (OFTs)

| Token | OFT Address |
|-------|-------------|
| **ETH** | `0x8e8539e4CcD69123c623a106773F2b0cbbc58746` |
| **USDC** | `0x77C71633C34C3784ede189d74223122422492a0f` |
| **USDT** | `0x1C10CC06DC6D35970d1D53B2A23c76ef370d4135` |

## Supported Destination Chains

- **Ethereum** (30101)
- **BNB Chain** (30102)
- **Avalanche** (30106)
- **Polygon** (30109)
- **Arbitrum** (30110)
- **Optimism** (30111)
- **Base** (30184)
- **Linea** (30183)
- **Scroll** (30214)
- **Mantle** (30181)

## Usage

### 1. Initialize the Connector

```python
from flare_ai_kit.ecosystem import Stargate
from flare_ai_kit.ecosystem.settings import EcosystemSettings

settings = EcosystemSettings(
    wallet_address="YOUR_WALLET_ADDRESS",
    private_key="YOUR_PRIVATE_KEY",
)

stargate = await Stargate.create(settings)
```

### 2. Get Token OFT Addresses

```python
# Get OFT contract address for bridgeable tokens
eth_oft = stargate.get_oft_address("ETH")
usdc_oft = stargate.get_oft_address("USDC")

print(f"ETH OFT: {eth_oft}")
print(f"USDC OFT: {usdc_oft}")
```

### 3. Get Destination Chain Endpoints

```python
# Get LayerZero endpoint ID for a chain
arbitrum_endpoint = stargate.get_chain_endpoint("arbitrum")
base_endpoint = stargate.get_chain_endpoint("base")

print(f"Arbitrum: {arbitrum_endpoint}")
print(f"Base: {base_endpoint}")
```

### 4. Get All Supported Tokens

```python
tokens = stargate.get_supported_tokens()
print(f"Bridgeable: {', '.join(tokens)}")
# Output: Bridgeable: ETH, USDC, USDT
```

### 5. Get All Supported Chains

```python
chains = stargate.get_supported_chains()
print(f"Destinations: {', '.join(chains)}")
```

### 6. Get Complete Bridge Info

```python
info = stargate.get_bridge_info()

print(f"Network: {info['network']}")
print(f"Endpoint ID: {info['endpoint_id']}")
print(f"Tokens: {info['supported_tokens']}")
print(f"Chains: {info['supported_chains']}")
```

## What This Connector Provides

This connector is designed for **AI agents** to understand Stargate's bridging capabilities on Flare:

✅ **Information Layer**:
- Get OFT token addresses
- Get destination chain endpoint IDs
- List supported tokens and chains
- Retrieve bridge configuration

❌ **NOT Included** (for good reason):
- Actual bridging transactions (use Stargate frontend or direct OFT calls)
- Fee estimation (requires live quotes)
- Complex LayerZero message passing

## How Bridging Works

1. **OFT Standard**: Stargate uses LayerZero's OFT (Omnichain Fungible Token) standard
2. **User Flow**:
   - Approve OFT contract to spend your tokens
   - Call `send()` on OFT with destination endpoint ID
   - Receive tokens on destination chain
3. **Unified Liquidity**: All chains share a single liquidity pool

## Example: Bridge Info Lookup

```python
# AI agent wants to bridge ETH from Flare to Arbitrum

# Get source token address
eth_oft = stargate.get_oft_address("ETH")

# Get destination chain endpoint
arb_endpoint = stargate.get_chain_endpoint("arbitrum")

# Now AI can instruct user:
print(f"To bridge ETH to Arbitrum:")
print(f"  1. Approve {eth_oft}")
print(f"  2. Bridge to endpoint {arb_endpoint}")
```

## Important Notes

### For AI Agents

This connector helps AI agents:
- Understand what tokens can be bridged
- Know which chains are supported
- Provide accurate contract addresses
- Guide users through bridging process

### For Actual Bridging

To perform actual bridge transactions:
- Use [Stargate's official frontend](https://stargate.finance/)
- Or interact directly with OFT contracts
- Or use LayerZero's SDK

### LayerZero Endpoint IDs

Each chain has a unique **endpoint ID** (eid):
- This is NOT the chain ID!
- Used by LayerZero for cross-chain messaging
- Example: Arbitrum is `30110` (not `42161`)

## Error Handling

The connector raises `StargateError` for protocol-specific errors:

```python
from flare_ai_kit.common import StargateError

try:
    address = stargate.get_oft_address("INVALID")
except StargateError as e:
    print(f"Error: {e}")
```

## Additional Resources

- [Stargate Finance](https://stargate.finance/)
- [Stargate Docs](https://stargateprotocol.gitbook.io/)
- [LayerZero Docs](https://docs.layerzero.network/)
- [FlareScan - Token Messaging](https://flarescan.com/address/0x45d417612e177672958dC0537C45a8f8d754Ac2E)
- [Example Script](../examples/13_stargate_bridge.py)

## Bridge Responsibly! 🌉

Connect Flare to the multichain world with Stargate!

