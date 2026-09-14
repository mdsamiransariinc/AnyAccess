# Quick review after a change

Run locally as described in README.md, then check:

- Empty login submission is blocked by the required field.
- An incorrect code shows a clear error.
- ANYACCESS opens the dashboard.
- Searching windows, linux, or ubuntu filters the cards (case-insensitive).
- A search with no matches shows the empty state; Clear search restores cards.
- Each Connect button opens the correct server name.
- An unknown server fragment returns to the dashboard.
- Fullscreen works where supported; unsupported browsers show a message.
- Disconnect and Servers return to the dashboard.
- Log out returns to login; protected fragments redirect back to login.
- Refresh resets demo access rather than pretending there is a real session.
- Tab navigation reaches the controls and has visible focus.
- Cards stack on a narrow screen; text and controls remain usable when zoomed.
- No console errors appear during this flow.

Packaging checks performed for this handoff: JavaScript syntax, referenced files,
HTML IDs used by the controller, and ZIP integrity. This is not a claim of a
complete browser or production security test.
