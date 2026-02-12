# Firelight Connector

The Firelight connector enables XRP staking on Flare Network, allowing users to stake wrapped XRP (FXRP) to earn rewards while providing DeFi coverage.

## Overview

Firelight is a protocol for DeFi cover that transforms staked XRP into protection for DeFi protocols. Users stake FXRP and receive stXRP, a liquid staking token that can be used across DeFi applications.

## Contract Information

| Item | Value |
|------|-------|
| **stXRP Vault Address** | `0x4C18Ff3C89632c3Dd62E796c0aFA5c07c4c1B2b3` |
| **Protocol** | ERC4626 Vault with Withdrawal Periods |
| **Network** | Flare Mainnet |

## Usage

### 1. Initialize the Connector

```python
from flare_ai_kit.ecosystem import Firelight
from flare_ai_kit.ecosystem.settings import EcosystemSettings

settings = EcosystemSettings(
    wallet_address="YOUR_WALLET_ADDRESS",
    private_key="YOUR_PRIVATE_KEY",
)

firelight = await Firelight.create(settings)
```

### 2. Stake FXRP (XRP)

```python
# Amount in wei (18 decimals)
amount = 100 * 10**18  # 100 FXRP

# IMPORTANT: Approve vault to spend your FXRP first!
# fxrp_contract.approve(firelight.STXRP_VAULT, amount)

tx_hash = await firelight.stake_xrp(amount)
print(f"Staked! TX: {tx_hash}")
```

### 3. Request Withdrawal

```python
# Request withdrawal (must wait 1 period before claiming)
amount = 50 * 10**18  # 50 FXRP

tx_hash = await firelight.request_withdrawal(amount)
print(f"Withdrawal requested! TX: {tx_hash}")
```

### 4. Claim Withdrawal

```python
# Get current period
current_period = await firelight.get_current_period()

# Claim from previous period
tx_hash = await firelight.claim_withdrawal(current_period - 1)
print(f"Claimed! TX: {tx_hash}")
```

### 5. Check Balances

```python
# Check stXRP balance
balance = await firelight.get_stxrp_balance("0xYourAddress")
print(f"stXRP Balance: {balance / 10**18}")

# Check total staked in vault
total = await firelight.get_total_assets()
print(f"Total Staked: {total / 10**18} FXRP")
```

### 6. Check Pending Withdrawals

```python
# Get current period
period = await firelight.get_current_period()

# Check pending amount for previous period
pending = await firelight.get_pending_withdrawal(period - 1, "0xYourAddress")
print(f"Pending: {pending / 10**18} FXRP")
```

## How It Works

1. **Stake**: Deposit FXRP to receive stXRP (liquid staking token)
2. **Earn**: stXRP represents your staked FXRP + rewards
3. **Use**: Trade or use stXRP in DeFi while still earning
4. **Withdraw**: Request withdrawal → wait 1 period → claim FXRP

## Withdrawal Periods

- Firelight uses **withdrawal periods** for security
- When you request a withdrawal, it becomes claimable in the **next period**
- Check `currentPeriod()` to see the active period
- Claim using `claimWithdraw(period)` after the period ends

## Important Notes

### Before Staking

⚠️ **You need FXRP (wrapped XRP on Flare)**:
- Get FXRP through Flare's FAssets bridge
- Or swap for FXRP on Flare DEXes

⚠️ **You must approve the vault to spend your FXRP**:

```python
# Using web3.py (example)
fxrp_contract = w3.eth.contract(address=FXRP_ADDRESS, abi=ERC20_ABI)
tx = fxrp_contract.functions.approve(
    firelight.STXRP_VAULT,
    amount
).build_transaction({...})
```

### What is stXRP?

- **stXRP** is an ERC20 liquid staking token
- Represents your staked FXRP in the vault
- Can be transferred, traded, or used in DeFi
- Earn rewards while your FXRP is staked

### DeFi Cover

Firelight provides **on-chain risk protection** for DeFi:
- Your staked XRP backs DeFi protocol coverage
- Earn fees from cover buyers
- Help secure the Flare DeFi ecosystem

## Error Handling

The connector raises `FirelightError` for protocol-specific errors:

```python
from flare_ai_kit.common import FirelightError

try:
    await firelight.stake_xrp(amount)
except FirelightError as e:
    print(f"Firelight error: {e}")
```

## Additional Resources

- [Firelight Website](https://firelight.finance/)
- [Firelight Docs](https://docs.firelight.finance/)
- [FlareScan - stXRP Vault](https://flarescan.com/address/0x4C18Ff3C89632c3Dd62E796c0aFA5c07c4c1B2b3)
- [Example Script](../examples/12_firelight_xrp_staking.py)

## XRP Gang! 🚀

Stake your XRP, earn rewards, and support DeFi security on Flare!

