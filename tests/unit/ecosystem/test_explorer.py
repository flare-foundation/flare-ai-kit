"""Unit tests for the BlockExplorer module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import HTTPStatusError, RequestError, TimeoutException
from pydantic import HttpUrl

from flare_ai_kit.common.exceptions import AbiError, ExplorerError
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.settings import EcosystemSettings

settings = EcosystemSettings(
    is_testnet=True,
    web3_provider_url=HttpUrl("https://explorer.example.com/api"),
    web3_provider_timeout=10,
    block_explorer_url=HttpUrl("https://explorer.example.com/api"),
    block_explorer_timeout=10,
    account_address=None,
    account_private_key=None,
)


@pytest_asyncio.fixture
async def block_explorer():
    """Create a BlockExplorer instance for testing."""
    explorer = BlockExplorer(settings)
    # Replace the real client with a mock
    explorer.client = AsyncMock()
    yield explorer
    # Clean up
    await explorer.close()


class TestBlockExplorer:
    """Test suite for the BlockExplorer class."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test that the BlockExplorer initializes correctly."""
        with patch("httpx.AsyncClient") as mockclient:
            explorer = BlockExplorer(settings)

            # Replace the real client with a mock that can be awaited
            explorer.client = AsyncMock()
            explorer.client.aclose = AsyncMock()

            # Check that AsyncClient was called with correct parameters
            mockclient.assert_called_once()
            call_kwargs = mockclient.call_args.kwargs
            assert call_kwargs["base_url"] == "https://explorer.example.com/api"
            assert call_kwargs["timeout"] == 10
            assert "accept" in call_kwargs["headers"]
            assert "content-type" in call_kwargs["headers"]

            # Clean up
            await explorer.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test that the BlockExplorer works as an async context manager."""
        with patch("httpx.AsyncClient"):
            explorer = BlockExplorer(settings)
            # Replace the real client with a mock that can be awaited
            explorer.client = AsyncMock()
            explorer.client.aclose = AsyncMock()
            # Use spy on close method to check if it was called
            explorer.close = AsyncMock(wraps=explorer.close)

            async with explorer as ex:
                assert ex == explorer

            # Verify close was called on exit
            explorer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_success(self, block_explorer: BlockExplorer):
        """Test successful _get method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "test_data"}
        mock_response.raise_for_status = MagicMock()

        block_explorer.client.get.return_value = mock_response

        # Call the method
        result = await block_explorer._get({"param1": "value1"})

        # Verify
        block_explorer.client.get.assert_called_once_with(
            url="/", params={"param1": "value1"}
        )
        assert result == {"result": "test_data"}

    @pytest.mark.asyncio
    async def test_get_http_error(self, block_explorer: BlockExplorer):
        """Test _get method with HTTP error."""
        # Setup mock to raise HTTPStatusError
        mock_response = MagicMock()
        http_error = HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error

        block_explorer.client.get.return_value = mock_response

        # Call the method and expect exception
        with pytest.raises(HTTPStatusError):
            await block_explorer._get({"param1": "value1"})

        # Verify
        block_explorer.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_timeout(self, block_explorer: BlockExplorer):
        """Test _get method with timeout."""
        # Setup mock to raise TimeoutException
        block_explorer.client.get.side_effect = TimeoutException("Request timed out")

        # Call the method and expect exception
        with pytest.raises(TimeoutException):
            await block_explorer._get({"param1": "value1"})

        # Verify
        block_explorer.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_request_error(self, block_explorer: BlockExplorer):
        """Test _get method with request error."""
        # Setup mock to raise RequestError
        block_explorer.client.get.side_effect = RequestError("Connection error")

        # Call the method and expect exception
        with pytest.raises(RequestError):
            await block_explorer._get({"param1": "value1"})

        # Verify
        block_explorer.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_json_decode_error(self, block_explorer: BlockExplorer):
        """Test _get method with JSON decode error."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = MagicMock()

        block_explorer.client.get.return_value = mock_response

        # Call the method and expect exception
        with pytest.raises(ExplorerError):
            await block_explorer._get({"param1": "value1"})

        # Verify
        block_explorer.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_malformed_response(self, block_explorer: BlockExplorer):
        """Test _get method with malformed response (missing 'result')."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "no_result_key"}
        mock_response.raise_for_status = MagicMock()

        block_explorer.client.get.return_value = mock_response

        # Call the method and expect exception
        with pytest.raises(ExplorerError, match="Malformed response from API"):
            await block_explorer._get({"param1": "value1"})

        # Verify
        block_explorer.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_non_dict_response(self, block_explorer: BlockExplorer):
        """Test _get method with non-dict response."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = ["not", "a", "dict"]
        mock_response.raise_for_status = MagicMock()

        block_explorer.client.get.return_value = mock_response

        # Call the method and expect exception
        with pytest.raises(ExplorerError, match="API response is not a JSON object"):
            await block_explorer._get({"param1": "value1"})

        # Verify
        block_explorer.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contract_abi_success(self, block_explorer: BlockExplorer):
        """Test successful get_contract_abi method."""
        # Setup mock for _get method
        abi_string = '[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}]}]'
        expected_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
            }
        ]

        with patch.object(block_explorer, "_get", new=AsyncMock()) as mock_get:
            mock_get.return_value = {"result": abi_string}

            # Call the method
            result = await block_explorer.get_contract_abi("0x1234567890abcdef")

            # Verify
            mock_get.assert_called_once_with(
                params={
                    "module": "contract",
                    "action": "getabi",
                    "address": "0x1234567890abcdef",
                }
            )
            assert result == expected_abi

    @pytest.mark.asyncio
    async def test_get_contract_abi_missing_result(self, block_explorer: BlockExplorer):
        """Test get_contract_abi with missing result."""
        with patch.object(block_explorer, "_get", new=AsyncMock()) as mock_get:
            mock_get.return_value = {"result": ""}

            # Call the method and expect exception
            with pytest.raises(AbiError, match="ABI result is missing or not string"):
                await block_explorer.get_contract_abi("0x1234567890abcdef")

            # Verify
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contract_abi_invalid_json(self, block_explorer: BlockExplorer):
        """Test get_contract_abi with invalid JSON in result."""
        with patch.object(block_explorer, "_get", new=AsyncMock()) as mock_get:
            mock_get.return_value = {"result": "invalid json{["}

            # Call the method and expect exception
            with pytest.raises(AbiError, match="Failed to parse ABI from API response"):
                await block_explorer.get_contract_abi("0x1234567890abcdef")

            # Verify
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contract_abi_not_list(self, block_explorer: BlockExplorer):
        """Test get_contract_abi with non-list ABI result."""
        with patch.object(block_explorer, "_get", new=AsyncMock()) as mock_get:
            mock_get.return_value = {"result": '{"not":"a list"}'}

            # Call the method and expect exception
            with pytest.raises(AbiError, match="Parsed ABI .* is not a list"):
                await block_explorer.get_contract_abi("0x1234567890abcdef")

            # Verify
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, block_explorer: BlockExplorer):
        """Test the close method."""
        await block_explorer.close()
        block_explorer.client.aclose.assert_called_once()
