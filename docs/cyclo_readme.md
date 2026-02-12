# Cyclo Connector

The Cyclo connector provides an interface to interact with the Cyclo protocol on Flare for non-liquidating leverage.

## Overview

Cyclo allows users to lock collateral (sFLR) and mint cy* tokens (cysFLR) without liquidation risk. The cy* tokens trade between $0-$1 and can be used to create leverage or as stable-value alternatives.

## Contract Addresses (Flare Mainnet)

- **cysFLR Vault**: `0x19831cfB53A0dbeAD9866C43557C1D48DfF76567`
- **cysFLR Receipt (ERC1155)**: `0xd387FC43E19a63036d8FCeD559E81f5dDeF7ef09`

## How It Works

1. **Lock & Mint**: User locks sFLR → mints cysFLR + receipt NFT
   - Receipt ID = price at time of lock (e.g., 0.015 USD per sFLR)
   - User gets cysFLR tokens (ERC20) that trade $0-$1

2. **Trade**: User can sell cysFLR to create leverage
   - Example: Lock 100 sFLR → get 100 cysFLR @ $0.80 → sell for 80 sFLR → lock again

3. **Unlock**: User buys back cysFLR + burns with receipt NFT → unlocks sFLR
   - Must burn SAME amount of cysFLR as receipt balance
   - Receipt ID determines redemption ratio

## Basic Usage

### Initialize

```python
from flare_ai_kit import FlareAIKit
from flare_ai_kit.ecosystem.applications.cyclo import Cyclo

kit = FlareAIKit(None)
cyclo = await Cyclo.create(kit.settings.ecosystem)
```

### Lock sFLR & Mint cysFLR

```python
# Lock 10 sFLR to mint cysFLR
tx_hash = await cyclo.deposit_sflr(
    assets=10 * 10**18,  # 10 sFLR (18 decimals)
    recipient="0xYourAddress",
    min_share_ratio=0,  # Slippage protection
    receipt_info=b"",   # Optional metadata
)
```

### Burn cysFLR & Unlock sFLR

```python
# Burn 5 cysFLR + receipt to unlock sFLR
tx_hash = await cyclo.redeem_sflr(
    shares=5 * 10**18,       # 5 cysFLR to burn
    recipient="0xYourAddress",
    owner="0xYourAddress",
    receipt_id=15000000000000000000,  # ID from deposit
    receipt_info=b"",
)
```

### Check Balances

```python
# Get cysFLR balance
balance = await cyclo.get_cysflr_balance("0xYourAddress")
print(f"cysFLR: {balance / 10**18}")

# Get receipt balance for specific ID
receipt_balance = await cyclo.get_receipt_balance(
    "0xYourAddress",
    receipt_id=15000000000000000000
)
print(f"Receipt NFTs: {receipt_balance}")
```

### Query Vault Info

```python
# Get underlying asset (sFLR address)
asset = await cyclo.get_vault_asset()
print(f"Vault asset: {asset}")
```

## Function Reference

### `deposit_sflr()`

Lock sFLR and mint cysFLR tokens + receipt NFT.

**Parameters:**
- `assets` (int): Amount of sFLR to lock (in wei, 18 decimals)
- `recipient` (str): Address to receive cysFLR and receipt
- `min_share_ratio` (int, optional): Minimum share ratio for slippage protection (default: 0)
- `receipt_info` (bytes, optional): Optional metadata for receipt (default: b"")

**Returns:** Transaction hash (str)

**Raises:** `CycloError` if deposit fails

---

### `redeem_sflr()`

Burn cysFLR tokens + receipt NFT to unlock sFLR.

**Parameters:**
- `shares` (int): Amount of cysFLR to burn (in wei, 18 decimals)
- `recipient` (str): Address to receive unlocked sFLR
- `owner` (str): Address that owns the cysFLR tokens and receipt NFT
- `receipt_id` (int): ID of the receipt NFT (price at time of lock)
- `receipt_info` (bytes, optional): Optional metadata (default: b"")

**Returns:** Transaction hash (str)

**Raises:** `CycloError` if redemption fails

---

### `get_cysflr_balance()`

Get cysFLR token balance for an address.

**Parameters:**
- `address` (str): Address to check balance for

**Returns:** Balance in wei (int, 18 decimals)

**Raises:** `CycloError` if query fails

---

### `get_receipt_balance()`

Get receipt NFT balance for a specific ID.

**Parameters:**
- `address` (str): Address to check balance for
- `receipt_id` (int): ID of the receipt NFT

**Returns:** Number of receipt NFTs with this ID (int)

**Raises:** `CycloError` if query fails

---

### `get_vault_asset()`

Get the underlying asset address (sFLR) for the vault.

**Returns:** Checksum address of the underlying asset (ChecksumAddress)

**Raises:** `CycloError` if query fails

## Example Script

See [`examples/09_cyclo_leverage.py`](../examples/09_cyclo_leverage.py) for a complete example.

## Notes

- **Receipt IDs**: Track receipt IDs from deposit events - you'll need them to redeem
- **Approvals**: Approve sFLR spending before deposit
- **No Liquidations**: Unlike traditional lending, Cyclo never liquidates your position
- **Price Bound**: cysFLR trades between $0-$1, creating natural leverage limits
- **Staking Rewards**: Locked sFLR continues earning staking rewards

## Error Handling

All functions raise `CycloError` on failure. Wrap calls in try/except:

```python
from flare_ai_kit.common import CycloError

try:
    tx_hash = await cyclo.deposit_sflr(10 * 10**18, recipient)
except CycloError as e:
    print(f"Deposit failed: {e}")
```

## Learn More

- **Cyclo Docs**: https://cyclo.finance
- **Mechanism**: Lock collateral → mint cy* tokens → no liquidations
- **Use Cases**: Non-liquidating leverage, stable-value tokens, yield strategies

