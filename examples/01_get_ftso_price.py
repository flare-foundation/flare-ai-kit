import asyncio

from flare_ai_kit import FlareAIKit


async def main() -> None:
    """
    Fetching prices from the FTSOv2 oracle.

    For a full list of feeds: https://dev.flare.network/ftso/feeds
    """
    # Initialize the Flare AI Kit with default settings
    kit = FlareAIKit(None)

    # Get the latest price for FLR/USD from the FTSOv2 oracle
    try:
        ftso = await kit.ftso
        price = await ftso.get_latest_price("FLR/USD")
        print(f"Latest FLR/USD price: {price}")
    except Exception as e:
        print(f"Error fetching price: {e}")

    # Get the latest price for BTC/USD, ETH/USD and SOL/USD from the FTSOv2 oracle
    try:
        ftso = await kit.ftso
        prices = await ftso.get_latest_prices(["BTC/USD", "ETH/USD", "SOL/USD"])
        print(f"Latest BTC/USD price: {prices[0]}")
        print(f"Latest ETH/USD price: {prices[1]}")
        print(f"Latest SOL/USD price: {prices[2]}")
    except Exception as e:
        print(f"Error fetching price: {e}")


if __name__ == "__main__":
    asyncio.run(main())
