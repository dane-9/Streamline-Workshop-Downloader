const statusEl = document.getElementById("setup-status");
const progressBarEl = document.getElementById("setup-progress-bar");
const errorEl = document.getElementById("setup-error");
const stepEls = Array.from(document.querySelectorAll(".setup-step"));
const steamcmdProgressEl = document.getElementById("setup-steamcmd-progress");
const steamcmdProgressBadgeEl = document.getElementById("setup-steamcmd-progress-badge");
const steamcmdProgressTextEl = document.getElementById("setup-steamcmd-progress-text");
const steamcmdProgressBarFillEl = document.getElementById("setup-steamcmd-progress-bar-fill");
const appidsProgressEl = document.getElementById("setup-appids-progress");
const appidsProgressBadgeEl = document.getElementById("setup-appids-progress-badge");
const appidsProgressTextEl = document.getElementById("setup-appids-progress-text");
const appidsProgressBarFillEl = document.getElementById("setup-appids-progress-bar-fill");

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
const STEP_ORDER = ["steamcmd", "appids", "finalize"];
const APPIDS_PROGRESS_STEPS = [
  { key: "connect", label: "Connect to source", runningText: "Connecting to SteamDB..." },
  { key: "fetch", label: "Fetch entries", runningText: "Fetching AppID rows..." },
  { key: "parse", label: "Parse payload", runningText: "Parsing AppIDs..." },
  { key: "write", label: "Write AppIDs file", runningText: "Writing AppIDs.txt..." },
  { key: "reload", label: "Reload in app", runningText: "Reloading AppIDs..." }
];
const STEAMCMD_PROGRESS_STEPS = [
  { key: "check", label: "Check installation" },
  { key: "download", label: "Download package" },
  { key: "initialize", label: "Initialize SteamCMD" },
  { key: "verify", label: "Verify setup" }
];
const APPIDS_STEP_ADVANCE_MS = 850;
let appidsStageSeen = false;
let appidsStepStartedAt = 0;
let appidsActiveStepIndex = -1;
let steamcmdActiveStepIndex = -1;

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

function setAppidsStepState(stepKey, state) {
  const row = appidsProgressEl?.querySelector(`[data-appids-step='${stepKey}']`);
  if (!row) {
    return;
  }
  row.classList.remove("is-pending", "is-active", "is-done", "is-error");
  row.classList.add(`is-${state}`);
}

function setSteamcmdStepState(stepKey, state) {
  const row = steamcmdProgressEl?.querySelector(`[data-steamcmd-step='${stepKey}']`);
  if (!row) {
    return;
  }
  row.classList.remove("is-pending", "is-active", "is-done", "is-error");
  row.classList.add(`is-${state}`);
}

function resetSteamcmdStepStates() {
  for (const step of STEAMCMD_PROGRESS_STEPS) {
    setSteamcmdStepState(step.key, "pending");
  }
  steamcmdActiveStepIndex = -1;
}

function setSteamcmdBadge(state, text) {
  if (!steamcmdProgressBadgeEl) {
    return;
  }
  steamcmdProgressBadgeEl.className = `setup-steamcmd-progress-badge state-${state}`;
  steamcmdProgressBadgeEl.textContent = text;
}

function setSteamcmdText(text) {
  if (!steamcmdProgressTextEl) {
    return;
  }
  steamcmdProgressTextEl.textContent = String(text || "");
}

function setSteamcmdBar(state, widthPercent = 0) {
  if (!steamcmdProgressBarFillEl) {
    return;
  }
  steamcmdProgressBarFillEl.className = `setup-steamcmd-progress-bar-fill state-${state}`;
  steamcmdProgressBarFillEl.style.width = `${Math.max(0, Math.min(100, Number(widthPercent) || 0))}%`;
}

