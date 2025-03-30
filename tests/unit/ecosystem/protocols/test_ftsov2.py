import pytest
import pytest_asyncio
from web3 import Web3

from flare_ai_kit.common import FtsoV2Error
from flare_ai_kit.ecosystem.protocols.ftsov2 import VALID_CATEGORIES, FtsoV2

# Dummy data - Ensure correctness
DUMMY_URL = "http://dummy-web3.flare.network"
DUMMY_FTSO_ADDRESS = Web3.to_checksum_address(
    "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)
DUMMY_ABI = [
    {"type": "function", "name": "getFeedById"},
    {"type": "function", "name": "getFeedsById"},
]
FEED_BTC_USD_NAME = "BTC/USD"
FEED_BTC_USD_CAT = "01"
FEED_BTC_USD_ID = "0x014254432f55534400000000000000000000000000"
FEED_ETH_USD_NAME = "ETH/USD"
FEED_ETH_USD_ID = "0x014554482f55534400000000000000000000000000"
FEED_INVALID_CAT = "99"
FEED_JUST_FITS_NAME = "A" * 20  # Results in 42 hex chars total (01 + 41*20)
FEED_TOO_LONG_NAME = "A" * 21  # Results in 44 hex chars total (01 + 41*21) -> Error


class TestFtsoV2StaticMethods:
    def test_check_category_validity_valid(self):
        """Test valid categories pass."""
        for cat in VALID_CATEGORIES:
            FtsoV2._check_category_validity(cat)  # Should not raise

    def test_check_category_validity_invalid(self):
        """Test invalid category raises FtsoV2Error."""
        with pytest.raises(FtsoV2Error, match="Invalid category"):
            FtsoV2._check_category_validity(FEED_INVALID_CAT)
        with pytest.raises(FtsoV2Error, match="Invalid category"):
            FtsoV2._check_category_validity("0")  # Too short
        with pytest.raises(FtsoV2Error, match="Invalid category"):
            FtsoV2._check_category_validity("")  # Empty

    def test_feed_name_to_id_success(self):
        """Test successful conversion of feed name/category to ID."""
        feed_id_btc = FtsoV2._feed_name_to_id(FEED_BTC_USD_NAME, FEED_BTC_USD_CAT)
        assert feed_id_btc == FEED_BTC_USD_ID
        assert len(feed_id_btc) == 44

    def test_feed_name_to_id_length_limits(self):
        """Test feed name length limits."""
        # This name should result in exactly 42 hex characters total and pass
        expected_id_just_fits = "0x01" + ("41" * 20)  # 01 + 40 chars = 42
        assert (
            FtsoV2._feed_name_to_id(FEED_JUST_FITS_NAME, "01") == expected_id_just_fits
        )

        # This name results in 44 hex characters total and should fail
        with pytest.raises(FtsoV2Error, match="Resulting hex string.*is too long"):
            FtsoV2._feed_name_to_id(FEED_TOO_LONG_NAME, "01")


# --- Instance Method Tests ---


@pytest.mark.asyncio
class TestFtsoV2:
    @pytest_asyncio.fixture(autouse=True)
    def setup_mocks(self, mocker):
        """Auto-used fixture to mock dependencies for all tests in this class."""
        mocker.patch(
            "flare_ai_kit.ecosystem.protocols.ftsov2.load_abi", return_value=DUMMY_ABI
        )
        mocker.patch.object(
            FtsoV2,
            "get_protocol_contract_address",
            new_callable=mocker.AsyncMock,
            return_value=DUMMY_FTSO_ADDRESS,
        )

        # --- Corrected Web3 Mocking ---
        mock_w3 = mocker.MagicMock(spec=Web3)
        # 1. Create the 'eth' attribute as a mock
        mock_w3.eth = mocker.MagicMock()
        # 2. Create the 'contract' attribute on 'eth' as a mock
        mock_w3.eth.contract = mocker.MagicMock()
        # 3. Simple pass-through for checksum address for testing
        mock_w3.to_checksum_address = (
            lambda addr: Web3.to_checksum_address(addr)
            if Web3.is_address(addr)
            else addr
        )
        # --- End Correction ---

        mocker.patch(
            "flare_ai_kit.ecosystem.flare.Flare.__init__",
            side_effect=lambda self_instance, **kwargs: setattr(
                self_instance, "w3", mock_w3
            ),
        )

        self.mock_contract = mocker.MagicMock()
        self.mock_contract.functions.getFeedById = mocker.MagicMock()
        self.mock_contract.functions.getFeedById().call = mocker.AsyncMock()
        self.mock_contract.functions.getFeedsById = mocker.MagicMock()
        self.mock_contract.functions.getFeedsById().call = mocker.AsyncMock()

        # Make w3.eth.contract return our mock contract object
        mock_w3.eth.contract.return_value = self.mock_contract
        self.mock_w3 = mock_w3

    async def test_create_success(self, mocker):
        """Test successful asynchronous initialization via create()."""
        instance = await FtsoV2.create(web3_provider_url=DUMMY_URL)

        assert isinstance(instance, FtsoV2)
        FtsoV2.get_protocol_contract_address.assert_awaited_once_with("FtsoV2")
        mocker.patch(
            "flare_ai_kit.ecosystem.protocols.ftsov2.load_abi"
        ).assert_called_once_with("FtsoV2")
        self.mock_w3.eth.contract.assert_called_once_with(
            address=DUMMY_FTSO_ADDRESS,
            abi=DUMMY_ABI,
        )
        assert instance.ftsov2 == self.mock_contract

    async def test_create_get_address_fails(self, mocker):
        """Test create() fails if getting the contract address fails."""
        mocker.patch.object(
            FtsoV2,
            "get_protocol_contract_address",
            side_effect=Exception("Registry lookup failed"),
            new_callable=mocker.AsyncMock,
        )

        with pytest.raises(Exception, match="Registry lookup failed"):
            await FtsoV2.create(web3_provider_url=DUMMY_URL)

    @pytest_asyncio.fixture
    async def initialized_instance(self):
        """Fixture to provide a fully initialized FtsoV2 instance."""
        instance = await FtsoV2.create(web3_provider_url=DUMMY_URL)
        self.mock_contract.functions.getFeedById().call.reset_mock()
        self.mock_contract.functions.getFeedsById().call.reset_mock()
        # Also reset the contract function mock itself if needed
        self.mock_contract.functions.getFeedById.reset_mock()
        self.mock_contract.functions.getFeedsById.reset_mock()
        return instance

    async def test_get_feed_by_id_not_initialized(self):
        """Test calling internal method before initialization raises AttributeError."""
        # Need to bypass the __init__ patch for this test specifically
        with patch(
            "flare_ai_kit.ecosystem.flare.Flare.__init__", return_value=None
        ):  # Basic patch
            instance = FtsoV2(web3_provider_url=DUMMY_URL)
            assert instance.ftsov2 is None
            with pytest.raises(AttributeError, match="not fully initialized"):
                await instance._get_feed_by_id(FEED_BTC_USD_ID)

    async def test_get_feed_by_id_success(self, initialized_instance):
        """Test successful internal call to getFeedById."""
        expected_result = (50000 * (10**8), 8, 1678886400)
        self.mock_contract.functions.getFeedById(
            FEED_BTC_USD_ID
        ).call.return_value = expected_result

        result = await initialized_instance._get_feed_by_id(FEED_BTC_USD_ID)

        assert result == expected_result
        # Check the function was accessed with the correct arg
        self.mock_contract.functions.getFeedById.assert_called_once_with(
            FEED_BTC_USD_ID
        )
        # Check the call() method was awaited
        self.mock_contract.functions.getFeedById(
            FEED_BTC_USD_ID
        ).call.assert_awaited_once()

    async def test_get_feed_by_id_contract_error(self, initialized_instance):
        """Test internal getFeedById wraps contract errors in FtsoV2Error."""
        contract_error = Exception("Contract execution reverted")
        # Configure the side effect on the call mock
        self.mock_contract.functions.getFeedById(
            FEED_BTC_USD_ID
        ).call.side_effect = contract_error

        with pytest.raises(
            FtsoV2Error, match=f"Contract call failed for getFeedById.*{contract_error}"
        ) as excinfo:
            await initialized_instance._get_feed_by_id(FEED_BTC_USD_ID)
        assert excinfo.value.__cause__ is contract_error
        self.mock_contract.functions.getFeedById.assert_called_once_with(
            FEED_BTC_USD_ID
        )
        self.mock_contract.functions.getFeedById(
            FEED_BTC_USD_ID
        ).call.assert_awaited_once()

    async def test_get_feeds_by_id_success(self, initialized_instance):
        """Test successful internal call to getFeedsById."""
        feed_ids = [FEED_BTC_USD_ID, FEED_ETH_USD_ID]
        expected_result = ([50000 * (10**8), 3000 * (10**8)], [8, 8], 1678886400)
        # Configure return value on the specific call mock
        self.mock_contract.functions.getFeedsById(
            feed_ids
        ).call.return_value = expected_result

        result = await initialized_instance._get_feeds_by_id(feed_ids)

        assert result == expected_result
        self.mock_contract.functions.getFeedsById.assert_called_once_with(feed_ids)
        self.mock_contract.functions.getFeedsById(feed_ids).call.assert_awaited_once()

    async def test_get_feeds_by_id_contract_error(self, initialized_instance):
        """Test internal getFeedsById wraps contract errors in FtsoV2Error."""
        feed_ids = [FEED_BTC_USD_ID, FEED_ETH_USD_ID]
        contract_error = Exception("Contract execution reverted")
        self.mock_contract.functions.getFeedsById(
            feed_ids
        ).call.side_effect = contract_error

        with pytest.raises(
            FtsoV2Error,
            match=f"Contract call failed for getFeedsById.*{contract_error}",
        ) as excinfo:
            await initialized_instance._get_feeds_by_id(feed_ids)
        assert excinfo.value.__cause__ is contract_error
        self.mock_contract.functions.getFeedsById.assert_called_once_with(feed_ids)
        self.mock_contract.functions.getFeedsById(feed_ids).call.assert_awaited_once()

    async def test_get_latest_price_success(self, initialized_instance, mocker):
        """Test successful get_latest_price call."""
        price_int = 50000 * (10**8)
        decimals = 8
        timestamp = 1678886400
        expected_float = 50000.0
        mock_internal = mocker.patch.object(
            initialized_instance, "_get_feed_by_id", new_callable=mocker.AsyncMock
        )
        mock_internal.return_value = (price_int, decimals, timestamp)

        result = await initialized_instance.get_latest_price(
            FEED_BTC_USD_NAME, FEED_BTC_USD_CAT
        )

        assert result == expected_float
        # Ensure internal method was called with the *correctly generated* ID
        mock_internal.assert_awaited_once_with(FEED_BTC_USD_ID)

    async def test_get_latest_price_zero_values(self, initialized_instance, mocker):
        """Test get_latest_price returns 0.0 if contract returns zero price."""
        mock_internal = mocker.patch.object(
            initialized_instance, "_get_feed_by_id", new_callable=mocker.AsyncMock
        )
        mock_internal.return_value = (0, 8, 1678886400)  # Zero price
        result = await initialized_instance.get_latest_price(
            FEED_BTC_USD_NAME, FEED_BTC_USD_CAT
        )
        assert result == 0.0

    # Test added for zero decimals specifically
    async def test_get_latest_price_zero_decimals(self, initialized_instance, mocker):
        """Test get_latest_price handles zero decimals correctly."""
        mock_internal = mocker.patch.object(
            initialized_instance, "_get_feed_by_id", new_callable=mocker.AsyncMock
        )
        # If decimals=0, price / (10**0) = price / 1 = price
        mock_internal.return_value = (50000, 0, 1678886400)  # Zero decimals
        expected_float_zero_dec = 50000.0
        result_zero_dec = await initialized_instance.get_latest_price(
            FEED_BTC_USD_NAME, FEED_BTC_USD_CAT
        )
        assert result_zero_dec == expected_float_zero_dec

    async def test_get_latest_price_invalid_category(self, initialized_instance):
        """Test get_latest_price raises error for invalid category."""
        with pytest.raises(FtsoV2Error, match="Invalid category"):
            await initialized_instance.get_latest_price(
                FEED_BTC_USD_NAME, FEED_INVALID_CAT
            )

    # Test added for feed name too long -> FtsoV2Error
    async def test_get_latest_price_invalid_name(self, initialized_instance):
        """Test get_latest_price raises error for feed name too long."""
        with pytest.raises(FtsoV2Error, match="Resulting hex string.*is too long"):
            await initialized_instance.get_latest_price(FEED_TOO_LONG_NAME, "01")

    async def test_get_latest_price_internal_error(self, initialized_instance, mocker):
        """Test get_latest_price propagates errors from _get_feed_by_id."""
        internal_error = FtsoV2Error("Internal contract failure")
        mocker.patch.object(
            initialized_instance,
            "_get_feed_by_id",
            side_effect=internal_error,
            new_callable=mocker.AsyncMock,
        )

        with pytest.raises(FtsoV2Error, match="Internal contract failure"):
            await initialized_instance.get_latest_price(
                FEED_BTC_USD_NAME, FEED_BTC_USD_CAT
            )

    async def test_get_latest_prices_success(self, initialized_instance, mocker):
        """Test successful get_latest_prices call."""
        feed_names = [FEED_BTC_USD_NAME, FEED_ETH_USD_NAME]
        feed_ids = [FEED_BTC_USD_ID, FEED_ETH_USD_ID]
        prices_int = [50000 * (10**8), 3000 * (10**8)]
        decimals_int = [8, 8]
        timestamp = 1678886400
        expected_floats = [50000.0, 3000.0]
        mock_internal = mocker.patch.object(
            initialized_instance, "_get_feeds_by_id", new_callable=mocker.AsyncMock
        )
        mock_internal.return_value = (prices_int, decimals_int, timestamp)

        results = await initialized_instance.get_latest_prices(
            feed_names, FEED_BTC_USD_CAT
        )

        assert results == expected_floats
        mock_internal.assert_awaited_once_with(
            feed_ids
        )  # Check called with correctly generated IDs

    async def test_get_latest_prices_invalid_category(self, initialized_instance):
        """Test get_latest_prices raises error for invalid category."""
        feed_names = [FEED_BTC_USD_NAME, FEED_ETH_USD_NAME]
        with pytest.raises(FtsoV2Error, match="Invalid category"):
            await initialized_instance.get_latest_prices(feed_names, FEED_INVALID_CAT)

    # Test added for one invalid name in list
    async def test_get_latest_prices_invalid_name(self, initialized_instance):
        """Test get_latest_prices raises error if any feed name is too long."""
        feed_names = [FEED_BTC_USD_NAME, FEED_TOO_LONG_NAME]
        with pytest.raises(FtsoV2Error, match="Resulting hex string.*is too long"):
            await initialized_instance.get_latest_prices(feed_names, "01")

    async def test_get_latest_prices_internal_error(self, initialized_instance, mocker):
        """Test get_latest_prices propagates errors from _get_feeds_by_id."""
        feed_names = [FEED_BTC_USD_NAME, FEED_ETH_USD_NAME]
        internal_error = FtsoV2Error("Internal contract failure")
        mocker.patch.object(
            initialized_instance,
            "_get_feeds_by_id",
            side_effect=internal_error,
            new_callable=mocker.AsyncMock,
        )

        with pytest.raises(FtsoV2Error, match="Internal contract failure"):
            await initialized_instance.get_latest_prices(feed_names, FEED_BTC_USD_CAT)
