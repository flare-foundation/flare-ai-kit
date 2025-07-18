import pytest
import pytest_asyncio
from web3 import AsyncWeb3, Web3
from web3.exceptions import ContractLogicError

from flare_ai_kit.common import FtsoFeedCategory, FtsoV2Error
from flare_ai_kit.ecosystem.protocols.ftsov2 import FtsoV2
from flare_ai_kit.ecosystem.settings import EcosystemSettings

settings = EcosystemSettings()  # type: ignore[reportCallIssue]


# Use pytest_asyncio.fixture for async fixtures
@pytest_asyncio.fixture(scope="function")
async def ftso_instance() -> FtsoV2:  # type: ignore[reportInvalidTypeForm]
    """Provides a real instance of FtsoV2 connected to the network."""
    try:
        # Use the async factory method
        instance = await FtsoV2.create(settings)
        # Perform an async check for connectivity instead of is_connected()
        chain_id = await instance.w3.eth.chain_id
        assert isinstance(chain_id, int)
        print(f"\nConnected to Flare network (Chain ID: {chain_id})")
    except Exception as e:
        pytest.fail(
            f"Failed to initialize FtsoV2 instance or connect to Flare network: {e}"
        )
    else:
        yield instance  # type: ignore[reportReturnType]


# This test uses a static SYNCHRONOUS method, so it remains synchronous
@pytest.mark.parametrize(
    ("feed_name", "category", "expected_id"),
    [
        (
            "BTC/USD",
            FtsoFeedCategory.CRYPTO,
            "014254432f55534400000000000000000000000000",
        ),
        (
            "ETH/USD",
            FtsoFeedCategory.CRYPTO,
            "014554482f55534400000000000000000000000000",
        ),
        (
            "FLR/USD",
            FtsoFeedCategory.CRYPTO,
            "01464c522f55534400000000000000000000000000",
        ),
    ],
)
def test_feed_name_to_id_static(
    feed_name: str, category: FtsoFeedCategory, expected_id: str
) -> None:
    """Test the static method _feed_name_to_id (no network required)."""
    # Call the static method on the FtsoV2 class
    assert FtsoV2._feed_name_to_id(feed_name, category) == f"0x{expected_id}"  # type: ignore[reportPrivateUsage]


# Mark test as async as it uses an async fixture
@pytest.mark.asyncio
async def test_ftso_v2_real_initialization(ftso_instance: FtsoV2) -> None:
    """Verify the real FtsoV2 instance initializes correctly."""
    assert ftso_instance is not None
    # Check if the w3 object is an instance of Web3 (or AsyncWeb3 if type hint updated)
    assert isinstance(ftso_instance.w3, AsyncWeb3)
    # Connectivity is checked in the fixture now.
    # Check if the ftsov2 contract object was initialized by the create method
    assert ftso_instance.ftsov2 is not None, (
        "FtsoV2 contract object should be initialized"
    )
    assert Web3.is_address(ftso_instance.ftsov2.address), (
        "Initialized contract address should be valid"
    )
    print(
        f"Successfully verified FtsoV2 contract initialization at address: {ftso_instance.ftsov2.address}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("feed_name", "category"),
    [
        ("FLR/USD", FtsoFeedCategory.CRYPTO),
        ("BTC/USD", FtsoFeedCategory.CRYPTO),
    ],
)
async def test_get_latest_price_real_valid_feeds(
    ftso_instance: FtsoV2, feed_name: str, category: FtsoFeedCategory
) -> None:
    """
    Test fetching the latest price asynchronously for known valid feeds.
    Asserts type and plausibility, not exact value.
    """
    print(f"Fetching latest price for {feed_name} (Category: {category})...")
    try:
        # Await the async method call
        price = await ftso_instance.get_latest_price(feed_name, category)
        print(f"Received price for {feed_name}: {price}")

        assert isinstance(price, float), f"Price for {feed_name} should be a float"
        # Price can be 0.0 if feed exists but hasn't updated recently,
        # so asserting > 0 might be too strict depending on network state.
        # Asserting >= 0 is safer.
        assert price >= 0, (
            f"Price for {feed_name} should be non-negative (received: {price})"
        )

    except Exception as e:
        pytest.fail(f"Fetching price for {feed_name} failed with error: {e}")


