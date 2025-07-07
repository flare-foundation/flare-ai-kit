"""Handles posting data to a smart contract on the Flare blockchain."""

import json
from typing import Any, Dict

import structlog
from web3.types import TxParams

from flare_ai_kit.common import FlareTxError
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ingestion.settings_models import OnchainContractSettings

logger = structlog.get_logger(__name__)


class ContractPoster(Flare):
    """A class to post data to a specified smart contract."""

    def __init__(self, settings: OnchainContractSettings, flare_instance: Flare):
        """
        Initializes the ContractPoster.

        Args:
            settings: The on-chain contract settings.
            flare_instance: An instance of the Flare class for blockchain interactions.
        """
        super().__init__(flare_instance.settings) # type: ignore
        self.contract_settings = settings
        with open(self.contract_settings.abi_path, "r") as f:
            abi = json.load(f)
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.contract_settings.contract_address),
            abi=abi,
        )

    async def post_data(self, data: Dict[str, Any]) -> str:
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
            function_call = self.contract.functions[self.contract_settings.function_name](
                data.get("invoiceId", ""),
                int(data.get("amountDue", 0)),
                data.get("issueDate", ""),
            )

            tx_params: TxParams = await self.build_transaction(
                function_call, self.w3.to_checksum_address(self.address) # type: ignore
            ) # type: ignore
            tx_hash = await self.sign_and_send_transaction(tx_params)
            if not tx_hash:
                raise FlareTxError("Transaction failed and did not return a hash.")
            logger.info("Data posted to contract successfully", tx_hash=tx_hash)
            return tx_hash
        except Exception as e:
            logger.exception("Failed to post data to contract", error=e)
            raise FlareTxError("Failed to post data to contract") from e