/**
 * Real remote desktop client. Django authorizes; Guacamole streams pixels/input.
 * Tokens stay in memory. Do not put them in localStorage, console logs, or links.
 * This version uses WebSocket transport; HTTP-tunnel fallback is not enabled.
 */
(() => {
  const page = document.getElementById("desktop");
  const screen = document.getElementById("remote-screen");
  const notice = document.getElementById("desktop-notice");
  const status = document.getElementById("connection-status");
  const csrf = document.querySelector("#csrf-form [name=csrfmiddlewaretoken]").value;
  const disconnectButton = document.getElementById("disconnect");
  const cadButton = document.getElementById("cad");
  let session = null;
  let client = null;
  let keyboard = null;
  let heartbeatTimer = null;
  let stopped = false;
  let connected = false;

  async function post(url, options = {}) {
    const response = await fetch(url, {
      method: "POST", credentials: "same-origin", cache: "no-store",
      headers: { "X-CSRFToken": csrf, "Accept": "application/json" }, ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status}). Please return to Servers and try again.`);
    return data;
  }

  function showMessage(message) { notice.hidden = false; notice.textContent = message; }

  // Called by buttons, errors, logout, navigation, and server-side revocation.
  async function stop(message = "Disconnected.") {
    if (stopped) return;
    stopped = true;
    connected = false;
    clearInterval(heartbeatTimer);
    cadButton.disabled = true;
    if (keyboard) keyboard.reset();
    if (client) client.disconnect();
    status.textContent = "Disconnected";
    showMessage(message);
    if (session) {
      try {
        const result = await post(`/api/sessions/${session.session_id}/stop/`, { keepalive: true });
        if (result.cleanup_pending) showMessage(`${message} Server cleanup is pending and will be retried.`);
      } catch {
        showMessage(`${message} Cleanup could not be confirmed; the background cleanup service will retry.`);
      }
      session = null;
    }
  }

  function resizeDisplay() {
    if (!client || !connected) return;
    const display = client.getDisplay();
    if (display.getWidth() && display.getHeight()) {
      display.scale(Math.min(screen.clientWidth / display.getWidth(), screen.clientHeight / display.getHeight(), 1));
    }
    client.sendSize(Math.max(320, screen.clientWidth), Math.max(240, screen.clientHeight));
  }

  async function start() {
    try {
      if (!window.Guacamole) throw new Error("The remote desktop client failed to load. Refresh the page.");
      session = await post(page.dataset.startUrl);
      if (stopped) {
        await post(`/api/sessions/${session.session_id}/stop/`, {keepalive: true});
        return;
      }
      const socketScheme = location.protocol === "https:" ? "wss:" : "ws:";
      const tunnel = new Guacamole.WebSocketTunnel(`${socketScheme}//${location.host}/guacamole/websocket-tunnel`);
      client = new Guacamole.Client(tunnel);
      const display = client.getDisplay();
      screen.replaceChildren(display.getElement());
      client.onerror = () => stop("Connection failed. Check the VM address, login credentials, remote desktop service, and firewall.");
      tunnel.onerror = () => stop("The remote desktop tunnel failed. Check the gateway and your network.");
      client.onstatechange = state => {
        if (state === 3) {
          connected = true;
          status.textContent = "Connected";
          notice.hidden = true;
          cadButton.disabled = false;
          resizeDisplay();
          screen.focus();
        } else if (state === 5 && !stopped) {
          stop("The remote server ended the connection.");
        }
      };
      display.onresize = () => {
        if (display.getWidth() && display.getHeight()) {
          display.scale(Math.min(screen.clientWidth / display.getWidth(), screen.clientHeight / display.getHeight(), 1));
        }
      };
      const mouse = new Guacamole.Mouse(display.getElement());
      mouse.onEach(["mousedown", "mouseup", "mousemove"], event => {
        if (connected) client.sendMouseState(event.state, true);
      });
      screen.addEventListener("pointerdown", () => screen.focus());
      screen.addEventListener("contextmenu", event => event.preventDefault());
      keyboard = new Guacamole.Keyboard(document);
      keyboard.onkeydown = keysym => {
        if (!connected || document.activeElement !== screen) return true;
        client.sendKeyEvent(1, keysym);
        return false;
      };
      keyboard.onkeyup = keysym => { if (connected) client.sendKeyEvent(0, keysym); };
      screen.addEventListener("blur", () => keyboard.reset());
      window.addEventListener("blur", () => keyboard.reset());
      const parameters = new URLSearchParams({
        token: session.token, GUAC_DATA_SOURCE: session.data_source,
        GUAC_ID: session.connection_id, GUAC_TYPE: "c",
        GUAC_WIDTH: Math.max(320, screen.clientWidth), GUAC_HEIGHT: Math.max(240, screen.clientHeight),
        GUAC_DPI: "96", GUAC_TIMEZONE: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      parameters.append("GUAC_IMAGE", "image/png");
      parameters.append("GUAC_IMAGE", "image/jpeg");
      client.connect(parameters.toString());
      heartbeatTimer = setInterval(async () => {
        if (stopped || !session) return;
        try { await post(`/api/sessions/${session.session_id}/heartbeat/`); }
        catch (error) { stop(error.message); }
      }, 20000);
    } catch (error) {
      await stop(error.message);
    }
  }

  disconnectButton.addEventListener("click", async () => {
    disconnectButton.disabled = true;
    await stop();
    location.assign("/dashboard/");
  });
  document.getElementById("back").addEventListener("click", async event => {
    event.preventDefault(); await stop(); location.assign("/dashboard/");
  });
  document.getElementById("logout-form").addEventListener("submit", async event => {
    event.preventDefault(); await stop(); event.target.submit();
  });
  cadButton.addEventListener("click", () => {
    if (!connected) return;
    [0xffe3, 0xffe9, 0xffff].forEach(key => client.sendKeyEvent(1, key));
    [0xffff, 0xffe9, 0xffe3].forEach(key => client.sendKeyEvent(0, key));
    screen.focus();
  });
  document.getElementById("fullscreen").addEventListener("click", async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await page.requestFullscreen();
    } catch { showMessage("Fullscreen is unavailable in this browser."); }
  });
  document.addEventListener("fullscreenchange", () => {
    document.getElementById("fullscreen").textContent = document.fullscreenElement ? "Exit fullscreen" : "⛶ Fullscreen";
    resizeDisplay();
  });
  window.addEventListener("resize", resizeDisplay);
  window.addEventListener("pagehide", () => {
    // Best effort only; the cleanup worker handles browsers that drop this request.
    if (client) client.disconnect();
    if (session) {
      const body = new FormData();
      body.append("csrfmiddlewaretoken", csrf);
      navigator.sendBeacon(`/api/sessions/${session.session_id}/stop/`, body);
    }
  });
  window.addEventListener("pageshow", event => { if (event.persisted) location.reload(); });
  start();
})();
