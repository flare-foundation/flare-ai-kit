"""Validator for Confidential Space Virtual TPM (vTPM) tokens."""

import base64
import datetime
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Final

import jwt
import requests
import structlog
from cryptography import x509
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from OpenSSL.crypto import X509, X509Store, X509StoreContext
from OpenSSL.crypto import Error as OpenSSLError

from flare_ai_kit.common import (
    CertificateParsingError,
    InvalidCertificateChainError,
    SignatureValidationError,
    VtpmValidationError,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class PKICertificates:
    """
    Immutable container for the complete certificate chain.

    Attributes:
        leaf_cert: The end-entity certificate used for token signing
        intermediate_cert: The intermediate CA certificate
        root_cert: The root CA certificate that anchors trust

    """

    leaf_cert: x509.Certificate
    intermediate_cert: x509.Certificate
    root_cert: x509.Certificate


type JSONWebKeySet = dict[str, list[dict[str, str]]]

# Constants
ALGO: Final[str] = "RS256"
CERT_HASH_ALGO: Final[str] = "sha256"
CERT_COUNT: Final[int] = 3
CERT_FINGERPRINT: Final[str] = (
    "B9:51:20:74:2C:24:E3:AA:34:04:2E:1C:3B:A3:AA:D2:8B:21:23:21"
)


class VtpmValidation:
    """
    Validates Confidential Space vTPM tokens through PKI or OIDC schemes.

    This class supports two validation methods:
    1. PKI-based validation using an x5c certificate chain in the token header
    2. OIDC-based validation using JWKS RSA public keys

    Args:
        expected_issuer: Base URL of the token issuer (default: Confidential Space URL)
        oidc_endpoint: Path to OpenID Connect configuration
            (default: /.well-known/openid-configuration)
        pki_endpoint: Path to root certificate
            (default: /.well-known/confidential_space_root.crt)

    Usage:
        validator = VtpmValidation()
        try:
            claims = validator.validate_token(token_string)
            # Claims contain verified token payload
        except VtpmValidationError as e:
            # Handle validation failure

    """

    def __init__(
        self,
        expected_issuer: str = "https://confidentialcomputing.googleapis.com",
        oidc_endpoint: str = "/.well-known/openid-configuration",
        pki_endpoint: str = "/.well-known/confidential_space_root.crt",
    ) -> None:
        self.expected_issuer = expected_issuer
        self.oidc_endpoint = oidc_endpoint
        self.pki_endpoint = pki_endpoint

    def validate_token(self, token: str) -> dict[str, Any]:
        """
        Validates a vTPM token and returns its claims if valid.

        The method automatically detects whether to use PKI or OIDC validation based on
        the presence of x5c certificates in the token header.

        Args:
            token: The JWT token string to validate

        Returns:
            dict: The validated token claims

        Raises:
            VtpmValidationError: If token validation fails for any reason
            InvalidCertificateChainError: If the certificate chain is invalid
            SignatureValidationError: If the token signature is invalid
            CertificateParsingError: If certificates cannot be parsed

        """
        unverified_header = jwt.get_unverified_header(token)
        logger.info("token", unverified_header=unverified_header)

        if unverified_header.get("alg") != ALGO:
            msg = f"Invalid algorithm: got {unverified_header.get('alg')}, "
            f"expected {ALGO}"
            raise VtpmValidationError(msg)

        if unverified_header.get("x5c", None):
            # if x5c certs in header, token uses pki scheme
            logger.info("PKI_token", alg=unverified_header.get("alg"))
            return self._decode_and_validate_pki(token, unverified_header)
        # token uses oidc scheme
        logger.info("OIDC_token", alg=unverified_header.get("alg"))
        return self._decode_and_validate_oidc(token, unverified_header)

    def _decode_and_validate_oidc(
        self, token: str, unverified_header: dict[str, str]
    ) -> dict[str, Any]:
        """
        Validates a token using OIDC JWKS-based validation.

        Fetches the JWKS from the issuer's endpoint, finds the matching key by key ID,
        and validates the token signature.

        Args:
            token: The JWT token string
            unverified_header: Pre-parsed token header

        Returns:
            dict: Validated token claims if successful

        Raises:
            VtpmValidationError: For any validation failure
            SignatureValidationError: If signature validation fails

        """
        res = self._get_well_known_file(self.expected_issuer, self.oidc_endpoint).json()
        jwks_uri = res["jwks_uri"]

        jwks = self._fetch_jwks(jwks_uri)
        rsa_key = None

        # Find the correct key based on the key ID (kid) in header
        for key in jwks["keys"]:
            if key.get("kid") == unverified_header["kid"]:
                logger.info("kid_match", kid=key["kid"])
                rsa_key = self._jwk_to_rsa_key(key)
                break

        if rsa_key is None:
            msg = "Unable to find appropriate key id (kid) in header"
            raise VtpmValidationError(msg)

        # Verify and decode the token using the public RSA key
        try:
            validated_token = jwt.decode(
                token, rsa_key, algorithms=[ALGO], options={"verify_aud": False}
            )
            logger.info(
                "signature_match",
                issuer=self.expected_issuer,
                public_numbers=rsa_key.public_numbers,
            )
        except jwt.ExpiredSignatureError as e:
            msg = "Token has expired"
            logger.exception("token_expired", error=e)
            raise SignatureValidationError(msg) from e
        except jwt.InvalidTokenError as e:
            msg = "Token is invalid"
            logger.exception("invalid_token", error=e)
            raise VtpmValidationError(msg) from e
        except Exception as e:
            msg = "Unexpected error during validation"
            logger.exception("unexpected_error", error=e)
            raise VtpmValidationError(msg) from e
        else:
            return validated_token

    def _decode_and_validate_pki(
        self, token: str, unverified_header: dict[str, str]
    ) -> dict[str, Any]:
        """
        Validates a token using PKI-based validation.

        Validates the certificate chain from the x5c header, verifies it
        against the trusted root certificate, and validates the token
        signature using the leaf certificate.

        Args:
            token: The JWT token string
            unverified_header: Pre-parsed token header containing x5c certificates

        Returns:
            dict: Validated token claims if successful

        Raises:
            VtpmValidationError: For any validation failure
            InvalidCertificateChainError: If certificate chain validation fails

        """
        res = self._get_well_known_file(self.expected_issuer, self.pki_endpoint).content
        root_cert = x509.load_pem_x509_certificate(res, default_backend())
        fingerprint = root_cert.fingerprint(hashes.SHA1())  # noqa: S303
        calculated_fingerprint = ":".join(format(b, "02x") for b in fingerprint).upper()

        if calculated_fingerprint != CERT_FINGERPRINT:
            msg = "Root certificate fingerprint does not match expected fingerprint."
            f"Expected: {CERT_FINGERPRINT}, Received: {calculated_fingerprint}"
            raise VtpmValidationError(msg)
        try:
            certs = self._extract_and_validate_certificates(unverified_header)
            self._validate_leaf_certificate(certs.leaf_cert)
            self._compare_root_certificates(certs.root_cert, root_cert)
            self._check_certificate_validity(certs)
            self._verify_certificate_chain(certs)

            public_key = certs.leaf_cert.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            return jwt.decode(
                token,
                key=public_pem,
                algorithms=[ALGO],
            )
        except (InvalidKey, jwt.InvalidTokenError) as e:
            msg = f"Token signature validation failed: {e}"
            raise VtpmValidationError(msg) from e
        except Exception as e:
            msg = f"Unexpected error during validation: {e}"
            raise VtpmValidationError(msg) from e

    @staticmethod
    def _get_well_known_file(
        expected_issuer: str, well_known_path: str
    ) -> requests.Response:
        """
        Fetch configuration data from a well-known endpoint.

        This static method retrieves data from a well-known URL endpoint by combining
        the issuer URL with the well-known path.

        Args:
            expected_issuer: Base URL of the token issuer
                (e.g., "https://confidentialcomputing.googleapis.com")
            well_known_path: Path to the well-known endpoint
                (e.g., "/.well-known/openid-configuration")

        Returns:
            requests.Response: The HTTP response from the well-known endpoint

        Raises:
            requests.exceptions.HTTPError: If the response status code is not 200

        """
        response = requests.get(expected_issuer + well_known_path, timeout=10)
        valid_status_code = 200
        if response.status_code == valid_status_code:
            return response
        msg = f"Failed to fetch well known file: {response.status_code}"
        raise requests.exceptions.HTTPError(msg)

    @staticmethod
    def _fetch_jwks(uri: str) -> JSONWebKeySet:
        """
        Fetch JSON Web Key Set (JWKS) from a remote endpoint.

        This static method retrieves and parses the JWKS containing public keys
        used for token validation.

        Args:
            uri: Full URL of the JWKS endpoint

        Returns:
            JWKSResponse: Parsed JWKS data containing public keys

        Raises:
            requests.exceptions.HTTPError: If the response status code is not 200

        """
        response = requests.get(uri, timeout=10)
        valid_status_code = 200
        if response.status_code == valid_status_code:
            return response.json()
        msg = f"Failed to fetch JWKS: {response.status_code}"
        raise requests.exceptions.HTTPError(msg)

    @staticmethod
    def _jwk_to_rsa_key(jwk: dict[str, str]) -> rsa.RSAPublicKey:
        """
        Convert a JSON Web Key (JWK) to an RSA public key.

        This static method converts a JWK dictionary into a cryptographic RSA public key
        by extracting and decoding the modulus (n) and exponent (e) values.

        Args:
            jwk: Dictionary containing the JWK parameters, must include 'n' (modulus)
                and 'e' (exponent) fields in base64url encoding

        Returns:
            RSAPublicKey: A cryptographic RSA public key object

        """
        n = int.from_bytes(base64.urlsafe_b64decode(jwk["n"] + "=="), "big")
        e = int.from_bytes(base64.urlsafe_b64decode(jwk["e"] + "=="), "big")
        return rsa.RSAPublicNumbers(e, n).public_key(backend=default_backend())

    def _extract_and_validate_certificates(
        self, headers: dict[str, Any]
    ) -> PKICertificates:
        """
        Extract and validate the certificate chain from the token header.

        Processes the x5c (X.509 Certificate Chain) header field from the
        JWT token header and validates that the expected number of certificates
        are present. The certificates are decoded from their DER format and returned
        in order (leaf, intermediate, root).

        Args:
            headers: Token header dictionary with x5c field with certificate chain

        Returns:
            PKICertificates: Container with the decoded certificate chain, ordered as:
                            - leaf_cert: End-entity certificate
                            - intermediate_cert: Intermediate CA certificate
                            - root_cert: Root CA certificate

        Raises:
            VtpmValidationError: If x5c header is missing or contains wrong
                number of certificates
            CertificateParsingError: If any certificate fails to decode or parse
            ValueError: If certificate format is invalid
            TypeError: If certificate data is malformed

        """
        x5c_headers = headers.get("x5c")

        if not x5c_headers or len(x5c_headers) != CERT_COUNT:
            msg = "Invalid x5c certificates in header"
            raise VtpmValidationError(msg)

        try:
            certs = [self._decode_der_certificate(cert) for cert in x5c_headers]
            return PKICertificates(certs[0], certs[1], certs[2])
        except (ValueError, TypeError) as e:
            msg = f"Failed to parse certificates: {e}"
            raise CertificateParsingError(msg) from e

    @staticmethod
    def _decode_der_certificate(cert_str: str) -> x509.Certificate:
        """
        Decode and parse a DER-encoded certificate from base64 string.

        This static method handles cleaning and decoding of a certificate string,
        removing PEM headers/footers and whitespace before base64 decoding.

        Args:
            cert_str: Base64-encoded certificate string, optionally with PEM markers

        Returns:
            x509.Certificate: Parsed X.509 certificate object

        Raises:
            CertificateParsingError: If certificate parsing fails

        """
        try:
            cleaned_cert = re.sub(
                r"-----BEGIN CERTIFICATE-----|-----END CERTIFICATE-----|\s+",
                "",
                cert_str,
            )
            cert_bytes = base64.b64decode(cleaned_cert)
            return x509.load_der_x509_certificate(cert_bytes, default_backend())
        except Exception as e:
            msg = f"Failed to decode certificate: {e}"
            raise CertificateParsingError(msg) from e

    def _validate_leaf_certificate(self, leaf_cert: x509.Certificate) -> None:
        """Validates the leaf certificate's algorithm and key type."""
        if not leaf_cert.signature_hash_algorithm:
            msg = "No signature hash algorithm found"
            raise SignatureValidationError(msg)

        if leaf_cert.signature_hash_algorithm.name != CERT_HASH_ALGO:
            msg = "Invalid signature algorithm: "
            f"{leaf_cert.signature_hash_algorithm.name}"
            raise SignatureValidationError(msg)

        if not isinstance(leaf_cert.public_key(), rsa.RSAPublicKey):
            msg = "Leaf certificate must use RSA public key"
            raise SignatureValidationError(msg)

    def _compare_root_certificates(
        self, token_root_cert: x509.Certificate, root_cert: x509.Certificate
    ) -> None:
        """Compare token root certificate with stored root certificate."""
        try:
            fingerprint1 = hashlib.sha256(root_cert.tbs_certificate_bytes).digest()
            fingerprint2 = hashlib.sha256(
                token_root_cert.tbs_certificate_bytes
            ).digest()

            if fingerprint1 != fingerprint2:
                msg = "Root certificate fingerprint mismatch"
                raise VtpmValidationError(msg)
        except AttributeError as e:
            msg = "Invalid certificate format"
            raise VtpmValidationError(msg) from e

    @staticmethod
    def _verify_certificate_chain(certificates: PKICertificates) -> None:
        """
        Verify the trust chain of certificates.

        This static method validates the certificate chain using OpenSSL, ensuring
        that each certificate is signed by its issuer and the chain leads to a
        trusted root certificate.

        Args:
            certificates: PKICertificates object containing leaf, intermediate,
                        and root certificates

        Raises:
            InvalidCertificateChainError: If chain validation fails

        """
        try:
            store = X509Store()
            store.add_cert(X509.from_cryptography(certificates.root_cert))
            store.add_cert(X509.from_cryptography(certificates.intermediate_cert))

            store_ctx = X509StoreContext(
                store, X509.from_cryptography(certificates.leaf_cert)
            )
            store_ctx.verify_certificate()

        except OpenSSLError as e:
            msg = f"Certificate chain verification failed: {e}"
            raise InvalidCertificateChainError(msg) from e

    def _check_certificate_validity(self, certificates: PKICertificates) -> None:
        """
        Compare token's root certificate with the trusted root certificate.

        Verifies that the root certificate in the token's certificate chain matches
        the trusted root certificate by comparing their TBS (To Be Signed) certificate
        fingerprints using SHA-256.

        Args:
            certificates: leaf, intermediate and root certificate from token's x5c chain

        Raises:
            VtpmValidationError: If the fingerprints don't match or if either
                                certificate is malformed
            AttributeError: If either certificate lacks the required TBS bytes

        """
        current_time = datetime.datetime.now(tz=datetime.UTC)

        for cert_name, cert in [
            ("Leaf", certificates.leaf_cert),
            ("Intermediate", certificates.intermediate_cert),
            ("Root", certificates.root_cert),
        ]:
            if not self._is_certificate_valid(cert, current_time):
                msg = f"{cert_name} certificate is not valid"
                raise InvalidCertificateChainError(msg)

    @staticmethod
    def _is_certificate_valid(
        cert: x509.Certificate, current_time: datetime.datetime
    ) -> bool:
        """
        Check if a certificate is valid at a specific time.

        This static method verifies that a certificate's validity period includes
        the specified time by checking the not-before and not-after dates.

        Args:
            cert: X.509 certificate to validate
            current_time: Timestamp to check validity against (must include timezone)

        Returns:
            bool: True if the certificate is valid at the specified time,
                False otherwise

        """
        not_before = cert.not_valid_before_utc.replace(tzinfo=datetime.UTC)
        not_after = cert.not_valid_after_utc.replace(tzinfo=datetime.UTC)
        return not_before <= current_time <= not_after
