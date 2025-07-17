"""FAssets protocol connector for interacting with FAssets on Flare."""

import logging
from typing import Any, cast

from web3.contract import Contract
from web3.exceptions import Web3Exception

from flare_ai_kit.common.exceptions import FAssetsContractError, FAssetsError
from flare_ai_kit.common.schemas import AgentInfo, FAssetInfo, FAssetType
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings import EcosystemSettings

logger = logging.getLogger(__name__)


class FAssets(Flare):
    """FAssets protocol connector for interacting with FAssets on Flare."""

    def __init__(self, settings: EcosystemSettings) -> None:
        """Initialize FAssets connector."""
        super().__init__(settings)
        self.supported_fassets: dict[str, FAssetInfo] = {}
        self.asset_managers: dict[str, Contract] = {}
        self.fasset_contracts: dict[str, Contract] = {}
        self.sparkdex_router: Contract | None = None

    @classmethod
    async def create(cls, settings: EcosystemSettings) -> "FAssets":
        """Create a new FAssets instance."""
        instance = cls(settings)
        await instance._initialize_sparkdex_router()
        await instance._initialize_supported_fassets()
        return instance

    def get_contract_abi(self, name: str) -> list[Any]:
        """Get contract ABI."""
        try:
            # This would be implemented in the base class or loaded from a file
            return []  # Placeholder
        except Exception as e:
            msg = f"Failed to get ABI for {name}"
            logger.exception(msg)
            raise FAssetsContractError(msg) from e

    async def get_contract(self, name: str, address: str) -> Contract:
        """Get contract instance."""
        try:
            checksum_address = self.w3.to_checksum_address(address)
            contract = self.w3.eth.contract(
                address=checksum_address,
                abi=self.get_contract_abi(name),
            )
            return cast("Contract", contract)
        except Web3Exception as e:
            msg = f"Failed to get contract {name} at {address}"
            logger.exception(msg)
            raise FAssetsContractError(msg) from e

    async def get_contract_address(self, name: str) -> str:
        """Get contract address from registry."""
        try:
            result = await self.contract_registry.functions.getContractAddressByName(
                name
            ).call()
            address = str(result)
            return self.w3.to_checksum_address(address)
        except Web3Exception as e:
            msg = f"Failed to get contract address for {name}"
            logger.exception(msg)
            raise FAssetsContractError(msg) from e

    async def _initialize_sparkdex_router(self) -> None:
        """Initialize SparkDEX router contract."""
        try:
            router_address = await self._get_router_address()
            if router_address:
                self.sparkdex_router = await self.get_contract(
                    "SparkDEXRouter",
                    router_address,
                )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to initialize SparkDEX router", exc_info=True)

    async def _initialize_supported_fassets(self) -> None:
        """Initialize supported FAssets contracts."""
        # For now, we'll use a simplified approach for testing
        # In production, this would query actual contract addresses
        test_fassets = {
            FAssetType.FXRP: True,  # Available in test
            FAssetType.FBTC: False,  # Not available in test
            FAssetType.FDOGE: False,  # Not available in test
        }

        for fasset_type, is_available in test_fassets.items():
            try:
                if is_available:
                    # Create a test FAsset info for available assets
                    fasset_info = FAssetInfo(
                        symbol=fasset_type.value,
                        name=f"Flare {fasset_type.value}",
                        # Mock addresses
                        asset_manager_address="0x1234567890abcdef1234567890abcdef12345678",
                        f_asset_address="0xabcdef1234567890abcdef1234567890abcdef12",
                        underlying_symbol=fasset_type.value[1:],  # Remove 'F' prefix
                        decimals=18,
                        is_active=True,
                    )
                    self.supported_fassets[fasset_type.value] = fasset_info

                    # For testing, we'll create mock contracts with empty ABIs
                    # In production, these would be real contract instances
                    try:
                        self.asset_managers[
                            fasset_type.value
                        ] = await self.get_contract(
                            f"{fasset_type.value}AssetManager",
                            fasset_info.asset_manager_address,
                        )
                        self.fasset_contracts[
                            fasset_type.value
                        ] = await self.get_contract(
                            fasset_type.value,
                            fasset_info.f_asset_address,
                        )
                    except Exception:  # noqa: BLE001
                        # Contract creation failed, but FAsset info is still available
                        logger.warning(
                            "Failed to create contracts for %s",
                            fasset_type.value,
                            exc_info=True,
                        )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to initialize %s", fasset_type.value, exc_info=True
                )

    async def get_supported_fassets(self) -> dict[str, FAssetInfo]:
        """Get information about all supported FAssets."""
        return self.supported_fassets

    async def _get_fasset_info(self, fasset_type: FAssetType) -> FAssetInfo | None:
        """Get information about a specific FAsset."""
        # This method is now unused since we handle initialization directly
        # in _initialize_supported_fassets, but keeping for compatibility
        return self.supported_fassets.get(fasset_type.value)

    async def _get_router_address(self) -> str | None:
        """Get SparkDEX router address from contract registry."""
        try:
            return await self.get_contract_address("SparkDEXRouter")
        except Exception:  # noqa: BLE001
            logger.warning("Failed to get SparkDEX router address", exc_info=True)
            return None

    # === PUBLIC API METHODS FOR QUERYING FASSET STATES ===

    async def get_fasset_info(self, fasset_type: FAssetType) -> FAssetInfo:
        """Get information about a specific FAsset."""
        if fasset_type.value not in self.supported_fassets:
            msg = f"FAsset type {fasset_type.value} is not active on this network"
            raise FAssetsError(msg)
        return self.supported_fassets[fasset_type.value]

    async def get_asset_manager_settings(
        self, fasset_type: FAssetType
    ) -> dict[str, Any]:
        """Get asset manager settings for a specific FAsset."""
        if fasset_type.value not in self.asset_managers:
            msg = "Asset manager not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would call contract methods
        return {
            "collateral_ratio": 150,  # 150% collateralization
            "mint_fee": 0.01,  # 1% minting fee
            "redeem_fee": 0.01,  # 1% redemption fee
            "liquidation_threshold": 120,  # 120% liquidation threshold
        }

    async def get_all_agents(self, fasset_type: FAssetType) -> list[AgentInfo]:
        """Get all agents for a specific FAsset."""
        if fasset_type.value not in self.asset_managers:
            msg = "Asset manager not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would call contract methods
        return [
            AgentInfo(
                agent_address="0x1234567890abcdef1234567890abcdef12345678",
                name="Mock Agent 1",
                description="Mock agent 1 for testing",
                icon_url="https://example.com/icon1.png",
                info_url="https://example.com/info1",
                vault_collateral_token=(
                    "0x" + "1234567890abcdef1234567890abcdef12345678"
                ),
                fee_share=100,
                mint_count=100,
                remaining_wnat=5000,
                free_underlying_balance_usd=1000,
                all_lots=20,
                available_lots=15,
            )
        ]

    async def get_agent_info(
        self, fasset_type: FAssetType, agent_address: str
    ) -> AgentInfo:
        """Get information about a specific agent."""
        if fasset_type.value not in self.asset_managers:
            msg = "Asset manager not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would call contract methods
        return AgentInfo(
            agent_address=agent_address,
            name="Mock Agent",
            description="Mock agent for testing",
            icon_url="https://example.com/icon.png",
            info_url="https://example.com/info",
            vault_collateral_token=("0x" + "1234567890abcdef1234567890abcdef12345678"),
            fee_share=100,
            mint_count=50,
            remaining_wnat=3000,
            free_underlying_balance_usd=750,
            all_lots=10,
            available_lots=8,
        )

    async def get_available_lots(
        self, fasset_type: FAssetType, _agent_address: str
    ) -> int:
        """Get available lots for a specific agent."""
        if fasset_type.value not in self.asset_managers:
            msg = "Asset manager not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would call contract methods
        return 25

    async def get_collateral_reservation_data(
        self, fasset_type: FAssetType, reservation_id: int
    ) -> dict[str, Any]:
        """Get collateral reservation data."""
        if fasset_type.value not in self.asset_managers:
            msg = "Asset manager not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would call contract methods
        return {
            "reservation_id": reservation_id,
            "agent_vault": "0x1234567890abcdef1234567890abcdef12345678",
            "lots": 10,
            "fee": 100000,
            "deadline": 1234567890,
        }

    async def get_redemption_request(
        self, fasset_type: FAssetType, request_id: int
    ) -> dict[str, Any]:
        """Get redemption request data."""
        if fasset_type.value not in self.asset_managers:
            msg = "Asset manager not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would call contract methods
        return {
            "request_id": request_id,
            "redeemer": "0x1234567890abcdef1234567890abcdef12345678",
            "lots": 5,
            "fee": 50000,
            "deadline": 1234567890,
        }

    # === FASSET TOKEN OPERATIONS ===

    async def get_fasset_balance(self, fasset_type: FAssetType, _address: str) -> int:
        """Get FAsset balance for an address."""
        if fasset_type.value not in self.fasset_contracts:
            msg = "FAsset contract not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would call contract methods
        return 1000000  # Return balance in wei

    async def get_fasset_allowance(
        self, fasset_type: FAssetType, _owner: str, _spender: str
    ) -> int:
        """Get FAsset allowance."""
        if fasset_type.value not in self.fasset_contracts:
            msg = "FAsset contract not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would call contract methods
        return 500000  # Return allowance in wei

    async def approve_fasset(
        self, fasset_type: FAssetType, _spender: str, _amount: int
    ) -> str:
        """Approve FAsset spending."""
        if fasset_type.value not in self.fasset_contracts:
            msg = "FAsset contract not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would build and send transaction
        return "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

    # === MINTING OPERATIONS ===

    async def reserve_collateral(
        self,
        fasset_type: FAssetType,
        agent_vault: str,
        lots: int,
        max_minting_fee_bips: int,
        executor: str,
    ) -> dict[str, Any]:
        """Reserve collateral for minting."""
        if fasset_type.value not in self.asset_managers:
            msg = "Asset manager not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would build and send transaction
        return {
            "reservation_id": 12345,
            "agent_vault": agent_vault,
            "lots": lots,
            "fee": max_minting_fee_bips,
            "executor": executor,
            "deadline": 1234567890,
        }

    async def execute_minting(
        self,
        fasset_type: FAssetType,
        _collateral_reservation_id: int,
        _payment_reference: str,
        _recipient: str,
    ) -> str:
        """Execute minting after collateral reservation."""
        if fasset_type.value not in self.asset_managers:
            msg = "Asset manager not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would build and send transaction
        return "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

    # === REDEMPTION OPERATIONS ===

    async def redeem_from_agent(
        self,
        fasset_type: FAssetType,
        lots: int,
        max_redemption_fee_bips: int,
        underlying_address: str,
        executor: str,
    ) -> dict[str, Any]:
        """Redeem FAssets from an agent."""
        if fasset_type.value not in self.asset_managers:
            msg = "Asset manager not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would build and send transaction
        return {
            "request_id": 67890,
            "lots": lots,
            "fee": max_redemption_fee_bips,
            "underlying_address": underlying_address,
            "executor": executor,
            "deadline": 1234567890,
        }

    # === SWAP OPERATIONS ===

    async def swap_fasset_for_native(
        self,
        fasset_type: FAssetType,
        amount_in: int,
        _amount_out_min: int,
        _deadline: int,
    ) -> str:
        """Swap FAsset for native FLR/SGB."""
        if self.sparkdex_router is None:
            msg = "SparkDEX router not initialized"
            raise FAssetsError(msg)

        if fasset_type.value not in self.fasset_contracts:
            msg = "FAsset contract not found"
            raise FAssetsError(msg)

        # Check and approve if needed
        allowance = await self.get_fasset_allowance(
            fasset_type,
            str(self.address),
            self.sparkdex_router.address,
        )

        if allowance < amount_in:
            await self.approve_fasset(
                fasset_type, self.sparkdex_router.address, amount_in
            )

        # Placeholder implementation - would build and send swap transaction
        msg = (
            "Swap FAsset for native failed: "
            "Transaction logic not implemented for test environment"
        )
        raise FAssetsContractError(msg)

    async def swap_native_for_fasset(
        self,
        fasset_type: FAssetType,
        _amount_out_min: int,
        _deadline: int,
        _amount_in: int,
    ) -> str:
        """Swap native FLR/SGB for FAsset."""
        if self.sparkdex_router is None:
            msg = "SparkDEX router not initialized"
            raise FAssetsError(msg)

        if fasset_type.value not in self.fasset_contracts:
            msg = "FAsset contract not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would build and send swap transaction
        msg = (
            "Swap native for FAsset failed: "
            "Transaction logic not implemented for test environment"
        )
        raise FAssetsContractError(msg)

    async def swap_fasset_for_fasset(
        self,
        fasset_type_from: FAssetType,
        fasset_type_to: FAssetType,
        _amount_in: int,
        _amount_out_min: int,
        _deadline: int,
    ) -> str:
        """Swap one FAsset for another."""
        if self.sparkdex_router is None:
            msg = "SparkDEX router not initialized"
            raise FAssetsError(msg)

        if fasset_type_from.value not in self.fasset_contracts:
            msg = "FAsset contract not found"
            raise FAssetsError(msg)

        if fasset_type_to.value not in self.fasset_contracts:
            msg = "FAsset contract not found"
            raise FAssetsError(msg)

        # Placeholder implementation - would build and send swap transaction
        msg = (
            "Swap FAsset for FAsset failed: "
            "Transaction logic not implemented for test environment"
        )
        raise FAssetsContractError(msg)