function setSteamcmdActiveStep(stepIndex) {
  const maxIndex = STEAMCMD_PROGRESS_STEPS.length - 1;
  const nextIndex = Math.max(0, Math.min(maxIndex, Number(stepIndex) || 0));
  steamcmdActiveStepIndex = nextIndex;
  for (let i = 0; i < STEAMCMD_PROGRESS_STEPS.length; i += 1) {
    const step = STEAMCMD_PROGRESS_STEPS[i];
    if (i < nextIndex) {
      setSteamcmdStepState(step.key, "done");
    } else if (i === nextIndex) {
      setSteamcmdStepState(step.key, "active");
    } else {
      setSteamcmdStepState(step.key, "pending");
    }
  }
  const width = 18 + ((nextIndex + 1) / STEAMCMD_PROGRESS_STEPS.length) * 70;
  setSteamcmdBar("running", width);
}

function markAllSteamcmdStepsDone() {
  for (const step of STEAMCMD_PROGRESS_STEPS) {
    setSteamcmdStepState(step.key, "done");
  }
}

function markSteamcmdStepError(stepIndex) {
  const maxIndex = STEAMCMD_PROGRESS_STEPS.length - 1;
  const safeIndex = Math.max(0, Math.min(maxIndex, Number(stepIndex) || 0));
  const step = STEAMCMD_PROGRESS_STEPS[safeIndex];
  if (step) {
    setSteamcmdStepState(step.key, "error");
  }
}

function renderSteamcmdProgress(state, stageInfo) {
  if (!steamcmdProgressEl) {
    return;
  }
  const statusText = String(state?.status || "");
  const statusLower = statusText.toLowerCase();
  const inSteamcmdStage = stageInfo?.id === "steamcmd"
    || statusLower.includes("steamcmd")
    || statusLower.includes("preparing");

  if (!inSteamcmdStage && appidsStageSeen) {
    return;
  }

  if (state?.done && !state?.success && !appidsStageSeen) {
    setSteamcmdBadge("error", "Failed");
    setSteamcmdBar("error", 100);
    setSteamcmdText(String(state?.error || "SteamCMD setup failed."));
    markSteamcmdStepError(steamcmdActiveStepIndex >= 0 ? steamcmdActiveStepIndex : 0);
    return;
  }

  if (!state?.running && !statusLower.includes("steamcmd") && appidsStageSeen) {
    setSteamcmdBadge("success", "Done");
    setSteamcmdBar("success", 100);
    setSteamcmdText("SteamCMD setup complete.");
    markAllSteamcmdStepsDone();
    return;
  }

  if (!state?.running && !inSteamcmdStage) {
    setSteamcmdBadge("idle", "Idle");
    setSteamcmdBar("idle", 0);
    setSteamcmdText("Waiting for SteamCMD stage...");
    resetSteamcmdStepStates();
    return;
  }

  setSteamcmdBadge("running", "Running");
  if (statusLower.includes("checking steamcmd")) {
    setSteamcmdText("Checking SteamCMD installation...");
    setSteamcmdActiveStep(0);
    return;
  }
  if (statusLower.includes("downloading steamcmd")) {
    setSteamcmdText("Downloading SteamCMD package...");
    setSteamcmdActiveStep(1);
    return;
  }
  if (statusLower.includes("initializing steamcmd")) {
    setSteamcmdText("Initializing SteamCMD...");
    setSteamcmdActiveStep(2);
    return;
  }
  if (statusLower.includes("steamcmd setup complete")) {
    markAllSteamcmdStepsDone();
    setSteamcmdBadge("success", "Done");
    setSteamcmdBar("success", 100);
    setSteamcmdText("SteamCMD setup complete.");
    return;
  }

  if (steamcmdActiveStepIndex < 0) {
    setSteamcmdActiveStep(0);
  }
  setSteamcmdText(statusText || "Running SteamCMD setup...");
}

function resetAppidsStepStates() {
  for (const step of APPIDS_PROGRESS_STEPS) {
    setAppidsStepState(step.key, "pending");
  }
  appidsActiveStepIndex = -1;
}

