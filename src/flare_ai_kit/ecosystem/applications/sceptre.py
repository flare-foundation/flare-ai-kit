from eth_typing import ChecksumAddress
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.types import TxParams, Wei

from flare_ai_kit.common.utils import load_abi
from flare_ai_kit.config import AppSettings
from flare_ai_kit.ecosystem.settings import Contracts


class SceptreClient:
    def __init__(self):
        self.settings = AppSettings().ecosystem
        self.client = AsyncWeb3(
            AsyncHTTPProvider(str(self.settings.web3_provider_url)),
        )
        self.contracts = Contracts()

    async def describe_sceptre_services(self) -> str:
        return """
        Sceptre is bringing a safe, efficient and well-integrated 
        liquid staking experience to the users and ecosystem partners
        on the Flare network.             
        """

    async def get_sceptre_contract_address(self) -> ChecksumAddress | None:
        """
        Get the Sceptre contract address for the current network.
        """
        return self.contracts.flare.sceptre_contract_address

    async def get_current_feed(self):
        """
        Calls the `getCurrentFeed()` method on the contract.
        """
        contract_address = await self.get_sceptre_contract_address()
        if not contract_address:
            raise ValueError(
                "Sceptre contract address is not set for the current network."
            )

        abi = load_abi("sceptre")
        contract = self.client.eth.contract(
            address=contract_address,
            abi=abi,
        )
        try:
            tx_params: TxParams = {"value": Wei(0)}
            value, decimals, timestamp = await contract.functions.getCurrentFeed().call(
                tx_params
            )
            return {
                "value": value,
                "decimals": decimals,
                "timestamp": timestamp,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to fetch current feed from Sceptre: {e}")

    async def get_feed_id(self) -> str:
        """
        Calls the `getFeedId()` method on the contract.
        """
        contract_address = await self.get_sceptre_contract_address()
        if not contract_address:
            raise ValueError(
                "Sceptre contract address is not set for the current network."
            )

        abi = load_abi("sceptre")
        contract = self.client.eth.contract(
            address=contract_address,
            abi=abi,
        )
        try:
            feed_id = await contract.functions.feedId().call()
            return feed_id.decode("utf-8").split("\x00")[0]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch feed ID from Sceptre: {e}")

    async def calculateFee(self) -> int:
        """
        Calls the `calculateFee()` method on the contract.
        """
        contract_address = await self.get_sceptre_contract_address()
        if not contract_address:
            raise ValueError(
                "Sceptre contract address is not set for the current network."
            )

        abi = load_abi("sceptre")
        contract = self.client.eth.contract(
            address=contract_address,
            abi=abi,
        )
        try:
            fee = await contract.functions.calculateFee().call()
            return fee
        except Exception as e:
            raise RuntimeError(f"Failed to calculate fee from Sceptre: {e}")

    async def deposit(self, amount: int, to: ChecksumAddress) -> str:
        """
        Calls the `depositTo()` method on the contract.
        """
        amount = Wei(amount)
        contract_address = await self.get_sceptre_contract_address()
        if not contract_address:
            raise ValueError(
                "Sceptre contract address is not set for the current network."
            )

        abi = load_abi("sceptreWflr")
        contract = self.client.eth.contract(
            address=contract_address,
            abi=abi,
        )
        if self.settings.account_address is None:
            raise ValueError("Address is not set")
        try:
            param: TxParams = {
                "from": self.settings.account_address,
                "value": amount,
                "gas": 300000,
                "gasPrice": self.client.to_wei(50, "gwei"),
                "nonce": await self.client.eth.get_transaction_count(
                    self.settings.account_address
                ),
            }
            tx = await contract.functions.depositTo(to).build_transaction(param)
            if self.settings.account_private_key is None:
                raise ValueError("Private key is not set")
            signed = self.client.eth.account.sign_transaction(
                tx, self.settings.account_private_key.get_secret_value()
            )
            tx_hash = await self.client.eth.send_raw_transaction(signed.raw_transaction)
            return tx_hash.hex()
        except Exception as e:
            raise RuntimeError(f"Failed to deposit to Sceptre: {e}")

    async def withdraw(self, amount: int) -> str:
        """
        Calls the `withdraw()` method on the contract.
        """
        contract_address = await self.get_sceptre_contract_address()
        if not contract_address:
            raise ValueError(
                "Sceptre contract address is not set for the current network."
            )

        abi = load_abi("sceptreWflr")
        contract = self.client.eth.contract(
            address=contract_address,
            abi=abi,
        )
        if self.settings.account_address is None:
            raise ValueError("Address is not set")
        try:
            tx = await contract.functions.withdraw(amount).build_transaction(
                {
                    "from": self.settings.account_address,
                    "gas": 300000,
                    "gasPrice": self.client.to_wei(50, "gwei"),
                    "nonce": await self.client.eth.get_transaction_count(
                        self.settings.account_address
                    ),
                }
            )
            if self.settings.account_private_key is None:
                raise ValueError("Private key is not set")
            signed = self.client.eth.account.sign_transaction(
                tx, self.settings.account_private_key.get_secret_value()
            )
            tx_hash = await self.client.eth.send_raw_transaction(signed.raw_transaction)
            return tx_hash.hex()
        except Exception as e:
            raise RuntimeError(f"Failed to withdraw from Sceptre: {e}")
