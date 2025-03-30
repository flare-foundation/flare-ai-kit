"""Asynchronous Interactions with Flare Block Explorers."""

import json

import httpx
import structlog
from httpx import HTTPStatusError, RequestError, TimeoutException

from flare_ai_kit.common import AbiError, ExplorerError

logger = structlog.get_logger(__name__)


class BlockExplorer:
    """Asynchronous interactions with Flare Block Explorer APIs."""

    def __init__(self, explorer_url: str, timeout: float = 10.0) -> None:
        """
        Initializes the BlockExplorer.

        Args:
            explorer_url (str): The base URL of the block explorer API endpoint.
            timeout (float): Default request timeout in seconds.

        """
        self.explorer_url = explorer_url
        self._headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }
        # Create an httpx async client for connection pooling and configuration
        # It's important to close this client when done.
        self._client = httpx.AsyncClient(
            base_url=explorer_url, headers=self._headers, timeout=timeout
        )
        self.logger = logger.bind(service="explorer-async", url=explorer_url)
        self.logger.debug("BlockExplorer initialized")

    async def close(self) -> None:
        """Closes the underlying HTTP client session."""
        await self._client.aclose()
        self.logger.debug("BlockExplorer client closed")

    # Implement async context manager protocol for easier resource management
    async def __aenter__(self) -> "BlockExplorer":
        """Enter the async context manager."""
        # The client is already created in __init__, just return self
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001 # type: ignore[reportUnknownParameterType]
        """Exit the async context manager, ensuring the client is closed."""
        await self.close()

    async def _get(self, params: dict[str, str]) -> dict[str, list[str]]:
        """
        Asynchronously GET data from the Chain Explorer API endpoint.

        Args:
            params: Query parameters for the API request.

        Returns:
            dict: JSON response parsed into a Python dictionary.

        Raises:
            ValueError: If the response is malformed or doesn't contain expected keys.
            RequestError: For connection-related issues.
            TimeoutException: If the request times out.
            HTTPStatusError: For non-2xx HTTP responses.

        """
        self.logger.debug("Sending async GET request", params=params)
        try:
            # Use the httpx client to make the request
            # Note: If explorer_url in __init__ includes the path, use '/' here.
            # If it's just the base domain, you might need '/api' or similar.
            # Assuming explorer_url is the full base path for API calls.
            response = await self._client.get(
                url="/", params=params
            )  # URL path relative to base_url

            # Check for HTTP errors (4xx or 5xx)
            response.raise_for_status()

            json_response = response.json()

            # Optional: Add more specific checks based on expected API structure
            if not isinstance(json_response, dict):
                msg = f"API response is not a JSON object: {json_response}"
                raise ExplorerError(msg)

            if "result" not in json_response:
                # Log the actual problematic response
                self.logger.warning(
                    "Malformed API response", response_data=json_response
                )
                msg = "Malformed response from API: 'result' key missing"
                raise ExplorerError(msg)

            self.logger.debug("Received successful API response", params=params)
        except TimeoutException:
            self.logger.exception("Request timed out", params=params)
            raise  # Re-raise the specific httpx exception
        except RequestError as e:
            # Covers connection errors, invalid URLs etc.
            self.logger.exception(
                "Network error during API request", params=params, error=str(e)
            )
            raise  # Re-raise the specific httpx exception
        except HTTPStatusError as e:
            # Log details from the HTTP error
            self.logger.exception(
                "HTTP error received from API",
                status_code=e.response.status_code,
                response_text=e.response.text,
                params=params,
            )
            raise  # Re-raise the specific httpx exception
        except json.JSONDecodeError as e:
            # Handle cases where response isn't valid JSON despite 2xx status
            self.logger.exception(
                "Failed to decode JSON response", params=params, error=str(e)
            )
            msg = "Failed to decode JSON response"
            raise ExplorerError(msg) from e
        else:
            return json_response  # type: ignore

    async def get_contract_abi(self, contract_address: str) -> list[dict[str, str]]:
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
        self.logger.info("Fetching ABI for contract", contract_address=contract_address)
        try:
            response_data = await self._get(
                params={
                    "module": "contract",
                    "action": "getabi",
                    "address": contract_address,
                }
            )
            # The 'result' field typically contains the ABI as a JSON *string*
            abi_string = response_data.get("result")

            if not abi_string or not isinstance(abi_string, str):
                msg = f"ABI result is missing or not string for {contract_address}"
                self.logger.warning(msg, response_data=response_data)
                raise AbiError(msg)

            # Parse the JSON string into a Python list/dict structure
            abi = json.loads(abi_string)
            if not isinstance(abi, list):
                msg = f"Parsed ABI for {contract_address} is not a list."
                self.logger.warning(msg, parsed_abi=abi)
                # Depending on API behavior, you might return [] or raise error
                raise AbiError(msg)

            self.logger.debug(
                "Successfully fetched and parsed ABI", contract_address=contract_address
            )
        except json.JSONDecodeError as e:
            self.logger.exception(
                "Failed to parse ABI JSON string",
                contract_address=contract_address,
                error=str(e),
            )
            msg = "Failed to parse ABI from API response"
            raise AbiError(msg) from e
        else:
            return abi  # type: ignore
