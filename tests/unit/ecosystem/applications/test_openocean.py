import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import requests
from web3 import AsyncWeb3, Web3

from flare_ai_kit.ecosystem import Contracts, EcosystemSettingsModel
from flare_ai_kit.ecosystem.applications.openocean import OpenOcean
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare


class TestOpenOcean(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """
        Set up mock dependencies, mimicking ra_tls_main.py instantiation.
        """
        # Mock EcosystemSettingsModel
        self.settings = MagicMock(spec=EcosystemSettingsModel)
        self.settings.account_address = "0x9e8318cc9c83427870ed8994d818Ba7A92739B99"
        self.settings.openocean_token_list = (
            "https://open-api.openocean.finance/v4/flare/tokenList"
        )
        self.settings.openocean_gas_price = (
            "https://open-api.openocean.finance/v4/flare/gasPrice"
        )
        self.settings.openocean_swap = (
            "https://open-api.openocean.finance/v4/flare/swap"
        )

        # Mock Contracts
        self.contracts = MagicMock(spec=Contracts)
        self.contracts.flare = MagicMock()
        self.contracts.flare.openocean_exchangeV2 = (
            "0x6352a56caadC4F1E25CD6c75970Fa768A3304e64"
        )

        # Mock BlockExplorer
        self.flare_explorer = MagicMock(spec=BlockExplorer)

        # Mock Flare provider
        self.provider = AsyncMock(spec=Flare)
        self.provider.address = "0x9e8318cc9c83427870ed8994d818Ba7A92739B99"
        self.provider.w3 = AsyncMock(spec=AsyncWeb3)
        self.provider.w3.to_wei = Web3.to_wei  # Use real Web3 method for wei conversion

        # Instantiate OpenOcean as in ra_tls_main.py
        self.open_ocean = await OpenOcean.create(
            settings=self.settings,
            contracts=self.contracts,
            flare_explorer=self.flare_explorer,
            provider=self.provider,
        )

    ### Test create method ###
    async def test_create_success(self):
        """
        Test that OpenOcean.create initializes correctly.
        """
        self.assertIsInstance(self.open_ocean, OpenOcean)
        self.assertEqual(self.open_ocean.settings, self.settings)
        self.assertEqual(self.open_ocean.contracts, self.contracts)
        self.assertEqual(self.open_ocean.flare_explorer, self.flare_explorer)
        self.assertEqual(self.open_ocean.provider, self.provider)
        self.assertEqual(self.open_ocean.account_address, self.settings.account_address)

    ### Test validate_config method ###
    def test_validate_config_success(self):
        """
        Test validate_config with valid settings.
        """
        self.open_ocean.validate_config()  # Should not raise

    def test_validate_config_invalid_account_address(self):
        """
        Test validate_config with an invalid account address.
        """
        self.settings.account_address = "0xINVALID"
        open_ocean_tmp = OpenOcean(
            settings=self.settings,
            contracts=self.contracts,
            flare_explorer=self.flare_explorer,
            provider=self.provider,
        )
        with self.assertRaises(Exception) as cm:
            open_ocean_tmp.validate_config()
        self.assertIn("not a valid Ethereum address", str(cm.exception))

    def test_validate_config_missing_token_list_url(self):
        """
        Test validate_config with missing token list URL.
        """
        self.settings.openocean_token_list = None
        with self.assertRaises(Exception) as cm:
            self.open_ocean.validate_config()
        self.assertIn("settings.openocean_token_list is not set", str(cm.exception))

    ### Test swap method ###
    @patch.object(OpenOcean, "get_token_info")
    @patch.object(OpenOcean, "get_gas_price")
    @patch.object(OpenOcean, "get_transaction_body")
    async def test_swap_success_no_approval(
        self, mock_get_transaction_body, mock_get_gas_price, mock_get_token_info
    ):
        """
        Test swap with sufficient allowance, mirroring ra_tls_main.py.
        """
        mock_get_token_info.return_value = {
            "WFLR": "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d",
            "USDT": "0x0B38e83B86d491735fEaa0a791F65c2B99535396",
        }
        mock_get_gas_price.return_value = 25000000000  # 25 Gwei
        mock_get_transaction_body.return_value = {
            "from": self.provider.address,
            "to": self.contracts.flare.openocean_exchangeV2,
            "value": "0",
            "data": "0xabcdef",
        }

        self.provider.erc20_allowance = AsyncMock(
            return_value=2000000000000000000
        )  # 2 WFLR
        self.provider.estimate_gas = AsyncMock(return_value=2233869)
        self.provider.sign_and_send_transaction = AsyncMock(
            return_value="0xf4690a9c5afe7032ba2ce82977aa24b94e6ab61e8afea2ed10bd8087dcbf8496"
        )

        self.provider._prepare_base_tx_params = AsyncMock(
            return_value={
                "from": self.provider.address,
                "nonce": 1,
                "maxFeePerGas": 25000000000,
                "maxPriorityFeePerGas": 2000000000,
                "chainId": 14,
                "type": 2,
            }
        )

        tx_hash = await self.open_ocean.swap("WFLR", "USDT", 1, "standard")
        self.assertEqual(
            tx_hash,
            "0xf4690a9c5afe7032ba2ce82977aa24b94e6ab61e8afea2ed10bd8087dcbf8496",
        )
        self.provider.erc20_approve.assert_not_awaited()

    @patch.object(OpenOcean, "get_token_info")
    @patch.object(OpenOcean, "get_gas_price")
    @patch.object(OpenOcean, "get_transaction_body")
    async def test_swap_with_approval(
        self, mock_get_transaction_body, mock_get_gas_price, mock_get_token_info
    ):
        """
        Test swap when approval is needed.
        """
        mock_get_token_info.return_value = {
            "WFLR": "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d",
            "USDT": "0x0B38e83B86d491735fEaa0a791F65c2B99535396",
        }
        mock_get_gas_price.return_value = 25000000000
        mock_get_transaction_body.return_value = {
            "from": self.provider.address,
            "to": self.contracts.flare.openocean_exchangeV2,
            "value": "0",
            "data": "0xabcdef",
        }

        self.provider.erc20_allowance = AsyncMock(return_value=0)
        self.provider.erc20_approve = AsyncMock(
            return_value="0x1234567890abcdef1234567890abcdef12345678"
        )
        self.provider.estimate_gas = AsyncMock(return_value=2233869)
        self.provider.sign_and_send_transaction = AsyncMock(
            return_value="0xf4690a9c5afe7032ba2ce82977aa24b94e6ab61e8afea2ed10bd8087dcbf8496"
        )

        self.provider._prepare_base_tx_params = AsyncMock(
            return_value={
                "from": self.provider.address,
                "nonce": 1,
                "maxFeePerGas": 25000000000,
                "maxPriorityFeePerGas": 2000000000,
                "chainId": 14,
                "type": 2,
            }
        )

        tx_hash = await self.open_ocean.swap("WFLR", "USDT", 1, "standard")
        self.assertEqual(
            tx_hash,
            "0xf4690a9c5afe7032ba2ce82977aa24b94e6ab61e8afea2ed10bd8087dcbf8496",
        )
        self.provider.erc20_approve.assert_awaited_once_with(
            token_address="0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d",
            spender_address=self.contracts.flare.openocean_exchangeV2,
            amount=1000000000000000000,  # 1 WFLR in wei
        )

    @patch.object(OpenOcean, "get_token_info")
    async def test_swap_invalid_token(self, mock_get_token_info):
        """
        Test swap with an invalid token.
        """
        mock_get_token_info.return_value = {
            "WFLR": "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d"
        }
        self.provider.erc20_allowance = AsyncMock(return_value=0)
        with self.assertRaises(KeyError):
            await self.open_ocean.swap("WFLR", "INVALID", 1, "standard")

    ### Test get_token_info ###
    @patch("requests.get")
    def test_get_token_info_success(self, mock_get):
        """
        Test get_token_info with a successful API response.
        """
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "data": [
                {
                    "symbol": "WFLR",
                    "address": "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d",
                },
                {
                    "symbol": "USDT",
                    "address": "0x0B38e83B86d491735fEaa0a791F65c2B99535396",
                },
            ]
        }
        mock_get.return_value = mock_response

        tokens = self.open_ocean.get_token_info()
        expected = {
            "WFLR": "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d",
            "USDT": "0x0B38e83B86d491735fEaa0a791F65c2B99535396",
        }
        self.assertEqual(tokens, expected)

    @patch("requests.get")
    def test_get_token_info_failure(self, mock_get):
        """
        Test get_token_info with a failed API response.
        """
        mock_get.return_value = MagicMock(status_code=500, text="Server error")
        with self.assertRaises(Exception):
            self.open_ocean.get_token_info()

    ### Test get_gas_price ###
    @patch("requests.get")
    def test_get_gas_price_success(self, mock_get):
        """
        Test get_gas_price with a successful API response.
        """
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"data": {"standard": 25000000000}}
        mock_get.return_value = mock_response

        gas_price = self.open_ocean.get_gas_price("standard")
        self.assertEqual(gas_price, 25000000000)

    @patch("requests.get")
    def test_get_gas_price_failure(self, mock_get):
        """
        Test get_gas_price with a failed API response.
        """
        mock_get.return_value = MagicMock(status_code=500, text="Server error")
        with self.assertRaises(requests.RequestException):
            self.open_ocean.get_gas_price("standard")

    ### Test get_transaction_body ###
    @patch("requests.get")
    def test_get_transaction_body_success(self, mock_get):
        """
        Test get_transaction_body with a successful API response.
        """
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "data": {
                "from": self.provider.address,
                "to": self.contracts.flare.openocean_exchangeV2,
                "value": "0",
                "data": "0xabcdef",
            }
        }
        mock_get.return_value = mock_response

        tx_body = self.open_ocean.get_transaction_body(
            token_in_addr="0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d",
            token_out_addr="0x0B38e83B86d491735fEaa0a791F65c2B99535396",
            gas_price=25000000000,
            amount=1.0,
        )
        expected = {
            "from": self.provider.address,
            "to": self.contracts.flare.openocean_exchangeV2,
            "value": "0",
            "data": "0xabcdef",
        }
        self.assertEqual(tx_body, expected)

    @patch("requests.get")
    def test_get_transaction_body_failure(self, mock_get):
        """
        Test get_transaction_body with a failed API response.
        """
        mock_get.return_value = MagicMock(status_code=500, text="Server error")
        with self.assertRaises(Exception):
            self.open_ocean.get_transaction_body(
                token_in_addr="0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d",
                token_out_addr="0x0B38e83B86d491735fEaa0a791F65c2B99535396",
                gas_price=25000000000,
                amount=1.0,
            )

    ### Test execute_swap ###
    async def test_execute_swap_success(self):
        """
        Test execute_swap with a successful transaction.
        """
        data = {
            "from": self.provider.address,
            "to": self.contracts.flare.openocean_exchangeV2,
            "value": "0",
            "data": "0xabcdef",
        }
        self.provider._prepare_base_tx_params = AsyncMock(
            return_value={
                "from": self.provider.address,
                "nonce": 1,
                "maxFeePerGas": 25000000000,
                "maxPriorityFeePerGas": 2000000000,
                "chainId": 14,  # Flare mainnet
                "type": 2,
            }
        )
        self.provider.estimate_gas = AsyncMock(return_value=2233869)
        self.provider.sign_and_send_transaction = AsyncMock(
            return_value="0xf4690a9c5afe7032ba2ce82977aa24b94e6ab61e8afea2ed10bd8087dcbf8496"
        )

        tx_hash = await self.open_ocean.execute_swap(data)
        self.assertEqual(
            tx_hash,
            "0xf4690a9c5afe7032ba2ce82977aa24b94e6ab61e8afea2ed10bd8087dcbf8496",
        )

    async def test_execute_swap_gas_estimation_failure(self):
        """
        Test execute_swap when gas estimation fails.
        """
        data = {
            "from": self.provider.address,
            "to": self.contracts.flare.openocean_exchangeV2,
            "value": "0",
            "data": "0xabcdef",
        }
        self.provider._prepare_base_tx_params = AsyncMock(
            return_value={
                "from": self.provider.address,
                "nonce": 1,
                "maxFeePerGas": 25000000000,
                "maxPriorityFeePerGas": 2000000000,
                "chainId": 14,
                "type": 2,
            }
        )
        self.provider.estimate_gas = AsyncMock(return_value=None)

        with self.assertRaises(Exception) as cm:
            await self.open_ocean.execute_swap(data)
        self.assertEqual(str(cm.exception), "Gas estimation failed")

    ### Test get_abi ###
    def test_get_abi(self):
        """
        Test get_abi returns the expected ABI structure.
        """
        abi = self.open_ocean.get_abi()
        self.assertIsInstance(abi, list)
        self.assertEqual(abi[0]["name"], "swap")
        self.assertEqual(len(abi[0]["inputs"]), 3)


if __name__ == "__main__":
    unittest.main()
