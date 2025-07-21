import httpx
import pytest

from flare_ai_kit.common import AbiError
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.settings import EcosystemSettings

settings = EcosystemSettings()  # type: ignore[reportCallIssue]
# Example: FlareContractRegistry (known to have a verified ABI)
REAL_CONTRACT_ADDRESS = "0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019"
# Example: An unverified address
INVALID_CONTRACT_ADDRESS = "0x000000000000000000000000000000000000dEaD"


@pytest.mark.asyncio
async def test_get_contract_abi_real_success() -> None:
    """Fetch a known ABI from the real network (requires network)."""
    # Use async with for proper resource management in integration tests
    async with BlockExplorer(settings) as explorer:
        print(
            f"\nFetching real ABI for {REAL_CONTRACT_ADDRESS} from {settings.block_explorer_url}"
        )
        try:
            abi = await explorer.get_contract_abi(REAL_CONTRACT_ADDRESS)
            # Assertions
            assert isinstance(abi, list), "ABI should be a list"
            assert len(abi) > 0, "ABI list should not be empty for this known contract"
            assert any(item.get("type") == "function" for item in abi), (
                "ABI should contain function definitions"
            )

            print(
                f"Successfully fetched real ABI for {REAL_CONTRACT_ADDRESS} with {len(abi)} elements."
            )

        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            pytest.fail(
                f"Real ABI fetch for {REAL_CONTRACT_ADDRESS} failed unexpectedly: {type(e).__name__}: {e}"
            )
        except Exception as e:
            pytest.fail(
                f"An unexpected error occurred during real ABI fetch: {type(e).__name__}: {e}"
            )


@pytest.mark.asyncio
async def test_get_contract_abi_real_invalid_address() -> None:
    """
    Test fetching ABI for an address unlikely to have a verified contract.
    Expected behavior depends heavily on the specific block explorer API.
    Common outcomes are ValueError (parsing error msg in 'result'), or HTTPStatusError.
    """
    async with BlockExplorer(settings) as explorer:
        print(
            f"\nAttempting to fetch ABI for invalid address {INVALID_CONTRACT_ADDRESS} from {settings.block_explorer_url}..."
        )
        try:
            # Expecting an error because this address shouldn't have a verified ABI
            with pytest.raises((AbiError, httpx.HTTPStatusError)) as excinfo:
                await explorer.get_contract_abi(INVALID_CONTRACT_ADDRESS)

            print(
                f"Received expected error for invalid address: {type(excinfo.value).__name__}"
            )

        except Exception as e:
            # Fail if an unexpected exception type occurs
            pytest.fail(
                f"Fetching ABI for invalid address {INVALID_CONTRACT_ADDRESS} failed with unexpected error: {type(e).__name__}: {e}"
            )
