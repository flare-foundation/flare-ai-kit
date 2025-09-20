"""TEE security integration for wallet operations."""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

import structlog
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel

from flare_ai_kit.tee.validation import VtpmValidation

logger = structlog.get_logger(__name__)


class SecureOperation(BaseModel):
    """Represents a secure operation within TEE."""

    operation_id: str
    operation_type: str
    timestamp: float
    attestation_token: str
    operation_data: dict[str, Any]
    integrity_hash: str


class TEESecurityManager:
    """Manages security operations within Trusted Execution Environment."""

    def __init__(self, vtpm_validator: VtpmValidation | None = None) -> None:
        self.vtpm_validator = vtpm_validator or VtpmValidation()
        self.secure_operations: list[SecureOperation] = []

    async def create_secure_operation(
        self,
        operation_type: str,
        operation_data: dict[str, Any],
        attestation_token: str,
    ) -> SecureOperation:
        """
        Create a secure operation with TEE attestation.

        Args:
            operation_type: Type of operation (e.g., "wallet_creation",
                "transaction_signing")
            operation_data: Operation-specific data
            attestation_token: TEE attestation token

        Returns:
            SecureOperation object

        """
        logger.info("Creating secure operation", operation_type=operation_type)

        # Validate TEE attestation
        try:
            claims = self.vtpm_validator.validate_token(attestation_token)
            logger.info("TEE attestation validated for secure operation", claims=claims)
        except Exception as e:
            logger.exception("TEE attestation validation failed", error=str(e))
            msg = f"Invalid TEE attestation: {e}"
            raise ValueError(msg) from e

        # Generate operation ID
        operation_id = self._generate_operation_id(operation_type, operation_data)

        # Calculate integrity hash
        integrity_hash = self._calculate_integrity_hash(operation_data)

        secure_op = SecureOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=time.time(),
            attestation_token=attestation_token,
            operation_data=operation_data,
            integrity_hash=integrity_hash,
        )

        # Store operation for audit
        self.secure_operations.append(secure_op)

        logger.info("Secure operation created", operation_id=operation_id)
        return secure_op

    def _generate_operation_id(
        self, operation_type: str, operation_data: dict[str, Any]
    ) -> str:
        """Generate unique operation ID."""
        data_str = json.dumps(operation_data, sort_keys=True, separators=(",", ":"))
        combined = f"{operation_type}:{data_str}:{time.time()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _calculate_integrity_hash(self, operation_data: dict[str, Any]) -> str:
        """Calculate integrity hash for operation data."""
        data_str = json.dumps(operation_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data_str.encode()).hexdigest()

    async def verify_operation_integrity(self, operation: SecureOperation) -> bool:
        """
        Verify the integrity of a secure operation.

        Args:
            operation: SecureOperation to verify

        Returns:
            True if operation integrity is valid

        """
        # Recalculate integrity hash
        current_hash = self._calculate_integrity_hash(operation.operation_data)

        if current_hash != operation.integrity_hash:
            logger.error(
                "Operation integrity check failed",
                operation_id=operation.operation_id,
                expected=operation.integrity_hash,
                actual=current_hash,
            )
            return False

        # Re-validate TEE attestation
        try:
            self.vtpm_validator.validate_token(operation.attestation_token)
        except Exception as e:
            logger.exception(
                "TEE attestation re-validation failed",
                operation_id=operation.operation_id,
                error=str(e),
            )
            return False
        else:
            return True

    async def encrypt_sensitive_data(
        self,
        data: bytes,
        attestation_token: str,
        additional_data: bytes | None = None,
    ) -> dict[str, str]:
        """
        Encrypt sensitive data within TEE context.

        Args:
            data: Data to encrypt
            attestation_token: TEE attestation token
            additional_data: Optional additional authenticated data

        Returns:
            Dictionary with encrypted data and metadata

        """
        # Validate TEE context
        try:
            claims = self.vtpm_validator.validate_token(attestation_token)
        except Exception as e:
            msg = f"Invalid TEE context: {e}"
            raise ValueError(msg) from e

        # Derive encryption key from TEE-specific data
        key_material = self._derive_tee_key(claims, additional_data)

        # Encrypt data using AES-GCM
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        cipher = Cipher(algorithms.AES(key_material), modes.GCM(nonce))
        encryptor = cipher.encryptor()

        if additional_data:
            encryptor.authenticate_additional_data(additional_data)

        ciphertext = encryptor.update(data) + encryptor.finalize()

        return {
            "ciphertext": ciphertext.hex(),
            "nonce": nonce.hex(),
            "tag": encryptor.tag.hex(),
            "algorithm": "AES-GCM",
            "key_derivation": "TEE-PBKDF2",
        }

    async def decrypt_sensitive_data(
        self,
        encrypted_data: dict[str, str],
        attestation_token: str,
        additional_data: bytes | None = None,
    ) -> bytes:
        """
        Decrypt sensitive data within TEE context.

        Args:
            encrypted_data: Encrypted data dictionary
            attestation_token: TEE attestation token
            additional_data: Optional additional authenticated data

        Returns:
            Decrypted data

        """
        # Validate TEE context
        try:
            claims = self.vtpm_validator.validate_token(attestation_token)
        except Exception as e:
            msg = f"Invalid TEE context: {e}"
            raise ValueError(msg) from e

        # Derive decryption key
        key_material = self._derive_tee_key(claims, additional_data)

        # Extract encrypted components
        ciphertext = bytes.fromhex(encrypted_data["ciphertext"])
        nonce = bytes.fromhex(encrypted_data["nonce"])
        tag = bytes.fromhex(encrypted_data["tag"])

        # Decrypt using AES-GCM
        cipher = Cipher(algorithms.AES(key_material), modes.GCM(nonce, tag))
        decryptor = cipher.decryptor()

        if additional_data:
            decryptor.authenticate_additional_data(additional_data)

        try:
            return decryptor.update(ciphertext) + decryptor.finalize()
        except Exception as e:
            logger.exception("Decryption failed", error=str(e))
            msg = "Decryption failed - invalid key or corrupted data"
            raise ValueError(msg) from e

    def _derive_tee_key(
        self, tee_claims: dict[str, Any], additional_data: bytes | None = None
    ) -> bytes:
        """
        Derive encryption key from TEE-specific claims.

        Args:
            tee_claims: Validated TEE token claims
            additional_data: Optional additional data for key derivation

        Returns:
            32-byte encryption key

        """
        # Use TEE-specific identifiers for key derivation
        salt_components = [
            tee_claims.get("sub", ""),
            tee_claims.get("iss", ""),
            str(tee_claims.get("iat", 0)),
        ]

        if additional_data:
            salt_components.append(additional_data.hex())

        salt = hashlib.sha256(":".join(salt_components).encode()).digest()

        # Use a fixed password for now - in production, this would come from
        # secure enclave or hardware security module
        password = b"turnkey_tee_secure_derivation"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        return kdf.derive(password)

    async def create_secure_audit_log(
        self, operation: SecureOperation, result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create secure audit log entry for an operation.

        Args:
            operation: Secure operation that was performed
            result: Result of the operation

        Returns:
            Audit log entry

        """
        audit_entry = {
            "timestamp": time.time(),
            "operation_id": operation.operation_id,
            "operation_type": operation.operation_type,
            "operation_timestamp": operation.timestamp,
            "integrity_hash": operation.integrity_hash,
            "result_hash": hashlib.sha256(
                json.dumps(result, sort_keys=True).encode()
            ).hexdigest(),
            "tee_validated": True,
        }

        # Sign audit entry for non-repudiation
        audit_signature = self._sign_audit_entry(audit_entry)
        audit_entry["audit_signature"] = audit_signature

        logger.info("Secure audit log created", operation_id=operation.operation_id)
        return audit_entry

    def _sign_audit_entry(self, audit_entry: dict[str, Any]) -> str:
        """
        Sign audit entry for integrity and non-repudiation.

        Args:
            audit_entry: Audit entry to sign

        Returns:
            Base64-encoded signature

        """
        # Create deterministic representation
        audit_data = json.dumps(audit_entry, sort_keys=True, separators=(",", ":"))

        # For demo purposes, use HMAC. In production, use asymmetric signing
        secret_key = b"audit_signing_key_should_be_in_hsm"
        signature = hmac.new(secret_key, audit_data.encode(), hashlib.sha256).digest()

        return base64.b64encode(signature).decode()

    async def get_operation_history(
        self, operation_type: str | None = None, limit: int = 100
    ) -> list[SecureOperation]:
        """
        Get history of secure operations.

        Args:
            operation_type: Optional filter by operation type
            limit: Maximum number of operations to return

        Returns:
            List of secure operations

        """
        operations = self.secure_operations

        if operation_type:
            operations = [
                op for op in operations if op.operation_type == operation_type
            ]

        # Sort by timestamp (most recent first)
        operations = sorted(operations, key=lambda x: x.timestamp, reverse=True)

        return operations[:limit]

    async def cleanup_expired_operations(self, max_age_hours: int = 168) -> int:
        """
        Clean up expired secure operations (older than max_age_hours).

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of operations cleaned up

        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        initial_count = len(self.secure_operations)

        self.secure_operations = [
            op for op in self.secure_operations if op.timestamp > cutoff_time
        ]

        cleaned_count = initial_count - len(self.secure_operations)

        if cleaned_count > 0:
            logger.info("Cleaned up expired operations", count=cleaned_count)

        return cleaned_count
