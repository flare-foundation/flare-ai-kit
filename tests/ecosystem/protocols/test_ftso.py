import pytest
from web3 import Web3  # Import Web3 itself for type checking if needed

from flare_ai_kit.common.exceptions import FtsoV2Error
from flare_ai_kit.ecosystem.protocols.ftsov2 import FtsoV2

RPC_URL = "https://stylish-light-theorem.flare-mainnet.quiknode.pro/ext/bc/C/rpc"


@pytest.fixture(scope="module")
def ftso_instance() -> FtsoV2:
    """Provides a real instance of FtsoV2 connected to the network."""
    print(f"Attempting to connect FtsoV2 instance using RPC: {RPC_URL}")
    try:
        instance = FtsoV2(web3_provider_url=RPC_URL)
        assert instance.w3.is_connected()
    except Exception as e:
        pytest.fail(
            f"Failed to initialize FtsoV2 instance or connect to Flare network: {e}"
        )
    else:
        return instance


@pytest.mark.parametrize(
    ("feed_name", "category", "expected_id"),
    [
        ("BTC/USD", "01", "014254432f55534400000000000000000000000000"),
        ("ETH/USD", "01", "014554482f55534400000000000000000000000000"),
        ("FLR/USD", "01", "01464c522f55534400000000000000000000000000"),
    ],
)
def test_feed_name_to_id_static(
    feed_name: str, category: str, expected_id: str
) -> None:
    """Test the static method _feed_name_to_id (no network required)."""
    assert FtsoV2._feed_name_to_id(feed_name, category) == f"0x{expected_id}"


def test_ftso_v2_real_initialization(ftso_instance: FtsoV2) -> None:
    """Verify the real FtsoV2 instance initializes and connects."""
    assert ftso_instance is not None
    assert isinstance(ftso_instance.w3, Web3)
    assert ftso_instance.w3.is_connected(), "web3 instance should be connected"
    assert ftso_instance.ftsov2 is not None, (
        "FtsoV2 contract object should be initialized"
    )
    # Check if the address looks like a valid address (basic check)
    assert Web3.is_address(ftso_instance.ftsov2.address)
    print(
        f"Successfully initialized FtsoV2 contract at address: {ftso_instance.ftsov2.address}"
    )


@pytest.mark.parametrize(
    ("feed_name", "category"),
    [
        ("FLR/USD", "01"),
        ("BTC/USD", "01"),
        ("ETH/USD", "01"),
    ],
)
def test_get_latest_price_real_valid_feeds(
    ftso_instance: FtsoV2, feed_name: str, category: str
) -> None:
    """
    Test fetching the latest price for known valid feeds.
    Asserts type and plausibility, not exact value.
    """
    print(f"Fetching latest price for {feed_name} (Category: {category})...")
    try:
        price = ftso_instance.get_latest_price(feed_name, category)
        print(f"Received price for {feed_name}: {price}")

        assert isinstance(price, float), f"Price for {feed_name} should be a float"
        assert price > 0, (
            f"Price for {feed_name} should be positive (received: {price})"
        )
        # Add more specific range checks if appropriate for the asset, e.g.,
        # if feed_name == "FLR/USD":
        #    assert 0.001 < price < 10.0 # Very broad check for FLR

    except Exception as e:
        pytest.fail(f"Fetching price for {feed_name} failed with error: {e}")


def test_get_feed_by_id_real_structure(ftso_instance: FtsoV2) -> None:
    """
    Test the internal _get_feed_by_id method for return structure and types.
    Uses a known valid feed ID.
    """
    # Example using FLR/USD feed ID
    feed_id = FtsoV2._feed_name_to_id("FLR/USD", "01")
    print(f"Querying _get_feed_by_id for feed ID: {feed_id}")

    try:
        # Note: Calling internal method directly for test purposes
        feeds, decimals, timestamp = ftso_instance._get_feed_by_id(feed_id)
        print(
            f"Received feed data: Feeds={feeds}, Decimals={decimals}, Timestamp={timestamp}"
        )

        assert isinstance(feeds, int), "Feeds value should be an integer"
        assert isinstance(decimals, int), "Decimals value should be an integer"
        assert isinstance(timestamp, int), "Timestamp value should be an integer"

        assert feeds >= 0, "Feeds value should be non-negative"
        assert 0 <= decimals <= 18, (
            "Decimals value typically between 0 and 18"
        )  # FTSO usually uses <= 18
        # Check if timestamp looks somewhat reasonable (e.g., not in the distant past/future)
        # This requires knowing the current time, which might be tricky in CI
        # A simple check is just ensuring it's positive
        assert timestamp > 1600000000, (
            "Timestamp should be a plausible Unix timestamp"
        )  # After ~Sept 2020

    except Exception as e:
        pytest.fail(f"Calling _get_feed_by_id for {feed_id} failed with error: {e}")


def test_get_latest_price_real_invalid_feed(ftso_instance: FtsoV2) -> None:
    """Test behavior when requesting a likely non-existent feed."""
    invalid_feed_name = "NONEXISTENT/XYZ"
    invalid_category = "99"
    print(
        f"Testing with invalid feed: {invalid_feed_name} (Category: {invalid_category})"
    )

    with pytest.raises(FtsoV2Error) as excinfo:
        ftso_instance.get_latest_price(invalid_feed_name, invalid_category)
    print(f"Received expected error: {excinfo.type.__name__}")
