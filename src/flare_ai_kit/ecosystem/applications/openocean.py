import logging
from typing import Any

import requests
import structlog
from eth_typing import ChecksumAddress, HexStr
from web3 import Web3
from web3.types import TxParams, Wei

from flare_ai_kit.ecosystem import (
    Contracts,
    EcosystemSettings,
)
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

logger = structlog.get_logger(__name__)


class OpenOcean:
    @classmethod
    async def create(
        cls,
        settings: EcosystemSettings,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        provider: Flare,
    ) -> "OpenOcean":
        instance = cls(
            settings=settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            provider=provider,
        )
        instance.validate_config()
        return instance

    def __init__(
        self,
        settings: EcosystemSettings,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        provider: Flare,
    ) -> None:
        if not settings.account_address:
            raise Exception("Please set settings.account_address in your .env file.")
        self.settings = settings
        self.contracts = contracts
        self.account_address = settings.account_address
        self.flare_explorer = flare_explorer
        self.provider = provider

    def validate_config(self) -> None:
        """Validate that all required configuration attributes are set and valid."""
        logger.info(f"Validating configuration for {self.__class__.__name__}")
        errors: list[str] = []

        print(f"self.account_address: {self.account_address}")
        print(
            f"Web3.is_address(self.account_address): {Web3.is_address(self.account_address)}"
        )

        # Validate settings.account_address
        if not self.account_address:
            errors.append("settings.account_address is not set")
        elif not Web3.is_address(self.account_address):
            errors.append(
                f"settings.account_address ({self.account_address}) is not a valid Ethereum address"
            )
        elif not Web3.is_checksum_address(self.account_address):
            errors.append(
                f"settings.account_address ({self.account_address}) is not a checksummed Ethereum address"
            )

        # Validate contracts.flare.openocean_exchangeV2
        if not hasattr(self.contracts, "flare") or not hasattr(
            self.contracts.flare, "openocean_exchangeV2"
        ):
            errors.append("contracts.flare.openocean_exchangeV2 is not set")
        elif not Web3.is_address(self.contracts.flare.openocean_exchangeV2):
            errors.append(
                f"contracts.flare.openocean_exchangeV2 ({self.contracts.flare.openocean_exchangeV2}) is not a valid Ethereum address"
            )
        elif not Web3.is_checksum_address(self.contracts.flare.openocean_exchangeV2):
            errors.append(
                f"contracts.flare.openocean_exchangeV2 ({self.contracts.flare.openocean_exchangeV2}) is not a checksummed Ethereum address"
            )

        # Validate provider.address
        if not hasattr(self.provider, "address") or not self.provider.address:
            errors.append("provider.address is not set")
        elif not Web3.is_address(self.provider.address):
            errors.append(
                f"provider.address ({self.provider.address}) is not a valid Ethereum address"
            )
        elif not Web3.is_checksum_address(self.provider.address):
            errors.append(
                f"provider.address ({self.provider.address}) is not a checksummed Ethereum address"
            )

        if not self.settings.openocean_token_list:
            errors.append("settings.openocean_token_list is not set")
        if not self.settings.openocean_gas_price:
            errors.append("settings.openocean_gas_price is not set")
        if not self.settings.openocean_swap:
            errors.append("settings.openocean_swap is not set")

        # Log and raise errors if any
        if errors:
            error_msg = f"Configuration errors in {self.__class__.__name__}: {', '.join(errors)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def swap(
        self, token_in_str: str, token_out_str: str, amount: int, speed: str
    ) -> str | None:
        """
        Execute a token swap on OpenOcean DEX.

        This function performs a complete token swap operation by:
        1. Converting the input amount to WEI units
        2. Fetching token information and gas prices from OpenOcean API
        3. Checking and setting token allowances if necessary
        4. Building the swap transaction
        5. Executing the swap on-chain

        Args:
            token_in_str (str): Symbol of the input token (e.g., 'FLR', 'USDC')
            token_out_str (str): Symbol of the output token (e.g., 'WFLR', 'USDT')
            amount (int): Amount of input tokens to swap (with decimals, e.g. WEI for ETH)
            speed (str): Transaction speed setting for gas pricing ('low', 'medium', 'high')

        Returns:
            str | None: Transaction hash of the executed swap, or None if failed

        Raises:
            Exception: If token allowance approval fails or swap execution fails

        Example:
            >>> hash = await openocean.swap('FLR', 'USDC', 100.0, 'medium')
            >>> print(f"Swap completed: {hash}")

        """
        if self.provider.address is None:
            raise ValueError("Wallet address cannot be None.")

        amount_WEI = self.provider.w3.to_wei(amount, unit="ether")

        # Get token info
        tokens = self.get_token_info()

        # Get gasPrice
        gas_price = self.get_gas_price(speed)

        # Check and set a token allowance (if needed)
        allowance = await self.provider.erc20_allowance(
            owner_address=self.provider.address,
            token_address=Web3.to_checksum_address(tokens[token_in_str]),
            spender_address=self.contracts.flare.openocean_exchangeV2,
        )
        logger.debug(
            f"Allowance is {allowance}. This is {round(100 * allowance / amount_WEI, 2)}% of amount."
        )

        if allowance < amount_WEI:
            await self.provider.erc20_approve(
                token_address=tokens[token_in_str],
                spender_address=self.contracts.flare.openocean_exchangeV2,
                amount=amount_WEI,
            )

        # Get transaction body
        tx_body = self.get_transaction_body(
            tokens[token_in_str], tokens[token_out_str], gas_price, amount
        )

        # Send transaction and signature
        hash = await self.execute_swap(tx_body)

        return hash

    def get_token_info(self) -> dict[str, ChecksumAddress]:
        """
        Fetches token information from OpenOcean API.

        Returns:
            dict: Dictionary mapping token symbols to their contract addresses

        Raises:
            requests.RequestException: If the API request fails
            KeyError: If the response format is unexpected

        Example:
            >>> tokens = self.get_token_info()
            >>> print(tokens['FLR'])  # Returns FLR token address

        """
        response = requests.get(self.settings.openocean_token_list)

        if response.status_code == 200:
            data = response.json()
            token = {
                token["symbol"].upper(): Web3.to_checksum_address(token["address"])
                for token in data["data"]
            }
            return token
        logging.error(f"Error occurred: {response.text}")
        raise Exception(
            f"Got status != 200 from token info request in get_token_info: {response.text}"
        )

    def get_gas_price(self, speed: str):
        """
        Fetches gas price information from OpenOcean API.

        Args:
            speed (str): Gas speed preference ('low', 'medium', 'high')

        Returns:
            int: Gas price in wei for the specified speed

        Raises:
            requests.RequestException: If the API request fails
            KeyError: If the response format is unexpected

        Example:
            >>> gas_price = self.get_gas_price('medium')
            >>> print(f"Gas price: {gas_price} wei")

        """
        response = requests.get(self.settings.openocean_gas_price)
        if response.status_code == 200:
            data = response.json()
            return data["data"][speed]
        error_msg = f"Error occurred: {response.text}"
        logger.error(error_msg)
        raise requests.RequestException(error_msg)

    def get_transaction_body(
        self,
        token_in_addr: str,
        token_out_addr: str,
        gas_price: int,
        amount: float,
        slippage: int = 1,
    ) -> dict[str, Any]:
        """
        Fetches swap transaction data from OpenOcean API.

        Args:
            token_in_addr (str): Input token address
            token_out_addr (str): Output token address
            gas_price (int): Gas price in wei
            amount (float): Amount to swap
            slippage (int): Slippage tolerance percentage (default: 1)

        Returns:
            dict: Transaction data for the swap

        Raises:
            requests.RequestException: If the API request fails
            KeyError: If the response format is unexpected

        Example:
            >>> tx_data = self.get_transaction_body('0x123...', '0x456...', 20000000000, 1.5, 2)
            >>> print(tx_data['to'])  # Returns destination address

        """
        params = {
            "inTokenAddress": token_in_addr,
            "outTokenAddress": token_out_addr,
            "slippage": slippage,
            "amountDecimals": amount,
            "gasPriceDecimals": gas_price,
            "account": self.provider.address,
            "referrer": self.provider.address,
        }
        logger.info(
            "Request about to be sent: ",
            url=self.settings.openocean_swap,
            params=params,
        )
        response = requests.get(self.settings.openocean_swap, params=params)

        if response.status_code == 200:
            data = response.json()
            return data["data"]

        logger.error(f"Error occurred: {response.text}")
        raise Exception(
            f"Got status != 200 back from transaction body request in get_transaction_body(): {response.text}"
        )

    async def execute_swap(self, data: dict[str, Any]) -> str:
        """
        Executes a swap transaction using the OpenOcean DEX.

        Args:
            data (dict): Transaction data containing swap details

        Returns:
            str | None: Transaction hash of the executed swap, or None if failed

        Raises:
            Exception: If gas estimation fails

        Example:
            >>> hash = await self.execute_swap(tx_data)
            >>> print(f"Swap transaction hash: {hash}")

        """
        base_tx_params = await self.provider.prepare_base_tx_params(
            Web3.to_checksum_address(data["from"])
        )

        tx_params: TxParams = {
            **base_tx_params,  # includes from, nonce, maxFeePerGas, maxPriorityFeePerGas, chainId, type
            "to": Web3.to_checksum_address(data["to"]),
            "value": Wei(int(data["value"])),
            "data": HexStr(data["data"]),
        }

        gas_estimate = await self.provider.estimate_gas(tx_params)
        if gas_estimate is None:
            raise Exception("Gas estimation failed")

        tx_params["gas"] = gas_estimate

        hash = await self.provider.sign_and_send_transaction(tx_params)
        if hash:
            return hash
        raise Exception(
            "No hash returned from sign_and_send_transaction() in execute_swap()"
        )

    def get_abi(self) -> list[dict[str, Any]]:
        return [
            {
                "constant": False,
                "inputs": [
                    {"internalType": "address", "name": "caller", "type": "address"},
                    {
                        "components": [
                            {
                                "internalType": "address",
                                "name": "srcToken",
                                "type": "address",
                            },
                            {
                                "internalType": "address",
                                "name": "dstToken",
                                "type": "address",
                            },
                            {
                                "internalType": "address",
                                "name": "srcReceiver",
                                "type": "address",
                            },
                            {
                                "internalType": "address",
                                "name": "dstReceiver",
                                "type": "address",
                            },
                            {
                                "internalType": "uint256",
                                "name": "amount",
                                "type": "uint256",
                            },
                            {
                                "internalType": "uint256",
                                "name": "minReturnAmount",
                                "type": "uint256",
                            },
                            {
                                "internalType": "uint256",
                                "name": "guaranteedAmount",
                                "type": "uint256",
                            },
                            {
                                "internalType": "uint256",
                                "name": "flags",
                                "type": "uint256",
                            },
                            {
                                "internalType": "address",
                                "name": "referrer",
                                "type": "address",
                            },
                            {
                                "internalType": "bytes",
                                "name": "permit",
                                "type": "bytes",
                            },
                        ],
                        "internalType": "struct IOpenOceanCaller.SwapDescription",
                        "name": "desc",
                        "type": "tuple",
                    },
                    {
                        "components": [
                            {
                                "internalType": "address",
                                "name": "target",
                                "type": "address",
                            },
                            {
                                "internalType": "uint256",
                                "name": "gasLimit",
                                "type": "uint256",
                            },
                            {
                                "internalType": "uint256",
                                "name": "value",
                                "type": "uint256",
                            },
                            {"internalType": "bytes", "name": "data", "type": "bytes"},
                        ],
                        "internalType": "struct IOpenOceanCaller.CallDescription[]",
                        "name": "calls",
                        "type": "tuple[]",
                    },
                ],
                "name": "swap",
                "outputs": [
                    {
                        "internalType": "uint256",
                        "name": "returnAmount",
                        "type": "uint256",
                    }
                ],
                "payable": True,
                "stateMutability": "payable",
                "type": "function",
            }
        ]
