"""ADK tool wrappers for Flare ecosystem components."""

import structlog

from typing import Any
from flare_ai_kit.agent.tool import tool
from flare_ai_kit.common import FtsoFeedCategory
from flare_ai_kit.ecosystem import BlockExplorer, Flare, FtsoV2
from flare_ai_kit.ecosystem.settings import EcosystemSettings

logger = structlog.get_logger(__name__)


@tool
async def get_ftso_price(
    feed_name: str, category: str = "01"
) -> dict[str, float | str]:
    """
    Get the latest price from Flare Time Series Oracle V2 (FTSOv2).
    
    Args:
        feed_name: The trading pair name (e.g., "BTC/USD", "ETH/USD", "FLR/USD")
        category: Feed category - "01" for crypto (default), "02" for forex, \
"03" for commodities
    
    Returns:
        Dictionary containing the price and feed information

    """
    logger.info("Fetching FTSO price", feed_name=feed_name, category=category)

    try:
        settings = EcosystemSettings()
        ftso = await FtsoV2.create(settings)
        # Convert category string to enum
        if category == "01":
            cat_enum = FtsoFeedCategory.CRYPTO
        elif category == "02":
            cat_enum = FtsoFeedCategory.FOREX
        elif category == "03":
            cat_enum = FtsoFeedCategory.COMMODITY
        elif category == "04":
            cat_enum = FtsoFeedCategory.STOCK
        elif category == "05":
            cat_enum = FtsoFeedCategory.CUSTOMFEED
        else:
            cat_enum = FtsoFeedCategory.CUSTOMFEED

        price = await ftso.get_latest_price(feed_name, cat_enum)

        return {
            "feed_name": feed_name,
            "category": category,
            "price": price,
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to fetch FTSO price", error=str(e))
        return {
            "feed_name": feed_name,
            "category": category,
            "price": 0.0,
            "status": "error",
            "error": str(e),
        }


@tool
async def get_multiple_ftso_prices(
    feed_names: list[str], category: str = "01"
) -> dict[str, list[float] | list[str] | str]:
    """
    Get latest prices for multiple feeds from FTSOv2.
    
    Args:
        feed_names: List of trading pair names (e.g., ["BTC/USD", "ETH/USD", "FLR/USD"])
        category: Feed category - "01" for crypto (default), "02" for forex, \
"03" for commodities
    
    Returns:
        Dictionary containing the prices and feed information

    """
    logger.info(
        "Fetching multiple FTSO prices", feed_names=feed_names, category=category
    )

    settings = EcosystemSettings()
    ftso = await FtsoV2.create(settings)

    try:
        # Convert category string to enum
        if category == "01":
            cat_enum = FtsoFeedCategory.CRYPTO
        elif category == "02":
            cat_enum = FtsoFeedCategory.FOREX
        elif category == "03":
            cat_enum = FtsoFeedCategory.COMMODITY
        elif category == "04":
            cat_enum = FtsoFeedCategory.STOCK
        elif category == "05":
            cat_enum = FtsoFeedCategory.CUSTOMFEED
        else:
            cat_enum = FtsoFeedCategory.CUSTOMFEED

        prices = await ftso.get_latest_prices(feed_names, cat_enum)

        return {
            "feed_names": feed_names,
            "category": category,
            "prices": prices,
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to fetch multiple FTSO prices", error=str(e))
        return {
            "feed_names": feed_names,
            "category": category,
            "prices": [],
            "status": "error",
            "error": str(e),
        }


@tool
async def check_flr_balance(address: str) -> dict[str, float | str]:
    """
    Check the FLR token balance for a given address.

    Args:
        address: The wallet address to check balance for

    Returns:
        Dictionary containing the balance and address information

    """
    logger.info("Checking FLR balance", address=address)

    settings = EcosystemSettings()
    flare = Flare(settings)

    try:
        balance = await flare.check_balance(address)

        return {
            "address": address,
            "balance": balance,
            "currency": "FLR",
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to check FLR balance", error=str(e))
        return {
            "address": address,
            "balance": 0.0,
            "currency": "FLR",
            "status": "error",
            "error": str(e),
        }


@tool
async def get_contract_abi(contract_address: str) -> dict[str, Any]:
    """
    Retrieve the ABI (Application Binary Interface) for a contract from the block explorer.

    Args:
        contract_address: The contract address to fetch ABI for

    Returns:
        Dictionary containing the contract ABI and address information

    """
    logger.info("Fetching contract ABI", contract_address=contract_address)

    settings = EcosystemSettings()

    try:
        async with BlockExplorer(settings) as explorer:
            abi = await explorer.get_contract_abi(contract_address)

            return {
                "contract_address": contract_address,
                "abi": abi,
                "status": "success",
            }
    except Exception as e:
        logger.error("Failed to fetch contract ABI", error=str(e))
        return {
            "contract_address": contract_address,
            "abi": [],
            "status": "error",
            "error": str(e),
        }


@tool
async def get_protocol_contract_address(contract_name: str) -> dict[str, str]:
    """
    Get the address of a protocol contract from the Flare Contract Registry.

    Args:
        contract_name: Name of the contract (e.g., "FtsoV2", "FtsoManager", "FlareSystemsManager")

    Returns:
        Dictionary containing the contract address and name

    """
    logger.info("Fetching protocol contract address", contract_name=contract_name)

    settings = EcosystemSettings()
    flare = Flare(settings)

    try:
        address = await flare.get_protocol_contract_address(contract_name)

        return {"contract_name": contract_name, "address": address, "status": "success"}
    except Exception as e:
        logger.error("Failed to fetch protocol contract address", error=str(e))
        return {
            "contract_name": contract_name,
            "address": "",
            "status": "error",
            "error": str(e),
        }


@tool
async def check_flare_connection() -> dict[str, bool | str]:
    """
    Check if connection to Flare network is working.

    Returns:
        Dictionary containing connection status and network information

    """
    logger.info("Checking Flare network connection")

    settings = EcosystemSettings()
    flare = Flare(settings)

    try:
        is_connected = await flare.check_connection()

        return {
            "connected": is_connected,
            "network": "Flare" if not settings.is_testnet else "Flare Testnet",
            "provider_url": str(settings.web3_provider_url),
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to check Flare connection", error=str(e))
        return {
            "connected": False,
            "network": "Unknown",
            "provider_url": str(settings.web3_provider_url),
            "status": "error",
            "error": str(e),
        }
