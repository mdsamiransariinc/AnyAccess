"""Run with Python 3. No pip packages required; refuses to overwrite secrets."""
import base64
import os
from pathlib import Path
import secrets
root = Path(__file__).resolve().parent.parent
path = root / ".env"
if path.exists():
    raise SystemExit(".env already exists. Edit it manually; do not regenerate keys for an existing database.")
content = (
    f"DJANGO_SECRET_KEY={secrets.token_urlsafe(48)}\n"
    f"GUACAMOLE_JSON_SECRET={secrets.token_hex(16)}\n"
    f"CREDENTIAL_KEY={base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()}\n"
    "PUBLIC_ORIGIN=http://localhost:8080\nBIND_ADDRESS=127.0.0.1\nHTTP_PORT=8080\n"
)
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as stream:
    stream.write(content)
print("Created .env. Keep it private and back it up with your database.")
