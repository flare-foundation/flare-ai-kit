"""Interactions with Flare Block Explorers."""

import json

import requests
import structlog
from requests.exceptions import RequestException, Timeout

logger = structlog.get_logger(__name__)


class BlockExplorer:
    """Interactions with Flare Block Explorer."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.logger = logger.bind(service="explorer")

    def _get(self, params: dict[str, str]) -> dict[str, str]:
        """
        Get data from the Chain Explorer API.

        :param params: Query parameters
        :return: JSON response
        """
        headers = {"accept": "application/json"}
        try:
            response = requests.get(
                self.base_url, params=params, headers=headers, timeout=10
            )
            response.raise_for_status()
            json_response = response.json()

            if "result" not in json_response:
                msg = (f"Malformed response from API: {json_response}",)
                raise ValueError(msg)

        except (RequestException, Timeout):
            self.logger.exception("Network error during API request")
            raise
        else:
            return json_response

    def get_contract_abi(self, contract_address: str) -> list[str]:
        """
        Get the ABI for a contract from the Chain Explorer API.

        :param contract_address: Address of the contract
        :return: Contract ABI
        """
        self.logger.debug(
            "Fetching ABI for `%s` from `%s`", contract_address, self.base_url
        )
        response = self._get(
            params={
                "module": "contract",
                "action": "getabi",
                "address": contract_address,
            }
        )
        return json.loads(response["result"])
