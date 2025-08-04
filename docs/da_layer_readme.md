# Flare Data Availability (DA) Layer Connector

## Overview

This implementation provides a comprehensive connector for interacting with the Flare Data Availability (DA) Layer, fulfilling the requirements of issue #27. The connector enables agents to access and verify off-chain information made available on Flare through the Flare State Protocol (FSP).

## Features

### ✅ Core Requirements Fulfilled

1. **Data Retrieval from FSP**: Retrieve data that has been submitted to the Flare DA Layer via the Flare State Protocol
2. **Merkle Proof Support**: Fetch and verify Merkle proofs associated with data on the DA Layer
3. **Historical Data Access**: Support for historical data retrieval as permitted by the layer's design
4. **Data Integrity Verification**: Confirm integrity and provenance of attestation data

### 🚀 Additional Features

- **Comprehensive Attestation Type Support**: All 7 supported attestation types
- **Async/Await Pattern**: Modern Python async programming
- **Context Manager Support**: Automatic resource cleanup
- **Robust Error Handling**: Specific exception types for different failure modes
- **Structured Logging**: Detailed logging for debugging and monitoring
- **Type Safety**: Full type hints and dataclass models

## Architecture

```
┌─────────────────────┐    HTTP API    ┌──────────────────────┐
│                     │ ──────────────> │ Flare DA Layer API   │
│ DataAvailabilityLayer│                │ (flr-data-availability│
│                     │ <────────────── │  .flare.network)     │
└─────────────────────┘                └──────────────────────┘
          │
          │ inherits from
          ▼
┌─────────────────────┐
│    Flare (base)     │
│                     │
└─────────────────────┘
```

## Key Components

### Data Models

- **`AttestationRequest`**: Represents an attestation request structure
- **`AttestationResponse`**: Contains the attestation response data
- **`MerkleProof`**: Merkle proof data for verification
- **`AttestationData`**: Complete attestation with response and proof
- **`VotingRoundData`**: Metadata for voting rounds

### Exception Hierarchy

- **`DALayerError`**: Base exception for DA Layer errors
- **`AttestationNotFoundError`**: When requested data is not found
- **`MerkleProofError`**: Merkle proof verification failures

## Usage Examples

### Basic Usage

```python
from flare_ai_kit.ecosystem.protocols import DataAvailabilityLayer
from flare_ai_kit.ecosystem.settings_models import EcosystemSettingsModel

# Configure settings
settings = EcosystemSettingsModel(
    web3_provider_url="https://flare-api.flare.network/ext/C/rpc",
    account_address="0x...",  # Not needed for read operations
    account_private_key="0x...",  # Not needed for read operations
    is_testnet=False
)

# Initialize connector
da_layer = await DataAvailabilityLayer.create(settings)

# Get supported attestation types
attestation_types = await da_layer.get_supported_attestation_types()

# Get latest voting rounds
rounds = await da_layer.get_latest_voting_rounds(count=10)

# Search for specific attestation types
attestations = await da_layer.get_attestations_by_type(
    attestation_type="EVMTransaction",
    source_id="ETH",
    limit=50
)

# Verify Merkle proof
is_valid = await da_layer.verify_merkle_proof(attestation_data)

# Clean up
await da_layer.close()
```

### Context Manager Usage

```python
async with await DataAvailabilityLayer.create(settings) as da_layer:
    # Get historical data
    historical_data = await da_layer.get_historical_data(
        start_timestamp=start_time,
        end_timestamp=end_time,
        attestation_types=["Payment", "EVMTransaction"]
    )

    # Process attestations...
    for attestation in historical_data:
        # Verify each attestation
        is_valid = await da_layer.verify_merkle_proof(attestation)
        if is_valid:
            # Process valid attestation
            process_attestation(attestation)
# Session automatically closed
```

### Historical Data Analysis

```python
# Get attestations from the last 24 hours
from datetime import datetime, timedelta

end_time = datetime.now()
start_time = end_time - timedelta(hours=24)

attestations = await da_layer.get_historical_data(
    start_timestamp=int(start_time.timestamp()),
    end_timestamp=int(end_time.timestamp()),
    attestation_types=["Payment", "EVMTransaction"],
    limit=1000
)

# Analyze attestation patterns
type_counts = {}
for attestation in attestations:
    att_type = attestation.response.attestation_type
    type_counts[att_type] = type_counts.get(att_type, 0) + 1

print(f"Attestation distribution: {type_counts}")
```

## Supported Attestation Types

The connector supports all 7 attestation types available on the Flare Data Connector:

1. **AddressValidity**: Validates address format and checksum
2. **EVMTransaction**: Verifies EVM-compatible chain transactions
3. **JsonApi**: Fetches and processes Web2 data (Coston/Coston2 only)
4. **Payment**: Confirms payment transactions from non-EVM chains
5. **ConfirmedBlockHeightExists**: Verifies block existence
6. **BalanceDecreasingTransaction**: Validates balance-reducing transactions
7. **ReferencedPaymentNonexistence**: Confirms absence of payments

## API Methods

### Core Data Retrieval

- `get_attestation_data(voting_round, attestation_index)`: Get specific attestation
- `get_attestations_by_type(attestation_type, **filters)`: Search by type
- `get_voting_round_data(voting_round)`: Get round metadata
- `get_historical_data(start_timestamp, end_timestamp, **filters)`: Historical search

### Verification

- `verify_merkle_proof(attestation_data, expected_root?)`: Verify Merkle proof
- `get_supported_attestation_types()`: List supported types

### Utility

