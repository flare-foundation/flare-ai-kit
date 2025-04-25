
# flare-ai-kit/tee/ra-tls.py

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ObjectIdentifier
from cryptography.hazmat.primitives import hashes
import datetime
import ssl

# Custom OID for the attestation token extension
ATTESTATION_TOKEN_OID = ObjectIdentifier("1.3.6.1.4.1.9999.1.1")  # Registered or private OID

def create_attestation_extension(attestation_token: str) -> x509.Extension:
    """
    Create a custom X.509 extension containing the attestation token.

    Args:
        attestation_token: The attestation token to embed.

    Returns:
        x509.Extension: The extension with the encoded token.
    """
    token_bytes = attestation_token.encode("utf-8")
    return x509.Extension(
        oid=ATTESTATION_TOKEN_OID,
        critical=False,
        value=x509.UnrecognizedExtension(
            oid=ATTESTATION_TOKEN_OID,
            value=token_bytes
        )
    )

def generate_key_and_csr(attestation_token: str, common_name: str = "localhost") -> tuple[bytes, bytes]:
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
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    # Build CSR
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject)
        .add_extension(
            create_attestation_extension(attestation_token),
            critical=False
        )
        .sign(private_key, hashes.SHA256())
    )

    # Serialize to PEM
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    csr_pem = csr.public_bytes(serialization.Encoding.PEM)

    return key_pem, csr_pem

def generate_self_signed_cert(attestation_token: str, common_name: str = "localhost", days_valid: int = 365) -> tuple[bytes, bytes]:
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
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    # Build certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=days_valid))
        .add_extension(
            create_attestation_extension(attestation_token),
            critical=False
        )
        .sign(private_key, hashes.SHA256())
    )

    # Serialize to PEM
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    return key_pem, cert_pem

def create_ssl_context(attestation_token: str, common_name: str = "localhost", days_valid: int = 365) -> ssl.SSLContext:
    """
    Create an SSLContext with an in-memory self-signed certificate containing the attestation token.

    Args:
        attestation_token: The attestation token to embed.
        common_name: The Common Name (CN) for the certificate.
        days_valid: Validity period of the certificate in days.

    Returns:
        ssl.SSLContext: Configured SSL context for server-side TLS.
    """
    # Generate self-signed certificate
    key_pem, cert_pem = generate_self_signed_cert(attestation_token, common_name, days_valid)

    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert_pem, keyfile=key_pem)

    return context