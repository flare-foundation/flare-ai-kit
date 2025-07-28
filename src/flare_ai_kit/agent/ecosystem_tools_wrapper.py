from eth_typing import ChecksumAddress
from httpx import HTTPStatusError, RequestError, TimeoutException
from web3.contract.async_contract import AsyncContractFunction
from web3.types import TxParams

from flare_ai_kit.agent import adk
from flare_ai_kit.common import AbiError, ExplorerError

# --- Flare Network ---


@adk.tool
async def check_balance(address: str) -> float:
    """
    Check the balance of a given Flare address in FLR.
    """
    from flare_ai_kit.ecosystem.flare import Flare
    from flare_ai_kit.ecosystem.settings import EcosystemSettings

    settings = EcosystemSettings()
    flare = Flare(settings)
    return await flare.check_balance(address)


@adk.tool
async def check_connection() -> bool:
    """
    Check the connection status to the configured RPC endpoint.

    Returns:
        True if connected, False otherwise.

    """
    from flare_ai_kit.ecosystem.flare import Flare
    from flare_ai_kit.ecosystem.settings import EcosystemSettings

    settings = EcosystemSettings()
    flare = Flare(settings)
    return await flare.check_connection()


@adk.tool
async def build_transaction(
    function_call: AsyncContractFunction, from_addr: ChecksumAddress
) -> TxParams | None:
    """Builds a transaction with dynamic gas and nonce parameters."""
    from flare_ai_kit.ecosystem.flare import Flare
    from flare_ai_kit.ecosystem.settings import EcosystemSettings

    settings = EcosystemSettings()
    flare = Flare(settings)
    return await flare.build_transaction(function_call, from_addr)


@adk.tool
async def sign_and_send_transaction(tx: TxParams) -> str | None:
    """
    Sign and send a transaction to the network.

    Args:
        tx (TxParams): Transaction parameters to be sent

    Returns:
        str: Transaction hash of the sent transaction

    Raises:
        ValueError: If account is not initialized

    """
    from flare_ai_kit.ecosystem.flare import Flare
    from flare_ai_kit.ecosystem.settings import EcosystemSettings

    settings = EcosystemSettings()
    flare = Flare(settings)
    return await flare.sign_and_send_transaction(tx)


@adk.tool
async def create_send_flr_tx(
    from_address: str, to_address: str, amount: float
) -> TxParams:
    """
    Create a transaction to send FLR tokens.

    Args:
        from_address (str): Sender address
        to_address (str): Recipient address
        amount (float): Amount of FLR to send

    Returns:
        TxParams: Transaction parameters for sending FLR

    Raises:
        ValueError: If account does not exist

    """
    from flare_ai_kit.ecosystem.flare import Flare
    from flare_ai_kit.ecosystem.settings import EcosystemSettings

    settings = EcosystemSettings()
    flare = Flare(settings)
    return await flare.create_send_flr_tx(from_address, to_address, amount)


# --- FTSO Protocol ---


@adk.tool
async def get_ftso_latest_price(feed_name: str) -> float:
    """
    Retrieves the latest price for a single feed.

    Args:
        feed_name: The human-readable feed name (e.g., "BTC/USD").
        category: The feed category (default: CRYPTO i.e. "01").

    Returns:
        The latest price as a float, adjusted for decimals.
        Returns 0.0 if the price or decimals returned by the contract are zero,
        which might indicate an invalid or unprovided feed.

    Raises:
        FtsoV2Error: If the category is invalid, feed name cannot be converted
            or the contract call fails.

    """
    from flare_ai_kit.ecosystem.protocols.ftsov2 import FtsoV2
    from flare_ai_kit.ecosystem.settings import EcosystemSettings

    settings = EcosystemSettings()
    ftso = await FtsoV2.create(settings)
    if not ftso:
        raise ValueError("FtsoV2 instance not fully initialized. Use FtsoV2.create().")

    return await ftso.get_latest_price(feed_name)


@adk.tool
async def get_ftso_latest_prices(feed_names: list[str]) -> list[float]:
    """
    Retrieves the latest prices for multiple feeds within the same category.

    Args:
        feed_names: A list of human-readable feed names.
        category: The feed category for all requested feeds (default: "01").

    Returns:
        A list of prices as floats, corresponding to the order of `feed_names`.
        Individual prices will be 0.0 if the contract returned zero values.

    Raises:
        FtsoV2Error: If the category is invalid, feed name cannot be converted
            or the contract call fails.

    """
    from flare_ai_kit.ecosystem.protocols.ftsov2 import FtsoV2
    from flare_ai_kit.ecosystem.settings import EcosystemSettings

    settings = EcosystemSettings()
    ftso = await FtsoV2.create(settings)
    if not ftso:
        raise ValueError("FtsoV2 instance not fully initialized. Use FtsoV2.create().")

    return await ftso.get_latest_prices(feed_names)


# --- Explorer ---


@adk.tool
async def get_contract_abi(contract_address: str) -> list[dict[str, str]]:
    """
    Asynchronously get the ABI for a contract from the Chain Explorer API.

    Args:
        contract_address: Address of the contract.

    Returns:
        list[dict]: Contract ABI parsed from the JSON string response.

    Raises:
        ValueError: If the ABI string in the response is not valid JSON
                    or if the underlying API request fails.
        (Exceptions from _get): RequestError, TimeoutException, HTTPStatusError

    """
    from flare_ai_kit.ecosystem.explorer import BlockExplorer
    from flare_ai_kit.ecosystem.settings import EcosystemSettings

    settings = EcosystemSettings()
    explorer = BlockExplorer(settings)
    try:
        async with explorer:
            return await explorer.get_contract_abi(contract_address)
    except (HTTPStatusError, RequestError, TimeoutException) as e:
        raise ExplorerError(f"Failed to fetch contract ABI: {e}")
    except AbiError as e:
        raise ValueError(f"Invalid ABI response for contract {contract_address}: {e}")


# --- Social: X (Twitter) ---


@adk.tool
async def post_to_x(content: str) -> bool:
    """Posts a message to X (Twitter)."""
    from flare_ai_kit.social.settings import SocialSettings
    from flare_ai_kit.social.x import XClient

    settings = SocialSettings() # type: ignore[call-arg]
    x_client = XClient(settings)
    if not x_client.is_configured:
        raise ValueError(
            "XClient is not configured. Ensure API keys are set in the environment."
        )

    return await x_client.post_tweet(content)


# --- Social: Telegram ---


@adk.tool
async def send_telegram_message(chat_id: str, message: str) -> bool:
    """
    Sends a message to a Telegram chat.

    This is an asynchronous operation.

    Args:
        chat_id: The unique identifier for the target chat
            (e.g., '@channelname' or a user ID).
        text: The text of the message to send.

    Returns:
        True if the message was sent successfully, False otherwise.

    """
    from flare_ai_kit.social.settings import SocialSettings
    from flare_ai_kit.social.telegram import TelegramClient

    settings = SocialSettings() # type: ignore[call-arg]
    telegram_client = TelegramClient(settings)
    if not telegram_client.is_configured:
        raise ValueError(
            "TelegramClient is not configured. Ensure API token is set in the environment."
        )

    return await telegram_client.send_message(chat_id, message)
