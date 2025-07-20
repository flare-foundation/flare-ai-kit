"""Handles posting data to a smart contract on the Flare blockchain."""

import json
from typing import Any

import structlog
from web3.types import TxParams

from flare_ai_kit.common import FlareTxError
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings import EcosystemSettings
from flare_ai_kit.ingestion.settings import OnchainContractSettings

logger = structlog.get_logger(__name__)


class ContractPoster(Flare):
    """A class to post data to a specified smart contract."""

    def __init__(
        self,
        contract_settings: OnchainContractSettings,
        ecosystem_settings: EcosystemSettings,
    ):
        """
        Initializes the ContractPoster.

        Args:
            contract_settings: The on-chain contract settings.
            ecosystem_settings: The ecosystem settings for the parent Flare class.

        """
        # Initialize the parent Flare class with the ecosystem settings
        super().__init__(ecosystem_settings)

        self.contract_settings = contract_settings
        with open(self.contract_settings.abi_path) as f:
            abi = json.load(f)
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(
                self.contract_settings.contract_address
            ),
            abi=abi,
        )

    async def post_data(self, data: dict[str, Any]) -> str | None:
        """
        Posts data to the smart contract.

        Args:
            data: A dictionary containing the data to post.

        Returns:
            The transaction hash of the on-chain transaction.

        Raises:
            FlareTxError: If the transaction fails.

        """
        try:
            function_name = self.contract_settings.function_name
            invoice_id = data.get("invoice_id", "")
            amount_due = int(data.get("amount_due", 0))
            issue_date = data.get("issue_date", "")

            function_call = self.contract.functions[function_name](
                invoice_id,
                amount_due,
                issue_date,
            )

            tx_params: TxParams = await self.build_transaction(
                function_call,
                self.w3.to_checksum_address(self.address),  # type: ignore
            )
            tx_hash = await self.sign_and_send_transaction(tx_params)

            logger.info("Data posted to contract successfully", tx_hash=tx_hash)
            return tx_hash
        except Exception as e:
            logger.exception("Failed to post data to contract", error=e)
            raise FlareTxError("Failed to post data to contract") from e
