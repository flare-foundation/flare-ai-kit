# Sceptre Liquid Staking Connector

The Sceptre connector provides an interface for liquid staking FLR tokens on the Flare Network.

## Overview

Sceptre allows users to:
- Stake FLR → Receive sFLR (liquid staked tokens)
- Earn staking rewards + FlareDrops automatically
- Use sFLR in DeFi while still earning rewards
- Unstake with a 14.5-day cooldown period

## Contract Address (Flare Mainnet)

- **sFLR Contract**: `0x12e605bc104e93B45e1aD99F9e555f659051c2BB`

## Basic Usage

### Initialize

```python
from flare_ai_kit import FlareAIKit
from flare_ai_kit.ecosystem.applications.sceptre import Sceptre

kit = FlareAIKit(None)
sceptre = await Sceptre.create(kit.settings.ecosystem)
```

### Stake FLR

```python
tx_hash = await sceptre.stake_flr(10 * 10**18)  # Stake 10 FLR
```

### Check Balance

```python
balance = await sceptre.get_sflr_balance("0xYourAddress")
print(f"sFLR: {balance / 10**18}")
```

### Request Withdrawal

```python
# Start cooldown (~14.5 days)
tx_hash = await sceptre.request_withdrawal(5 * 10**18)
```

### Claim Withdrawal

```python
# After cooldown period
tx_hash = await sceptre.claim_withdrawal(request_id)
```

## Function Reference

### `stake_flr(amount: int) -> str`
Stake FLR tokens to receive sFLR.

### `get_sflr_balance(address: str) -> int`
Get sFLR balance for an address.

### `get_total_pooled_flr() -> int`
Get total FLR staked in Sceptre.

### `get_flr_by_shares(shares: int) -> int`
Convert sFLR shares to FLR amount.

### `get_shares_by_flr(flr_amount: int) -> int`
Convert FLR amount to sFLR shares.

### `request_withdrawal(amount: int) -> str`
Request unstaking (starts 14.5-day cooldown).

### `claim_withdrawal(request_id: int) -> str`
Claim FLR after cooldown period.

## Example

See [`examples/10_sceptre_staking.py`](../examples/10_sceptre_staking.py) for a complete example.

## Learn More

- **Sceptre Docs**: https://docs.sceptre.fi
- **Mechanism**: Liquid staking with auto-compounding rewards
- **Use Cases**: DeFi collateral, trading, yield farming
