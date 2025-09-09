import argparse
import datetime
import ipaddress
import os

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def create_attestation_extension(attestation_token: str) -> x509.SubjectAlternativeName:
    """Create a SubjectAlternativeName extension with the attestation token as a URI."""
    token_uri = f"attestation:{attestation_token}"
    return x509.SubjectAlternativeName([x509.UniformResourceIdentifier(token_uri)])


def generate_certificate(
    ip_address: str,
    output_dir: str,
    cert_name: str,
    key_name: str,
    days_valid: int = 365,
) -> None:
    """Generate a self-signed certificate and private key for the given IP address."""
    # Generate private key
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Create subject and issuer
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, ip_address)])

    # Build certificate
    placeholder_token = "placeholder-attestation-token"
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(subject)
    builder = builder.issuer_name(issuer)
    builder = builder.not_valid_before(datetime.datetime.utcnow())
    builder = builder.not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
    )
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.public_key(public_key)
    builder = builder.add_extension(
        x509.SubjectAlternativeName(
            [x509.IPAddress(ipaddress.IPv4Address(ip_address))]
        ),
        critical=False,
    )
    # builder = builder.add_extension(
    #    create_attestation_extension(placeholder_token),
    #    critical=False,
    # )
    certificate = builder.sign(private_key=private_key, algorithm=hashes.SHA256())

    # Serialize to PEM
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Save to files
    os.makedirs(output_dir, exist_ok=True)
    cert_path = os.path.join(output_dir, cert_name)  # f"cert-ss-{ip_address}.pem")
    key_path = os.path.join(output_dir, key_name)  # f"key-ss-{ip_address}.pem")
    with open(cert_path, "wb") as f:
        f.write(cert_pem)
    with open(key_path, "wb") as f:
        f.write(key_pem)
    print(f"Generated certificate: {cert_path}")
    print(f"Generated private key: {key_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate self-signed certificate for an IP address"
    )
    parser.add_argument("--ip", required=True, help="IP address for the certificate")
    parser.add_argument(
        "--output-dir", default="certs", help="Output directory for certificate and key"
    )
    parser.add_argument(
        "--days", type=int, default=365, help="Certificate validity in days"
    )
    args = parser.parse_args()

    import ipaddress

    try:
        ipaddress.IPv4Address(args.ip)  # Validate IP address
        generate_certificate(args.ip, args.output_dir, args.days)
    except ValueError as e:
        print(f"Invalid IP address: {e}")
        exit(1)
