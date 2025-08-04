"""Tests for Turnkey wallet implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from flare_ai_kit.wallet.base import TransactionRequest, WalletAddress
from flare_ai_kit.wallet.permissions import PermissionEngine, PolicyViolation
from flare_ai_kit.wallet.turnkey_wallet import TurnkeySettings, TurnkeyWallet


@pytest.fixture
def mock_settings():
    """Create mock Turnkey settings."""
    return TurnkeySettings(
        organization_id="test_org_id",
        api_public_key="test_public_key",
        api_private_key="-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VDc3BhkA...\n-----END PRIVATE KEY-----",
    )


@pytest.fixture
def mock_permission_engine():
    """Create mock permission engine."""
    engine = MagicMock(spec=PermissionEngine)
    engine.evaluate_transaction = AsyncMock(return_value=("allow", []))
    engine.record_transaction = MagicMock()
    return engine


@pytest.fixture
def turnkey_wallet(mock_settings, mock_permission_engine):
    """Create TurnkeyWallet instance for testing."""
    return TurnkeyWallet(
        settings=mock_settings, permission_engine=mock_permission_engine
    )


class TestTurnkeyWallet:
    """Test TurnkeyWallet functionality."""

    @pytest.mark.asyncio
    async def test_create_wallet_success(self, turnkey_wallet):
        """Test successful wallet creation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "activity": {
                "result": {
                    "createSubOrganizationResult": {
                        "subOrganizationId": "test_sub_org_id"
                    }
                }
            }
        }

        with patch.object(
            turnkey_wallet, "_make_authenticated_request", return_value=mock_response
        ):
            wallet_id = await turnkey_wallet.create_wallet("test_wallet")

        assert wallet_id == "test_sub_org_id"

    @pytest.mark.asyncio
    async def test_create_wallet_failure(self, turnkey_wallet):
        """Test wallet creation failure."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        with (
            patch.object(
                turnkey_wallet,
                "_make_authenticated_request",
                return_value=mock_response,
            ),
            pytest.raises(RuntimeError, match="Failed to create wallet"),
        ):
            await turnkey_wallet.create_wallet("test_wallet")

    @pytest.mark.asyncio
    async def test_get_address_success(self, turnkey_wallet):
        """Test successful address retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "walletAccounts": [
                {
                    "address": "0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
                    "path": "m/44'/60'/0'/0/0",
                    "walletAccountId": "account_id_1",
                }
            ]
        }

        with patch.object(
            turnkey_wallet, "_make_authenticated_request", return_value=mock_response
        ):
            address = await turnkey_wallet.get_address("test_wallet_id")

        assert isinstance(address, WalletAddress)
        assert address.address == "0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b"
        assert address.wallet_id == "test_wallet_id"
        assert address.derivation_path == "m/44'/60'/0'/0/0"

    @pytest.mark.asyncio
    async def test_get_address_not_found(self, turnkey_wallet):
        """Test address retrieval when path not found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "walletAccounts": [
                {
                    "address": "0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
                    "path": "m/44'/60'/0'/0/1",  # Different path
                    "walletAccountId": "account_id_1",
                }
            ]
        }

        with (
            patch.object(
                turnkey_wallet,
                "_make_authenticated_request",
                return_value=mock_response,
            ),
            pytest.raises(RuntimeError, match="No account found for derivation path"),
        ):
            await turnkey_wallet.get_address("test_wallet_id", "m/44'/60'/0'/0/0")

    @pytest.mark.asyncio
    async def test_sign_transaction_success(self, turnkey_wallet):
        """Test successful transaction signing."""
        # Mock permission engine to allow transaction
        turnkey_wallet.permission_engine.evaluate_transaction.return_value = (
            "allow",
            [],
        )

        # Mock accounts response
        accounts_response = MagicMock()
        accounts_response.status_code = 200
        accounts_response.json.return_value = {
            "walletAccounts": [
                {
                    "walletAccountId": "account_id_1",
                    "address": "0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
                }
            ]
        }

        # Mock signing response
        sign_response = MagicMock()
        sign_response.status_code = 200
        sign_response.json.return_value = {
            "activity": {
                "result": {
                    "signTransactionResult": {
                        "signedTransaction": "0xf86c808504a817c800825208947..."
                    }
                }
            }
        }

        transaction = TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="1000000000000000000",  # 1 ETH
            chain_id=1,
        )

        with patch.object(
            turnkey_wallet, "_make_authenticated_request"
        ) as mock_request:
            mock_request.side_effect = [accounts_response, sign_response]

            with patch("web3.Web3.keccak") as mock_keccak:
                mock_keccak.return_value.hex.return_value = "0x123abc..."

                signed_tx = await turnkey_wallet.sign_transaction(
                    "test_wallet_id", transaction
                )

        assert signed_tx.signed_transaction == "0xf86c808504a817c800825208947..."
        assert signed_tx.transaction_hash == "0x123abc..."

        # Verify permission engine was called
        turnkey_wallet.permission_engine.evaluate_transaction.assert_called_once()
        turnkey_wallet.permission_engine.record_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_transaction_denied_by_policy(self, turnkey_wallet):
        """Test transaction signing denied by policy."""
        # Mock permission engine to deny transaction

        violation = PolicyViolation(
            policy_name="test_policy",
            violation_type="max_value_exceeded",
            description="Transaction value too high",
            suggested_action="deny",
        )
        turnkey_wallet.permission_engine.evaluate_transaction.return_value = (
            "deny",
            [violation],
        )

        transaction = TransactionRequest(
            to="0x742d35Cc6634C0532925a3b8D8C8EE7c9e92bb1b",
            value="1000000000000000000",  # 1 ETH
            chain_id=1,
        )

        with pytest.raises(PermissionError, match="Transaction denied by policy"):
            await turnkey_wallet.sign_transaction("test_wallet_id", transaction)

    @pytest.mark.asyncio
    async def test_list_wallets(self, turnkey_wallet):
        """Test listing wallets."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "subOrganizations": [
                {"subOrganizationId": "wallet_1"},
                {"subOrganizationId": "wallet_2"},
                {"subOrganizationId": "wallet_3"},
            ]
        }

        with patch.object(
            turnkey_wallet, "_make_authenticated_request", return_value=mock_response
        ):
            wallets = await turnkey_wallet.list_wallets()

        assert wallets == ["wallet_1", "wallet_2", "wallet_3"]

    @pytest.mark.asyncio
    async def test_export_wallet(self, turnkey_wallet):
        """Test wallet export."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organization": {"organizationName": "test_wallet"}
        }

        with patch.object(
            turnkey_wallet, "_make_authenticated_request", return_value=mock_response
        ):
            export_data = await turnkey_wallet.export_wallet(
                "test_wallet_id", "password123"
            )

        assert export_data["wallet_id"] == "test_wallet_id"
        assert export_data["organization_name"] == "test_wallet"
        assert export_data["encrypted"] is True

    @pytest.mark.asyncio
    async def test_import_wallet_not_implemented(self, turnkey_wallet):
        """Test that wallet import raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await turnkey_wallet.import_wallet({}, "password123")

    @pytest.mark.asyncio
    async def test_delete_wallet_not_supported(self, turnkey_wallet):
        """Test that wallet deletion returns False (not supported)."""
        result = await turnkey_wallet.delete_wallet("test_wallet_id")
        assert result is False

    def test_sign_request(self, turnkey_wallet):
        """Test request signing functionality."""
        test_body = '{"test": "data"}'

        # Mock private key operations

        with patch(
            "cryptography.hazmat.primitives.serialization.load_pem_private_key"
        ) as mock_load_key:
            mock_private_key = MagicMock(spec=ec.EllipticCurvePrivateKey)
            mock_private_key.sign.return_value = b"mock_signature"
            mock_load_key.return_value = mock_private_key

            with patch("base64.b64encode") as mock_b64encode:
                mock_b64encode.return_value.decode.return_value = (
                    "mock_encoded_signature"
                )

                signature = turnkey_wallet._sign_request(test_body)

        assert signature == "mock_encoded_signature"
        mock_private_key.sign.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_tee_attestation_success(self, turnkey_wallet):
        """Test successful TEE attestation validation."""
        mock_claims = {"sub": "test", "iss": "test_issuer"}

        with patch.object(
            turnkey_wallet.tee_validator, "validate_token", return_value=mock_claims
        ):
            result = await turnkey_wallet.validate_tee_attestation("valid_token")

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_tee_attestation_failure(self, turnkey_wallet):
        """Test failed TEE attestation validation."""
        with patch.object(
            turnkey_wallet.tee_validator,
            "validate_token",
            side_effect=Exception("Invalid token"),
        ):
            result = await turnkey_wallet.validate_tee_attestation("invalid_token")

        assert result is False

    @pytest.mark.asyncio
    async def test_context_manager(self, turnkey_wallet):
        """Test async context manager functionality."""
        with patch.object(turnkey_wallet.client, "aclose") as mock_close:
            async with turnkey_wallet:
                pass

        mock_close.assert_called_once()
