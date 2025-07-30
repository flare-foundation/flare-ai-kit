
import structlog

from flare_ai_kit.ecosystem import (
    Contracts,
    EcosystemSettingsModel,
)
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

logger = structlog.get_logger(__name__)


class Kinetic:
    @classmethod
    async def create(
        cls,
        settings: EcosystemSettingsModel,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
    ) -> "Kinetic":
        """
        Asynchronously create a Kinetic instance with the provided configuration.

        Args:
            settings (EcosystemSettingsModel): Configuration settings, including account details.
            contracts (Contracts): Contract addresses for the Flare blockchain.
            flare_explorer (BlockExplorer): Block explorer instance for transaction queries.
            flare_provider (Flare): Provider instance for blockchain interactions.

        Returns:
            Kinetic: An initialized Kinetic instance.
        """
        instance = cls(
            settings=settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )
        return instance

    def __init__(
        self,
        settings: EcosystemSettingsModel,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
    ) -> None:
        """
        Initialize a Kinetic instance with configuration and dependencies.

        Args:
            settings (EcosystemSettingsModel): Configuration settings, including account address and private key.
            contracts (Contracts): Contract addresses for the Flare blockchain.
            flare_explorer (BlockExplorer): Block explorer instance for transaction queries.
            flare_provider (Flare): Provider instance for blockchain interactions.

        Raises:
            Exception: If account_private_key or account_address is not set in the settings.
        """
        self.settings = settings  # Store settings for test compatibility
        self.contracts = contracts
        self.account_private_key = settings.account_private_key
        self.account_address = settings.account_address
        self.flare_explorer = flare_explorer
        self.flare_provider = flare_provider

        if not self.account_private_key or not self.account_address:
            raise Exception(
                "Please set self.account_private_key and self.account_address in your .env file."
            )

    def get_addresses(self, token: str) -> (str, str):
        """
        Retrieve the token address and corresponding Kinetic lending contract address for a specified token.

        Args:
            token (str): The token symbol (case-insensitive). Supported values are "sflr", "usdce", "weth", "usdt", or "flreth".

        Returns:
            Tuple[str, str]: A tuple containing:
                - token_address (str): The Ethereum address of the specified token.
                - lending_address (str): The Ethereum address of the corresponding Kinetic lending contract.

        Raises:
            Exception: If the token is not supported, raises an exception with the message "Unsupported token".
        """
        token = token.lower()
        match token:
            case "sflr":
                token_address = self.contracts.flare.sflr
                lending_address = self.contracts.flare.kinetic_ksflr
            case "usdce":
                token_address = self.contracts.flare.usdce
                lending_address = self.contracts.flare.kinetic_kUSDCe
            case "weth":
                token_address = self.contracts.flare.weth
                lending_address = self.contracts.flare.kinetic_kwETH
            case "usdt":
                token_address = self.contracts.flare.usdt
                lending_address = self.contracts.flare.kinetic_kUSDT
            case "flreth":
                token_address = self.contracts.flare.flreth
                lending_address = self.contracts.flare.kinetic_kFLRETH
            case _:
                raise Exception("Unsupported token")

        return token_address, lending_address

    async def supply(self, token: str, amount: float) -> str:
        """
        Supply a specified amount of tokens to a Kinetic lending contract.

        This method approves the lending contract to spend the tokens if necessary, builds a mint transaction to supply
        liquidity, simulates the transaction, and executes it on the Flare blockchain.

        Args:
            token (str): The token to supply (case-insensitive, e.g., "sflr", "usdce", "weth", "usdt", "flreth").
            amount (float): The amount of tokens to supply, in ether units.

        Returns:
            str: The hexadecimal transaction hash of the supply operation.

        Raises:
            Exception: If the token is unsupported or transaction building fails.
        """
        amount_WEI = self.flare_provider.w3.to_wei(amount, unit="ether")

        # ======== Get addresses from token string ==============
        token_address, lending_address = self.get_addresses(token)

        # ============= Give allowance if needed  ===============
        allowance = await self.flare_provider.erc20_allowance(
            owner_address=self.flare_provider.address,
            token_address=token_address,
            spender_address=self.contracts.flare.sparkdex_swap_router,
        )
        logger.debug(
            f"Allowance is {allowance}. This is {round(100 * allowance / amount_WEI, 2)}% of amount."
        )

        if allowance < amount_WEI:
            await self.flare_provider.erc20_approve(
                token_address=token_address,
                spender_address=lending_address,
                amount=amount_WEI,
            )

        # ============= Build transaction ================
        lending_contract = await self.flare_provider.w3.eth.contract(
            address=lending_address, abi=self.get_lending_contract_abi()
        )

        mint_fn = lending_contract.functions.mint(amount_WEI)
        mint_tx = await self.flare_provider.build_transaction(
            function_call=mint_fn, from_addr=self.flare_provider.address
        )

        logger.debug("mint", tx=mint_tx)

        # ============= Simulate transaction ================
        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=self.get_lending_contract_abi(), call_tx=mint_tx
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated transaction was not successful"
            )
            return None

        # ============= Execute transaction ================
        mint_tx_hash = await self.flare_provider.sign_and_send_transaction(mint_tx)
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            mint_tx_hash
        )
        logger.debug(f"mint transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{mint_tx_hash}")

        return mint_tx_hash

    async def withdraw(self, token: str, amount: float) -> str:
        """
        Withdraw a specified amount of tokens from a Kinetic lending contract.

        This method builds a transaction to call the redeemUnderlying function, simulates the transaction, and
        executes it on the Flare blockchain.

        Args:
            token (str): The token to withdraw (case-insensitive, e.g., "sflr", "usdce", "weth", "usdt", "flreth").
            amount (float): The amount of tokens to withdraw, in ether units.

        Returns:
            str: The hexadecimal transaction hash of the withdraw operation.

        Raises:
            Exception: If the token is unsupported or transaction building fails.
        """
        amount_WEI = self.flare_provider.w3.to_wei(amount, unit="ether")

        # ============= Map token string to addresses ================
        token_address, lending_address = self.get_addresses(token)

        # ============= Build transaction ================
        lending_contract = await self.flare_provider.w3.eth.contract(
            address=lending_address, abi=self.get_lending_contract_abi()
        )

        withdraw_fn = lending_contract.functions.redeemUnderlying(amount_WEI)
        withdraw_tx = await self.flare_provider.build_transaction(
            function_call=withdraw_fn, from_addr=self.flare_provider.address
        )

        logger.debug("withdraw", tx=withdraw_tx)

        # ============= Simulate transaction ================
        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=self.get_lending_contract_abi(), call_tx=withdraw_tx
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated transaction was not successful"
            )
            return None

        # ============= Execute transaction ================
        withdraw_tx_hash = await self.flare_provider.sign_and_send_transaction(
            withdraw_tx
        )
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            withdraw_tx_hash
        )
        logger.debug(f"withdraw transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{withdraw_tx_hash}")

        return withdraw_tx_hash

    async def enable_collateral(self, token: str) -> str:
        """
        Enable a token as collateral in the Kinetic Unitroller contract.

        This method calls the enterMarkets function in the Unitroller contract to enable the specified token's
        lending contract as collateral.

        Args:
            token (str): The token to enable as collateral (case-insensitive, e.g., "sflr", "usdce", "weth", "usdt", "flreth").

        Returns:
            str: The hexadecimal transaction hash of the enable collateral operation.

        Raises:
            Exception: If the token is unsupported or transaction building fails.
        """
        # ============= Map token string to addresses ================
        token_address, lending_address = self.get_addresses(token)

        # ============= Build transaction ================
        unitroller_contract = await self.flare_provider.w3.eth.contract(
            address=self.contracts.flare.kinetic_Unitroller,
            abi=self.get_unitroller_contract_abi(),
        )

        enable_col_fn = unitroller_contract.functions.enterMarkets([lending_address])
        enable_col_tx = await self.flare_provider.build_transaction(
            function_call=enable_col_fn, from_addr=self.flare_provider.address
        )
        logger.debug("enable_col", tx=enable_col_tx)

        # ============= Simulate transaction ================
        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=self.get_unitroller_contract_abi(), call_tx=enable_col_tx
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated transaction was not successful"
            )
            return None

        # ============= Execute transaction ================
        enable_col_tx_hash = await self.flare_provider.sign_and_send_transaction(
            enable_col_tx
        )
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            enable_col_tx_hash
        )
        logger.debug(f"enable_col transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{enable_col_tx_hash}")

        return enable_col_tx_hash

    async def disable_collateral(self, token: str) -> str:
        """
        Disable a token as collateral in the Kinetic Unitroller contract.

        This method calls the exitMarket function in the Unitroller contract to disable the specified token's
        lending contract as collateral.

        Args:
            token (str): The token to disable as collateral (case-insensitive, e.g., "sflr", "usdce", "weth", "usdt", "flreth").

        Returns:
            str: The hexadecimal transaction hash of the disable collateral operation.

        Raises:
            Exception: If the token is unsupported or transaction building fails.
        """
        # ============= Map token string to addresses ================
        token_address, lending_address = self.get_addresses(token)

        # ============= Build transaction ================
        unitroller_contract = await self.flare_provider.w3.eth.contract(
            address=self.contracts.flare.kinetic_Unitroller,
            abi=self.get_unitroller_contract_abi(),
        )

        disable_col_fn = unitroller_contract.functions.exitMarket(lending_address)
        disable_col_tx = await self.flare_provider.build_transaction(
            function_call=disable_col_fn, from_addr=self.flare_provider.address
        )
        logger.debug("disable_col", tx=disable_col_tx)

        # ============= Simulate transaction ================
        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=self.get_unitroller_contract_abi(), call_tx=disable_col_tx
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated transaction was not successful"
            )
            return None

        # ============= Execute transaction ================
        disable_col_tx_hash = await self.flare_provider.sign_and_send_transaction(
            disable_col_tx
        )
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            disable_col_tx_hash
        )
        logger.debug(f"disable_col transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{disable_col_tx_hash}")

        return disable_col_tx_hash

    def get_unitroller_contract_abi(self) -> list:
        """
        Retrieve the ABI for the Kinetic Unitroller contract.

        Returns:
            list: The ABI (Application Binary Interface) for the Unitroller contract, defining functions like enterMarkets and exitMarket.
        """
        return [
            {
                "constant": False,
                "inputs": [
                    {
                        "internalType": "address[]",
                        "name": "cTokens",
                        "type": "address[]",
                    }
                ],
                "name": "enterMarkets",
                "outputs": [
                    {"internalType": "uint256[]", "name": "", "type": "uint256[]"}
                ],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "constant": False,
                "inputs": [
                    {
                        "internalType": "address",
                        "name": "cTokenAddress",
                        "type": "address",
                    }
                ],
                "name": "exitMarket",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "constant": False,
                "inputs": [
                    {"internalType": "uint8", "name": "rewardType", "type": "uint8"},
                    {
                        "internalType": "address payable",
                        "name": "holder",
                        "type": "address",
                    },
                ],
                "name": "claimReward",
                "outputs": [],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "constant": False,
                "inputs": [
                    {"internalType": "uint8", "name": "rewardType", "type": "uint8"},
                    {
                        "internalType": "address payable",
                        "name": "holder",
                        "type": "address",
                    },
                    {
                        "internalType": "contract CToken[]",
                        "name": "cTokens",
                        "type": "address[]",
                    },
                ],
                "name": "claimReward",
                "outputs": [],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "constant": False,
                "inputs": [
                    {"internalType": "uint8", "name": "rewardType", "type": "uint8"},
                    {
                        "internalType": "address payable[]",
                        "name": "holders",
                        "type": "address[]",
                    },
                    {
                        "internalType": "contract CToken[]",
                        "name": "cTokens",
                        "type": "address[]",
                    },
                    {"internalType": "bool", "name": "borrowers", "type": "bool"},
                    {"internalType": "bool", "name": "suppliers", "type": "bool"},
                ],
                "name": "claimReward",
                "outputs": [],
                "payable": True,
                "stateMutability": "payable",
                "type": "function",
            },
        ]

    def get_lending_contract_abi(self) -> list:
        """
        Retrieve the ABI for the Kinetic lending contract.

        Returns:
            list: The ABI (Application Binary Interface) for the lending contract, defining functions like mint and redeemUnderlying.
        """
        return [
            {
                "constant": False,
                "inputs": [
                    {"internalType": "uint256", "name": "mintAmount", "type": "uint256"}
                ],
                "name": "mint",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "constant": False,
                "inputs": [
                    {
                        "internalType": "uint256",
                        "name": "redeemAmount",
                        "type": "uint256",
                    }
                ],
                "name": "redeemUnderlying",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function",
            },
        ]
