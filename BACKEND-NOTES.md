# Python backend integration notes

This document proposes the next phase. None of these endpoints exists in this
package. Agree on the endpoint names and payloads as a team before implementing.
Django is the previously selected backend direction; the frontend remains plain
HTML, CSS, and JavaScript.

## Suggested endpoint contract

| Method and path | Responsibility |
| --- | --- |
| `POST /api/login/` | Verify the user's credentials and establish a server-side session |
| `GET /api/session/` | Return the current signed-in user, or 401 |
| `POST /api/logout/` | Invalidate the session |
| `GET /api/servers/` | Return only servers assigned to the signed-in user |
| `POST /api/servers/<id>/sessions/` | Check permission and create a remote desktop session |
| `DELETE /api/sessions/<id>/` | Authorize and close an active remote session |

The access-code page can remain visually simple, but a shared static code must
not become production authentication. Decide whether each user receives a unique
revocable credential or uses Django username/password authentication. If using
passwords, rely on Django's authentication and password handling.

## Where the frontend changes

1. `handleLogin()` calls the login API instead of comparing a code in JavaScript.
2. Initialization checks `/api/session/` instead of trusting client state.
3. Load the server catalog from `/api/servers/` instead of `DEMO_SERVERS`.
4. The Connect handler requests a session for the chosen server.
5. Replace the desktop placeholder with the selected gateway's browser client.
6. Disconnect closes the remote session; logout also invalidates the login session.
7. Display loading, denied-access, unavailable-server, and expired-session states.

Use Django session cookies and CSRF protection for state-changing requests when
using cookie authentication. Prefer serving frontend and backend on the same
origin to keep integration simple. Reject unauthorized server/session IDs even
when someone manually changes a URL or sends a request outside the UI.

Never send RDP passwords to the browser. Keep credentials and VM configuration
on the server. Return only the safe fields the frontend needs. Keep icon markup
local and choose it by OS identifier rather than accepting SVG/HTML from an API.

## Remote desktop integration boundary

A browser cannot open a native RDP connection just by loading an iframe or an IP
address. A compatible browser remote desktop gateway/client must bridge the web
session to the Windows VM. The Python backend manages identity, permission, and
session creation; the gateway handles desktop transport and input.

The gateway choice and your laptop/VM setup remain a separate step. Do not add
fake online status or pretend a connection succeeded before that integration.
