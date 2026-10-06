# Testing and troubleshooting

## Automated tests

```bash
docker compose exec web python manage.py test portal --verbosity 2
```

The 13 tests cover real Django login, CSRF rejection, per-user server visibility,
unauthorized connection rejection, encrypted credential handling, gateway token
binding, logout/stop revocation, abandoned-session cleanup, retrying failed
revocation, admin password preservation, and OpenSSL compatibility.

Gateway HTTP calls are mocked. The tests do not establish a real WebSocket or
contact a Windows VM. Passing them is necessary but not sufficient for the live
installation. OpenSSL must be installed for the encryption comparison test.

## Live acceptance (run on your laptops)

- `docker compose ps`: web, cleanup, guacamole, guacd, proxy remain running;
  migrate exited successfully.
- `docker compose exec proxy nginx -t`: configuration parses.
- Guacamole startup logs show encrypted JSON authentication enabled.
- TCP test from guacd network reaches the VM's RDP port.
- Create Alice and Bob; assign a VM only to Alice.
- Alice can connect, see the desktop, type in Notepad, use mouse and fullscreen.
- Bob cannot see Alice's VM or open its numeric URL manually.
- A connection attempted with an incorrect VM password fails visibly.
- Disconnect stops interaction. Reconnecting establishes a new gateway token.
- Logging out closes that browser login's open sessions.
- Closing a browser tab is cleaned up; with cleanup running, the session should
  be revoked within about 140 seconds of its last heartbeat.
- Removing a user's assignment while connected leads to disconnection by the
  next heartbeat/cleanup pass (not instantaneous at the database write).
- HTTPS: both laptops trust the lab CA, the browser shows no certificate error,
  and the WebSocket uses wss://.

## Common problems

| Symptom | What to check |
| --- | --- |
| Docker cannot start | Supported host OS, hardware virtualization, Docker Desktop/WSL configuration |
| VM will not boot | Guest OS requirements and hypervisor configuration; this is separate from Django |
| Website unavailable | `docker compose ps`; port conflict; web health; host firewall |
| 400 Bad Request | Browser hostname must match PUBLIC_ORIGIN; restart after editing .env |
| 403 CSRF error | Use the configured origin consistently and keep the cookie/CSRF checks intact |
| Login throttled (429) | Stop retrying and wait; nginx limits requests to login endpoints |
| No server cards | Enabled flag and Allowed users; normal users need explicit assignment |
| 502 at session creation | Guacamole not ready, wrong JSON key, gateway configuration |
| WebSocket 403 | PUBLIC_ORIGIN scheme/name/port mismatch, expired login, or unassigned server |
| WebSocket 404/502 | nginx route/gateway startup; inspect container logs |
| RDP timeout | guacd network cannot reach VM; wrong IP/port, sleep, firewall, Wi-Fi isolation |
| RDP authentication fails | Actual Windows password, username/domain, RDP user permission, NLA |
| RDP certificate failure | Correct trusted certificate or deliberate lab-only Ignore certificate setting |
| Ubuntu xrdp fails with NLA | Select TLS if that matches the xrdp server configuration |
| Connected but input seems inactive | Click inside the desktop first; browser shortcuts may stay local |
| Session ends in background | Browser timers may be throttled; heartbeat grace is intentionally bounded |
| Credentials unreadable after restart | CREDENTIAL_KEY changed or wrong .env loaded; restore the original key |
| Session stays open after leaving | Cleanup service must run; inspect its logs and gateway reachability |
| Styles missing after edits | Rebuild image; collectstatic runs on web startup |

Useful commands:

```bash
docker compose logs --tail=100 web guacamole guacd cleanup proxy
docker compose exec proxy nginx -t
docker compose exec web python manage.py check
docker compose exec web python manage.py reap_sessions
```

Avoid sharing log files publicly without checking their contents. Default nginx
access logging omits query strings because tunnel URLs contain session tokens.
Do not enable verbose gateway logging when collecting logs to share.

## Preparation result

The preparation environment passed: migrations, Django system checks, static
collection, JavaScript syntax, and all 13 automated tests. No Docker daemon or
Windows VM was available there. The live acceptance steps above remain for the
actual installation; this package is not labeled end-to-end verified.