function setAppidsBadge(state, text) {
  if (!appidsProgressBadgeEl) {
    return;
  }
  appidsProgressBadgeEl.className = `setup-appids-progress-badge state-${state}`;
  appidsProgressBadgeEl.textContent = text;
}

function setAppidsText(text) {
  if (!appidsProgressTextEl) {
    return;
  }
  appidsProgressTextEl.textContent = String(text || "");
}

function setAppidsBar(state, widthPercent = 0) {
  if (!appidsProgressBarFillEl) {
    return;
  }
  appidsProgressBarFillEl.className = `setup-appids-progress-bar-fill state-${state}`;
  appidsProgressBarFillEl.style.width = `${Math.max(0, Math.min(100, Number(widthPercent) || 0))}%`;
}

function setAppidsActiveStep(stepIndex) {
  const maxIndex = APPIDS_PROGRESS_STEPS.length - 1;
  const nextIndex = Math.max(0, Math.min(maxIndex, Number(stepIndex) || 0));
  appidsActiveStepIndex = nextIndex;
  for (let i = 0; i < APPIDS_PROGRESS_STEPS.length; i += 1) {
    const step = APPIDS_PROGRESS_STEPS[i];
    if (i < nextIndex) {
      setAppidsStepState(step.key, "done");
    } else if (i === nextIndex) {
      setAppidsStepState(step.key, "active");
    } else {
      setAppidsStepState(step.key, "pending");
    }
  }
  const active = APPIDS_PROGRESS_STEPS[nextIndex];
  if (active?.runningText) {
    setAppidsText(active.runningText);
  }
  const width = 20 + ((nextIndex + 1) / APPIDS_PROGRESS_STEPS.length) * 58;
  setAppidsBar("running", width);
}

function markAllAppidsStepsDone() {
  for (const step of APPIDS_PROGRESS_STEPS) {
    setAppidsStepState(step.key, "done");
  }
}

function markAppidsStepError(stepIndex) {
  const maxIndex = APPIDS_PROGRESS_STEPS.length - 1;
  const safeIndex = Math.max(0, Math.min(maxIndex, Number(stepIndex) || 0));
  const step = APPIDS_PROGRESS_STEPS[safeIndex];
  if (step) {
    setAppidsStepState(step.key, "error");
  }
}

function renderAppidsProgress(state, stageInfo) {
  if (!appidsProgressEl) {
    return;
  }
  const statusText = String(state?.status || "");
  const statusLower = statusText.toLowerCase();
  const inAppidsStage = stageInfo?.id === "appids"
    || statusLower.includes("appids")
    || statusLower.includes("steamdb");
  const runningSteamcmdStage = Boolean(state?.running) && !inAppidsStage && stageInfo?.id === "steamcmd";

  if (runningSteamcmdStage) {
    appidsStageSeen = false;
  }
  if (inAppidsStage) {
    appidsStageSeen = true;
  }

  const shouldShow = appidsStageSeen || inAppidsStage;
  setVisible(appidsProgressEl, shouldShow);
  if (steamcmdProgressEl) {
    setVisible(steamcmdProgressEl, !shouldShow);
  }
  if (!shouldShow) {
    resetAppidsStepStates();
    appidsStepStartedAt = 0;
    return;
  }

  if (state?.done && state?.success) {
    setAppidsBadge("success", "Done");
    setAppidsBar("success", 100);
    setAppidsText("AppIDs are ready.");
    markAllAppidsStepsDone();
    appidsStepStartedAt = 0;
    return;
  }

  if (state?.done && !state?.success) {
    setAppidsBadge("error", "Failed");
    setAppidsBar("error", 100);
    setAppidsText(String(state?.error || "AppIDs setup failed."));
    markAppidsStepError(appidsActiveStepIndex >= 0 ? appidsActiveStepIndex : 0);
    appidsStepStartedAt = 0;
    return;
  }

  if (statusLower.includes("appids database already exists")) {
    setAppidsBadge("success", "Skipped");
    setAppidsBar("success", 100);
    setAppidsText("AppIDs database already exists.");
    markAllAppidsStepsDone();
    appidsStepStartedAt = 0;
    return;
  }

  if (!state?.running || !inAppidsStage) {
    setAppidsBadge("idle", "Idle");
    setAppidsBar("idle", 0);
    setAppidsText("Waiting for AppIDs stage...");
    resetAppidsStepStates();
    appidsStepStartedAt = 0;
    return;
  }

  setAppidsBadge("running", "Running");
  if (statusLower.includes("checking appids")) {
    appidsStepStartedAt = 0;
    setAppidsText("Checking local AppIDs database...");
    setAppidsActiveStep(0);
    return;
  }

  if (!appidsStepStartedAt) {
    appidsStepStartedAt = Date.now();
  }
  const elapsedMs = Date.now() - appidsStepStartedAt;
  const stepIndex = Math.min(
    APPIDS_PROGRESS_STEPS.length - 1,
    Math.floor(elapsedMs / APPIDS_STEP_ADVANCE_MS)
  );
  setAppidsActiveStep(stepIndex);
}

