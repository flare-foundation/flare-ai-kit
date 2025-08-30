"""ADK tool wrappers for Flare TEE (Trusted Execution Environment) components."""

import structlog
from typing import Any

from flare_ai_kit.agent.tool import tool
from flare_ai_kit.tee import VtpmAttestation, VtpmValidation

logger = structlog.get_logger(__name__)


@tool
async def get_attestation_token(
    nonces: list[str],
    audience: str = "https://sts.google.com",
    token_type: str = "OIDC",
    simulate: bool = False,
) -> dict[str, Any]:
    """
    Request a vTPM attestation token for verifying trusted execution environment.

    Args:
        nonces: List of random nonce strings (10-74 bytes each) for replay protection
        audience: Intended audience for the token (default: Google STS)
        token_type: Type of token - "OIDC" or "PKI" (default: "OIDC")
        simulate: If True, returns a simulated token for testing (default: False)

    Returns:
        Dictionary containing the attestation token and metadata

    """
    logger.info(
        "Requesting vTPM attestation token",
        nonces_count=len(nonces),
        audience=audience,
        token_type=token_type,
        simulate=simulate,
    )

    try:
        attestation = VtpmAttestation(simulate=simulate)
        token = attestation.get_token(
            nonces=nonces, audience=audience, token_type=token_type
        )

        return {
            "token": token,
            "token_type": token_type,
            "audience": audience,
            "nonces_count": len(nonces),
            "simulated": simulate,
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to get attestation token", error=str(e))
        return {
            "token": "",
            "token_type": token_type,
            "audience": audience,
            "nonces_count": len(nonces),
            "simulated": simulate,
            "status": "error",
            "error": str(e),
        }


@tool
async def validate_attestation_token(
    token: str, expected_issuer: str = "https://confidentialcomputing.googleapis.com"
) -> dict[str, Any]:
    """
    Validate a vTPM attestation token and extract its claims.

    Args:
        token: The JWT attestation token to validate
        expected_issuer: Expected token issuer URL (default: Confidential Computing service)

    Returns:
        Dictionary containing validation results and token claims

    """
    logger.info("Validating vTPM attestation token", expected_issuer=expected_issuer)

    try:
        validator = VtpmValidation(expected_issuer=expected_issuer)
        claims = validator.validate_token(token)

        return {
            "valid": True,
            "claims": claims,
            "issuer": expected_issuer,
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to validate attestation token", error=str(e))
        return {
            "valid": False,
            "claims": {},
            "issuer": expected_issuer,
            "status": "error",
            "error": str(e),
        }


@tool
async def create_secure_nonces(count: int = 1, length: int = 32) -> dict[str, Any]:
    """
    Generate cryptographically secure nonces for attestation token requests.

    Args:
        count: Number of nonces to generate (default: 1)
        length: Length of each nonce in bytes - must be between 10-74 (default: 32)

    Returns:
        Dictionary containing the generated nonces

    """
    import secrets
    import string

    logger.info("Generating secure nonces", count=count, length=length)

    try:
        if length < 10 or length > 74:
            raise ValueError("Nonce length must be between 10 and 74 bytes")

        if count < 1 or count > 10:
            raise ValueError("Nonce count must be between 1 and 10")

        # Generate secure random nonces using letters and digits
        alphabet = string.ascii_letters + string.digits
        nonces = [
            "".join(secrets.choice(alphabet) for _ in range(length))
            for _ in range(count)
        ]

        return {"nonces": nonces, "count": count, "length": length, "status": "success"}
    except Exception as e:
        logger.error("Failed to generate secure nonces", error=str(e))
        return {
            "nonces": [],
            "count": count,
            "length": length,
            "status": "error",
            "error": str(e),
        }


@tool
async def check_tee_environment() -> dict[str, Any]:
    """
    Check if the current environment supports TEE attestation.

    Returns:
        Dictionary containing TEE environment status and capabilities

    """
    import os
    from pathlib import Path

    logger.info("Checking TEE environment")

    try:
        # Check for TEE socket path
        socket_path = "/run/container_launcher/teeserver.sock"
        socket_exists = Path(socket_path).exists()

        # Check for Confidential Space environment variables
        cs_env = os.getenv("CONFIDENTIAL_SPACE")
        workload_name = os.getenv("WORKLOAD_NAME", "")

        # Determine environment type
        if cs_env and socket_exists:
            environment = "confidential_space"
        elif socket_exists:
            environment = "tee_enabled"
        else:
            environment = "standard"

        return {
            "environment": environment,
            "tee_socket_exists": socket_exists,
            "confidential_space": bool(cs_env),
            "workload_name": workload_name,
            "socket_path": socket_path,
            "attestation_available": socket_exists,
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to check TEE environment", error=str(e))
        return {
            "environment": "unknown",
            "tee_socket_exists": False,
            "confidential_space": False,
            "workload_name": "",
            "socket_path": "/run/container_launcher/teeserver.sock",
            "attestation_available": False,
            "status": "error",
            "error": str(e),
        }


@tool
async def extract_token_claims(token: str) -> dict[str, Any]:
    """
    Extract claims from a JWT token without validation (for inspection purposes).

    Args:
        token: The JWT token to extract claims from

    Returns:
        Dictionary containing the token header and payload claims

    """
    import jwt

    logger.info("Extracting token claims")

    try:
        # Extract header and payload without verification
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})

        return {
            "header": header,
            "payload": payload,
            "algorithm": header.get("alg", "unknown"),
            "token_type": header.get("typ", "unknown"),
            "key_id": header.get("kid", ""),
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to extract token claims", error=str(e))
        return {
            "header": {},
            "payload": {},
            "algorithm": "unknown",
            "token_type": "unknown",
            "key_id": "",
            "status": "error",
            "error": str(e),
        }
