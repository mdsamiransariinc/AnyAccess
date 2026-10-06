"""Create a private lab CA + server certificate. Trust only lab-ca.crt on clients.
Run inside the web image with /certs mounted, as described in docs/SETUP.md.
"""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import ipaddress
import os
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

parser = argparse.ArgumentParser()
parser.add_argument("--hostname", required=True, help="Laptop 1 LAN IP or DNS name, without scheme/port")
parser.add_argument("--output", default="/certs", help="Certificate output directory")
args = parser.parse_args()
output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)
if any(output.iterdir()):
    raise SystemExit("/certs is not empty. Refusing to replace existing keys/certificates.")
now = datetime.now(timezone.utc)
ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AnyAccess private lab CA")])
ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
      .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
      .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=3650))
      .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
      .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
          data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True,
          encipher_only=False, decipher_only=False), critical=True)
      .sign(ca_key, hashes.SHA256()))
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
names = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
try: names.append(x509.IPAddress(ipaddress.ip_address(args.hostname)))
except ValueError: names.append(x509.DNSName(args.hostname))
cert = (x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, args.hostname)]))
        .issuer_name(ca_name).public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(names), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256()))
for name, value in [("lab-ca.key", ca_key), ("server.key", key)]:
    data = value.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    fd = os.open(output/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream: stream.write(data)
for name, value in [("lab-ca.crt", ca), ("server.crt", cert)]:
    (output/name).write_bytes(value.public_bytes(serialization.Encoding.PEM))
print("Created lab certificates. Trust lab-ca.crt on client devices; keep both .key files private.")
