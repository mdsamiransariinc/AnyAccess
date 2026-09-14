# AnyAccess — team source package

A readable, commented version of the AnyAccess frontend built from your sketches.
The design follows the published prototype. The code is organized for a team to
edit without a framework, package manager, or build step.

## 1. Run it locally

1. Extract this ZIP.
2. Open the extracted `AnyAccess-source` folder in VS Code or another editor.
3. Open a terminal **inside that folder**.
4. Run:

   ```bash
   python -m http.server 8000 --bind 127.0.0.1
   ```

   On Windows, use `py` instead of `python` if needed. On macOS/Linux, use
   `python3` if that is your installed command.

5. Open http://127.0.0.1:8000 in your browser.
6. Enter **ANYACCESS**, then click **Log in**.
7. Press Ctrl+C in the terminal when you want to stop the server.

Python here only serves the frontend files. This is not a Django application or
an RDP backend. The local development server is not intended for deployment.
You can also open `index.html` directly for this prototype, but a local HTTP
server will be more useful once API integration begins.

The optional DM Sans font loads from Google Fonts. Without internet, the site
uses an installed system font; the pages still work.

## 2. Files and responsibilities

| File | Purpose | Typical changes |
| --- | --- | --- |
| `index.html` | Shared header/footer and all three page layouts | Headings, labels, page structure |
| `assets/css/styles.css` | Appearance and responsive layouts | Colors, spacing, cards, mobile layout |
| `assets/js/servers.js` | Sample server catalog | Add/remove servers, rename them, change icons |
| `assets/js/app.js` | Login simulation, search, routing, fullscreen | Buttons, validation, navigation behavior |
| `BACKEND-NOTES.md` | Suggested Python integration plan | Coordinate frontend/backend work |
| `MANUAL-CHECKS.md` | Short checklist for reviewing changes | Verify the user flow |

Scripts are loaded at the bottom of `index.html`. Keep `servers.js` before
`app.js`, because the controller needs `DEMO_SERVERS` from the catalog.

## 3. How the pages work

The three screens are separate `<main>` elements in one HTML document. JavaScript
shows one and hides the others. They are not three independent HTML files.

| URL fragment | Visible screen |
| --- | --- |
| `#login` | Access-code form |
| `#dashboard` | Server cards and search |
| `#desktop/windows` | Windows desktop placeholder |
| `#desktop/linux` | Linux desktop placeholder |
| `#desktop/ubuntu` | Ubuntu desktop placeholder |

`showCurrentPage()` reads the fragment and chooses a screen. Unknown routes
redirect to login or the dashboard. Browser Back and Forward use the same logic.

`state.hasDemoAccess` is memory-only. Refreshing the page resets the preview and
returns you to login. This is intentional until real sessions are implemented.

## 4. Common edits

### Change text or page layout

Open `index.html`. Search for `PAGE 1`, `PAGE 2`, or `PAGE 3` comments. Edit the
text or markup within that section. Preserve IDs used by `getElement()` in
`app.js`, or update both files together.

### Change colors or spacing

Open `assets/css/styles.css`. Sections are labeled. For example, `.primary`
controls the blue action buttons; `.card` controls server cards; `.cards`
controls the grid. Responsive rules near the end adjust the layout for smaller
screens. The accent color currently uses `#2d55e7` in several rules.

### Add a server

Copy one object in `DEMO_SERVERS` inside `assets/js/servers.js`. Give it a unique,
URL-safe `id`, then change `name`, `os`, and `description`. Reuse a trusted icon or
supply developer-authored SVG. Add `.os-icon.your-id` in CSS if it needs a specific
color. The total server count updates automatically.

Do not enter an IP address, password, or real access credential in this catalog.
It only describes demo cards. `protocol` is a reserved metadata field and is not
yet rendered or used to make connections.

### Change the demo code

Edit `DEMO_ACCESS_CODE` at the top of `app.js`. Also update the displayed example
inside the `fill-code` button in `index.html`, and these README instructions.
This changes the demo experience only; it does not create secure authentication.

### Change the Connect action

Find the listener for `cards` in `registerEventListeners()`. It currently changes
the URL fragment. Later, request a real session from Python and initialize the
remote desktop client. See `BACKEND-NOTES.md` before integrating.

## 5. Work together

A simple division of responsibility:

| Area | Suggested ownership |
| --- | --- |
| Page layout and accessibility | HTML teammate |
| Styling and mobile layout | CSS teammate |
| Search, navigation, and browser actions | JavaScript teammate |
| Users, server permissions, and remote sessions | Python/backend teammate |

These are areas of ownership, not a required team size. One person can own more
than one area. Coordinate changes to element IDs and CSS class names.

Put the extracted folder in your own Git repository. Make one branch per feature,
use descriptive commits, and review each other's changes before merging. Avoid
editing the same section simultaneously when possible. Do not commit credentials,
virtual environments, or local configuration containing secrets.

## 6. What is complete and what is still a demo

Works now: access-code validation for the demo flow, server search, server cards,
page navigation, fullscreen where supported, and logout/disconnect navigation.

Not implemented: real authentication, permissions, a database, server discovery,
health checks, Windows access, an RDP gateway, or real remote sessions.

The code is entirely visible to the browser. The demo code and route guard are
not security controls. Never put server credentials into frontend source. Real
access must be checked by the backend for every request.

This package is a separate, readable handoff copy. Editing it locally does not
automatically update the previously published site.