# Mark test as async
@pytest.mark.asyncio
async def test_get_feed_by_id_real_structure(ftso_instance: FtsoV2) -> None:
    """
    Test the internal async _get_feed_by_id method for return structure and types.
    Uses a known valid feed ID.
    """
    # Sync call to static method is fine
    feed_id = FtsoV2._feed_name_to_id("FLR/USD", FtsoFeedCategory.CRYPTO)  # type: ignore[reportPrivateUsage]
    print(f"Querying _get_feed_by_id for feed ID: {feed_id}")

    try:
        # Await the internal async method call
        feeds, decimals, timestamp = await ftso_instance._get_feed_by_id(feed_id)  # type: ignore[reportPrivateUsage]
        print(
            f"Received feed data: Feeds={feeds}, Decimals={decimals}, Timestamp={timestamp}"
        )

        assert isinstance(feeds, int), "Feeds value should be an integer"
        assert isinstance(decimals, int), "Decimals value should be an integer"
        assert isinstance(timestamp, int), "Timestamp value should be an integer"

        assert feeds >= 0, "Feeds value should be non-negative"
        assert 0 <= decimals <= 18, "Decimals value typically between 0 and 18"
        # Check timestamp is positive (basic sanity check)
        assert timestamp > 0, "Timestamp should be positive"

    except Exception as e:
        pytest.fail(f"Calling _get_feed_by_id for {feed_id} failed with error: {e}")


# Mark test as async
@pytest.mark.asyncio
async def test_get_latest_price_real_invalid_category(ftso_instance: FtsoV2) -> None:
    """Test behavior when requesting a valid feed with an invalid category."""
    valid_feed_name = "FLR/USD"
    invalid_category = (
        FtsoFeedCategory.COMMODITY
    )  # Assuming '99' is never a valid category
    print(
        f"Testing with valid feed '{valid_feed_name}' and invalid category '{invalid_category}'"
    )

    # Expecting FtsoV2Error due to category validation fail before network call
    with pytest.raises(FtsoV2Error) as excinfo:
        # Await the call inside the context manager
        await ftso_instance.get_latest_price(valid_feed_name, invalid_category)

    assert "feed does not exist" in str(excinfo.value)
    print(f"Received expected FtsoV2Error: {excinfo.value}")


# Mark test as async
@pytest.mark.asyncio
async def test_get_latest_price_real_nonexistent_feed(ftso_instance: FtsoV2) -> None:
    """
    Test behavior when requesting a likely non-existent feed ID (syntactically valid).
    This should ideally result in a price of 0 after the async call.
    """
    # Create a feed name that is unlikely to exist but converts to a valid ID format
    invalid_feed_name = "NONEXISTENTXYZABC/NON"
    category = FtsoFeedCategory.CRYPTO
    print(
        f"Testing with likely non-existent feed: {invalid_feed_name} (Category: {category})"
    )

    try:
        # This feed ID might not cause an immediate revert, but return 0s
        price = await ftso_instance.get_latest_price(invalid_feed_name, category)
        print(f"Received price for {invalid_feed_name}: {price}")
        # A non-existent feed ID that doesn't cause a revert should return 0,0,0
        # from the contract, resulting in a price of 0.0
        assert price == 0.0, "Expected 0.0 price for a non-existent feed ID"

    except FtsoV2Error as e:
        # It's also possible the specific node/contract setup *does* revert.
        # This makes the test slightly less deterministic, but catching the error is valid.
        print(
            f"Received FtsoV2Error (this might happen depending on node behavior): {e}"
        )
        # Optionally assert something specific about the error message if needed
    except ContractLogicError as e:
        # Catching web3's ContractLogicError specifically if the node reverts
        print(f"Received ContractLogicError (node reverted): {e}")
    except Exception as e:
        pytest.fail(
            f"Fetching price for {invalid_feed_name} failed with unexpected error: {e}"
        )


# Example for testing get_latest_prices (plural)
@pytest.mark.asyncio
async def test_get_latest_prices_real_valid_feeds(ftso_instance: FtsoV2) -> None:
    """Test fetching multiple prices asynchronously."""
    feeds = ["FLR/USD", "BTC/USD", "ETH/USD"]
    category = FtsoFeedCategory.CRYPTO
    print(f"\nFetching latest prices for {feeds} (Category: {category})...")
    try:
        prices = await ftso_instance.get_latest_prices(feeds, category)
        print(f"Received prices: {prices}")

        assert isinstance(prices, list), "Result should be a list"
        assert len(prices) == len(feeds), "Should receive one price per requested feed"
        for i, price in enumerate(prices):
            assert isinstance(price, float), f"Price for {feeds[i]} should be float"
            assert price >= 0.0, f"Price for {feeds[i]} should be non-negative"

    except Exception as e:
        pytest.fail(f"Fetching multiple prices failed with error: {e}")
