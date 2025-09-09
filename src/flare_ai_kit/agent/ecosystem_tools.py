"""
Wrapper for Flare ecosystem and social tools, adapted for the Google ADK.

This module provides a set of functions decorated as ADK tools. Each function
acts as a simple, clean wrapper around a method from the centralized FlareAIKit
SDK instance, ensuring efficient and consistent behavior.
"""

from eth_typing import ChecksumAddress
from httpx import HTTPStatusError, RequestError, TimeoutException
from web3.contract.async_contract import AsyncContractFunction
from web3.types import TxParams

from flare_ai_kit.agent.context import kit
from flare_ai_kit.agent.tools import adk_tool
from flare_ai_kit.common import AbiError, ExplorerError

# --- Flare Network ---


@adk_tool
async def check_balance(address: str) -> float:
    """Check FLR balance of a given address."""
    return await kit.flare.check_balance(address)


@adk_tool
async def check_connection() -> bool:
    """
    Check the connection status to the configured RPC endpoint.

    Returns:
        True if connected, False otherwise.

    """
    return await kit.flare.check_connection()


@adk_tool
async def build_transaction(
    function_call: AsyncContractFunction, from_addr: ChecksumAddress
) -> TxParams | None:
    """Builds a transaction with dynamic gas and nonce parameters."""
    return await kit.flare.build_transaction(function_call, from_addr)


@adk_tool
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
    return await kit.flare.sign_and_send_transaction(tx)


@adk_tool
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
    return await kit.flare.create_send_flr_tx(from_address, to_address, amount)


# --- FTSO ---


@adk_tool
async def get_ftso_latest_price(feed_name: str) -> float:
    """
    Retrieves the latest price for a single feed.

    Args:
        feed_name: The human-readable feed name (e.g., "BTC/USD").

    Returns:
        The latest price as a float, adjusted for decimals.

    """
    ftso_client = await kit.ftso
    return await ftso_client.get_latest_price(feed_name)


@adk_tool
async def get_ftso_latest_prices(feed_names: list[str]) -> list[float]:
    """
    Retrieves the latest prices for multiple feeds.

    Args:
        feed_names: A list of human-readable feed names.

    Returns:
        A list of prices as floats, corresponding to the order of `feed_names`.

    """
    ftso_client = await kit.ftso
    return await ftso_client.get_latest_prices(feed_names)


# --- Explorer ---


@adk_tool
async def get_contract_abi(contract_address: str) -> list[dict[str, str]]:
    """
    Asynchronously get the ABI for a contract from the Chain Explorer API.

    Args:
        contract_address: Address of the contract.

    Returns:
        list[dict]: Contract ABI parsed from the JSON string response.

    Raises:
        ValueError: If the ABI string is not valid JSON.
        ExplorerError: If the underlying API request fails.

    """
    try:
        async with kit.block_explorer as explorer:
            return await explorer.get_contract_abi(contract_address)
    except (HTTPStatusError, RequestError, TimeoutException) as e:
        msg = f"Failed to fetch contract ABI: {e}"
        raise ExplorerError(msg) from e
    except AbiError as e:
        msg = f"Invalid ABI response for contract {contract_address}: {e}"
        raise ValueError(msg) from e


# --- Social: X (Twitter) ---


@adk_tool
async def post_to_x(content: str) -> bool:
    """Posts a message to X (Twitter)."""
    if not kit.x_client.is_configured:
        msg = "XClient is not configured. Ensure API keys are set."
        raise ValueError(msg)
    return await kit.x_client.post_tweet(content)


# --- Social: Telegram ---


@adk_tool
async def send_telegram_message(chat_id: str, message: str) -> bool:
    """
    Sends a message to a Telegram chat.

    Args:
        chat_id: The unique identifier for the target chat.
        message: The text of the message to send.

    Returns:
        True if the message was sent successfully, False otherwise.

    """
    if not kit.telegram.is_configured:
        msg = "TelegramClient is not configured. Ensure API keys are set."
        raise ValueError(msg)
    return await kit.telegram.send_message(chat_id, message)
