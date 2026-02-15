const statusEl = document.getElementById("setup-status");
const progressBarEl = document.getElementById("setup-progress-bar");
const progressTextEl = document.getElementById("setup-progress-text");
const errorEl = document.getElementById("setup-error");

const cancelBtn = document.getElementById("setup-cancel-btn");
const retryBtn = document.getElementById("setup-retry-btn");
const openAnywayBtn = document.getElementById("setup-open-anyway-btn");
const openBtn = document.getElementById("setup-open-btn");
const closeBtn = document.getElementById("setup-close-btn");

let pollTimer = null;
let autoOpenTriggered = false;
let bridgeReady = false;
let bridgeInitTimer = null;
let isNavigating = false;
let isClosing = false;

function hasApi() {
  return Boolean(window.pywebview && window.pywebview.api);
}

async function callSetupApi(method, ...args) {
  if (isClosing && method !== "setup_exit") {
    throw new Error("Window is closing.");
  }
  if (!hasApi() || typeof window.pywebview.api[method] !== "function") {
    throw new Error("Desktop API not available.");
  }
  return window.pywebview.api[method](...args);
}

function beginSetupShutdown() {
  if (isClosing) {
    return;
  }
  isClosing = true;
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
  if (bridgeInitTimer) {
    window.clearInterval(bridgeInitTimer);
    bridgeInitTimer = null;
  }
}

function setVisible(el, visible) {
  if (visible) {
    el.classList.remove("hidden");
  } else {
    el.classList.add("hidden");
  }
}

function renderState(state) {
  const progress = Number(state.progress || 0);
  statusEl.textContent = state.status || "Preparing setup...";
  progressBarEl.style.width = `${Math.max(0, Math.min(100, progress))}%`;
  progressTextEl.textContent = `${Math.round(progress)}%`;

  const hasError = Boolean(state.error);
  errorEl.textContent = hasError ? state.error : "";
  setVisible(errorEl, hasError);

  if (state.running) {
    setVisible(cancelBtn, true);
    setVisible(retryBtn, false);
    setVisible(openAnywayBtn, false);
    setVisible(openBtn, false);
    setVisible(closeBtn, false);
    return;
  }

  if (state.done && state.success) {
    setVisible(cancelBtn, false);
    setVisible(retryBtn, false);
    setVisible(openAnywayBtn, false);
    setVisible(openBtn, false);
    setVisible(closeBtn, true);
    return;
  }

  if (state.done && !state.success) {
    setVisible(cancelBtn, false);
    setVisible(retryBtn, true);
    setVisible(openAnywayBtn, Boolean(state.can_open_anyway));
    setVisible(openBtn, false);
    setVisible(closeBtn, true);
  }
}

async function pollSetupState() {
  if (!bridgeReady) {
    return;
  }
  try {
    const state = await callSetupApi("setup_get_state");
    renderState(state || {});

    if (state?.done && state?.success && !autoOpenTriggered) {
      autoOpenTriggered = true;
      window.setTimeout(async () => {
        await openMainUi();
      }, 250);
    }
  } catch (error) {
    statusEl.textContent = error.message || "Setup bridge is unavailable.";
    errorEl.textContent = "This page must run inside the desktop app.";
    setVisible(errorEl, true);
    setVisible(cancelBtn, false);
    setVisible(retryBtn, false);
    setVisible(openAnywayBtn, false);
    setVisible(openBtn, false);
    setVisible(closeBtn, true);
  }
}

async function openMainUi() {
  if (isNavigating) {
    return;
  }
  try {
    const result = await callSetupApi("setup_continue_to_main");
    if (!result?.success) {
      autoOpenTriggered = false;
      errorEl.textContent = result?.error || "Failed to open the main UI.";
      setVisible(errorEl, true);
      setVisible(openBtn, true);
      return;
    }

    if (!result?.redirect_url) {
      autoOpenTriggered = false;
      errorEl.textContent = "Main UI redirect URL was not provided.";
      setVisible(errorEl, true);
      setVisible(openBtn, true);
      return;
    }
    isNavigating = true;
    document.body.classList.add("fade-out");
    window.setTimeout(() => {
      window.location.replace(result.redirect_url);
    }, 260);
  } catch (error) {
    isNavigating = false;
    autoOpenTriggered = false;
    errorEl.textContent = error.message || "Failed to open the main UI.";
    setVisible(errorEl, true);
    setVisible(openBtn, true);
  }
}

cancelBtn.addEventListener("click", async () => {
  await callSetupApi("setup_cancel");
});

retryBtn.addEventListener("click", async () => {
  autoOpenTriggered = false;
  setVisible(errorEl, false);
  errorEl.textContent = "";
  await callSetupApi("setup_retry");
});

openAnywayBtn.addEventListener("click", async () => {
  const result = await callSetupApi("setup_open_anyway");
  if (result?.success) {
    await openMainUi();
  }
});

openBtn.addEventListener("click", async () => {
  await openMainUi();
});

closeBtn.addEventListener("click", async () => {
  beginSetupShutdown();
  await callSetupApi("setup_exit");
});

function startPolling() {
  if (pollTimer) {
    return;
  }
  pollSetupState();
  pollTimer = window.setInterval(pollSetupState, 600);
}

function markBridgeReady() {
  if (!hasApi()) {
    return false;
  }
  bridgeReady = true;
  if (bridgeInitTimer) {
    window.clearInterval(bridgeInitTimer);
    bridgeInitTimer = null;
  }
  setVisible(errorEl, false);
  errorEl.textContent = "";
  startPolling();
  return true;
}

document.addEventListener("pywebviewready", () => {
  markBridgeReady();
});

// Fallback for cases where the event listener races with injection timing.
bridgeInitTimer = window.setInterval(() => {
  markBridgeReady();
}, 120);

window.setTimeout(() => {
  if (!bridgeReady) {
    statusEl.textContent = "Waiting for desktop bridge...";
  }
}, 1000);

window.addEventListener("beforeunload", beginSetupShutdown);
