# Kinetic Connector

The Kinetic connector provides seamless integration with the Kinetic lending protocol on Flare Network, focusing on the ksFLR market for supplying and earning interest on sFLR tokens.

## Overview

Kinetic is an overcollateralized lending protocol built on Flare, facilitating peer-to-peer borrowing with dynamic interest rates. This connector enables:

- **Supply**: Lend sFLR to earn interest
- **Redeem**: Withdraw supplied sFLR + accrued interest
- **Balance Queries**: Check ksFLR holdings and underlying sFLR value
- **Market Data**: Get exchange rates and supply APY

## Contract Information

| Item | Value |
|------|-------|
| **ksFLR Market Address** | `0x291487beC339c2fE5D83DD45F0a15EFC9Ac45656` |
| **Protocol** | Compound V2 Fork |
| **Network** | Flare Mainnet |

## Usage

### 1. Initialize the Connector

```python
from flare_ai_kit.ecosystem import Kinetic
from flare_ai_kit.ecosystem.settings import EcosystemSettings

settings = EcosystemSettings(
    wallet_address="YOUR_WALLET_ADDRESS",
    private_key="YOUR_PRIVATE_KEY",
)

kinetic = await Kinetic.create(settings)
```

### 2. Supply sFLR

Supply sFLR to the ksFLR market to earn interest:

```python
# Amount in wei (18 decimals)
amount = 10 * 10**18  # 10 sFLR

# IMPORTANT: Approve ksFLR market to spend your sFLR first!
# sflr_contract.approve(kinetic.KSFLR_MARKET, amount)

tx_hash = await kinetic.supply(amount)
print(f"Supplied! TX: {tx_hash}")
```

**Parameters:**
- `amount` (int): Amount of sFLR to supply in wei (18 decimals)

**Returns:**
- Transaction hash as hex string

### 3. Redeem ksFLR

Withdraw your supplied sFLR by redeeming ksFLR tokens:

```python
# Amount of ksFLR to redeem (in wei, 18 decimals)
amount = 5 * 10**18  # 5 ksFLR

tx_hash = await kinetic.redeem(amount)
print(f"Redeemed! TX: {tx_hash}")
```

**Parameters:**
- `amount` (int): Amount of ksFLR to redeem in wei (18 decimals)

**Returns:**
- Transaction hash as hex string

### 4. Check Balances

#### Get ksFLR Balance

```python
balance = await kinetic.get_balance("0xYourAddress")
print(f"ksFLR Balance: {balance / 10**18}")
```

#### Get Underlying sFLR Balance

```python
underlying = await kinetic.get_underlying_balance("0xYourAddress")
print(f"Can withdraw: {underlying / 10**18} sFLR")
```

### 5. Get Market Data

#### Exchange Rate

```python
rate = await kinetic.get_exchange_rate()
print(f"1 ksFLR = {rate / 10**18} sFLR")
```

#### Supply APY

```python
supply_rate = await kinetic.get_supply_rate()

# Convert to APY (rate is per timestamp)
blocks_per_year = 15768000  # Flare average
apy = (supply_rate / 10**18) * blocks_per_year * 100
print(f"Supply APY: {apy:.2f}%")
```

## Complete Example

```python
import asyncio
from flare_ai_kit.ecosystem import Kinetic
from flare_ai_kit.ecosystem.settings import EcosystemSettings

async def main():
    # Initialize
    settings = EcosystemSettings(
        wallet_address="YOUR_WALLET_ADDRESS",
        private_key="YOUR_PRIVATE_KEY",
    )
    kinetic = await Kinetic.create(settings)
    
    # Check balances
    balance = await kinetic.get_balance(settings.wallet_address)
    print(f"ksFLR Balance: {balance / 10**18}")
    
    # Get market info
    rate = await kinetic.get_exchange_rate()
    print(f"Exchange Rate: 1 ksFLR = {rate / 10**18} sFLR")
    
    # Supply sFLR (make sure to approve first!)
    # tx = await kinetic.supply(10 * 10**18)
    
    # Redeem ksFLR
    # tx = await kinetic.redeem(5 * 10**18)

asyncio.run(main())
```

## How It Works

1. **Supply**: When you supply sFLR, you receive ksFLR tokens representing your share
2. **Interest Accrual**: The exchange rate between ksFLR and sFLR increases over time
3. **Redeem**: Burn ksFLR to withdraw sFLR at the current (higher) exchange rate
4. **Profit**: The difference between supply and redeem rates is your earned interest

## Important Notes

### Before Supplying

⚠️ **You must approve the ksFLR market to spend your sFLR before calling `supply()`**:

```python
# Using web3.py (example)
sflr_contract = w3.eth.contract(address=SFLR_ADDRESS, abi=ERC20_ABI)
tx = sflr_contract.functions.approve(
    kinetic.KSFLR_MARKET,
    amount
).build_transaction({...})
```

### Exchange Rate

- The exchange rate starts at a value (e.g., 2e26) and increases as interest accrues
- 1 ksFLR is always worth ≥ the sFLR you supplied
- Rate formula: `underlying_balance = ksflr_balance * exchange_rate / 1e18`

### Gas Considerations

- Supply and redeem operations require gas (in FLR)
- Balance queries are free (view functions)

## Error Handling

The connector raises `KineticError` for protocol-specific errors:

```python
from flare_ai_kit.common import KineticError

try:
    await kinetic.supply(amount)
except KineticError as e:
    print(f"Kinetic error: {e}")
```

## Additional Resources

- [Kinetic Documentation](https://docs.kinetic.market/)
- [FlareScan - ksFLR Market](https://flarescan.com/address/0x291487beC339c2fE5D83DD45F0a15EFC9Ac45656)
- [Example Script](../examples/11_kinetic_lending.py)

## See Also

- [Sceptre Connector](./sceptre_readme.md) - Get sFLR by staking FLR
- [Cyclo Connector](./cyclo_readme.md) - Leverage sFLR with liquidation-free positions

