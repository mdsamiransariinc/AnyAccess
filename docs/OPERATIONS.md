# Operations and limits

## Start, stop, update

```bash
docker compose up -d
docker compose stop
docker compose up -d --build
```

Include `-f compose.yaml -f compose.https.yaml` for HTTPS starts/updates.
Stopping Docker or shutting down the gateway laptop disconnects everyone.
A stopped/hibernating VM host makes its guests unavailable too.

`docker compose down` removes containers but retains the named data volume.
**Do not use `docker compose down -v` unless you intentionally want to delete the
saved database, users, server records, and session history.**

## Backup

Keep a copy of the database AND the `.env` keys. Backups contain sensitive data.
One simple consistent home-lab backup is to stop writers, copy the database, and
restart. Create a local `backups` folder first:

```bash
docker compose stop web cleanup
docker compose cp web:/data/db.sqlite3 ./backups/db.sqlite3
docker compose start web cleanup
```

Copy `.env` and `deploy/certs` separately to secure storage. Do not commit them.
Test restores using a separate disposable installation before depending on them.
With web and cleanup stopped, `docker compose cp ./backups/db.sqlite3 web:/data/db.sqlite3`
can restore the database into the existing container/volume; restore its matching
keys too, then start the writers. Confirm file ownership allows appuser to write.

## Permissions and session lifecycle

AnyAccess website accounts are distinct from guest OS accounts. A website login
only receives assigned servers; the saved guest account determines permissions
inside Windows/Linux. An administrator can change assignments or disable a server.
The cleanup service observes these changes within its next scan.

The browser heartbeat runs every 20 seconds. Missing heartbeats for 120 seconds,
an expired Django login, disabled user/server, removed assignment, explicit stop,
or an eight-hour session age triggers revocation. Cleanup retries if Guacamole
is temporarily unreachable. During a gateway outage, new connection attempts are
denied; old transport closure cannot be guaranteed until the gateway is reachable
or the underlying connection fails. Review the Remote sessions admin page.

The three-open-session limit is an MVP guard, not an atomic resource scheduler;
simultaneous requests can race. Do not use this SQLite home-lab setup as a public
multi-tenant desktop service without stronger quotas and concurrency controls.

## Secrets

- DJANGO_SECRET_KEY signs Django data.
- CREDENTIAL_KEY encrypts database passwords and gateway tokens using Fernet.
- GUACAMOLE_JSON_SECRET signs/encrypts grants accepted by Guacamole.
- Certificate private keys are separate and stored in deploy/certs.

Encryption at rest reduces exposure from a database-only leak. Someone with both
the database and its encryption key can decrypt credentials. Host/Docker admins
can access environment variables and therefore must be trusted. Key rotation
requires an intentional migration or re-entering credentials, not just rerunning
setup_env.py.

## Network boundaries

Only nginx publishes a host port. Django, Guacamole's API, and guacd stay inside
the Compose network. nginx validates browser identity/Origin before upgrading a
WebSocket. JSON authentication grants contain one authorized connection each;
Guacamole's administration/login APIs are not publicly proxied.

HTTP is provided only for the initial localhost test. Use the HTTPS profile and
trusted certificates for other devices. Keep remote desktop ports on your private
network; internet/VPN setup is a separate deployment task. Public deployment needs
a security review, MFA, hardened login controls, patch management, and monitoring.
The OS/hardware choices are still yours because the laptop specifications were
not supplied.