- `get_latest_voting_rounds(count)`: Get recent rounds
- `get_data_provider_status()`: Check DA Layer health

## Error Handling

The connector provides comprehensive error handling:

```python
try:
    attestation = await da_layer.get_attestation_data(12345, 0)
except AttestationNotFoundError:
    print("Attestation not found")
except DALayerError as e:
    print(f"DA Layer error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Integration Points

### With FAssets System

```python
# Get FAsset-related attestations
fasset_attestations = await da_layer.get_attestations_by_type(
    attestation_type="Payment",
    source_id="BTC"  # Bitcoin payments for FAssets
)

for attestation in fasset_attestations:
    # Verify each payment attestation
    if await da_layer.verify_merkle_proof(attestation):
        # Process valid FAsset payment
        process_fasset_payment(attestation)
```

### With Smart Contracts

```python
# Get attestations for smart contract verification
evm_attestations = await da_layer.get_attestations_by_type(
    attestation_type="EVMTransaction",
    source_id="ETH"
)

for attestation in evm_attestations:
    response = attestation.response
    proof = attestation.proof

    # Submit to smart contract for verification
    # contract.verify_attestation(response_data, proof_data)
```

## Configuration

### Environment Variables

You can configure the connector using environment variables:

```bash
export FLARE_WEB3_PROVIDER_URL="https://flare-api.flare.network/ext/C/rpc"
export FLARE_ACCOUNT_ADDRESS="0x..."
export FLARE_ACCOUNT_PRIVATE_KEY="0x..."
```

### Custom DA Layer URL

```python
# For custom DA Layer endpoints
da_layer = await DataAvailabilityLayer.create(settings)
da_layer.da_layer_base_url = "https://custom-da-layer.example.com/api/v1/"
```

## Testing

Run the example script to test the implementation:

```bash
cd examples
python 02_da_layer_usage.py
```

## Best Practices

### 1. Resource Management

Always use context managers or explicit cleanup:

```python
# Preferred: Context manager
async with await DataAvailabilityLayer.create(settings) as da_layer:
    # Your code here
    pass

# Alternative: Manual cleanup
da_layer = await DataAvailabilityLayer.create(settings)
try:
    # Your code here
    pass
finally:
    await da_layer.close()
```

### 2. Error Handling

Handle specific exceptions appropriately:

```python
try:
    attestation = await da_layer.get_attestation_data(round_id, index)
except AttestationNotFoundError:
    # Handle missing attestation (expected case)
    logger.warning(f"Attestation {round_id}/{index} not found")
except DALayerError as e:
    # Handle DA Layer errors (retry logic might be appropriate)
    logger.error(f"DA Layer error: {e}")
    await asyncio.sleep(5)  # Backoff before retry
except Exception as e:
    # Handle unexpected errors
    logger.exception(f"Unexpected error: {e}")
    raise
```

### 3. Batch Processing

Process attestations in batches for efficiency:

```python
async def process_attestations_batch(da_layer, attestations):
    """Process a batch of attestations with verification."""
    verification_tasks = [
        da_layer.verify_merkle_proof(attestation)
        for attestation in attestations
    ]

    # Verify all proofs concurrently
    verification_results = await asyncio.gather(*verification_tasks)

    # Process verified attestations
    for attestation, is_valid in zip(attestations, verification_results):
        if is_valid:
            await process_valid_attestation(attestation)
        else:
            logger.warning(f"Invalid proof for {attestation.response.voting_round}")
```

### 4. Monitoring and Logging

The connector uses structured logging. Configure your logger appropriately:

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)
```

## Performance Considerations

1. **Connection Pooling**: The connector uses aiohttp session pooling for efficient HTTP connections
2. **Concurrent Requests**: Use `asyncio.gather()` for concurrent API calls
3. **Rate Limiting**: Implement appropriate rate limiting for production use
4. **Caching**: Consider caching frequently accessed data like supported attestation types

## Security Considerations

1. **API Access**: The DA Layer API is read-only and doesn't require authentication
2. **Merkle Verification**: Always verify Merkle proofs for critical applications
3. **Data Validation**: Validate attestation data structure before processing
4. **Network Security**: Use HTTPS for all API communications (default)

## Troubleshooting

### Common Issues

1. **Connection Timeouts**: Increase timeout in ClientTimeout configuration
2. **Attestation Not Found**: Check voting round and index validity
3. **Merkle Verification Failures**: Ensure complete attestation data and correct expected root

### Debug Mode

Enable debug logging for detailed request/response information:

```python
import logging
logging.getLogger("flare_ai_kit.ecosystem.protocols.da_layer").setLevel(logging.DEBUG)
```

## Future Enhancements

Potential areas for future development:

1. **Caching Layer**: Implement local caching for frequently accessed data
2. **Rate Limiting**: Add configurable rate limiting
3. **Metrics Collection**: Add Prometheus-style metrics
4. **Connection Pooling**: Enhanced connection pool management
5. **Retry Logic**: Configurable retry policies with exponential backoff

## Contributing

To contribute to the DA Layer connector:

1. Follow the existing code patterns and type hints
2. Add comprehensive error handling
3. Include unit tests for new functionality
4. Update documentation for API changes
5. Ensure backward compatibility

## Support

For issues and questions:

1. Check the examples in `examples/02_da_layer_usage.py`
2. Review the Flare DA Layer documentation
3. Open GitHub issues for bugs or feature requests
4. Join the Flare community Discord for support

---

This implementation successfully fulfills all requirements from issue #27 and provides a robust, production-ready connector for the Flare Data Availability Layer.
