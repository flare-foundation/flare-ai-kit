from typing import cast

import structlog
from web3.types import TxParams

from flare_ai_kit.common import load_abi
from flare_ai_kit.ecosystem import Contracts, EcosystemSettings
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

logger = structlog.get_logger(__name__)


class Sceptre:
    @classmethod
    async def create(
        cls,
        settings: EcosystemSettings,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
    ) -> "Sceptre":
        """
        Asynchronously create a Sceptre instance with the provided configuration.

        Initializes the sFLR proxy contract using the provided Flare provider and contract addresses,
        then constructs a Sceptre instance. The contract ABI is fetched from the block explorer.

        Args:
            settings (EcosystemSettings): Configuration settings, including account details.
            contracts (Contracts): Contract addresses for the Flare blockchain.
            flare_explorer (BlockExplorer): Block explorer instance for querying contract ABIs.
            flare_provider (Flare): Provider instance for blockchain interactions.

        Returns:
            Sceptre: An initialized Sceptre instance configured for staking operations.

        Raises:
            Exception: If the sFLR contract ABI cannot be fetched or the contract initialization fails.

        """
        # Create Sceptre instance
        instance = cls(
            settings=settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )
        return instance

    def __init__(
        self,
        settings: EcosystemSettings,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
    ) -> None:
        if not flare_provider.address:
            raise Exception("Please set settings.account_address in your .env file.")
        self.settings = settings
        self.contracts = contracts
        self.flare_explorer = flare_explorer
        self.flare_provider = flare_provider
        self.account_address = flare_provider.address

    async def stake(self, amount_WEI: int) -> str:
        """
        Stake native FLR tokens to receive sFLR (Staked FLR).

        Builds and executes a transaction to stake the specified amount of FLR tokens by calling
        the `submit` function on the sFLR contract. The transaction is simulated before execution
        to ensure it will succeed.

        Args:
            amount_WEI (int): The amount of tokens to lock, in wei.

        Returns:
            str: The hexadecimal transaction hash of the staking operation, or None if the
                simulation fails.

        Raises:
            ValueError: If the amount_FLR is negative or zero.
            Exception: If the transaction building or execution fails.

        """
        if self.flare_provider.address is None:
            raise ValueError("Wallet address cannot be None.")

        if amount_WEI <= 0:
            raise ValueError("Amount to stake must be positive")

        impl_contract = self.flare_provider.w3.eth.contract(
            address=self.contracts.flare.sflr,
            abi=load_abi("Sceptre"),  # Torkel
        )
        stake_fn = impl_contract.functions.submit()
        stake_tx = await self.flare_provider.build_transaction(
            function_call=stake_fn,
            from_addr=self.flare_provider.address,
            custom_params=cast("TxParams", {"value": amount_WEI}),
        )

        logger.debug("Stake FLR to sFLR", tx=stake_tx)

        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=load_abi("Sceptre"),
            call_tx=stake_tx,  # Torkel
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated stake transaction was not sucessfull"
            )
            raise Exception(
                "We stop here because the simulated transaction was not sucessfull"
            )

        stake_tx_hash = await self.flare_provider.sign_and_send_transaction(stake_tx)
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            stake_tx_hash  # type: ignore
        )
        logger.debug(f"Stake transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{stake_tx_hash}")
        return stake_tx_hash

    async def unstake(self, amount_WEI: int) -> str:
        """
        Unstake sFLR tokens to retrieve native FLR tokens.

        Builds and executes a transaction to request unlocking of the specified amount of sFLR
        tokens by calling the `requestUnlock` function on the sFLR contract. The transaction is
        simulated before execution to ensure it will succeed.

        Args:
            amount_WEI (int): The amount of tokens to lock, in wei.

        Returns:
            str: The hexadecimal transaction hash of the unstaking operation, or None if the
                simulation fails.

        Raises:
            ValueError: If the amount_FLR is negative or zero.
            Exception: If the transaction building or execution fails.

        """
        if self.flare_provider.address is None:
            raise ValueError("Wallet address cannot be None.")

        if amount_WEI <= 0:
            raise ValueError("Amount to unstake must be positive")

        impl_contract = self.flare_provider.w3.eth.contract(
            address=self.contracts.flare.sflr,
            abi=load_abi("Sceptre"),  # Torkel
        )
        stake_fn = impl_contract.functions.requestUnlock(amount_WEI)
        stake_tx = await self.flare_provider.build_transaction(
            function_call=stake_fn, from_addr=self.flare_provider.address
        )

        logger.debug("Unstake sFLR to FLR", tx=stake_tx)

        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=load_abi("Sceptre"),
            call_tx=stake_tx,  # Torkel
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated stake transaction was not sucessfull"
            )
            raise Exception(
                "We stop here because the simulated transaction was not sucessfull"
            )

        stake_tx_hash = await self.flare_provider.sign_and_send_transaction(stake_tx)
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            stake_tx_hash  # type: ignore
        )
        logger.debug(f"Stake transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{stake_tx_hash}")
        return stake_tx_hash