function initializeAppidsProgressUi() {
  if (!appidsProgressEl) {
    return;
  }
  setVisible(appidsProgressEl, false);
  setAppidsBadge("idle", "Idle");
  setAppidsBar("idle", 0);
  setAppidsText("Waiting for AppIDs stage...");
  resetAppidsStepStates();
}

function initializeSteamcmdProgressUi() {
  if (!steamcmdProgressEl) {
    return;
  }
  setVisible(steamcmdProgressEl, true);
  setSteamcmdBadge("idle", "Idle");
  setSteamcmdBar("idle", 0);
  setSteamcmdText("Waiting for SteamCMD stage...");
  resetSteamcmdStepStates();
}

function getStageInfo(state) {
  const statusText = String(state?.status || "").toLowerCase();
  const progress = Number(state?.progress || 0);

  if (state?.done) {
    return { id: "finalize", label: state?.success ? "Complete" : "Finalize", index: 2 };
  }
  if (
    statusText.includes("appids")
    || statusText.includes("steamdb")
    || progress >= 60
  ) {
    return { id: "appids", label: "AppIDs", index: 1 };
  }
  if (
    statusText.includes("steamcmd")
    || statusText.includes("preparing")
    || progress < 60
  ) {
    return { id: "steamcmd", label: "SteamCMD", index: 0 };
  }
  return { id: "steamcmd", label: "Preparing", index: 0 };
}

function renderStepper(stageInfo, state) {
  const activeIndex = Math.max(0, Number(stageInfo?.index || 0));
  const done = !!state?.done;
  const success = !!state?.success;
  const failed = done && !success;

  stepEls.forEach((stepEl, index) => {
    stepEl.classList.remove("is-active", "is-complete", "is-error");

    if (done && success) {
      stepEl.classList.add("is-complete");
      if (index === STEP_ORDER.length - 1) {
        stepEl.classList.add("is-active");
      }
      return;
    }

    if (index < activeIndex) {
      stepEl.classList.add("is-complete");
      return;
    }

    if (index === activeIndex) {
      if (failed && index === STEP_ORDER.length - 1) {
        stepEl.classList.add("is-error");
      } else {
        stepEl.classList.add("is-active");
      }
      return;
    }

    if (failed && index === STEP_ORDER.length - 1) {
      stepEl.classList.add("is-error");
    }
  });
}

function renderState(state) {
  const progress = Number(state.progress || 0);
  const statusText = state.status || "Preparing setup...";
  statusEl.textContent = statusText;
  progressBarEl.style.width = `${Math.max(0, Math.min(100, progress))}%`;
  const stageInfo = getStageInfo(state);
  renderStepper(stageInfo, state);
  renderSteamcmdProgress(state, stageInfo);
  renderAppidsProgress(state, stageInfo);

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

initializeSteamcmdProgressUi();
initializeAppidsProgressUi();
window.addEventListener("beforeunload", beginSetupShutdown);
