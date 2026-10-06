# Team guide: understand and modify the code

## File map

| File | Responsibility |
| --- | --- |
| `config/settings.py` | Django, session, origin, database, gateway settings |
| `config/urls.py` | Page and API routes |
| `portal/models.py` | Server records, assignments, remote session records |
| `portal/admin.py` | Admin forms; password encryption and session disconnect action |
| `portal/crypto.py` | Credential encryption and Guacamole's signed JSON format |
| `portal/gateway.py` | The only place that calls Guacamole HTTP APIs |
| `portal/views.py` | Login-adjacent views, permissions, page/API responses |
| `portal/management/commands/reap_sessions.py` | Cleanup for expired/abandoned/revoked sessions |
| `portal/migrations/` | Database schema changes; commit these with model changes |
| `templates/portal/` | Readable HTML for login, dashboard, desktop, shared layout |
| `static/portal/styles.css` | Original AnyAccess appearance |
| `static/portal/backend.css` | Extra styles for the real login and remote screen |
| `static/portal/dashboard.js` | Server search |
| `static/portal/desktop.js` | Real Guacamole display, keyboard/mouse, session lifecycle |
| `static/vendor/` | Official Apache Guacamole 1.6.0 client + license/notice |
| `compose.yaml` | Container wiring and persistent database volume |
| `deploy/nginx.conf` | Routing, WebSocket authorization, login throttling |
| `compose.https.yaml` and `deploy/nginx.https.conf` | Optional HTTPS profile |

## What changed from your old ZIP

The old `index.html` contained three hidden sections with hash-based navigation.
They are now separate Django templates and real URL routes. `servers.js` is
replaced by database-backed server records, and the shared ANYACCESS code is
replaced by Django login. The previous CSS is retained.

Use this folder as the new project root. Do not copy the old demo `app.js` or
`servers.js` into the new templates: those files bypass the intended real flow.
Port your own styling changes to `static/portal/styles.css`, and text/layout
changes to the corresponding template. Keep element IDs used by desktop.js.

## Request flow

1. Django validates username/password and creates an HttpOnly session cookie.
2. Django queries only servers assigned to that user (superusers are an exception).
3. Connect opens `/servers/<id>/` and JavaScript POSTs to create a session.
4. Django rechecks permission, signs/encrypts a one-connection grant, and exchanges
   it with Guacamole over the internal Docker network.
5. Django returns a gateway session token and the actual connection identifier.
   The VM password is not returned. The token itself is sensitive but the browser
   needs it to establish the authorized tunnel; keep it in memory only.
6. The browser opens a same-origin WebSocket. nginx asks Django to validate the
   browser login, exact Origin, token ownership, server assignment, and expiry.
7. Guacamole/guacd connect to the VM and stream the desktop to the official client.
8. The browser sends heartbeats every 20 seconds. Disconnect revokes the token;
   cleanup runs every 20 seconds and closes abandoned sessions after ~120–140
   seconds without a heartbeat. A blocked/missing cleanup service delays this.

The 60-second encrypted grant expiry is only for exchanging that grant for a
Guacamole token. It is not the duration of a remote desktop session. Remote
sessions have an eight-hour maximum enforced by checks and background cleanup.

## Endpoints

| Method | Path | Result |
| --- | --- | --- |
| GET/POST | `/login/` | Django login form |
| POST | `/logout/` | Revoke this login's remote sessions and log out |
| GET | `/dashboard/` | Assigned servers rendered into HTML |
| GET | `/servers/<id>/` | Authorized desktop page |
| POST | `/api/servers/<id>/sessions/` | `{session_id, token, data_source, connection_id}` |
| POST | `/api/sessions/<uuid>/heartbeat/` | `{ok: true}` or expiry/access error |
| POST | `/api/sessions/<uuid>/stop/` | `{closed, cleanup_pending}`; 202 means retry pending |
| GET | `/api/gateway-check/` | Internal nginx authorization only; blocked externally |

All external POSTs require a CSRF token. Templates already provide it and
JavaScript sends `X-CSRFToken`. There is no public API that accepts an arbitrary
hostname/password from an ordinary user.

## Dependency versions

`requirements.txt` describes the intended version ranges. Docker installs
`requirements.lock.txt`, which records the versions used for the preparation
checks. When upgrading, regenerate the lock in a clean Python environment and
run the integration tests before rebuilding. Keep Guacamole containers and its
vendored client at the same version.

## Editing and rebuilding

1. Make changes in the source files.
2. Run `docker compose up -d --build` (include the HTTPS override when using it).
3. Refresh the browser. This production-style Compose setup does not live-mount
   source files, so editing files alone does not update running containers.

If models change, create migrations and copy them out of the container before
rebuilding (otherwise they exist only in that container):

```bash
docker compose exec web python manage.py makemigrations portal
docker compose cp web:/app/portal/migrations/. ./portal/migrations/
docker compose up -d --build --force-recreate migrate web cleanup
```

Review generated migrations before applying them to a database with real data;
back up first. Use local Django development if your team later prefers hot reload,
but keep nginx/Guacamole and same-origin routing for full desktop integration.

## Team ownership

- UI teammate: templates and CSS.
- Browser teammate: dashboard.js and desktop.js.
- Python teammate: views/models/admin/gateway and migrations.
- Infrastructure teammate: VM networking, Compose, nginx, certificates, backups.

Keep edits to gateway security and crypto small and reviewed. Do not delete CSRF
or permission checks to make an error disappear. Never commit `.env`, database
copies, remote passwords, private certificate keys, or bearer tokens.

## Intentional MVP limits

The gateway API adapter is tied to Guacamole 1.6.0. Test token creation,
connection identifiers, transport, and revocation before upgrading Guacamole and
its bundled JavaScript together. Clipboard sync, file transfers, audio, webcam,
mobile on-screen keyboard, VM power control, and VM provisioning are not wired
into this custom UI. Desktop mouse/keyboard is the acceptance target.
