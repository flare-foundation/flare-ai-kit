"""Interactions with Flare FAssets protocol."""

from typing import Any, Self, TypeVar

import structlog
from eth_typing import ChecksumAddress

from flare_ai_kit.common import (
    AgentInfo,
    FAssetInfo,
    FAssetsContractError,
    FAssetsError,
    FAssetType,
    load_abi,
)
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings_models import EcosystemSettingsModel

logger = structlog.get_logger(__name__)

# Type variable for the factory method pattern
T = TypeVar("T", bound="FAssets")


class FAssets(Flare):
    """Handles interactions with the FAssets protocol for asset bridging."""

    def __init__(self, settings: EcosystemSettingsModel) -> None:
        super().__init__(settings)
        self.asset_managers: dict[str, Any] = {}  # Will be initialized in 'create'
        self.supported_fassets: dict[str, FAssetInfo] = {}
        self.fasset_contracts: dict[str, Any] = {}  # FAsset ERC20 contracts
        self.sparkdex_router: Any = None  # SparkDEX router for swaps
        self.contracts = settings.contracts  # Store contracts config
        self.is_testnet = settings.is_testnet

    @classmethod
    async def create(cls, settings: EcosystemSettingsModel) -> Self:
        """
        Asynchronously creates and initializes a FAssets instance.

        Args:
            settings: Instance of EcosystemSettingsModel.

        Returns:
            A fully initialized FAssets instance.

        """
        instance = cls(settings)
        logger.debug("Initializing FAssets...")

        # Initialize supported FAssets based on network
        await instance._initialize_supported_fassets()

        # Initialize asset manager contracts
        for fasset_type, fasset_info in instance.supported_fassets.items():
            instance.asset_managers[fasset_type] = instance.w3.eth.contract(
                address=instance.w3.to_checksum_address(
                    fasset_info.asset_manager_address
                ),
                abi=load_abi("AssetManager"),
            )

            # Initialize FAsset ERC20 contracts for swap operations
            instance.fasset_contracts[fasset_type] = instance.w3.eth.contract(
                address=instance.w3.to_checksum_address(fasset_info.f_asset_address),
                abi=load_abi("ERC20"),  # Standard ERC20 ABI
            )

        # Initialize SparkDEX router for swap operations
        await instance._initialize_sparkdex_router()

        logger.debug(
            "FAssets initialized",
            supported_types=list(instance.supported_fassets.keys()),
        )
        return instance

    async def _initialize_sparkdex_router(self) -> None:
        """Initialize SparkDEX router for swap operations."""
        chain_id = await self.w3.eth.chain_id

        # Get the appropriate contract addresses based on network
        if chain_id == 14:  # Flare Mainnet
            router_address = self.contracts.flare.sparkdex_swap_router
        elif chain_id == 114:  # Coston2 testnet
            router_address = self.contracts.coston2.sparkdex_swap_router
        else:
            logger.warning(
                "SparkDEX router not configured for this network", chain_id=chain_id
            )
            return

        if router_address:
            self.sparkdex_router = self.w3.eth.contract(
                address=router_address,
                abi=load_abi("SparkDEXRouter"),
            )
            logger.debug("SparkDEX router initialized", address=router_address)

    async def _initialize_supported_fassets(self) -> None:
        """Initialize supported FAssets based on the network."""
        chain_id = await self.w3.eth.chain_id

        # Real contract addresses for Songbird (FXRP is live)
        if chain_id == 19:  # Songbird (where FXRP is live)
            self.supported_fassets["FXRP"] = FAssetInfo(
                symbol="FXRP",
                name="Flare XRP",
                asset_manager_address="0xf9a84f4ec903f4eab117a9c1098bec078ba7027d",
                f_asset_address="0xf9a84f4ec903f4eab117a9c1098bec078ba7027d",
                underlying_symbol="XRP",
                decimals=6,
                is_active=True,
            )
        elif chain_id == 14:  # Flare Mainnet
            # FAssets contracts to be deployed on Flare Mainnet
            self.supported_fassets["FBTC"] = FAssetInfo(
                symbol="FBTC",
                name="Flare Bitcoin",
                asset_manager_address="0x0000000000000000000000000000000000000000",  # Placeholder
                f_asset_address="0x0000000000000000000000000000000000000000",  # Placeholder
                underlying_symbol="BTC",
                decimals=8,
                is_active=False,  # Coming soon
            )
            self.supported_fassets["FDOGE"] = FAssetInfo(
                symbol="FDOGE",
                name="Flare Dogecoin",
                asset_manager_address="0x33C1E9DEca32864c79161b1AAEc98cAF8D3041fb",
                f_asset_address="0x33C1E9DEca32864c79161b1AAEc98cAF8D3041fb",
                underlying_symbol="DOGE",
                decimals=8,
                is_active=False,  # Coming soon
            )
        elif chain_id in [114, 16]:  # Testnets
            # Add testnet FAssets
            self.supported_fassets["FXRP"] = FAssetInfo(
                symbol="FXRP",
                name="Flare XRP (Testnet)",
                asset_manager_address="0x4140a324d7e60e633bb7cBD7bdcE330FF5702B5E",
                f_asset_address="0x4140a324d7e60e633bb7cBD7bdcE330FF5702B5E",
                underlying_symbol="XRP",
                decimals=6,
                is_active=True,
            )

    async def get_supported_fassets(self) -> dict[str, FAssetInfo]:
        """
        Get information about all supported FAssets.

        Returns:
            Dictionary mapping FAsset symbols to their information.

        """
        return self.supported_fassets.copy()

    async def get_fasset_info(self, fasset_type: FAssetType) -> FAssetInfo:
        """
        Get information about a specific FAsset.

        Args:
            fasset_type: The FAsset type to get information for.

        Returns:
            FAssetInfo object containing the asset information.

        Raises:
            FAssetsError: If the FAsset type is not supported.

        """
        if fasset_type.value not in self.supported_fassets:
            msg = f"FAsset type {fasset_type.value} is not supported on this network"
            raise FAssetsError(msg)

        fasset_info = self.supported_fassets[fasset_type.value]
        if not fasset_info.is_active:
            msg = f"FAsset type {fasset_type.value} is not active on this network"
            raise FAssetsError(msg)

        return fasset_info

    async def get_all_agents(self, fasset_type: FAssetType) -> list[ChecksumAddress]:
        """
        Get all agents for a specific FAsset.

        Args:
            fasset_type: The FAsset type to get agents for.

        Returns:
            List of agent vault addresses.

        Raises:
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.asset_managers:
            msg = f"Asset manager not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            asset_manager = self.asset_managers[fasset_type.value]
            agents = await asset_manager.functions.getAllAgents().call()
            return [self.w3.to_checksum_address(agent) for agent in agents]
        except Exception as e:
            msg = f"Failed to get agents for {fasset_type.value}: {e}"
            raise FAssetsContractError(msg) from e

    async def get_agent_info(
        self, fasset_type: FAssetType, agent_vault: str
    ) -> AgentInfo:
        """
        Get detailed information about a specific agent.

        Args:
            fasset_type: The FAsset type.
            agent_vault: The agent vault address.

        Returns:
            AgentInfo object containing agent details.

        Raises:
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.asset_managers:
            msg = f"Asset manager not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            asset_manager = self.asset_managers[fasset_type.value]
            agent_vault_address = self.w3.to_checksum_address(agent_vault)

            info, status = await asset_manager.functions.getAgentInfo(
                agent_vault_address
            ).call()

            return AgentInfo(
                agent_address=agent_vault_address,
                name=info[2],  # name
                description=info[3],  # description
                icon_url=info[4],  # iconUrl
                info_url=info[5],  # infoUrl
                vault_collateral_token=info[6],  # vaultCollateralToken
                fee_share=info[7],  # feeBIPS
                mint_count=0,  # This would need to be calculated
                remaining_wnat=0,  # This would need to be calculated
                free_underlying_balance_usd=status[3],  # freeUnderlyingBalanceUBA
                all_lots=0,  # This would need to be calculated
                available_lots=0,  # This would need to be calculated separately
            )
        except Exception as e:
            msg = f"Failed to get agent info for {agent_vault}: {e}"
            raise FAssetsContractError(msg) from e

    async def get_available_lots(
        self, fasset_type: FAssetType, agent_vault: str
    ) -> int:
        """
        Get the number of available lots for minting from a specific agent.

        Args:
            fasset_type: The FAsset type.
            agent_vault: The agent vault address.

        Returns:
            Number of available lots.

        Raises:
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.asset_managers:
            msg = f"Asset manager not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            asset_manager = self.asset_managers[fasset_type.value]
            agent_vault_address = self.w3.to_checksum_address(agent_vault)

            available_lots = await asset_manager.functions.getAvailableLots(
                agent_vault_address
            ).call()
            return available_lots
        except Exception as e:
            msg = f"Failed to get available lots for {agent_vault}: {e}"
            raise FAssetsContractError(msg) from e

    async def reserve_collateral(
        self,
        fasset_type: FAssetType,
        agent_vault: str,
        lots: int,
        max_minting_fee_bips: int,
        executor: str,
        executor_fee_nat: int = 0,
    ) -> int:
        """
        Reserve collateral for minting FAssets.

        Args:
            fasset_type: The FAsset type to mint.
            agent_vault: The agent vault address.
            lots: Number of lots to mint.
            max_minting_fee_bips: Maximum minting fee in BIPS.
            executor: Executor address.
            executor_fee_nat: Executor fee in NAT wei.

        Returns:
            Collateral reservation ID.

        Raises:
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.asset_managers:
            msg = f"Asset manager not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            asset_manager = self.asset_managers[fasset_type.value]
            agent_vault_address = self.w3.to_checksum_address(agent_vault)
            executor_address = self.w3.to_checksum_address(executor)

            # Build the transaction
            function_call = asset_manager.functions.reserveCollateral(
                agent_vault_address, lots, max_minting_fee_bips, executor_address
            )

            # Prepare transaction parameters
            tx_params = await self.build_transaction(
                function_call, self.w3.to_checksum_address(self.address)
            )

            if tx_params is None:
                msg = "Failed to build reserve collateral transaction"
                raise FAssetsContractError(msg)

            # Add value for executor fee
            tx_params["value"] = executor_fee_nat

            # Sign and send transaction
            tx_hash = await self.sign_and_send_transaction(tx_params)

            if tx_hash is None:
                msg = "Failed to send reserve collateral transaction"
                raise FAssetsContractError(msg)

            # Wait for transaction receipt and extract collateral reservation ID
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)

            # Extract collateral reservation ID from logs
            # This would need proper event parsing
            logger.info("Collateral reserved", tx_hash=tx_hash)

            raise NotImplementedError(
                "Transaction logic not implemented for test environment"
            )

        except Exception as e:
            msg = f"Failed to reserve collateral: {e}"
            raise FAssetsContractError(msg) from e

    async def get_asset_manager_settings(self, fasset_type: FAssetType) -> dict:
        """
        Get the settings for a specific FAsset's asset manager.

        Args:
            fasset_type: The FAsset type.

        Returns:
            Dictionary containing asset manager settings.

        Raises:
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.asset_managers:
            msg = f"Asset manager not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            asset_manager = self.asset_managers[fasset_type.value]
            settings = await asset_manager.functions.getSettings().call()

            return {
                "asset_name": settings[4],
                "asset_symbol": settings[5],
                "asset_decimals": settings[6],
                "lot_size_amg": settings[23],
                "minting_vault_collateral_ratio": settings[9],
                "minting_pool_collateral_ratio": settings[10],
                "buyback_collateral_ratio": settings[11],
                "redeem_collateral_ratio": settings[12],
            }
        except Exception as e:
            msg = f"Failed to get asset manager settings: {e}"
            raise FAssetsContractError(msg) from e

    async def redeem_from_agent(
        self,
        fasset_type: FAssetType,
        lots: int,
        max_redemption_fee_bips: int,
        underlying_address: str,
        executor: str,
        executor_fee_nat: int = 0,
    ) -> int:
        """
        Redeem FAssets back to underlying assets.

        Args:
            fasset_type: The FAsset type to redeem.
            lots: Number of lots to redeem.
            max_redemption_fee_bips: Maximum redemption fee in BIPS.
            underlying_address: Address on the underlying blockchain to receive assets.
            executor: Executor address.
            executor_fee_nat: Executor fee in NAT wei.

        Returns:
            Redemption request ID.

        Raises:
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.asset_managers:
            msg = f"Asset manager not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            asset_manager = self.asset_managers[fasset_type.value]
            executor_address = self.w3.to_checksum_address(executor)

            # Build the transaction
            function_call = asset_manager.functions.redeemFromAgent(
                lots, max_redemption_fee_bips, underlying_address, executor_address
            )

            # Prepare transaction parameters
            tx_params = await self.build_transaction(
                function_call, self.w3.to_checksum_address(self.address)
            )

            if tx_params is None:
                msg = "Failed to build redemption transaction"
                raise FAssetsContractError(msg)

            # Add value for executor fee
            tx_params["value"] = executor_fee_nat

            # Sign and send transaction
            tx_hash = await self.sign_and_send_transaction(tx_params)

            if tx_hash is None:
                msg = "Failed to send redemption transaction"
                raise FAssetsContractError(msg)

            # Wait for transaction receipt and extract redemption request ID
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)

            # Extract redemption request ID from logs
            # This would need proper event parsing
            logger.info("Redemption requested", tx_hash=tx_hash)

            raise NotImplementedError(
                "Transaction logic not implemented for test environment"
            )

        except Exception as e:
            msg = f"Failed to redeem FAssets: {e}"
            raise FAssetsContractError(msg) from e

    async def get_redemption_request(
        self, fasset_type: FAssetType, request_id: int
    ) -> dict:
        """
        Get details of a redemption request.

        Args:
            fasset_type: The FAsset type.
            request_id: The redemption request ID.

        Returns:
            Dictionary containing redemption request details.

        Raises:
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.asset_managers:
            msg = f"Asset manager not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            asset_manager = self.asset_managers[fasset_type.value]
            request_data = await asset_manager.functions.getRedemptionRequest(
                request_id
            ).call()

            return {
                "agent_vault": request_data[0],
                "redeemer": request_data[1],
                "value_uba": request_data[2],
                "fee_uba": request_data[3],
                "first_underlying_block": request_data[4],
                "last_underlying_block": request_data[5],
                "last_underlying_timestamp": request_data[6],
                "payment_address": request_data[7],
                "executor": request_data[8],
                "executor_fee_nat_wei": request_data[9],
            }
        except Exception as e:
            msg = f"Failed to get redemption request: {e}"
            raise FAssetsContractError(msg) from e

    async def get_collateral_reservation_data(
        self, fasset_type: FAssetType, reservation_id: int
    ) -> dict:
        """
        Get details of a collateral reservation.

        Args:
            fasset_type: The FAsset type.
            reservation_id: The collateral reservation ID.

        Returns:
            Dictionary containing collateral reservation details.

        Raises:
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.asset_managers:
            msg = f"Asset manager not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            asset_manager = self.asset_managers[fasset_type.value]
            reservation_data = (
                await asset_manager.functions.getCollateralReservationData(
                    reservation_id
                ).call()
            )

            return {
                "agent_vault": reservation_data[0],
                "minter": reservation_data[1],
                "value_uba": reservation_data[2],
                "fee_uba": reservation_data[3],
                "first_underlying_block": reservation_data[4],
                "last_underlying_block": reservation_data[5],
                "last_underlying_timestamp": reservation_data[6],
                "payment_address": reservation_data[7],
                "executor": reservation_data[8],
                "executor_fee_nat_wei": reservation_data[9],
            }
        except Exception as e:
            msg = f"Failed to get collateral reservation data: {e}"
            raise FAssetsContractError(msg) from e

    async def get_fasset_balance(self, fasset_type: FAssetType, account: str) -> int:
        """
        Get the FAsset balance for a specific account.

        Args:
            fasset_type: The FAsset type.
            account: The account address.

        Returns:
            FAsset balance in wei.

        Raises:
            FAssetsError: If the FAsset type is not supported.
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.fasset_contracts:
            msg = f"FAsset contract not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            fasset_contract = self.fasset_contracts[fasset_type.value]
            account_address = self.w3.to_checksum_address(account)
            balance = await fasset_contract.functions.balanceOf(account_address).call()
            return balance
        except Exception as e:
            msg = f"Failed to get FAsset balance: {e}"
            raise FAssetsContractError(msg) from e

    async def get_fasset_allowance(
        self, fasset_type: FAssetType, owner: str, spender: str
    ) -> int:
        """
        Get the FAsset allowance for a spender.

        Args:
            fasset_type: The FAsset type.
            owner: The owner address.
            spender: The spender address.

        Returns:
            Allowance amount in wei.

        Raises:
            FAssetsError: If the FAsset type is not supported.
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.fasset_contracts:
            msg = f"FAsset contract not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            fasset_contract = self.fasset_contracts[fasset_type.value]
            owner_address = self.w3.to_checksum_address(owner)
            spender_address = self.w3.to_checksum_address(spender)
            allowance = await fasset_contract.functions.allowance(
                owner_address, spender_address
            ).call()
            return allowance
        except Exception as e:
            msg = f"Failed to get FAsset allowance: {e}"
            raise FAssetsContractError(msg) from e

    async def approve_fasset(
        self,
        fasset_type: FAssetType,
        spender: str,
        amount: int,
    ) -> str:
        """
        Approve a spender to use FAssets.

        Args:
            fasset_type: The FAsset type.
            spender: The spender address.
            amount: Amount to approve in wei.

        Returns:
            Transaction hash.

        Raises:
            FAssetsError: If the FAsset type is not supported.
            FAssetsContractError: If the transaction fails.

        """
        if fasset_type.value not in self.fasset_contracts:
            msg = f"FAsset contract not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            fasset_contract = self.fasset_contracts[fasset_type.value]
            spender_address = self.w3.to_checksum_address(spender)

            # Build the transaction
            function_call = fasset_contract.functions.approve(spender_address, amount)

            # Prepare transaction parameters
            tx_params = await self.build_transaction(
                function_call, self.w3.to_checksum_address(self.address)
            )

            if tx_params is None:
                msg = "Failed to build approve transaction"
                raise FAssetsContractError(msg)

            # Sign and send transaction
            tx_hash = await self.sign_and_send_transaction(tx_params)

            if tx_hash is None:
                msg = "Failed to send approve transaction"
                raise FAssetsContractError(msg)

            logger.info(
                "FAsset approval completed", tx_hash=tx_hash, fasset=fasset_type.value
            )
            return tx_hash.hex()

        except Exception as e:
            msg = f"Failed to approve FAsset: {e}"
            raise FAssetsContractError(msg) from e

    async def swap_fasset_for_native(
        self,
        fasset_type: FAssetType,
        amount_in: int,
        amount_out_min: int,
        deadline: int,
    ) -> str:
        """
        Swap FAsset for native token (SGB/FLR) using SparkDEX.

        Args:
            fasset_type: The FAsset type to swap from.
            amount_in: Amount of FAsset to swap (in wei).
            amount_out_min: Minimum amount of native token to receive (in wei).
            deadline: Transaction deadline timestamp.

        Returns:
            Transaction hash.

        Raises:
            FAssetsError: If swap is not supported.
            FAssetsContractError: If the transaction fails.

        """
        if self.sparkdex_router is None:
            msg = "SparkDEX router not initialized - swaps not available"
            raise FAssetsError(msg)

        if fasset_type.value not in self.fasset_contracts:
            msg = f"FAsset contract not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            fasset_info = self.supported_fassets[fasset_type.value]
            fasset_address = fasset_info.f_asset_address

            # First, ensure we have sufficient allowance for the router
            router_address = self.sparkdex_router.address
            current_allowance = await self.get_fasset_allowance(
                fasset_type, self.address, router_address
            )

            if current_allowance < amount_in:
                # Approve the router to spend our FAssets
                await self.approve_fasset(fasset_type, router_address, amount_in)

            # TODO: Implement actual SparkDEX swap call
            # This would use the router's swapExactTokensForETH or similar function
            # For now, returning placeholder
            logger.info(
                "FAsset to native swap initiated",
                fasset=fasset_type.value,
                amount_in=amount_in,
                amount_out_min=amount_out_min,
            )

            # Placeholder - would implement actual swap transaction
            raise NotImplementedError(
                "Transaction logic not implemented for test environment"
            )

        except Exception as e:
            msg = f"Failed to swap FAsset for native: {e}"
            raise FAssetsContractError(msg) from e

    async def swap_native_for_fasset(
        self,
        fasset_type: FAssetType,
        amount_out_min: int,
        deadline: int,
        amount_in: int,
    ) -> str:
        """
        Swap native token (SGB/FLR) for FAsset using SparkDEX.

        Args:
            fasset_type: The FAsset type to swap to.
            amount_out_min: Minimum amount of FAsset to receive (in wei).
            deadline: Transaction deadline timestamp.
            amount_in: Amount of native token to swap (in wei).

        Returns:
            Transaction hash.

        Raises:
            FAssetsError: If swap is not supported.
            FAssetsContractError: If the transaction fails.

        """
        if self.sparkdex_router is None:
            msg = "SparkDEX router not initialized - swaps not available"
            raise FAssetsError(msg)

        if fasset_type.value not in self.fasset_contracts:
            msg = f"FAsset contract not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            fasset_info = self.supported_fassets[fasset_type.value]
            fasset_address = fasset_info.f_asset_address

            # TODO: Implement actual SparkDEX swap call
            # This would use the router's swapExactETHForTokens or similar function
            logger.info(
                "Native to FAsset swap initiated",
                fasset=fasset_type.value,
                amount_in=amount_in,
                amount_out_min=amount_out_min,
            )

            # Placeholder - would implement actual swap transaction
            raise NotImplementedError(
                "Transaction logic not implemented for test environment"
            )

        except Exception as e:
            msg = f"Failed to swap native for FAsset: {e}"
            raise FAssetsContractError(msg) from e

    async def swap_fasset_for_fasset(
        self,
        fasset_from: FAssetType,
        fasset_to: FAssetType,
        amount_in: int,
        amount_out_min: int,
        deadline: int,
    ) -> str:
        """
        Swap one FAsset for another using SparkDEX.

        Args:
            fasset_from: The FAsset type to swap from.
            fasset_to: The FAsset type to swap to.
            amount_in: Amount of input FAsset to swap (in wei).
            amount_out_min: Minimum amount of output FAsset to receive (in wei).
            deadline: Transaction deadline timestamp.

        Returns:
            Transaction hash.

        Raises:
            FAssetsError: If swap is not supported.
            FAssetsContractError: If the transaction fails.

        """
        if self.sparkdex_router is None:
            msg = "SparkDEX router not initialized - swaps not available"
            raise FAssetsError(msg)

        if fasset_from.value not in self.fasset_contracts:
            msg = f"FAsset contract not found for {fasset_from.value}"
            raise FAssetsError(msg)

        if fasset_to.value not in self.fasset_contracts:
            msg = f"FAsset contract not found for {fasset_to.value}"
            raise FAssetsError(msg)

        try:
            fasset_from_info = self.supported_fassets[fasset_from.value]
            fasset_to_info = self.supported_fassets[fasset_to.value]

            # First, ensure we have sufficient allowance for the router
            router_address = self.sparkdex_router.address
            current_allowance = await self.get_fasset_allowance(
                fasset_from, self.address, router_address
            )

            if current_allowance < amount_in:
                # Approve the router to spend our FAssets
                await self.approve_fasset(fasset_from, router_address, amount_in)

            # TODO: Implement actual SparkDEX swap call
            # This would use the router's swapExactTokensForTokens function
            logger.info(
                "FAsset to FAsset swap initiated",
                fasset_from=fasset_from.value,
                fasset_to=fasset_to.value,
                amount_in=amount_in,
                amount_out_min=amount_out_min,
            )

            # Placeholder - would implement actual swap transaction
            raise NotImplementedError(
                "Transaction logic not implemented for test environment"
            )

        except Exception as e:
            msg = f"Failed to swap FAsset for FAsset: {e}"
            raise FAssetsContractError(msg) from e

    async def execute_minting(
        self,
        fasset_type: FAssetType,
        collateral_reservation_id: int,
        payment_reference: str,
        recipient: str,
    ) -> int:
        """
        Execute minting after collateral reservation and underlying payment.

        Args:
            fasset_type: The FAsset type to mint.
            collateral_reservation_id: The collateral reservation ID.
            payment_reference: Reference of the underlying blockchain payment.
            recipient: Address to receive the minted FAssets.

        Returns:
            Amount of FAssets minted (in wei).

        Raises:
            FAssetsContractError: If the contract call fails.

        """
        if fasset_type.value not in self.asset_managers:
            msg = f"Asset manager not found for {fasset_type.value}"
            raise FAssetsError(msg)

        try:
            asset_manager = self.asset_managers[fasset_type.value]
            recipient_address = self.w3.to_checksum_address(recipient)
            payment_ref_bytes = self.w3.to_bytes(hexstr=payment_reference)

            # Build the transaction
            function_call = asset_manager.functions.executeMinting(
                collateral_reservation_id, payment_ref_bytes, recipient_address
            )

            # Prepare transaction parameters
            tx_params = await self.build_transaction(
                function_call, self.w3.to_checksum_address(self.address)
            )

            if tx_params is None:
                msg = "Failed to build execute minting transaction"
                raise FAssetsContractError(msg)

            # Sign and send transaction
            tx_hash = await self.sign_and_send_transaction(tx_params)

            if tx_hash is None:
                msg = "Failed to send execute minting transaction"
                raise FAssetsContractError(msg)

            # Wait for transaction receipt and extract minted amount
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)

            # TODO: Parse events to extract actual minted amount
            logger.info("Minting executed", tx_hash=tx_hash)

            raise NotImplementedError(
                "Transaction logic not implemented for test environment"
            )

        except Exception as e:
            msg = f"Failed to execute minting: {e}"
            raise FAssetsContractError(msg) from e
