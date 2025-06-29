#!/usr/bin/env python3
"""
Example demonstrating the usage of Flare Data Availability (DA) Layer connector.

This script shows how to:
1. Connect to the Flare DA Layer
2. Retrieve attestation data by voting round and index
3. Search for attestations by type
4. Verify Merkle proofs
5. Query historical data
6. Get supported attestation types

Requirements:
- Install flare-ai-kit: pip install flare-ai-kit
- Configure environment variables or update the settings below
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from flare_ai_kit.ecosystem.protocols import (
    AttestationData,
    AttestationNotFoundError,
    DALayerError,
    DataAvailabilityLayer,
    MerkleProofError,
)
from flare_ai_kit.ecosystem.settings_models import EcosystemSettingsModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_da_layer_basic_usage() -> None:
    """Demonstrate basic DA Layer connectivity and data retrieval."""
    print("=" * 80)
    print("Flare Data Availability Layer - Basic Usage Example")
    print("=" * 80)

    # Configure settings for Flare mainnet
    # Note: For this example, we only need minimal settings since DA Layer is read-only
    settings = EcosystemSettingsModel(
        web3_provider_url="https://flare-api.flare.network/ext/C/rpc",
        account_address="0x0000000000000000000000000000000000000000",  # Placeholder
        account_private_key="0x" + "0" * 64,  # Placeholder - not needed for read operations
        is_testnet=False
    )

    # Initialize DA Layer connector
    try:
        da_layer = await DataAvailabilityLayer.create(settings)
        print("✅ Successfully connected to Flare Data Availability Layer")

        # Get supported attestation types
        await demonstrate_supported_attestation_types(da_layer)

        # Get latest voting rounds information
        await demonstrate_voting_rounds(da_layer)

        # Search for specific attestation types
        await demonstrate_attestation_search(da_layer)

        # Demonstrate historical data retrieval
        await demonstrate_historical_data(da_layer)

        # Clean up
        await da_layer.close()
        print("\n✅ DA Layer connection closed successfully")

    except DALayerError as e:
        print(f"❌ DA Layer error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


async def demonstrate_supported_attestation_types(da_layer: DataAvailabilityLayer):
    """Show supported attestation types."""
    print("\n" + "=" * 60)
    print("📋 Supported Attestation Types")
    print("=" * 60)

    try:
        attestation_types = await da_layer.get_supported_attestation_types()

        print(f"Found {len(attestation_types)} supported attestation types:")
        for i, att_type in enumerate(attestation_types, 1):
            name = att_type.get("name", "Unknown")
            description = att_type.get("description", "No description available")
            print(f"{i:2d}. {name}")
            print(f"     Description: {description}")

            # Show supported source chains if available
            sources = att_type.get("supportedSources", [])
            if sources:
                print(f"     Supported sources: {', '.join(sources)}")
            print()

    except Exception as e:
        print(f"❌ Failed to retrieve attestation types: {e}")


async def demonstrate_voting_rounds(da_layer: DataAvailabilityLayer):
    """Show recent voting rounds information."""
    print("\n" + "=" * 60)
    print("🗳️  Recent Voting Rounds")
    print("=" * 60)

    try:
        # Get information for recent voting rounds (sample from recent rounds)
        # Since we don't have a direct get_latest_voting_rounds method,
        # we'll try to get data for the last few voting rounds
        current_round = 12000  # Approximate recent round number
        rounds = []
        for round_num in range(current_round - 4, current_round + 1):
            try:
                round_data = await da_layer.get_voting_round_data(round_num)
                rounds.append(round_data)
            except Exception:
                continue  # Skip rounds that don't exist

        print(f"Latest {len(rounds)} voting rounds:")
        print(f"{'Round':>8} {'Finalized':>10} {'Attestations':>12} {'Timestamp':>20}")
        print("-" * 60)

        for round_data in rounds:
            timestamp = datetime.fromtimestamp(round_data.timestamp, tz=timezone.utc)
            finalized = "✅ Yes" if round_data.finalized else "⏳ No"

            print(f"{round_data.voting_round:>8d} {finalized:>10} "
                  f"{round_data.total_attestations:>12d} {timestamp.strftime('%Y-%m-%d %H:%M'):>20}")

        # Try to get detailed data for the latest finalized round
        if rounds and rounds[0].finalized:
            await demonstrate_round_details(da_layer, rounds[0].voting_round)

    except Exception as e:
        print(f"❌ Failed to retrieve voting rounds: {e}")


async def demonstrate_round_details(da_layer: DataAvailabilityLayer, voting_round: int):
    """Show detailed information for a specific round."""
    print(f"\n📊 Detailed information for voting round {voting_round}:")

    try:
        round_data = await da_layer.get_voting_round_data(voting_round)

        print(f"  Voting Round: {round_data.voting_round}")
        print(f"  Merkle Root: {round_data.merkle_root}")
        print(f"  Timestamp: {datetime.fromtimestamp(round_data.timestamp, tz=timezone.utc)}")
        print(f"  Total Attestations: {round_data.total_attestations}")
        print(f"  Finalized: {'Yes' if round_data.finalized else 'No'}")

        # Try to get the first few attestations from this round
        if round_data.total_attestations > 0:
            print("\n  First few attestations:")
            for i in range(min(3, round_data.total_attestations)):
                try:
                    attestation = await da_layer.get_attestation_data(voting_round, i)
                    print(f"    [{i}] Type: {attestation.response.attestation_type}, "
                          f"Source: {attestation.response.source_id}")
                except AttestationNotFoundError:
                    print(f"    [{i}] Attestation not found")
                except Exception as e:
                    print(f"    [{i}] Error: {e}")

    except Exception as e:
        print(f"❌ Failed to get round details: {e}")


async def demonstrate_attestation_search(da_layer: DataAvailabilityLayer):
    """Search for specific types of attestations."""
    print("\n" + "=" * 60)
    print("🔍 Attestation Search Examples")
    print("=" * 60)

    # Common attestation types to search for
    search_types = ["EVMTransaction", "Payment", "AddressValidity"]

    for attestation_type in search_types:
        try:
            print(f"\n🔎 Searching for {attestation_type} attestations...")

            attestations = await da_layer.get_attestations_by_type(
                attestation_type=attestation_type,
                limit=5  # Limit to 5 results for the example
            )

            print(f"Found {len(attestations)} {attestation_type} attestations:")

            for i, attestation in enumerate(attestations, 1):
                resp = attestation.response
                print(f"  {i}. Round {resp.voting_round}, Source: {resp.source_id}")

                # Show some details from the response body if available
                if resp.response_body:
                    # Try to show relevant fields based on attestation type
                    if attestation_type == "EVMTransaction":
                        tx_hash = resp.response_body.get("transactionHash", "N/A")
                        block_num = resp.response_body.get("blockNumber", "N/A")
                        print(f"     Transaction: {tx_hash}, Block: {block_num}")
                    elif attestation_type == "Payment":
                        amount = resp.response_body.get("amount", "N/A")
                        print(f"     Amount: {amount}")

                # Demonstrate Merkle proof verification for the first attestation
                if i == 1:
                    await demonstrate_merkle_verification(da_layer, attestation)

        except Exception as e:
            print(f"❌ Failed to search {attestation_type}: {e}")


async def demonstrate_merkle_verification(da_layer: DataAvailabilityLayer, attestation: AttestationData):
    """Demonstrate Merkle proof verification."""
    print(f"\n🔐 Verifying Merkle proof for attestation in round {attestation.response.voting_round}...")

    try:
        is_valid = await da_layer.verify_merkle_proof(attestation)

        if is_valid:
            print("  ✅ Merkle proof verification: VALID")
            print(f"     Leaf index: {attestation.proof.leaf_index}")
            print(f"     Total leaves: {attestation.proof.total_leaves}")
            print(f"     Proof elements: {len(attestation.proof.merkle_proof)}")
        else:
            print("  ❌ Merkle proof verification: INVALID")

    except MerkleProofError as e:
        print(f"  ❌ Merkle proof verification failed: {e}")
    except Exception as e:
        print(f"  ❌ Unexpected error during verification: {e}")


async def demonstrate_historical_data(da_layer: DataAvailabilityLayer):
    """Demonstrate historical data retrieval."""
    print("\n" + "=" * 60)
    print("📚 Historical Data Retrieval")
    print("=" * 60)

    try:
        # Get data from the last 24 hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        print(f"🕐 Retrieving attestations from {start_time.strftime('%Y-%m-%d %H:%M')} "
              f"to {end_time.strftime('%Y-%m-%d %H:%M')}")

        historical_data = await da_layer.get_historical_data(
            start_timestamp=int(start_time.timestamp()),
            end_timestamp=int(end_time.timestamp()),
            attestation_types=["EVMTransaction", "Payment"],  # Filter for specific types
            limit=10  # Limit results for the example
        )

        print(f"Found {len(historical_data)} historical attestations:")

        # Group by attestation type
        type_counts = {}
        for attestation in historical_data:
            att_type = attestation.response.attestation_type
            type_counts[att_type] = type_counts.get(att_type, 0) + 1

        for att_type, count in type_counts.items():
            print(f"  📊 {att_type}: {count} attestations")

        # Show details of first few attestations
        if historical_data:
            print("\nFirst few attestations:")
            for i, attestation in enumerate(historical_data[:3], 1):
                resp = attestation.response
                timestamp = datetime.fromtimestamp(resp.lowest_used_timestamp)
                print(f"  {i}. [{resp.attestation_type}] Round {resp.voting_round}, "
                      f"Time: {timestamp.strftime('%H:%M:%S')}")

    except Exception as e:
        print(f"❌ Failed to retrieve historical data: {e}")


async def demonstrate_advanced_usage():
    """Demonstrate advanced DA Layer usage patterns."""
    print("\n" + "=" * 80)
    print("🚀 Advanced Usage Patterns")
    print("=" * 80)

    settings = EcosystemSettingsModel(
        web3_provider_url="https://flare-api.flare.network/ext/C/rpc",
        account_address="0x0000000000000000000000000000000000000000",
        account_private_key="0x" + "0" * 64,
        is_testnet=False
    )

    # Demonstrate context manager usage
    print("📁 Using DA Layer with context manager:")

    try:
        async with await DataAvailabilityLayer.create(settings) as da_layer:
            # Context manager automatically handles session cleanup

            # Get attestations for a specific source
            print("🎯 Searching for Ethereum mainnet attestations...")
            eth_attestations = await da_layer.get_attestations_by_type(
                attestation_type="EVMTransaction",
                source_id="ETH",  # Ethereum mainnet
                limit=3
            )

            print(f"Found {len(eth_attestations)} Ethereum attestations")

            for i, attestation in enumerate(eth_attestations, 1):
                resp = attestation.response
                print(f"  {i}. Round {resp.voting_round}")

                # Extract transaction details if available
                if "transactionHash" in resp.response_body:
                    tx_hash = resp.response_body["transactionHash"]
                    print(f"     Transaction Hash: {tx_hash}")

        print("✅ Context manager automatically closed the session")

    except Exception as e:
        print(f"❌ Advanced usage example failed: {e}")


async def main():
    """Main function to run all examples."""
    print("🌟 Flare Data Availability Layer Connector Examples")
    print("This script demonstrates comprehensive usage of the DA Layer API")

    try:
        # Run basic usage examples
        await demonstrate_da_layer_basic_usage()

        # Run advanced usage examples
        await demonstrate_advanced_usage()

        print("\n" + "=" * 80)
        print("🎉 All examples completed successfully!")
        print("=" * 80)
        print("Next steps:")
        print("- Integrate DA Layer into your Flare applications")
        print("- Use attestation data for cross-chain verification")
        print("- Build applications that leverage Merkle proof verification")
        print("- Explore historical data for analytics and insights")

    except KeyboardInterrupt:
        print("\n⛔ Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Examples failed with error: {e}")
        raise


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
