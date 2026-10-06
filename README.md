# AnyAccess — Django backend and working remote desktop integration

This package replaces the earlier static demo with a Python/Django application.
It preserves the AnyAccess layout and connects its desktop area to Apache
Guacamole's actual browser client. Supply your own reachable VMs and credentials.

**Start with [docs/SETUP.md](docs/SETUP.md).** It contains the full installation,
VM networking, account setup, server registration, and HTTPS instructions.

## What is included

- Real Django username/password login, logout, CSRF protection, and sessions.
- Server records and per-user assignments in Django admin.
- Searchable cards containing only servers the current user can access.
- Real browser desktop transport through Guacamole, with mouse, keyboard,
  fullscreen, resize, Ctrl+Alt+Del, and Disconnect.
- RDP and VNC desktop targets; SSH targets show a terminal, not a graphical OS.
- Encrypted stored server passwords, isolated gateway sessions, origin/session
  checks at the WebSocket entrypoint, and a background cleanup worker.
- Docker Compose for Django/Gunicorn, nginx, Guacamole, guacd, and cleanup.
- An optional HTTPS configuration with a private lab certificate generator.
- Comments, migrations, integration tests, and team modification notes.

## Quick start (after installing Python 3 and Docker with Compose)

Run in this extracted folder:

```bash
python scripts/setup_env.py
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Open http://localhost:8080/admin/ and add a Server and an ordinary User. Assign
that User in the Server's Allowed users field. Then open http://localhost:8080/
and log in. The old shared ANYACCESS code is intentionally removed.

You need a running RDP/VNC/SSH target before Connect can succeed. Follow the
Windows VM instructions in SETUP.md, including the test from the guacd network.

## Read these guides

| Guide | Purpose |
| --- | --- |
| [SETUP](docs/SETUP.md) | Complete installation, Windows VM setup, second laptop, HTTPS |
| [TEAM-GUIDE](docs/TEAM-GUIDE.md) | File responsibilities, modifying the old frontend, API contracts |
| [TESTING](docs/TESTING.md) | Automated checks, live acceptance checklist, troubleshooting |
| [OPERATIONS](docs/OPERATIONS.md) | Start/stop, backups, permissions, keys, limitations |
| [SOURCES](docs/SOURCES.md) | Official technical references and third-party licensing |

## Verification boundary

Django checks, migrations, static collection, JavaScript syntax, and 13 focused
backend tests passed during preparation. The tests mock gateway HTTP calls;
an encryption test separately matches OpenSSL output. Docker and a reachable
Windows VM were unavailable in the preparation environment, so the complete
container-to-browser-to-RDP path has NOT been run here. Perform the live
acceptance checklist on your laptops before relying on it.

This is a runnable home-lab integration, not a claim of completed deployment to
your hardware. It does not create VMs, install operating systems, or turn the
previously hosted preview into a network path to your home.
