from typing import Any, cast

import structlog
from hexbytes import HexBytes
from web3.types import TxParams

from flare_ai_kit.ecosystem import Contracts, EcosystemSettings
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

logger = structlog.get_logger(__name__)


class FlarePortal:
    """
    A class to interact with the Wrapped FLR (WFLR) contract on the Flare blockchain.

    Provides methods to wrap native FLR into WFLR and unwrap WFLR back to FLR, handling
    transaction building, simulation, and execution through the Flare provider.
    """

    @classmethod
    async def create(
        cls,
        settings: EcosystemSettings,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
    ) -> "FlarePortal":
        """
        Asynchronously create a FlarePortal instance with the provided configuration.

        Fetches the ABI for the Wrapped FLR (WFLR) contract from the block explorer and
        initializes a FlarePortal instance with the provided settings, contracts, explorer,
        and provider.

        Args:
            settings (EcosystemSettings): Configuration settings, including account details.
            contracts (Contracts): Contract addresses for the Flare blockchain.
            flare_explorer (BlockExplorer): Block explorer instance for querying contract ABIs.
            flare_provider (Flare): Provider instance for blockchain interactions.

        Returns:
            FlarePortal: An initialized FlarePortal instance configured for WFLR operations.

        Raises:
            Exception: If the WFLR contract ABI cannot be fetched or initialization fails.

        """
        # Fetch ABI for Wrap FLR contract
        wflr_abi = await flare_explorer.get_contract_abi(contracts.flare.wflr)

        # Create FlarePortal instance
        instance = cls(
            settings=settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
            wflr_abi=wflr_abi,
        )
        return instance

    def __init__(
        self,
        settings: EcosystemSettings,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
        wflr_abi: list[dict[str, Any]],
    ) -> None:
        """
        Initialize a FlarePortal instance with the provided configuration and ABI.

        Sets up the FlarePortal instance with the necessary attributes for WFLR operations,
        including account details, contract addresses, and the WFLR contract instance.

        Args:
            settings (EcosystemSettings): Configuration settings, including account details.
            contracts (Contracts): Contract addresses for the Flare blockchain.
            flare_explorer (BlockExplorer): Block explorer instance for querying contract ABIs.
            flare_provider (Flare): Provider instance for blockchain interactions.
            wflr_abi (list): ABI for the WFLR contract.

        Raises:
            Exception: If the account address is not set in the flare_provider.

        """
        if not flare_provider.address:
            raise Exception("Please set settings.account_address in your .env file.")
        self.settings = settings
        self.contracts = contracts
        self.flare_explorer = flare_explorer
        self.flare_provider = flare_provider
        self.account_address = flare_provider.address
        self.wflr_abi = wflr_abi

        self.wflr_contract = flare_provider.w3.eth.contract(
            address=contracts.flare.wflr, abi=wflr_abi
        )

    async def wrap_flr_to_wflr(self, amount_WEI: int):
        """
        Wrap native FLR into Wrapped FLR (WFLR).

        Builds and executes a transaction to deposit native FLR into the WFLR contract,
        converting it to WFLR tokens. The transaction is simulated before execution to ensure
        it will succeed.

        Args:
            amount_WEI (int): The amount of tokens to lock, in wei.

        Returns:
            str | None: The hexadecimal transaction hash of the wrap operation, or None if the
                simulation fails.

        Raises:
            Exception: If transaction building or execution fails.

        """
        if self.flare_provider.address is None:
            raise ValueError("Wallet address cannot be None.")

        wrap_fn = self.wflr_contract.functions.deposit()
        wrap_tx = await self.flare_provider.build_transaction(
            function_call=wrap_fn,
            from_addr=self.flare_provider.address,
            custom_params=cast("TxParams", {"value": amount_WEI}),
        )

        logger.debug("Wrap FLR to WFLR", tx=wrap_tx)

        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=self.wflr_abi, call_tx=wrap_tx
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated wrap transaction was not sucessfull"
            )
            raise Exception(
                "We stop here because the simulated transaction was not sucessfull"
            )

        wrap_tx_hash = await self.flare_provider.sign_and_send_transaction(wrap_tx)
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            HexBytes(wrap_tx_hash)
        )
        logger.debug(f"Wrap transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{wrap_tx_hash}")
        return wrap_tx_hash

    async def unwrap_wflr_to_flr(self, amount_WEI: int):
        """
        Unwrap WFLR to native FLR.

        Builds and executes a transaction to withdraw WFLR from the WFLR contract, converting
        it back to native FLR. The transaction is simulated before execution to ensure it will
        succeed.

        Args:
            amount_WEI (int): The amount of tokens to lock, in wei.

        Returns:
            str | None: The hexadecimal transaction hash of the unwrap operation, or None if the
                simulation fails.

        Raises:
            Exception: If transaction building or execution fails.

        """
        if self.flare_provider.address is None:
            raise ValueError("Wallet address cannot be None.")

        unwrap_fn = self.wflr_contract.functions.withdraw(amount_WEI)
        unwrap_tx = await self.flare_provider.build_transaction(
            function_call=unwrap_fn, from_addr=self.flare_provider.address
        )

        logger.debug("unwrap FLR to WFLR", tx=unwrap_tx)

        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=self.wflr_abi, call_tx=unwrap_tx
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated unwrap transaction was not sucessfull"
            )
            raise Exception(
                "We stop here because the simulated transaction was not sucessfull"
            )

        unwrap_tx_hash = await self.flare_provider.sign_and_send_transaction(unwrap_tx)
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            HexBytes(unwrap_tx_hash)
        )
        logger.debug(f"unwrap transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{unwrap_tx_hash}")
        return unwrap_tx_hash
