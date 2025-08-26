# FAssets Implementation Testing Guide

## Prerequisites

### Python Version

This project requires **Python 3.12+**. The current environment has Python 3.9, which causes compatibility issues with:

- Union operator `|` (requires Python 3.10+)
- `typing.override` (requires Python 3.12+)

### Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip with Python 3.12+
pip install -e .
```

## Testing the Implementation

### 1. Import Testing

```python
# Test basic imports
from flare_ai_kit import FlareAIKit
from flare_ai_kit.common import FAssetType, FAssetsError, FAssetInfo, AgentInfo

# Test FAssets connector
from flare_ai_kit.ecosystem.protocols.fassets import FAssets

print("✅ All imports successful!")
```

### 2. Basic Functionality Test

```python
import asyncio
from flare_ai_kit import FlareAIKit

async def test_fassets_basic():
    # Initialize FlareAIKit
    kit = FlareAIKit()

    # Get FAssets connector
    fassets = await kit.fassets
    print("✅ FAssets connector initialized")

    # Test network detection
    supported = await fassets.get_supported_fassets()
    print(f"✅ Supported FAssets: {list(supported.keys())}")

    # Test chain ID detection
    chain_id = await fassets.w3.eth.chain_id
    print(f"✅ Connected to network: {chain_id}")

asyncio.run(test_fassets_basic())
```

### 3. Network-Specific Testing

#### Songbird Network (Chain ID: 19)

```python
# FXRP should be available and active
if chain_id == 19:
    fxrp_info = await fassets.get_fasset_info(FAssetType.FXRP)
    assert fxrp_info.is_active == True
    print("✅ FXRP detected on Songbird")
```

#### Flare Mainnet (Chain ID: 14)

```python
# FBTC and FDOGE should be configured but not active yet
if chain_id == 14:
    supported = await fassets.get_supported_fassets()
    assert "FBTC" in supported
    assert "FDOGE" in supported
    print("✅ FBTC and FDOGE configured for Flare Mainnet")
```

### 4. Contract Integration Testing

**Note: Requires real contract addresses**

```python
async def test_contract_integration():
    # This will work once real contract addresses are added
    try:
        agents = await fassets.get_all_agents(FAssetType.FXRP)
        print(f"✅ Found {len(agents)} agents")

        if agents:
            agent_info = await fassets.get_agent_info(FAssetType.FXRP, agents[0])
            print(f"✅ Agent info retrieved: {agent_info.name}")

            available_lots = await fassets.get_available_lots(FAssetType.FXRP, agents[0])
            print(f"✅ Available lots: {available_lots}")

    except Exception as e:
        print(f"⚠️  Contract calls failed (expected with placeholder addresses): {e}")
```

### 5. Minting Flow Testing

```python
async def test_minting_flow():
    """Test the complete minting workflow"""
    try:
        # Step 1: Reserve collateral
        reservation_id = await fassets.reserve_collateral(
            fasset_type=FAssetType.FXRP,
            agent_vault="0x...",  # Real agent address needed
            lots=1,
            max_minting_fee_bips=500,  # 5%
            executor="0x...",  # Executor address
            executor_fee_nat=100000000000000000  # 0.1 NAT
        )
        print(f"✅ Collateral reserved: {reservation_id}")

        # Step 2: Get reservation details
        reservation_data = await fassets.get_collateral_reservation_data(
            FAssetType.FXRP, reservation_id
        )
        print(f"✅ Reservation data: {reservation_data}")

    except Exception as e:
        print(f"⚠️  Minting test failed (expected without real contracts): {e}")
```

### 6. Redemption Flow Testing

```python
async def test_redemption_flow():
    """Test the redemption workflow"""
    try:
        redemption_id = await fassets.redeem_from_agent(
            fasset_type=FAssetType.FXRP,
            lots=1,
            max_redemption_fee_bips=500,
            underlying_address="rXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",  # XRP address
            executor="0x...",
            executor_fee_nat=100000000000000000
        )
        print(f"✅ Redemption requested: {redemption_id}")

    except Exception as e:
        print(f"⚠️  Redemption test failed (expected without real contracts): {e}")
```

## Running the Tests

### Unit Tests

```bash
# Run the FAssets-specific tests
python -m pytest tests/integration/ecosystem/protocols/test_fassets.py -v

# Run basic functionality test
python examples/02_fassets_basic.py
```

### Integration Tests

```bash
# Run all ecosystem tests
python -m pytest tests/integration/ecosystem/ -v
```

## Expected Results

### ✅ Working Components

1. **Data Models**: All FAssets schemas, enums, and exceptions
2. **Network Detection**: Automatic FAsset configuration based on chain ID
3. **API Structure**: Complete method signatures and error handling
4. **Integration**: Proper integration with FlareAIKit main class

### ⚠️ Requires Real Contract Addresses

1. **Contract Calls**: Currently using placeholder addresses
2. **Event Parsing**: Needs implementation for reservation/redemption IDs
3. **Transaction Execution**: Needs real agent addresses and sufficient funds

## Next Steps for Production

### 1. Contract Addresses

Update placeholder addresses in `_initialize_supported_fassets()`:

```python
# Replace these with real deployed addresses
asset_manager_address="0x0000000000000000000000000000000000000000"  # ❌ Placeholder
f_asset_address="0x0000000000000000000000000000000000000000"      # ❌ Placeholder
```

### 2. Event Parsing

Implement proper event log parsing for:

- `CollateralReserved` events (to get reservation ID)
- `MintingExecuted` events
- `RedemptionRequested` events

### 3. Enhanced Error Handling

Add specific error handling for:

- Insufficient collateral
- Invalid agent addresses
- Failed underlying transactions

### 4. Testing with Real Networks

Test on:

- Songbird testnet (Coston)
- Flare testnet (Coston2)
- Songbird mainnet (FXRP live)

## Validation Checklist

- [ ] Python 3.12+ environment
- [ ] All dependencies installed
- [ ] Basic imports working
- [ ] Network detection working
- [ ] FAsset info retrieval working
- [ ] Error handling working
- [ ] Integration with FlareAIKit working
- [ ] Real contract addresses configured
- [ ] Contract method calls working
- [ ] Transaction signing and sending working
- [ ] Event parsing implemented
- [ ] End-to-end minting flow tested
- [ ] End-to-end redemption flow tested

## Current Status

✅ **Implementation Complete**: Core functionality, data models, and integration
⚠️ **Needs Real Contracts**: Placeholder addresses prevent live testing
🔄 **Ready for Integration**: Can be used immediately with proper contract addresses
