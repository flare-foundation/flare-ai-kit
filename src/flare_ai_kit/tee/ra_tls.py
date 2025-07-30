# flare-ai-kit/tee/ra-tls.py
import datetime
import os
import ssl
import tempfile

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

# Custom OID for the attestation token extension
# ATTESTATION_TOKEN_OID = ObjectIdentifier("1.3.6.1.4.1.9999.1.1")  # Registered or private OID


def create_attestation_extension(attestation_token: str) -> x509.SubjectAlternativeName:
    """
    Create a SubjectAlternativeName extension containing the attestation token as a URI.

    Args:
        attestation_token: The attestation token to embed.

    Returns:
        x509.SubjectAlternativeName: The extension with the encoded token as a URI.

    """
    token_uri = f"attestation:{attestation_token}"
    return x509.SubjectAlternativeName([x509.UniformResourceIdentifier(token_uri)])


def generate_key_and_csr(
    attestation_token: str, common_name: str = "localhost"
) -> tuple[bytes, bytes]:
    """
    Generate a new private key and CSR with an attestation token extension, all in memory.

    Args:
        attestation_token: The attestation token to embed in the CSR.
        common_name: The Common Name (CN) for the certificate subject.

    Returns:
        tuple[bytes, bytes]: PEM-encoded private key and CSR.

    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Create subject name
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    # Build CSR
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject)
        .add_extension(create_attestation_extension(attestation_token), critical=False)
        .sign(private_key, hashes.SHA256())
    )

    # Serialize to PEM
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    csr_pem = csr.public_bytes(serialization.Encoding.PEM)

    return key_pem, csr_pem


def generate_self_signed_cert(token, common_name, days_valid):
    # logger.info("Generating self-signed certificate with SAN")
    try:
        # Generate private key
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        # Create certificate builder
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(
            x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                ]
            )
        )
        builder = builder.issuer_name(
            x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                ]
            )
        )
        builder = builder.not_valid_before(datetime.datetime.utcnow())
        builder = builder.not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
        )
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.public_key(public_key)

        # Add SAN for localhost
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )

        # Sign certificate
        certificate = builder.sign(private_key=private_key, algorithm=hashes.SHA256())

        # Serialize to PEM
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # logger.info("Certificate generated with SAN: DNS=localhost")
        return key_pem, cert_pem
    except Exception:
        # logger.error("Failed to generate certificate", exc_info=e)
        raise


def generate_self_signed_cert_OLD(
    attestation_token: str, common_name: str = "localhost", days_valid: int = 365
) -> tuple[bytes, bytes]:
    """
    Generate a new private key and self-signed certificate with an attestation token extension, all in memory.

    Args:
        attestation_token: The attestation token to embed in the certificate.
        common_name: The Common Name (CN) for the certificate subject.
        days_valid: Validity period of the certificate in days.

    Returns:
        tuple[bytes, bytes]: PEM-encoded private key and certificate.

    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Create subject and issuer (same for self-signed)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    # Build certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
        )
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False
        )
        .add_extension(create_attestation_extension(attestation_token), critical=False)
        .sign(private_key, hashes.SHA256())
    )

    # Serialize to PEM
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    return key_pem, cert_pem


def create_ssl_context(
    attestation_token: str, common_name: str = "localhost", days_valid: int = 365
) -> ssl.SSLContext:
    """
    Create an SSLContext with an in-memory self-signed certificate containing the attestation token.

    Args:
        attestation_token: The attestation token to embed.
        common_name: The Common Name (CN) for the certificate.
        days_valid: Validity period of the certificate in days.

    Returns:
        ssl.SSLContext: Configured SSL context for server-side TLS.

    """
    key_pem, cert_pem = generate_self_signed_cert(
        attestation_token, common_name, days_valid
    )

    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    # Use temporary files to load certificate and key
    cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    key_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")

    try:
        cert_file.write(cert_pem)
        cert_file.flush()
        key_file.write(key_pem)
        key_file.flush()

        # Load certificate and key into the SSL context
        context.load_cert_chain(certfile=cert_file.name, keyfile=key_file.name)
    finally:
        # Clean up temporary files
        cert_file.close()
        key_file.close()
        os.unlink(cert_file.name)
        os.unlink(key_file.name)

    return context
