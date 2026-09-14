/**
 * AnyAccess frontend controller.
 * Read in order: configuration → cards → navigation → actions → initialization.
 * servers.js must load first. No framework or package installation is required.
 *
 * SECURITY: the access code and state below only simulate the website flow.
 * They cannot protect a real server. Python must authenticate and authorize
 * every real server request when backend integration is added.
 */

const DEMO_ACCESS_CODE = "ANYACCESS";

// In-memory state intentionally resets when the page is refreshed.
const state = {
  hasDemoAccess: false,
};

/** Find an element by the ID used in index.html. */
function getElement(id) {
  return document.getElementById(id);
}

/** Insert text safely into the server-card HTML template. */
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character];
  });
}

// ── SERVER CARDS ──────────────────────────────────────────────────────

/** Generate one card. The SVG icon comes only from our trusted local catalog. */
function createServerCard(server) {
  return `
    <article class="card">
      <div class="card-top">
        <div class="os-icon ${escapeHtml(server.id)}">
          <svg viewBox="0 0 24 24" aria-hidden="true">${server.icon}</svg>
        </div>
        <span class="tag">Demo server</span>
      </div>
      <h2>${escapeHtml(server.name)}</h2>
      <p class="description">${escapeHtml(server.description)}</p>
      <div class="server-meta">
        <span>Connection</span>
        <strong>Not configured</strong>
      </div>
      <button
        class="primary"
        data-connect="${escapeHtml(server.id)}"
        aria-label="Connect to ${escapeHtml(server.name)}"
      >
        Connect <span aria-hidden="true">↗</span>
      </button>
    </article>
  `;
}

/** Rebuild the visible cards after the search input changes. */
function renderServerCards(searchText = "") {
  const query = searchText.trim().toLowerCase();
  const matchingServers = DEMO_SERVERS.filter((server) => {
    const searchableText = `${server.name} ${server.os}`.toLowerCase();
    return searchableText.includes(query);
  });

  getElement("cards").innerHTML = matchingServers.map(createServerCard).join("");
  getElement("empty").hidden = matchingServers.length > 0;

  // Calculate the count so adding a server does not require editing the HTML.
  document.querySelector(".count").textContent = String(DEMO_SERVERS.length).padStart(2, "0");
}

function clearSearch() {
  getElement("search").value = "";
  renderServerCards();
}

// ── PAGE NAVIGATION ───────────────────────────────────────────────────

/** Hash routes work on any static server: #login, #dashboard, #desktop/windows. */
function showCurrentPage() {
  const route = window.location.hash || "#login";

  // This is a demo navigation guard, NOT a security boundary.
  if (!state.hasDemoAccess && route !== "#login") {
    window.location.hash = "login";
    return;
  }

  const isDesktopRoute = route.startsWith("#desktop/");
  const selectedServerId = route.slice("#desktop/".length);
  const selectedServer = isDesktopRoute
    ? DEMO_SERVERS.find((server) => server.id === selectedServerId)
    : null;

  if (isDesktopRoute && !selectedServer) {
    window.location.hash = "dashboard";
    return;
  }

  if (!["#login", "#dashboard"].includes(route) && !isDesktopRoute) {
    window.location.hash = state.hasDemoAccess ? "dashboard" : "login";
    return;
  }

  const activePage = isDesktopRoute ? "desktop" : route.slice(1);
  for (const pageId of ["login", "dashboard", "desktop"]) {
    getElement(pageId).hidden = pageId !== activePage;
  }

  getElement("logout").hidden = activePage === "login";
  if (selectedServer) {
    getElement("desktop-name").textContent = selectedServer.name;
    getElement("fullscreen-error").textContent = "";
  }

  const pageTitle = selectedServer
    ? selectedServer.name
    : activePage === "dashboard" ? "Servers" : "Log in";
  document.title = `${pageTitle} — AnyAccess`;
}

// ── LOGIN, LOGOUT, AND DESKTOP ACTIONS ─────────────────────────────────

function handleLogin(event) {
  event.preventDefault(); // Keep the browser from submitting/reloading the page.
  const codeInput = getElement("code");

  if (codeInput.value.trim() !== DEMO_ACCESS_CODE) {
    getElement("code-error").textContent = `Use ${DEMO_ACCESS_CODE} to enter the preview.`;
    codeInput.setAttribute("aria-invalid", "true");
    return;
  }

  state.hasDemoAccess = true;
  getElement("code-error").textContent = "";
  codeInput.removeAttribute("aria-invalid");
  codeInput.value = "";
  window.location.hash = "dashboard";
}

async function exitFullscreenIfNeeded() {
  if (document.fullscreenElement) {
    try {
      await document.exitFullscreen();
    } catch {
      // Navigation can still proceed if the browser refuses this request.
    }
  }
}

async function returnToDashboard() {
  await exitFullscreenIfNeeded();
  // Later: ask the backend/gateway to close the active remote session here.
  window.location.hash = "dashboard";
}

async function handleLogout() {
  await exitFullscreenIfNeeded();
  // Later: also invalidate the real session in the Python backend.
  state.hasDemoAccess = false;
  clearSearch();
  window.location.hash = "login";
}

async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      // Include the toolbar so Disconnect remains available in fullscreen.
      await getElement("desktop").requestFullscreen();
    }
  } catch {
    getElement("fullscreen-error").textContent =
      "Fullscreen is unavailable in this browser. You can still use the desktop view.";
  }
}

// ── EVENT LISTENERS ───────────────────────────────────────────────────

function registerEventListeners() {
  getElement("login-form").addEventListener("submit", handleLogin);
  getElement("fill-code").addEventListener("click", () => {
    getElement("code").value = DEMO_ACCESS_CODE;
    getElement("code").focus();
  });

  getElement("search").addEventListener("input", (event) => {
    renderServerCards(event.target.value);
  });
  getElement("clear-search").addEventListener("click", () => {
    clearSearch();
    getElement("search").focus();
  });

  // One listener on the parent handles all cards, including newly rendered ones.
  getElement("cards").addEventListener("click", (event) => {
    const connectButton = event.target.closest("[data-connect]");
    if (connectButton) {
      window.location.hash = `desktop/${connectButton.dataset.connect}`;
    }
  });

  getElement("back").addEventListener("click", returnToDashboard);
  getElement("disconnect").addEventListener("click", returnToDashboard);
  getElement("logout").addEventListener("click", handleLogout);
  getElement("fullscreen").addEventListener("click", toggleFullscreen);

  document.addEventListener("fullscreenchange", () => {
    getElement("fullscreen").textContent = document.fullscreenElement
      ? "⛶ Exit fullscreen"
      : "⛶ Fullscreen";
  });
  window.addEventListener("hashchange", showCurrentPage);
}

// Scripts load at the end of <body>, so all HTML elements already exist here.
registerEventListeners();
renderServerCards();
showCurrentPage();
