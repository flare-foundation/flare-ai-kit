# Troubleshooting Guide

This guide helps you diagnose and resolve common issues when using the Flare AI Kit SDK.

## Exception Categories

The Flare AI Kit SDK uses structured exceptions that inherit from `FlareAIKitError`. All exceptions include:
- Human-readable error messages
- Structured context information
- Error codes for programmatic handling
- Automatic masking of sensitive data

## Common Error Scenarios

### Wallet Errors

#### WalletCreationError
**Error Code:** `WALLET_CREATION_FAILED`, `WALLET_CREATION_UNEXPECTED_ERROR`

**Common Causes:**
- Invalid wallet name
- Network connectivity issues
- Turnkey API authentication problems
- Insufficient permissions

**Solutions:**
1. Verify wallet name is valid (alphanumeric, no special characters)
2. Check network connection
3. Verify Turnkey API credentials are correct
4. Ensure organization has sufficient permissions

**Example:**
```python
try:
    wallet_id = await turnkey_wallet.create_wallet("my_wallet")
except WalletCreationError as e:
    print(f"Failed to create wallet: {e}")
    print(f"Error code: {e.error_code}")
    print(f"Context: {e.context}")
```

#### WalletNotFoundError
**Error Code:** `WALLET_ACCOUNT_NOT_FOUND`

**Common Causes:**
- Invalid wallet ID
- Derivation path doesn't exist
- Wallet was deleted

**Solutions:**
1. Verify wallet ID is correct
2. Check available derivation paths
3. Ensure wallet exists and is accessible

#### WalletPermissionError
**Error Code:** `WALLET_PERMISSION_DENIED`

**Common Causes:**
- Insufficient permissions for operation
- Policy restrictions
- Authentication issues

**Solutions:**
1. Check wallet permissions
2. Review policy configuration
3. Verify authentication credentials

### FAssets Errors

#### FAssetsContractError
**Error Code:** `FASSETS_ABI_RETRIEVAL_FAILED`, `FASSETS_CONTRACT_INTERACTION_FAILED`

**Common Causes:**
- Contract ABI not found
- Invalid contract address
- Network connectivity issues
- Contract not deployed

**Solutions:**
1. Verify contract address is correct
2. Ensure contract ABI is available
3. Check network connection
4. Verify contract is deployed on the network

#### FAssetsMintError
**Error Code:** `FASSETS_MINT_FAILED`

**Common Causes:**
- Insufficient collateral
- Invalid mint parameters
- Contract logic errors

**Solutions:**
1. Check collateral balance
2. Verify mint parameters
3. Review contract state

### Network Errors

#### ConnectionError
**Error Code:** `NETWORK_CONNECTION_FAILED`

**Common Causes:**
- Network connectivity issues
- Firewall blocking connections
- DNS resolution problems

**Solutions:**
1. Check internet connection
2. Verify firewall settings
3. Test DNS resolution
4. Check proxy settings if applicable

#### TimeoutError
**Error Code:** `NETWORK_TIMEOUT`

**Common Causes:**
- Slow network response
- Server overload
- Network congestion

**Solutions:**
1. Increase timeout settings
2. Retry the operation
3. Check server status
4. Use a different network if possible

#### HTTPError
**Error Code:** `HTTP_ERROR`

**Common Causes:**
- Invalid API endpoint
- Authentication failures
- Rate limiting
- Server errors

**Solutions:**
1. Verify API endpoint URL
2. Check authentication credentials
3. Implement rate limiting
4. Check server status

### Validation Errors

#### InvalidInputError
**Error Code:** `VALIDATION_INVALID_INPUT`

**Common Causes:**
- Invalid parameter types
- Missing required parameters
- Parameter value out of range

**Solutions:**
1. Check parameter types and values
2. Verify all required parameters are provided
3. Validate parameter ranges

#### InvalidAddressError
**Error Code:** `VALIDATION_INVALID_ADDRESS`

**Common Causes:**
- Invalid blockchain address format
- Address checksum mismatch
- Unsupported address type

**Solutions:**
1. Verify address format
2. Check address checksum
3. Ensure address type is supported

### vTPM Errors

#### VtpmAttestationError
**Error Code:** `VTPM_ATTESTATION_FAILED`

**Common Causes:**
- vTPM service unavailable
- Invalid attestation request
- Certificate chain issues

**Solutions:**
1. Check vTPM service status
2. Verify attestation parameters
3. Check certificate chain validity

#### VtpmValidationError
**Error Code:** `VTPM_VALIDATION_FAILED`

**Common Causes:**
- Invalid certificate chain
- Signature validation failure
- Certificate parsing errors

**Solutions:**
1. Verify certificate chain
2. Check signature validity
3. Ensure certificate format is correct

## Debugging Tips

### Enable Debug Logging
```python
from flare_ai_kit.config import AppSettings

settings = AppSettings(log_level="DEBUG")
```

### Check Exception Context
All exceptions include structured context information:
```python
try:
    # Your code here
    pass
except FlareAIKitError as e:
    print(f"Error: {e}")
    print(f"Error Code: {e.error_code}")
    print(f"Context: {e.context}")
```

### Logging Best Practices
- Use structured logging for better debugging
- Sensitive data is automatically masked
- Include relevant context in log messages

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [GitHub Issues](https://github.com/flare-foundation/flare-ai-kit/issues)
2. Review the [API Documentation](https://docs.flare.ai)
3. Join the [Flare Community Discord](https://discord.gg/flare)

## Error Code Reference

| Error Code | Exception Type | Description |
|------------|----------------|-------------|
| `WALLET_CREATION_FAILED` | WalletCreationError | Wallet creation failed |
| `WALLET_ACCOUNT_NOT_FOUND` | WalletNotFoundError | Wallet account not found |
| `WALLET_PERMISSION_DENIED` | WalletPermissionError | Permission denied |
| `FASSETS_ABI_RETRIEVAL_FAILED` | FAssetsContractError | ABI retrieval failed |
| `FASSETS_MINT_FAILED` | FAssetsMintError | Minting failed |
| `NETWORK_CONNECTION_FAILED` | ConnectionError | Network connection failed |
| `NETWORK_TIMEOUT` | TimeoutError | Network timeout |
| `HTTP_ERROR` | HTTPError | HTTP request failed |
| `VALIDATION_INVALID_INPUT` | InvalidInputError | Invalid input validation |
| `VALIDATION_INVALID_ADDRESS` | InvalidAddressError | Invalid address format |
| `VTPM_ATTESTATION_FAILED` | VtpmAttestationError | vTPM attestation failed |
| `VTPM_VALIDATION_FAILED` | VtpmValidationError | vTPM validation failed |
