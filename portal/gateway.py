"""All Guacamole HTTP calls stay here, making the gateway easy to replace/test."""
from datetime import timedelta
from urllib.parse import quote
import uuid
import requests
from django.conf import settings
from django.utils import timezone
from .crypto import guacamole_payload, decrypt_secret, encrypt_secret, token_digest
from .models import RemoteSession

class GatewayError(Exception):
    pass

def issue_session(user, server, django_session_key):
    parameters = {"hostname": server.hostname, "port": str(server.port), "username": server.username}
    if server.password_encrypted:
        parameters["password"] = decrypt_secret(server.password_encrypted)
    if server.protocol == "rdp":
        parameters.update({"security": server.rdp_security, "ignore-cert": str(server.ignore_certificate).lower(),
            "domain": server.domain, "resize-method": "display-update", "enable-drive": "false"})
    session_id = uuid.uuid4()
    now = timezone.now()
    # A unique gateway identity isolates sessions, including concurrent browser tabs.
    payload = {"username": f"anyaccess-{user.pk}-{session_id}",
        "expires": int((now + timedelta(seconds=60)).timestamp() * 1000),
        "connections": {server.name: {"protocol": server.protocol, "parameters": parameters}}}
    token = None
    try:
        response = requests.post(f"{settings.GUACAMOLE_URL}/api/tokens",
            data={"data": guacamole_payload(payload)}, timeout=10)
        response.raise_for_status()
        auth = response.json()
        token = auth["authToken"]
        source = auth["dataSource"]
        response = requests.get(f"{settings.GUACAMOLE_URL}/api/session/data/{quote(source, safe='')}/connections",
            params={"token": token}, timeout=10)
        response.raise_for_status()
        connections = response.json()
        if len(connections) != 1:
            raise ValueError("Expected exactly one authorized connection")
        connection_id = next(iter(connections))
        record = RemoteSession.objects.create(id=session_id, user=user, server=server,
            django_session_key=django_session_key, token_encrypted=encrypt_secret(token),
            token_hash=token_digest(token), last_seen=now,
            expires_at=now + timedelta(seconds=settings.REMOTE_SESSION_SECONDS))
        return {"session_id": str(record.id), "token": token,
                "data_source": source, "connection_id": connection_id}
    except Exception as exc:
        if token:
            try:
                requests.delete(f"{settings.GUACAMOLE_URL}/api/tokens/{quote(token, safe='')}", timeout=5)
            except requests.RequestException:
                pass
        # Never return upstream error bodies: these may contain connection details.
        raise GatewayError("Cannot create a remote session. Check Guacamole and the server configuration.") from exc

def revoke_session(record):
    """Deny new tunnels immediately; retry token revocation if the gateway is down."""
    RemoteSession.objects.filter(pk=record.pk).update(stop_requested=True)
    if record.revoked_at:
        return True
    try:
        token = decrypt_secret(record.token_encrypted)
        response = requests.delete(f"{settings.GUACAMOLE_URL}/api/tokens/{quote(token, safe='')}", timeout=5)
        if response.status_code not in (200, 204, 404):
            return False
    except requests.RequestException:
        return False
    RemoteSession.objects.filter(pk=record.pk).update(revoked_at=timezone.now(), token_encrypted="")
    return True
