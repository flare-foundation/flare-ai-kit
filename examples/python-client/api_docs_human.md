```markdown
# FlareAIKit API Documentation

This API provides endpoints for blockchain operations on the Flare network (chain ID 14), supporting token swaps, cross-chain bridging, wrapping, staking, and lending via protocols like Stargate, SparkDEX, FlarePortal, Sceptre, Kinetic, Cyclo, and OpenOcean. All endpoints use POST requests with JSON payloads over a secure TLS connection on `https://0.0.0.0:4433`. Responses include transaction hashes (`tx_hash`) and, for some endpoints, additional data like `deposit_id`.

## Base URL
`https://0.0.0.0:4433`

## Endpoints

### POST /bridge
**Summary**: Bridge WETH to another chain via Stargate

**Description**: Initiates a cross-chain bridge of WETH to a specified chain (e.g., Flare or Ethereum) using the Stargate protocol.

**Request Body**:
- `chain_id` (integer, required): Destination chain ID (e.g., 14 for Flare, 101 for Ethereum). See [Stargate Contracts](https://docs.stargate.finance/resources/contracts/mainnet-contracts).
- `amount_wei` (integer, required): Amount to bridge in wei (e.g., 100000000000000 for 0.0001 ETH).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'chain_id' (must be a non-empty integer)"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/bridge -H "Content-Type: application/json" -d '{"chain_id": 14, "amount_wei": 100000000000000}'
```

### POST /swap
**Summary**: Swap ERC-20 tokens via SparkDEX

**Description**: Swaps one ERC-20 token for another on SparkDEX, specifying input/output tokens and a minimum output amount.

**Request Body**:
- `token_in_addr` (string, required): Input token address (e.g., WFLR: "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d").
- `token_out_addr` (string, required): Output token address (e.g., WETH: "0x1502FA4be69d526124D453619276FacCab275d3D").
- `amount_in_WEI` (integer, required): Amount to swap in wei (e.g., 1000000000000000000 for 1 token).
- `amount_out_min_WEI` (integer, required): Minimum output amount in wei (e.g., 0 for no minimum).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'token_in_addr' (must be a valid EVM address)"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/swap -H "Content-Type: application/json" -d '{"token_in_addr": "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d", "token_out_addr": "0x1502FA4be69d526124D453619276FacCab275d3D", "amount_in_WEI": 1000000000000000000, "amount_out_min_WEI": 0}'
```

### POST /wrap
**Summary**: Wrap FLR to WFLR via FlarePortal

**Description**: Wraps native FLR to WFLR tokens using FlarePortal.

**Request Body**:
- `amount_WEI` (integer, required): Amount to wrap in wei (e.g., 1000000000000000000 for 1 FLR).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/wrap -H "Content-Type: application/json" -d '{"amount_WEI": 1000000000000000000}'
```

### POST /unwrap
**Summary**: Unwrap WFLR to FLR via FlarePortal

**Description**: Unwraps WFLR tokens to native FLR using FlarePortal.

**Request Body**:
- `amount_WEI` (integer, required): Amount to unwrap in wei (e.g., 1000000000000000000 for 1 WFLR).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/unwrap -H "Content-Type: application/json" -d '{"amount_WEI": 1000000000000000000}'
```

### POST /stake
**Summary**: Stake tokens via Sceptre

**Description**: Stakes tokens using the Sceptre protocol.

**Request Body**:
- `amount_WEI` (integer, required): Amount to stake in wei (e.g., 1000000000000000000 for 1 token).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/stake -H "Content-Type: application/json" -d '{"amount_WEI": 1000000000000000000}'
```

### POST /unstake
**Summary**: Unstake tokens via Sceptre

**Description**: Unstakes tokens using the Sceptre protocol.

**Request Body**:
- `amount_WEI` (integer, required): Amount to unstake in wei (e.g., 1000000000000000000 for 1 token).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/unstake -H "Content-Type: application/json" -d '{"amount_WEI": 1000000000000000000}'
```

### POST /kinetic_supply
**Summary**: Supply tokens to Kinetic protocol

**Description**: Supplies tokens to the Kinetic lending protocol.

**Request Body**:
- `token_symbol` (string, required): Symbol of the token to supply (e.g., "sflr").
- `amount_WEI` (integer, required): Amount to supply in wei (e.g., 1000000000000000000 for 1 token).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'token_symbol'"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/kinetic_supply -H "Content-Type: application/json" -d '{"token_symbol": "sflr", "amount_WEI": 1000000000000000000}'
```

### POST /kinetic_withdraw
**Summary**: Withdraw tokens from Kinetic protocol

**Description**: Withdraws tokens from the Kinetic lending protocol.

**Request Body**:
- `token_symbol` (string, required): Symbol of the token to withdraw (e.g., "sflr").
- `amount_WEI` (integer, required): Amount to withdraw in wei (e.g., 1000000000000000000 for 1 token).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'token_symbol'"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/kinetic_withdraw -H "Content-Type: application/json" -d '{"token_symbol": "sflr", "amount_WEI": 1000000000000000000}'
```

### POST /kinetic_enable_collateral
**Summary**: Enable token as collateral in Kinetic

**Description**: Enables a token as collateral in the Kinetic lending protocol.

**Request Body**:
- `token_symbol` (string, required): Symbol of the token to enable (e.g., "sflr").

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'token_symbol'"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/kinetic_enable_collateral -H "Content-Type: application/json" -d '{"token_symbol": "sflr"}'
```

### POST /kinetic_disable_collateral
**Summary**: Disable token as collateral in Kinetic

**Description**: Disables a token as collateral in the Kinetic lending protocol.

**Request Body**:
- `token_symbol` (string, required): Symbol of the token to disable (e.g., "sflr").

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'token_symbol'"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/kinetic_disable_collateral -H "Content-Type: application/json" -d '{"token_symbol": "sflr"}'
```

### POST /cyclo_lock
**Summary**: Lock tokens in Cyclo protocol

**Description**: Locks tokens in the Cyclo protocol, returning a transaction hash and deposit ID.

**Request Body**:
- `token_symbol` (string, required): Symbol of the token to lock (e.g., "sflr").
- `amount_WEI` (integer, required): Amount to lock in wei (e.g., 1000000000000000000 for 1 token).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "deposit_id": 123
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'token_symbol'"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/cyclo_lock -H "Content-Type: application/json" -d '{"token_symbol": "sflr", "amount_WEI": 1000000000000000000}'
```

### POST /cyclo_unlock
**Summary**: Unlock tokens in Cyclo protocol

**Description**: Unlocks a proportion of tokens in the Cyclo protocol using a deposit ID.

**Request Body**:
- `token_symbol` (string, required): Symbol of the token to unlock (e.g., "sflr").
- `deposit_id` (integer, required): Deposit ID from a previous lock operation.
- `unlock_proportion` (number, required): Proportion to unlock (0 to 1, e.g., 1.0 for full unlock).

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'deposit_id'"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/cyclo_unlock -H "Content-Type: application/json" -d '{"token_symbol": "sflr", "deposit_id": 123, "unlock_proportion": 1.0}'
```

### POST /openocean_swap
**Summary**: Swap tokens via OpenOcean

**Description**: Performs a token swap on the Flare network using the OpenOcean protocol with a speed preference.

**Request Body**:
- `token_in_str` (string, required): Input token symbol (e.g., "wflr").
- `token_out_str` (string, required): Output token symbol (e.g., "weth").
- `amount` (number, required): Amount to swap in token units (e.g., 1.0 for 1 token).
- `speed` (string, required): Swap speed preference (e.g., "low", "medium", "high").

**Responses**:
- **201 Success**:
  ```json
  {
    "success": true,
    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
  ```
- **400 Bad Request**:
  ```json
  {
    "error": "Invalid or missing 'token_in_str'"
  }
  ```
- **500 Server Error**:
  ```json
  {
    "error": "Transaction failed: ..."
  }
  ```

**Example**:
```bash
curl -X POST https://0.0.0.0:4433/openocean_swap -H "Content-Type: application/json" -d '{"token_in_str": "wflr", "token_out_str": "weth", "amount": 1.0, "speed": "fast"}'
```

## Notes
- **TLS**: Requests require a valid attestation token (`sim_token.txt`) for the TLS handshake, configured in `ra_tls_main.py`.
- **Chain ID**: For `/bridge`, use valid chain IDs (e.g., 14 for Flare, 101 for Ethereum), not 30184. See [Stargate Contracts](https://docs.stargate.finance/resources/contracts/mainnet-contracts).
- **Precision**: Use integers for `amount_WEI` (e.g., `1000000000000000000` for 1 token) to avoid floating-point issues. Clients like `client_test.py` convert floats (e.g., `1.0`) to wei using `int(amount * 10**18)`.
- **Errors**: Check server logs for transaction failures (e.g., insufficient balance) or invalid parameters.

## Testing
1. **Run Server**:
   ```bash
   cd /Users/simonjonsson/Library/Mobile Documents/com~apple~CloudDocs/Documents/SmartContracts/Projects/FlareAIKit/flare-ai-kit/examples/python-client/backend
   python3.12 ra_tls_main.py
   ```
2. **Test with Client**:
   ```bash
   cd /Users/simonjonsson/.../client
   python3.12 client_test.py
   ```
3. **Verify Balance**:
   ```python
   from web3 import AsyncWeb3
   w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("https://flare-api.flare.network/ext/C/rpc"))
   balance = await w3.eth.get_balance("0xYourWalletAddress")
   print(w3.from_wei(balance, "ether"))
   ```
```