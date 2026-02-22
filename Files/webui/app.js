const queueBody = document.getElementById("queue-body");
const queueForm = document.getElementById("queue-form");
const eventLog = document.getElementById("event-log");
const logCopyBtn = document.getElementById("log-copy-btn");
const logClearBtn = document.getElementById("log-clear-btn");
const searchInput = document.getElementById("search-input");
const filterBtn = document.getElementById("filter-btn");
const filterPopup = document.getElementById("filter-popup");
const caseBtn = document.getElementById("case-btn");
const regexBtn = document.getElementById("regex-btn");
const providerSelect = document.getElementById("provider");
const providerDisplayName = document.getElementById("provider-display-name");
const accountSelect = document.getElementById("account-select");
const openDownloadsBtn = document.getElementById("open-downloads-btn");
const startDownloadBtn = document.getElementById("start-download-btn");
const downloadNowBtn = document.getElementById("download-now-btn");
const urlHelpBtn = document.getElementById("url-help-btn");
const minimizeBtn = document.getElementById("minimize-btn");
const closeBtn = document.getElementById("close-btn");
const searchRow = document.getElementById("search-row");
const logWrap = document.getElementById("log-wrap");
const providerWrap = document.getElementById("provider-wrap");
const inputRowActions = document.querySelector(".input-row-zone-right");
const importExportWrap = document.getElementById("import-export-wrap");
const importExportSpacer = document.getElementById("import-export-spacer");
const itemUrlInput = document.getElementById("item-url");
const settingsBtn = document.getElementById("settings-btn");
const settingsCommandShell = document.getElementById("settings-command-shell");
const accountsBtn = document.getElementById("accounts-btn");
const appidsBtn = document.getElementById("appids-btn");
const commandPaletteBtn = document.getElementById("command-palette-btn");
const commandsSplitMenu = document.getElementById("commands-split-menu");
const openCommandPaletteMenuBtn = document.getElementById("open-command-palette-btn");
const importBtn = document.getElementById("import-btn");
const exportBtn = document.getElementById("export-btn");
const queueContextMenu = document.getElementById("queue-context-menu");
const logsContextMenu = document.getElementById("logs-context-menu");
const headerContextMenu = document.getElementById("header-context-menu");
const commandPaletteOverlay = document.getElementById("command-palette-overlay");
const commandPaletteInput = document.getElementById("command-palette-input");
const commandPaletteList = document.getElementById("command-palette-list");
const queueTable = document.getElementById("queue-table");
const queueHeadRow = document.getElementById("queue-head-row");
const queueTableWrap = document.querySelector(".queue-table-wrap");
const modalOverlay = document.getElementById("modal-overlay");
const modalTitle = document.getElementById("modal-title");
const modalMessage = document.getElementById("modal-message");
const modalForm = document.getElementById("modal-form");
const modalInput = document.getElementById("modal-input");
const modalCancelBtn = document.getElementById("modal-cancel-btn");
const modalOkBtn = document.getElementById("modal-ok-btn");
const titlebarLogo = document.getElementById("titlebar-logo");
const windowResizeEast = document.getElementById("window-resize-east");
const windowResizeSouth = document.getElementById("window-resize-south");

document.body.style.opacity = "0";
document.body.style.transition = "opacity 220ms ease";

let started = false;
let eventPollTimer = null;
let eventPollInFlight = false;
let eventPollRequested = false;
let queueRefreshTimer = null;
let queueRefreshForceReload = false;
let browserQueue = [];
let activeColumnResize = null;
let searchRenderTimer = null;
let appShuttingDown = false;
let tutorialSession = null;
let commandPaletteActions = [];
let commandPaletteResults = [];
let commandPaletteSelectedIndex = 0;
let commandPaletteLastFocusedElement = null;
let lastShiftTapAt = 0;
const animatedSelectControllers = new Map();
let suppressNextBackendClearEvent = false;
let logTopItems = [];
let logGroupsByOperation = new Map();
let logRenderQueued = false;
let logRenderPreserveScroll = false;
const SEARCH_RENDER_DEBOUNCE_MS = 180;
const DOUBLE_SHIFT_WINDOW_MS = 360;
const EVENT_POLL_INTERVAL_MS = 250;
const VIRTUAL_ROW_HEIGHT_FALLBACK = 18;
const VIRTUAL_OVERSCAN_ROWS = 14;
const VIRTUAL_FETCH_BUFFER_ROWS = 80;
const VIRTUAL_FETCH_MAX_LIMIT = 1200;
const STARTUP_LOG_TONE_TEST_DEFAULTS = {
  enabled: false,
  info: "Startup tone test: INFO Startup tone test: INFO Startup tone test: INFO Startup tone test: INFO Startup tone test: INFO Startup tone test: INFO Startup tone test: INFO Startup tone test: INFO",
  good: "Startup tone test: GOOD",
  bad: "Startup tone test: ERROR"
};

let virtualRowHeight = VIRTUAL_ROW_HEIGHT_FALLBACK;
let virtualItems = [];
let virtualLayoutKey = "";
let virtualHiddenColumns = [];
let virtualShowRowNumbers = false;
let lastVirtualStart = -1;
let lastVirtualEnd = -1;
let virtualScrollQueued = false;
let virtualBackendEnabled = true;
let virtualBackendTotal = 0;
let virtualBackendPageStart = 0;
let virtualBackendPageEnd = 0;
let virtualBackendPageItems = [];
let virtualBackendQueryKey = "";
let virtualBackendFetchId = 0;
let virtualBackendLoading = false;
let virtualBackendRegexErrorShownFor = "";

const state = {
  queue: [],
  filter: "All",
  regex: false,
  caseSensitive: false,
  config: {},
  version: "",
  selectedModIds: new Set(),
  isDownloading: false,
  cancelPending: false,
  apiAvailable: false,
  lastEventId: 0,
  tutorialStartupHandled: false,
  queueStats: {
    total: 0,
    queued: 0,
    downloaded: 0,
    failed: 0,
    downloading: 0
  },
  searchMatcherCache: {
    query: null,
    regex: null,
    caseSensitive: null,
    matcher: null
  },
  selectionAnchorIndex: null,
  selectionAnchorModId: "",
  rowCache: new Map(),
  logEntries: [],
  logEntrySeq: 0,
  sort: {
    key: "",
    direction: "asc",
    clicked: false
  }
};

const SETTINGS_DEFAULTS = {
  current_theme: "Dark",
  logo_style: "Light",
  batch_size: 20,
  show_logs: true,
  show_provider: true,
  show_queue_entire_workshop: true,
  keep_downloaded_in_queue: false,
  folder_naming_format: "id",
  auto_detect_urls: false,
  auto_add_to_queue: false,
  delete_downloads_on_cancel: false,
  steamcmd_existing_mod_behavior: "Only Redownload if Updated",
  download_button: true,
  show_searchbar: true,
  show_commands_button: true,
  show_export_import_buttons: true,
  show_sort_indicator: true,
  show_row_numbers: false,
  header_locked: true,
  queue_tree_default_widths: [115, 90, 230, 100, 95],
  queue_tree_column_widths: null,
  queue_tree_column_hidden: null,
  reset_provider_on_startup: false,
  download_provider: "Default",
  log_category_filter: "all",
  reset_window_size_on_startup: true,
  show_tutorial_on_startup: true
};
const LOG_CATEGORY_FILTER_OPTIONS = ["all", "ui", "system", "queue", "download", "clipboard", "debug"];

const QUEUE_COLUMNS = [
  { key: "game_name", label: "Game", defaultWidth: 115 },
  { key: "mod_id", label: "Mod ID", defaultWidth: 90 },
  { key: "mod_name", label: "Mod Name", defaultWidth: 230 },
  { key: "status", label: "Status", defaultWidth: 100 },
  { key: "provider", label: "Provider", defaultWidth: 95 }
];

function syncProviderDisplay() {
  if (providerDisplayName) {
    providerDisplayName.textContent = providerSelect?.value || "Default";
  }
  syncAnimatedSelect("provider");
}

function setProviderValue(value) {
  if (!providerSelect || !value) {
    syncProviderDisplay();
    return;
  }
  const exists = Array.from(providerSelect.options).some((option) => option.value === value);
  if (exists) {
    providerSelect.value = value;
  }
  syncProviderDisplay();
}

function normalizeLogTone(value) {
  const tone = String(value || "").trim().toLowerCase();
  if (tone === "good" || tone === "bad") {
    return tone;
  }
  return "info";
}

function normalizeLogTimestampMs(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return Date.now();
  }
  return numeric < 1e12 ? numeric * 1000 : numeric;
}

function formatLogClock(timestampMs) {
  return new Date(timestampMs).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function logToneLabel(tone) {
  if (tone === "good") {
    return "GOOD";
  }
  if (tone === "bad") {
    return "ERROR";
  }
  return "INFO";
}

function normalizeLogCategoryFilter(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (LOG_CATEGORY_FILTER_OPTIONS.includes(normalized)) {
    return normalized;
  }
  return "all";
}

function getCurrentLogCategoryFilter() {
  const configured = state?.config?.log_category_filter ?? state?.config?.log_level_filter;
  return normalizeLogCategoryFilter(
    configured === undefined ? SETTINGS_DEFAULTS.log_category_filter : configured
  );
}

function getLogEntryCategory(entry) {
  const source = String(entry?.source || "").trim().toLowerCase();
  if (LOG_CATEGORY_FILTER_OPTIONS.includes(source) && source !== "all") {
    return source;
  }
  if (!source) {
    return "system";
  }
  return "ui";
}

function doesLogEntryMatchCategory(entry, categoryFilter) {
  const filter = normalizeLogCategoryFilter(categoryFilter);
  if (filter === "all") {
    return true;
  }
  return getLogEntryCategory(entry) === filter;
}

function getStartupLogToneTestConfig() {
  const runtime = window.STREAMLINE_STARTUP_LOG_TEST;
  if (!runtime || typeof runtime !== "object") {
    return STARTUP_LOG_TONE_TEST_DEFAULTS;
  }
  return {
    enabled: runtime.enabled !== false,
    info: String(runtime.info || STARTUP_LOG_TONE_TEST_DEFAULTS.info),
    good: String(runtime.good || STARTUP_LOG_TONE_TEST_DEFAULTS.good),
    bad: String(runtime.bad || STARTUP_LOG_TONE_TEST_DEFAULTS.bad)
  };
}

function emitStartupLogToneTests() {
  const config = getStartupLogToneTestConfig();
  if (!config.enabled) {
    return;
  }
  addLog(config.info, "info", { source: "debug", action: "startup_tone_test" });
  addLog(config.good, "good", { source: "debug", action: "startup_tone_test" });
  addLog(config.bad, "bad", { source: "debug", action: "startup_tone_test" });
}

function buildLogClipboardText() {
  if (!eventLog) {
    return "";
  }
  const renderedRows = eventLog.querySelectorAll(".log-line");
  if (!renderedRows.length) {
    return "";
  }
  const lines = [];
  for (const row of renderedRows) {
    const time = row.querySelector(".log-time")?.textContent?.trim() || "";
    const tone = row.querySelector(".log-tone")?.textContent?.trim() || "";
    const message = row.querySelector(".log-message")?.textContent?.trim() || "";
    const source = row.querySelector(".log-source")?.textContent?.trim() || "";
    if (!time && !tone && !message && !source) {
      continue;
    }
    const parts = [];
    if (time) {
      parts.push(`[${time}]`);
    }
    if (tone) {
      parts.push(`[${tone}]`);
    }
    if (message) {
      parts.push(message);
    }
    if (source) {
      parts.push(`(${source})`);
    }
    lines.push(parts.join(" "));
  }
  return lines.join("\n");
}

function showFullLogMessageDialog(entry) {
  const messageText = String(entry?.message || "");
  const source = String(entry?.source || "ui").trim().toLowerCase() || "ui";
  const tone = normalizeLogTone(entry?.tone || "info");
  const timeText = formatLogClock(normalizeLogTimestampMs(entry?.timestampMs));

  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "confirm-overlay";
    overlay.innerHTML = `
      <div class="log-message-dialog-card" role="dialog" aria-modal="true" aria-label="Full log message">
        <h3 class="confirm-title">Full Log Message</h3>
        <p class="log-message-dialog-meta">${escapeHtml(timeText)}  ${escapeHtml(logToneLabel(tone))}  ${escapeHtml(source)}</p>
        <pre class="log-message-dialog-body">${escapeHtml(messageText)}</pre>
        <div class="confirm-actions">
          <button type="button" class="control modal-btn" data-log-message-action="copy">Copy</button>
          <button type="button" class="control modal-btn primary" data-log-message-action="close">Close</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const closeBtn = overlay.querySelector("[data-log-message-action='close']");
    const copyBtn = overlay.querySelector("[data-log-message-action='copy']");

    const cleanup = () => {
      document.removeEventListener("keydown", onKeyDown, true);
      overlay.remove();
      resolve(true);
    };

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        cleanup();
      }
    };

    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) {
        cleanup();
      }
    });

    closeBtn?.addEventListener("click", cleanup);
    copyBtn?.addEventListener("click", async () => {
      const ok = await copyTextToClipboard(messageText);
      copyBtn.textContent = ok ? "Copied" : "Copy Failed";
    });
    document.addEventListener("keydown", onKeyDown, true);
    closeBtn?.focus();
  });
}

function getOperationPrefixFromId(operationId) {
  const raw = String(operationId || "").trim().toLowerCase();
  if (!raw) {
    return "";
  }
  const matched = raw.match(/^([a-z0-9-]+?)-\d{10,}-\d+$/);
  return matched ? matched[1] : raw;
}

function formatOperationLabel(prefix) {
  const key = String(prefix || "").trim().toLowerCase();
  const known = {
    "queue-build": "Queue Build",
    "queue-input": "Queue Input",
    "download": "Download Queue"
  };
  if (known[key]) {
    return known[key];
  }
  return key
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ") || "Operation";
}

function deriveOperationState(currentState, entry) {
  const current = String(currentState || "").toLowerCase();
  const action = String(entry?.action || "").toLowerCase();
  const tone = normalizeLogTone(entry?.tone || "info");
  const rawContext = entry?.context;
  const context = rawContext && typeof rawContext === "object" && !Array.isArray(rawContext)
    ? rawContext
    : null;
  const explicitState = String(context?.operation_state || context?.operationState || "").trim().toLowerCase();

  if (explicitState === "run" || explicitState === "done" || explicitState === "error" || explicitState === "canceled") {
    return explicitState;
  }

  if (/cancel/.test(action)) {
    return "canceled";
  }
  if (tone === "bad" || /(fail|error|crash|exception)/.test(action)) {
    return "error";
  }
  if (/(start|progress|process|building|running|downloading|worker|detect)/.test(action)) {
    return current === "queued" ? "run" : (current || "run");
  }
  if (/(finish|complete|queued|processed|updated|done)/.test(action)) {
    return "done";
  }
  if (!current) {
    return "run";
  }
  return current;
}

function getOperationToneByState(stateName) {
  const state = String(stateName || "").toLowerCase();
  if (state === "run") {
    return "run";
  }
  if (state === "done") {
    return "good";
  }
  if (state === "error") {
    return "bad";
  }
  if (state === "canceled") {
    return "stop";
  }
  return "info";
}

function getOperationTagLabel(stateName) {
  const state = String(stateName || "").toLowerCase();
  if (state === "run") {
    return "RUN";
  }
  if (state === "done") {
    return "DONE";
  }
  if (state === "error") {
    return "ERROR";
  }
  if (state === "canceled") {
    return "STOP";
  }
  return "INFO";
}

function moveGroupTopItemToFront(operationId) {
  const opId = String(operationId || "").trim();
  if (!opId) {
    return;
  }
  const exists = logTopItems.some((item) => item?.kind === "group" && item.operationId === opId);
  if (!exists) {
    logTopItems.unshift({ kind: "group", operationId: opId });
  }
}

function shouldUpsertProgressEntry(group, entry) {
  const prefix = String(group?.prefix || "").toLowerCase();
  const action = String(entry?.action || "").toLowerCase();
  if (prefix !== "queue-build") {
    return prefix === "download" && action === "download_progress";
  }
  return action === "queue_build_progress" || action === "pages_fetched";
}

function addEntryToGroupedTimeline(entry) {
  const opId = String(entry?.operationId || "").trim();
  if (!opId) {
    logTopItems.unshift({ kind: "single", entry });
    return;
  }

  let group = logGroupsByOperation.get(opId);
  if (!group) {
    const prefix = getOperationPrefixFromId(opId);
    group = {
      operationId: opId,
      prefix,
      label: formatOperationLabel(prefix),
      source: String(entry.source || "system"),
      entries: [],
      expanded: false,
      state: "run",
      lastMessage: "",
      updatedAt: 0,
      progressEntryId: ""
    };
    logGroupsByOperation.set(opId, group);
  }

  if (shouldUpsertProgressEntry(group, entry)) {
    const progressId = String(group.progressEntryId || `progress:${opId}:queue-build`);
    group.progressEntryId = progressId;
    let progressEntry = group.entries.find((item) => String(item?.id) === progressId);
    if (!progressEntry) {
      progressEntry = { ...entry, id: progressId };
      group.entries.push(progressEntry);
    } else {
      Object.assign(progressEntry, entry, { id: progressId });
      const existingIndex = group.entries.indexOf(progressEntry);
      if (existingIndex >= 0) {
        const [moved] = group.entries.splice(existingIndex, 1);
        group.entries.push(moved);
      }
    }
  } else {
    group.entries.push(entry);
  }
  group.source = String(entry.source || group.source || "system");
  group.lastMessage = String(entry.message || "");
  group.updatedAt = Number(entry.timestampMs || Date.now());
  group.state = deriveOperationState(group.state, entry);
  moveGroupTopItemToFront(opId);
}

function captureLogScrollAnchor() {
  if (!eventLog) {
    return null;
  }
  const containerTop = eventLog.getBoundingClientRect().top;
  const rows = eventLog.querySelectorAll(".log-line[data-log-key]");
  for (const row of rows) {
    const rect = row.getBoundingClientRect();
    if (rect.bottom >= containerTop + 1) {
      return {
        key: row.dataset.logKey || "",
        offset: rect.top - containerTop,
      };
    }
  }
  return null;
}

function findRenderedLogRowByKey(key) {
  if (!eventLog || !key) {
    return null;
  }
  const rows = eventLog.querySelectorAll(".log-line[data-log-key]");
  for (const row of rows) {
    if (row.dataset.logKey === key) {
      return row;
    }
  }
  return null;
}

function restoreLogScrollAnchor(anchor) {
  if (!eventLog || !anchor || !anchor.key) {
    return;
  }
  const row = findRenderedLogRowByKey(anchor.key);
  if (!row) {
    return;
  }
  const containerTop = eventLog.getBoundingClientRect().top;
  const currentOffset = row.getBoundingClientRect().top - containerTop;
  const delta = currentOffset - Number(anchor.offset || 0);
  if (Math.abs(delta) >= 0.5) {
    eventLog.scrollTop += delta;
  }
}

function scheduleLogTimelineRender({ preserveScroll = false } = {}) {
  logRenderPreserveScroll = logRenderPreserveScroll || !!preserveScroll;
  if (logRenderQueued) {
    return;
  }
  logRenderQueued = true;
  window.requestAnimationFrame(() => {
    const preserve = logRenderPreserveScroll;
    logRenderQueued = false;
    logRenderPreserveScroll = false;
    renderLogTimeline({ preserveScroll: preserve });
  });
}

function createLogEntryLineElement(entry, extraClass = "", keyPrefix = "s") {
  const line = document.createElement("p");
  line.className = `log-line ${entry.tone} ${extraClass}`.trim();
  line.dataset.logKey = `${keyPrefix}:${entry.id}`;
  line.addEventListener("dblclick", () => {
    void showFullLogMessageDialog(entry);
  });

  const time = document.createElement("span");
  time.className = "log-time";
  time.textContent = formatLogClock(entry.timestampMs);

  const tone = document.createElement("span");
  tone.className = `log-tone ${entry.tone}`;
  tone.textContent = logToneLabel(entry.tone);

  const message = document.createElement("span");
  message.className = "log-message";
  message.textContent = entry.message;

  const source = document.createElement("span");
  source.className = "log-source";
  source.textContent = entry.source || "ui";

  line.append(time, tone, message, source);
  return line;
}

function createLogGroupLineElement(group, view = null) {
  const effectiveState = String(view?.state || group.state || "run");
  const effectiveUpdatedAt = Number(view?.updatedAt || group.updatedAt || Date.now());
  const effectiveMessage = String(view?.lastMessage || group.lastMessage || "Running...");
  const visibleCount = Number(view?.visibleCount || group.entries.length || 0);
  const totalCount = Number(view?.totalCount || group.entries.length || 0);

  const line = document.createElement("p");
  line.className = `log-line log-group-line state-${effectiveState}`.trim();
  line.dataset.logKey = `g:${group.operationId}`;
  line.addEventListener("click", () => {
    group.expanded = !group.expanded;
    scheduleLogTimelineRender({ preserveScroll: true });
  });

  const toggle = document.createElement("span");
  toggle.className = "log-group-toggle";
  toggle.textContent = group.expanded ? "▾" : "▸";

  const time = document.createElement("span");
  time.className = "log-time";
  time.textContent = formatLogClock(effectiveUpdatedAt);

  const tone = document.createElement("span");
  tone.className = `log-tone ${getOperationToneByState(effectiveState)}`;
  tone.textContent = getOperationTagLabel(effectiveState);

  const message = document.createElement("span");
  message.className = "log-message";
  message.textContent = `${group.label}: ${effectiveMessage}`;

  const source = document.createElement("span");
  source.className = "log-source";
  if (visibleCount !== totalCount) {
    source.textContent = `${visibleCount}/${totalCount} logs`;
  } else {
    source.textContent = `${visibleCount} ${visibleCount === 1 ? "log" : "logs"}`;
  }

  line.append(toggle, time, tone, message, source);
  return line;
}

function updateLogHeaderUi() {
  if (logCopyBtn) {
    const visibleRows = eventLog ? eventLog.querySelectorAll(".log-line").length : 0;
    logCopyBtn.disabled = visibleRows <= 0;
  }
  if (logClearBtn) {
    logClearBtn.disabled = state.logEntries.length === 0;
  }
}

function renderLogTimeline(options = {}) {
  if (!eventLog) {
    return;
  }

  const anchor = options.preserveScroll ? captureLogScrollAnchor() : null;
  if (!logTopItems.length) {
    eventLog.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "log-empty";
    eventLog.appendChild(empty);
    updateLogHeaderUi();
    return;
  }

  const categoryFilter = getCurrentLogCategoryFilter();
  const fragment = document.createDocumentFragment();
  let renderedLineCount = 0;
  for (const item of logTopItems) {
    if (!item) {
      continue;
    }
    if (item.kind === "single") {
      if (item.entry && doesLogEntryMatchCategory(item.entry, categoryFilter)) {
        fragment.appendChild(createLogEntryLineElement(item.entry, "log-plain-line", "s"));
        renderedLineCount += 1;
      }
      continue;
    }
    if (item.kind !== "group") {
      continue;
    }
    const group = logGroupsByOperation.get(String(item.operationId || ""));
    if (!group) {
      continue;
    }
    const filteredEntries = categoryFilter === "all"
      ? group.entries
      : group.entries.filter((entry) => doesLogEntryMatchCategory(entry, categoryFilter));
    if (!filteredEntries.length) {
      continue;
    }
    let filteredState = "";
    for (const entry of filteredEntries) {
      filteredState = deriveOperationState(filteredState, entry);
    }
    const lastVisibleEntry = filteredEntries[filteredEntries.length - 1] || null;
    fragment.appendChild(createLogGroupLineElement(group, {
      state: filteredState || group.state,
      updatedAt: Number(lastVisibleEntry?.timestampMs || group.updatedAt || Date.now()),
      lastMessage: String(lastVisibleEntry?.message || group.lastMessage || ""),
      visibleCount: filteredEntries.length,
      totalCount: group.entries.length,
    }));
    renderedLineCount += 1;
    if (group.expanded) {
      for (const childEntry of filteredEntries) {
        fragment.appendChild(createLogEntryLineElement(childEntry, "log-child-line", "c"));
        renderedLineCount += 1;
      }
    }
  }
  if (renderedLineCount <= 0) {
    const empty = document.createElement("div");
    empty.className = "log-empty";
    empty.textContent = "No logs match selected category.";
    eventLog.replaceChildren(empty);
  } else {
    eventLog.replaceChildren(fragment);
  }
  if (anchor) {
    restoreLogScrollAnchor(anchor);
  }
  updateLogHeaderUi();
}

function clearLogTimeline() {
  state.logEntries = [];
  state.logEntrySeq = 0;
  logTopItems = [];
  logGroupsByOperation = new Map();
  scheduleLogTimelineRender();
}

function addLog(text, tone = "", meta = {}) {
  const message = String(text ?? "");
  if (!message) {
    return;
  }

  const wasAtTop = !eventLog || eventLog.scrollTop <= 2;
  const entry = {
    id: ++state.logEntrySeq,
    message,
    tone: normalizeLogTone(tone),
    timestampMs: normalizeLogTimestampMs(meta?.timestamp),
    source: String(meta?.source || "ui").trim().toLowerCase() || "ui",
    action: String(meta?.action || "").trim().toLowerCase(),
    operationId: String(meta?.operationId || meta?.operation_id || "").trim(),
    context: meta?.context
  };

  state.logEntries.push(entry);
  addEntryToGroupedTimeline(entry);
  scheduleLogTimelineRender({ preserveScroll: !wasAtTop });
}

async function copyTextToClipboard(text) {
  const value = String(text || "");
  if (!value) {
    return false;
  }
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    try {
      const temp = document.createElement("textarea");
      temp.value = value;
      temp.style.position = "fixed";
      temp.style.opacity = "0";
      document.body.appendChild(temp);
      temp.focus();
      temp.select();
      const ok = document.execCommand("copy");
      temp.remove();
      return !!ok;
    } catch {
      return false;
    }
  }
}

function showInputModal({ title, message, defaultValue = "", rows = 8, okLabel = "OK" }) {
  return new Promise((resolve) => {
    modalTitle.textContent = title || "Dialog";
    modalMessage.textContent = message || "";
    modalForm.classList.add("hidden");
    modalForm.innerHTML = "";
    modalInput.classList.remove("hidden");
    modalInput.value = defaultValue || "";
    modalInput.rows = rows;
    modalOkBtn.textContent = okLabel;
    modalCancelBtn.style.display = "";
    modalOverlay.classList.remove("hidden");
    modalInput.focus();
    modalInput.select();

    const cleanup = () => {
      modalOverlay.classList.add("hidden");
      modalOkBtn.removeEventListener("click", onOk);
      modalCancelBtn.removeEventListener("click", onCancel);
      modalOverlay.removeEventListener("click", onBackdrop);
      modalInput.removeEventListener("keydown", onKeyDown);
    };

    const onOk = () => {
      const value = modalInput.value;
      cleanup();
      resolve(value);
    };

    const onCancel = () => {
      cleanup();
      resolve(null);
    };

    const onBackdrop = (event) => {
      if (event.target === modalOverlay) {
        onCancel();
      }
    };

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        onCancel();
      }
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        onOk();
      }
    };

    modalOkBtn.addEventListener("click", onOk);
    modalCancelBtn.addEventListener("click", onCancel);
    modalOverlay.addEventListener("click", onBackdrop);
    modalInput.addEventListener("keydown", onKeyDown);
  });
}

function showFormModal({
  title,
  message,
  html,
  okLabel = "OK",
  cancelLabel = "Cancel",
  showCancel = true,
  onMount = null,
  onSubmit = null
}) {
  return new Promise((resolve) => {
    document.querySelectorAll(".settings-modal-actions-brand").forEach((node) => node.remove());
    document.querySelectorAll(".modal-actions-banner").forEach((node) => node.remove());
    modalTitle.textContent = title || "Dialog";
    modalMessage.textContent = message || "";
    modalInput.classList.add("hidden");
    modalInput.value = "";
    modalForm.classList.remove("hidden");
    modalForm.innerHTML = html || "";
    initAllAnimatedSelects(modalForm);
    modalOkBtn.textContent = okLabel;
    modalCancelBtn.textContent = cancelLabel;
    modalCancelBtn.style.display = showCancel ? "" : "none";
    modalOverlay.classList.remove("hidden");

    const context = {
      setFormHtml: (newHtml) => {
        modalForm.innerHTML = newHtml || "";
        initAllAnimatedSelects(modalForm);
      }
    };

    const cleanup = () => {
      modalOverlay.classList.add("hidden");
      modalOkBtn.removeEventListener("click", onOk);
      modalCancelBtn.removeEventListener("click", onCancel);
      modalOverlay.removeEventListener("click", onBackdrop);
      modalInput.removeEventListener("keydown", onKeyDown);
    };

    const close = (value) => {
      cleanup();
      resolve(value);
    };

    const onOk = async () => {
      if (!onSubmit) {
        close(true);
        return;
      }
      try {
        const submitResult = await onSubmit(modalForm, context);
        if (submitResult !== false) {
          close(submitResult === undefined ? true : submitResult);
        }
      } catch (error) {
        addLog(error.message || "Dialog action failed.", "bad");
      }
    };

    const onCancel = () => {
      close(null);
    };

    const onBackdrop = (event) => {
      if (event.target === modalOverlay) {
        onCancel();
      }
    };

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        onCancel();
      }
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        onOk();
      }
    };

    modalOkBtn.addEventListener("click", onOk);
    modalCancelBtn.addEventListener("click", onCancel);
    modalOverlay.addEventListener("click", onBackdrop);
    modalInput.addEventListener("keydown", onKeyDown);

    if (onMount) {
      onMount(modalForm, context);
    }
  });
}

function showConfirmDialog({
  title = "Confirm",
  message = "",
  okLabel = "Yes",
  cancelLabel = "No"
}) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "confirm-overlay";
    overlay.innerHTML = `
      <div class="confirm-card" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
        <h3 class="confirm-title">${escapeHtml(title)}</h3>
        <p class="confirm-message">${escapeHtml(message)}</p>
        <div class="confirm-actions">
          <button type="button" class="control modal-btn" data-confirm-action="cancel">${escapeHtml(cancelLabel)}</button>
          <button type="button" class="control modal-btn primary" data-confirm-action="ok">${escapeHtml(okLabel)}</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const okBtn = overlay.querySelector("[data-confirm-action='ok']");
    const cancelBtn = overlay.querySelector("[data-confirm-action='cancel']");

    const cleanup = (value) => {
      document.removeEventListener("keydown", onKeyDown, true);
      overlay.remove();
      resolve(!!value);
    };

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        cleanup(false);
      } else if (event.key === "Enter") {
        event.preventDefault();
        cleanup(true);
      }
    };

    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) {
        cleanup(false);
      }
    });
    okBtn?.addEventListener("click", () => cleanup(true));
    cancelBtn?.addEventListener("click", () => cleanup(false));
    document.addEventListener("keydown", onKeyDown, true);
    okBtn?.focus();
  });
}

function showKeywordConfirmDialog({
  title = "Confirm",
  message = "",
  keyword = "PURGE",
  okLabel = "Confirm",
  cancelLabel = "Cancel"
}) {
  return new Promise((resolve) => {
    const expected = String(keyword || "").trim();
    const overlay = document.createElement("div");
    overlay.className = "confirm-overlay";
    overlay.innerHTML = `
      <div class="confirm-card" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
        <h3 class="confirm-title">${escapeHtml(title)}</h3>
        <p class="confirm-message">${escapeHtml(message)}</p>
        <input class="form-control confirm-keyword-input" type="text" placeholder="${escapeHtml(expected)}">
        <div class="confirm-actions" style="margin-top:10px;">
          <button type="button" class="control modal-btn" data-confirm-action="cancel">${escapeHtml(cancelLabel)}</button>
          <button type="button" class="control modal-btn primary" data-confirm-action="ok" disabled>${escapeHtml(okLabel)}</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const okBtn = overlay.querySelector("[data-confirm-action='ok']");
    const cancelBtn = overlay.querySelector("[data-confirm-action='cancel']");
    const input = overlay.querySelector(".confirm-keyword-input");

    const cleanup = (value) => {
      document.removeEventListener("keydown", onKeyDown, true);
      overlay.remove();
      resolve(!!value);
    };

    const updateState = () => {
      if (!okBtn || !input) {
        return;
      }
      okBtn.disabled = String(input.value || "").trim() !== expected;
    };

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        cleanup(false);
        return;
      }
      if (event.key === "Enter" && !okBtn?.disabled) {
        event.preventDefault();
        cleanup(true);
      }
    };

    input?.addEventListener("input", updateState);
    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) {
        cleanup(false);
      }
    });
    okBtn?.addEventListener("click", () => cleanup(true));
    cancelBtn?.addEventListener("click", () => cleanup(false));
    document.addEventListener("keydown", onKeyDown, true);
    updateState();
    input?.focus();
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function callApi(method, ...args) {
  if (appShuttingDown && method !== "close_window") {
    throw new Error("Window is closing.");
  }
  if (!window.pywebview || !window.pywebview.api || typeof window.pywebview.api[method] !== "function") {
    throw new Error("PyWebView API is unavailable.");
  }
  return window.pywebview.api[method](...args);
}

function beginAppShutdown() {
  if (appShuttingDown) {
    return;
  }
  appShuttingDown = true;
  if (eventPollTimer) {
    window.clearInterval(eventPollTimer);
    eventPollTimer = null;
  }
  if (queueRefreshTimer) {
    window.clearTimeout(queueRefreshTimer);
    queueRefreshTimer = null;
  }
  if (searchRenderTimer) {
    window.clearTimeout(searchRenderTimer);
    searchRenderTimer = null;
  }
}

function closeMenuPopups() {
  document.querySelectorAll(".menu-popup").forEach((menu) => menu.classList.remove("open"));
  document.querySelectorAll(".menu-btn").forEach((btn) => btn.classList.remove("active"));
  hideCommandSplitMenu();
  animatedSelectControllers.forEach((controller) => controller?.close?.());
}

function isCommandPaletteOpen() {
  return !!commandPaletteOverlay && !commandPaletteOverlay.classList.contains("hidden");
}

function hideCommandSplitMenu() {
  commandsSplitMenu?.classList.add("hidden");
  commandPaletteBtn?.classList.remove("active");
}

function syncAnimatedSelect(selectId) {
  const controller = animatedSelectControllers.get(String(selectId || ""));
  controller?.sync?.();
}

function destroyAnimatedSelect(selectId) {
  const id = String(selectId || "");
  if (!id) {
    return;
  }
  const controller = animatedSelectControllers.get(id);
  if (!controller) {
    return;
  }
  try {
    controller.close?.();
  } catch {
    // ignore close failures
  }
  try {
    controller.observer?.disconnect?.();
  } catch {
    // ignore observer disconnect failures
  }
  if (controller.trigger instanceof HTMLElement) {
    controller.trigger.remove();
  }
  if (controller.menu instanceof HTMLElement) {
    controller.menu.remove();
  }
  if (controller.selectEl instanceof HTMLSelectElement) {
    controller.selectEl.classList.remove("animated-select-native");
    if (controller.selectEl.getAttribute("tabindex") === "-1") {
      controller.selectEl.removeAttribute("tabindex");
    }
    const wrap = controller.selectEl.parentElement;
    if (wrap instanceof HTMLElement && !wrap.querySelector(".animated-select-trigger")) {
      wrap.classList.remove("custom-select-enabled");
    }
  }
  animatedSelectControllers.delete(id);
}

function pruneAnimatedSelectControllers() {
  Array.from(animatedSelectControllers.entries()).forEach(([id, controller]) => {
    if (!(controller?.selectEl instanceof HTMLSelectElement) || !controller.selectEl.isConnected) {
      destroyAnimatedSelect(id);
    }
  });
}

function setAnimatedSelectAvatarContent(avatarEl, avatarUrl, fallbackText = "") {
  if (!(avatarEl instanceof HTMLElement)) {
    return;
  }
  avatarEl.textContent = "";
  avatarEl.classList.remove("has-image");
  const safeLabel = String(fallbackText || "").trim();
  const fallback = (safeLabel.charAt(0) || "?").toUpperCase();
  const url = String(avatarUrl || "").trim();
  if (!url) {
    avatarEl.textContent = fallback;
    return;
  }
  const img = document.createElement("img");
  img.src = url;
  img.alt = "";
  img.loading = "lazy";
  img.decoding = "async";
  img.addEventListener("error", () => {
    avatarEl.classList.remove("has-image");
    avatarEl.textContent = fallback;
  });
  avatarEl.classList.add("has-image");
  avatarEl.appendChild(img);
}

function initAnimatedSelect(selectEl, options = {}) {
  if (!(selectEl instanceof HTMLSelectElement)) {
    return null;
  }
  const id = String(options.id || selectEl.id || selectEl.dataset.animatedSelectId || "");
  if (!id) {
    return null;
  }
  if (!selectEl.dataset.animatedSelectId) {
    selectEl.dataset.animatedSelectId = id;
  }
  const existing = animatedSelectControllers.get(id);
  if (existing) {
    if (existing.selectEl === selectEl) {
      existing.sync();
      return existing;
    }
    if (!(existing.selectEl instanceof HTMLSelectElement) || !existing.selectEl.isConnected) {
      destroyAnimatedSelect(id);
    } else {
      return existing;
    }
  }

  const wrap = selectEl.parentElement;
  if (!(wrap instanceof HTMLElement)) {
    return null;
  }

  const preexistingTrigger = wrap.querySelector(".animated-select-trigger");
  if (preexistingTrigger) {
    preexistingTrigger.remove();
  }
  const preexistingMenu = wrap.querySelector(".animated-select-menu");
  if (preexistingMenu) {
    preexistingMenu.remove();
  }

  wrap.classList.add("custom-select-enabled");
  selectEl.classList.add("animated-select-native");
  selectEl.setAttribute("tabindex", "-1");

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "animated-select-trigger control";
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");

  const isAccountSelect = id === "account-select";
  const label = document.createElement("span");
  label.className = "animated-select-label";
  if (options.prefix) {
    const prefix = document.createElement("span");
    prefix.className = "animated-select-prefix";
    prefix.textContent = String(options.prefix);
    label.appendChild(prefix);
  }
  let triggerAvatar = null;
  if (isAccountSelect) {
    triggerAvatar = document.createElement("span");
    triggerAvatar.className = "animated-select-account-avatar";
    label.appendChild(triggerAvatar);
  }
  const value = document.createElement("span");
  value.className = "animated-select-value";
  label.appendChild(value);
  trigger.appendChild(label);

  const menu = document.createElement("div");
  menu.className = "animated-select-menu hidden";
  menu.setAttribute("role", "listbox");
  menu.setAttribute("aria-label", String(options.ariaLabel || selectEl.getAttribute("aria-label") || id));

  wrap.appendChild(trigger);
  wrap.appendChild(menu);

  const controller = {
    id,
    selectEl,
    trigger,
    menu,
    observer: null,
    open: false,
    close: () => {
      if (!controller.open) {
        return;
      }
      controller.open = false;
      trigger.classList.remove("open");
      trigger.setAttribute("aria-expanded", "false");
      menu.classList.add("hidden");
    },
    renderOptions: () => {
      menu.innerHTML = "";
      Array.from(selectEl.options).forEach((option) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "animated-select-option";
        const optionText = option.textContent || option.value || "";
        if (isAccountSelect) {
          item.classList.add("animated-select-option-account");
          const avatar = document.createElement("span");
          avatar.className = "animated-select-account-avatar";
          setAnimatedSelectAvatarContent(avatar, option.dataset.avatarUrl || "", optionText);
          const text = document.createElement("span");
          text.className = "animated-select-option-text";
          text.textContent = optionText;
          item.appendChild(avatar);
          item.appendChild(text);
        } else {
          item.textContent = optionText;
        }
        item.dataset.value = option.value;
        item.setAttribute("role", "option");
        if (option.selected) {
          item.classList.add("active");
          item.setAttribute("aria-selected", "true");
        } else {
          item.setAttribute("aria-selected", "false");
        }
        item.disabled = !!option.disabled;
        item.addEventListener("click", () => {
          if (option.disabled) {
            return;
          }
          const changed = selectEl.value !== option.value;
          selectEl.value = option.value;
          controller.sync();
          controller.close();
          if (changed) {
            selectEl.dispatchEvent(new Event("change", { bubbles: true }));
          }
          trigger.focus();
        });
        menu.appendChild(item);
      });
    },
    sync: () => {
      const selectedOption = selectEl.selectedOptions?.[0] || selectEl.options?.[selectEl.selectedIndex] || null;
      value.textContent = selectedOption?.textContent || selectedOption?.value || "";
      if (isAccountSelect && triggerAvatar) {
        setAnimatedSelectAvatarContent(
          triggerAvatar,
          selectedOption?.dataset?.avatarUrl || "",
          selectedOption?.textContent || selectedOption?.value || ""
        );
      }
      trigger.disabled = !!selectEl.disabled;
      controller.renderOptions();
    },
    toggle: () => {
      if (controller.open) {
        controller.close();
        return;
      }
      animatedSelectControllers.forEach((candidate, candidateId) => {
        if (candidateId !== id) {
          candidate?.close?.();
        }
      });
      controller.open = true;
      trigger.classList.add("open");
      trigger.setAttribute("aria-expanded", "true");
      controller.renderOptions();
      menu.classList.remove("hidden");
    }
  };

  trigger.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    controller.toggle();
  });

  trigger.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " " || event.key === "ArrowDown") {
      event.preventDefault();
      controller.toggle();
      const active = menu.querySelector(".animated-select-option.active, .animated-select-option:not(:disabled)");
      if (active instanceof HTMLElement) {
        active.focus();
      }
      return;
    }
    if (event.key === "Escape") {
      controller.close();
    }
  });

  menu.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      controller.close();
      trigger.focus();
    }
  });

  const observer = new MutationObserver(() => controller.sync());
  observer.observe(selectEl, { childList: true, subtree: true, attributes: true, attributeFilter: ["disabled"] });
  controller.observer = observer;

  if (!document.body.dataset.animatedSelectBound) {
    document.body.dataset.animatedSelectBound = "1";
    document.addEventListener("mousedown", (event) => {
      if (event.target instanceof Element && event.target.closest(".custom-select-enabled")) {
        return;
      }
      animatedSelectControllers.forEach((candidate) => candidate?.close?.());
    });
    document.addEventListener("scroll", () => {
      animatedSelectControllers.forEach((candidate) => candidate?.close?.());
    }, true);
    window.addEventListener("resize", () => {
      animatedSelectControllers.forEach((candidate) => candidate?.close?.());
    });
  }

  animatedSelectControllers.set(id, controller);
  controller.sync();
  return controller;
}

let autoAnimatedSelectCounter = 0;

function initAnimatedSelectsIn(root, optionsResolver = null) {
  pruneAnimatedSelectControllers();
  const scope = root instanceof Element || root instanceof Document ? root : document;
  const selects = Array.from(scope.querySelectorAll("select"));
  selects.forEach((selectEl) => {
    if (!(selectEl instanceof HTMLSelectElement)) {
      return;
    }
    const forcedId = String(selectEl.id || selectEl.dataset.animatedSelectId || `auto-select-${++autoAnimatedSelectCounter}`);
    selectEl.dataset.animatedSelectId = forcedId;
    const resolved = typeof optionsResolver === "function" ? (optionsResolver(selectEl) || {}) : {};
    const initOptions = {
      id: forcedId,
      ariaLabel: selectEl.getAttribute("aria-label") || selectEl.name || forcedId,
      ...resolved
    };
    initAnimatedSelect(selectEl, initOptions);
  });
}

function resolveAnimatedSelectOptions(selectEl) {
  const id = String(selectEl?.id || "");
  if (id === "provider") {
    return { prefix: "Provider:", ariaLabel: "Provider" };
  }
  if (id === "account-select") {
    return { ariaLabel: "Account" };
  }
  return {};
}

function initAllAnimatedSelects(root = document) {
  initAnimatedSelectsIn(root, resolveAnimatedSelectOptions);
}

function getSharedCommands() {
  const config = {
    ...SETTINGS_DEFAULTS,
    ...(state.config || {})
  };
  const showSearch = config.show_searchbar !== false;
  const showLogs = config.show_logs !== false;
  const showProvider = config.show_provider !== false;
  const autoDetect = !!config.auto_detect_urls;
  const autoAdd = !!config.auto_add_to_queue;
  const theme = String(config.current_theme || "Dark");
  const logoStyle = String(config.logo_style || "Light");

  return [
    {
      id: "open_settings",
      label: "Open Settings",
      hint: "Controls",
      keywords: "settings preferences options",
      run: async () => {
        try {
          await openSettingsEditor();
        } catch (error) {
          addLog(error?.message || "Settings action failed.", "bad");
        }
      }
    },
    {
      id: "manage_accounts",
      label: "Manage Accounts",
      hint: "Controls",
      keywords: "accounts login users",
      run: async () => {
        try {
          await openAccountsManager();
        } catch (error) {
          addLog(error?.message || "Accounts action failed.", "bad");
        }
      }
    },
    {
      id: "manage_appids",
      label: "Manage AppIDs",
      hint: "Controls",
      keywords: "appids ids overrides",
      run: async () => {
        try {
          await openAppIdsManager();
        } catch (error) {
          addLog(error?.message || "AppIDs action failed.", "bad");
        }
      }
    },
    {
      id: "import_queue",
      label: "Import Queue",
      hint: "Controls",
      keywords: "import queue file",
      run: async () => {
        const browse = await callApi("browse_import_queue_file");
        if (!browse?.success) {
          if (!browse?.cancelled) {
            addLog(browse?.error || "Import file selection failed.", "bad");
          }
          return;
        }
        const filePath = browse.path;
        const result = await callApi("import_queue", filePath);
        if (result?.success) {
          addLog(`Queue imported (${result.added} added, ${result.skipped} skipped).`, "good");
          await refreshQueue({ forceReload: true });
        } else {
          addLog(result?.error || "Import failed.", "bad");
        }
      }
    },
    {
      id: "export_queue",
      label: "Export Queue",
      hint: "Controls",
      keywords: "export queue file",
      run: async () => {
        const browse = await callApi("browse_export_queue_file");
        if (!browse?.success) {
          if (!browse?.cancelled) {
            addLog(browse?.error || "Export file selection failed.", "bad");
          }
          return;
        }
        const filePath = browse.path;
        const result = await callApi("export_queue", filePath);
        if (result?.success) {
          addLog(`Queue exported to ${result.path}.`, "good");
        } else {
          addLog(result?.error || "Export failed.", "bad");
        }
      }
    },
    {
      id: "start_or_cancel_download",
      label: state.isDownloading ? "Cancel Download" : "Start Download",
      hint: "Queue",
      keywords: "download start cancel",
      run: () => startDownloadBtn?.click()
    },
    {
      id: "open_downloads_folder",
      label: "Open Downloads Folder",
      hint: "Queue",
      keywords: "open downloads folder path",
      run: () => openDownloadsBtn?.click()
    },
    {
      id: "download_now",
      label: "Download Now",
      hint: "Queue",
      keywords: "download now immediate",
      run: () => downloadNowBtn?.click()
    },
    {
      id: "theme_dark",
      label: "Theme: Dark",
      hint: theme === "Dark" ? "Current" : "Appearance",
      keywords: "theme dark",
      run: async () => {
        await applySettingsPatch({ current_theme: "Dark" }, "Theme changed to Dark.");
      }
    },
    {
      id: "theme_light",
      label: "Theme: Light",
      hint: theme === "Light" ? "Current" : "Appearance",
      keywords: "theme light",
      run: async () => {
        await applySettingsPatch({ current_theme: "Light" }, "Theme changed to Light.");
      }
    },
    {
      id: "logo_light",
      label: "Logo Style: Light",
      hint: logoStyle === "Light" ? "Current" : "Appearance",
      keywords: "logo style light",
      run: async () => {
        await applySettingsPatch({ logo_style: "Light" }, "Logo style changed to Light.");
      }
    },
    {
      id: "logo_dark",
      label: "Logo Style: Dark",
      hint: logoStyle === "Dark" ? "Current" : "Appearance",
      keywords: "logo style dark",
      run: async () => {
        await applySettingsPatch({ logo_style: "Dark" }, "Logo style changed to Dark.");
      }
    },
    {
      id: "logo_darker",
      label: "Logo Style: Darker",
      hint: logoStyle === "Darker" ? "Current" : "Appearance",
      keywords: "logo style darker",
      run: async () => {
        await applySettingsPatch({ logo_style: "Darker" }, "Logo style changed to Darker.");
      }
    },
    {
      id: "toggle_search_bar",
      label: showSearch ? "Hide Search Bar" : "Show Search Bar",
      hint: "Appearance",
      keywords: "search bar visibility",
      run: async () => {
        await applySettingsPatch({ show_searchbar: !state.config.show_searchbar }, "Toggled search bar visibility.");
      }
    },
    {
      id: "toggle_logs",
      label: showLogs ? "Hide Logs View" : "Show Logs View",
      hint: "Appearance",
      keywords: "logs console visibility",
      run: async () => {
        await applySettingsPatch({ show_logs: !state.config.show_logs }, "Toggled logs view visibility.");
      }
    },
    {
      id: "toggle_provider",
      label: showProvider ? "Hide Provider Selector" : "Show Provider Selector",
      hint: "Appearance",
      keywords: "provider visibility dropdown",
      run: async () => {
        await applySettingsPatch({ show_provider: !state.config.show_provider }, "Toggled provider dropdown visibility.");
      }
    },
    {
      id: "toggle_auto_detect",
      label: autoDetect ? "Disable Auto-detect URLs" : "Enable Auto-detect URLs",
      hint: "Tools",
      keywords: "auto detect clipboard urls",
      run: async () => {
        const nextValue = !state.config.auto_detect_urls;
        const patch = { auto_detect_urls: nextValue };
        if (!nextValue) {
          patch.auto_add_to_queue = false;
        }
        await applySettingsPatch(patch, `Auto-detect URLs ${nextValue ? "enabled" : "disabled"}.`);
      }
    },
    {
      id: "toggle_auto_add",
      label: autoAdd ? "Disable Auto-add URLs" : "Enable Auto-add URLs",
      hint: "Tools",
      keywords: "auto add queue urls",
      run: async () => {
        if (!state.config.auto_detect_urls) {
          addLog("Enable auto-detect URLs first.", "bad");
          return;
        }
        const nextValue = !state.config.auto_add_to_queue;
        await applySettingsPatch({ auto_add_to_queue: nextValue }, `Auto-add URLs ${nextValue ? "enabled" : "disabled"}.`);
      }
    },
    {
      id: "open_documentation",
      label: "Documentation",
      hint: "Help",
      keywords: "docs guide manual",
      run: async () => {
        const result = await callApi("launch_documentation");
        if (!result?.success) {
          addLog(result?.error || "Failed to open documentation.", "bad");
        }
      }
    },
    {
      id: "open_report_issue",
      label: "Report Issue",
      hint: "Help",
      keywords: "bug issue github",
      run: async () => {
        const result = await callApi("launch_report_issue");
        if (!result?.success) {
          addLog(result?.error || "Failed to open issues page.", "bad");
        }
      }
    },
    {
      id: "show_tutorial",
      label: "Show Tutorial",
      hint: "Help",
      keywords: "tutorial walkthrough onboarding",
      run: async () => {
        await openTutorialDialog();
      }
    },
    {
      id: "show_about",
      label: "About",
      hint: "Help",
      keywords: "about version info",
      run: async () => {
        await openAboutDialog();
      }
    }
  ];
}

function getPaletteCommands() {
  return getSharedCommands();
}

function getSharedCommandById(commandId) {
  return getSharedCommands().find((command) => command.id === commandId) || null;
}

async function runCommandById(commandId, { closeMenus = false } = {}) {
  const command = getSharedCommandById(commandId);
  if (!command) {
    addLog(`Unknown command: ${commandId}`, "bad");
    return false;
  }
  if (closeMenus) {
    closeMenuPopups();
  }
  try {
    await command.run();
    return true;
  } catch (error) {
    addLog(error?.message || `Command failed: ${command.label}`, "bad");
    return false;
  }
}

function bindCommandToButton(button, commandId, { closeMenus = false } = {}) {
  if (!button) {
    return;
  }
  button.addEventListener("click", () => {
    void runCommandById(commandId, { closeMenus });
  });
}

function filterCommandPaletteActions(queryText) {
  const terms = String(queryText || "")
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);

  if (!terms.length) {
    return commandPaletteActions.slice();
  }

  return commandPaletteActions.filter((action) => {
    const haystack = `${action.label} ${action.hint || ""} ${action.keywords || ""}`.toLowerCase();
    return terms.every((term) => haystack.includes(term));
  });
}

function setCommandPaletteSelection(index, scroll = true) {
  if (!Array.isArray(commandPaletteResults) || commandPaletteResults.length === 0) {
    commandPaletteSelectedIndex = 0;
    return;
  }
  const maxIndex = commandPaletteResults.length - 1;
  commandPaletteSelectedIndex = Math.max(0, Math.min(index, maxIndex));

  const items = commandPaletteList?.querySelectorAll(".command-palette-item");
  if (!items || items.length === 0) {
    return;
  }
  items.forEach((itemNode, itemIndex) => {
    itemNode.classList.toggle("active", itemIndex === commandPaletteSelectedIndex);
  });
  if (scroll) {
    items[commandPaletteSelectedIndex]?.scrollIntoView({ block: "nearest" });
  }
}

function renderCommandPaletteList() {
  if (!commandPaletteList) {
    return;
  }

  commandPaletteResults = filterCommandPaletteActions(commandPaletteInput?.value || "");
  if (commandPaletteResults.length === 0) {
    commandPaletteList.innerHTML = '<div class="command-palette-empty">No commands found.</div>';
    commandPaletteSelectedIndex = 0;
    return;
  }

  commandPaletteList.innerHTML = "";
  commandPaletteResults.forEach((action, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "command-palette-item";
    button.dataset.commandIndex = String(index);

    const label = document.createElement("span");
    label.className = "command-palette-item-label";
    label.textContent = action.label;
    button.appendChild(label);

    if (action.hint) {
      const hint = document.createElement("span");
      hint.className = "command-palette-item-hint";
      hint.textContent = action.hint;
      button.appendChild(hint);
    }

    button.addEventListener("mouseenter", () => setCommandPaletteSelection(index, false));
    button.addEventListener("click", () => executeCommandPaletteAction(index));
    commandPaletteList.appendChild(button);
  });

  if (commandPaletteSelectedIndex >= commandPaletteResults.length) {
    commandPaletteSelectedIndex = commandPaletteResults.length - 1;
  }
  setCommandPaletteSelection(commandPaletteSelectedIndex, false);
}

function closeCommandPalette({ restoreFocus = true } = {}) {
  if (!isCommandPaletteOpen()) {
    return;
  }
  commandPaletteOverlay.classList.add("hidden");
  commandPaletteList.innerHTML = "";
  commandPaletteResults = [];
  commandPaletteActions = [];
  commandPaletteSelectedIndex = 0;

  const restoreTarget = commandPaletteLastFocusedElement;
  commandPaletteLastFocusedElement = null;
  if (restoreFocus && restoreTarget instanceof HTMLElement && document.contains(restoreTarget)) {
    restoreTarget.focus();
  }
}

function executeCommandPaletteAction(index = commandPaletteSelectedIndex) {
  const action = commandPaletteResults[index];
  if (!action?.id) {
    return;
  }
  closeCommandPalette();
  void runCommandById(action.id);
}

function focusCommandPaletteInput({ selectAll = false } = {}) {
  if (!commandPaletteInput) {
    return;
  }

  let attempts = 0;
  const maxAttempts = 8;
  const applyFocus = () => {
    if (!isCommandPaletteOpen()) {
      return;
    }
    try {
      commandPaletteInput.focus();
    } catch {
      return;
    }
    if (selectAll) {
      if (commandPaletteInput.value.length > 0) {
        commandPaletteInput.select();
      } else {
        commandPaletteInput.setSelectionRange(0, 0);
      }
    }
    if (document.activeElement !== commandPaletteInput && attempts < maxAttempts) {
      attempts += 1;
      window.setTimeout(applyFocus, 16);
    }
  };

  applyFocus();
  window.requestAnimationFrame(applyFocus);
  window.setTimeout(applyFocus, 0);
}

function applyCommandPaletteInputKey(rawKey) {
  if (!commandPaletteInput) {
    return false;
  }
  const keyText = String(rawKey || "");
  const key = keyText.toLowerCase();
  const valueLength = commandPaletteInput.value.length;
  const start = Number.isInteger(commandPaletteInput.selectionStart) ? commandPaletteInput.selectionStart : valueLength;
  const end = Number.isInteger(commandPaletteInput.selectionEnd) ? commandPaletteInput.selectionEnd : start;

  if (keyText.length === 1) {
    commandPaletteInput.setRangeText(keyText, start, end, "end");
    commandPaletteInput.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  }
  if (key === "backspace") {
    if (start !== end) {
      commandPaletteInput.setRangeText("", start, end, "end");
    } else if (start > 0) {
      commandPaletteInput.setRangeText("", start - 1, start, "end");
    } else {
      return false;
    }
    commandPaletteInput.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  }
  if (key === "delete") {
    if (start !== end) {
      commandPaletteInput.setRangeText("", start, end, "end");
    } else if (start < valueLength) {
      commandPaletteInput.setRangeText("", start, start + 1, "end");
    } else {
      return false;
    }
    commandPaletteInput.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  }
  return false;
}

function openCommandPalette() {
  if (!commandPaletteOverlay || !commandPaletteInput || !commandPaletteList) {
    return;
  }
  if (modalOverlay && !modalOverlay.classList.contains("hidden")) {
    return;
  }

  closeMenuPopups();
  hideQueueContextMenu();
  hideLogsContextMenu();
  hideHeaderContextMenu();

  commandPaletteLastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  commandPaletteActions = getPaletteCommands();
  commandPaletteSelectedIndex = 0;
  commandPaletteInput.value = "";
  commandPaletteOverlay.classList.remove("hidden");
  renderCommandPaletteList();
  focusCommandPaletteInput({ selectAll: true });
}

function wireCommandPalette() {
  if (!commandPaletteOverlay || !commandPaletteInput || !commandPaletteList) {
    return;
  }

  commandPaletteOverlay.addEventListener("mousedown", (event) => {
    if (event.target === commandPaletteOverlay) {
      closeCommandPalette();
    }
  });

  commandPaletteInput.addEventListener("input", () => {
    commandPaletteSelectedIndex = 0;
    renderCommandPaletteList();
  });

  commandPaletteInput.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeCommandPalette();
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setCommandPaletteSelection(commandPaletteSelectedIndex + 1);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setCommandPaletteSelection(commandPaletteSelectedIndex - 1);
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      executeCommandPaletteAction(commandPaletteSelectedIndex);
    }
  });
}

function wireCommandSplitMenu() {
  if (!commandPaletteBtn || !commandsSplitMenu) {
    return;
  }

  commandPaletteBtn.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (commandPaletteBtn.style.display === "none") {
      return;
    }
    const willOpen = commandsSplitMenu.classList.contains("hidden");
    hideCommandSplitMenu();
    if (!willOpen) {
      return;
    }
    closeMenuPopups();
    hideQueueContextMenu();
    hideLogsContextMenu();
    hideHeaderContextMenu();
    commandsSplitMenu.classList.remove("hidden");
    commandPaletteBtn.classList.add("active");
  });

  openCommandPaletteMenuBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    hideCommandSplitMenu();
    openCommandPalette();
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("#settings-command-shell")) {
      hideCommandSplitMenu();
    }
  });

  document.addEventListener("scroll", () => hideCommandSplitMenu(), true);
  window.addEventListener("resize", () => hideCommandSplitMenu());
}

function parseModId(inputUrl) {
  const idMatch = (inputUrl || "").match(/[?&]id=(\d+)/);
  if (idMatch) {
    return idMatch[1];
  }
  if (/^\d+$/.test(inputUrl || "")) {
    return inputUrl;
  }
  return "N/A";
}

function normalizeQueueItem(item, index) {
  const fallbackUrl = item.url || "";
  const modId = String(item.mod_id || parseModId(fallbackUrl) || String(index + 1));
  const modName = String(item.mod_name || fallbackUrl || "Untitled Mod");
  const gameName = String(item.game_name || "Unknown");
  const status = String(item.status || "Queued");
  const provider = String(item.provider || "Default");
  const retryCount = Math.max(0, Number(item.retry_count || 0));
  const maxRetries = Math.max(1, Number(item.max_retries || 3));
  return {
    game_name: gameName,
    mod_id: modId,
    mod_name: modName,
    status,
    retry_count: retryCount,
    max_retries: maxRetries,
    provider,
    app_id: item.app_id || "",
    _search_mod_id: modId.toLowerCase(),
    _search_mod_name: modName.toLowerCase(),
    _search_mod_id_raw: modId,
    _search_mod_name_raw: modName
  };
}

function syncStartButton() {
  if (state.cancelPending) {
    startDownloadBtn.textContent = "Canceling...";
    startDownloadBtn.classList.add("active");
    startDownloadBtn.disabled = true;
    return;
  }
  startDownloadBtn.disabled = false;
  if (state.isDownloading) {
    startDownloadBtn.textContent = "Cancel Download";
    startDownloadBtn.classList.add("active");
  } else {
    startDownloadBtn.textContent = "Start Download";
    startDownloadBtn.classList.remove("active");
  }
}

function isFilterMatch(item) {
  if (state.filter === "All") {
    return true;
  }
  if (state.filter === "Queued") {
    return item.status === "Queued";
  }
  if (state.filter === "Downloaded") {
    return item.status === "Downloaded";
  }
  if (state.filter === "Failed") {
    return String(item.status).includes("Failed");
  }
  return true;
}

function isSearchMatch(item, query) {
  if (!query) {
    return true;
  }
  const cache = state.searchMatcherCache;
  if (
    cache.query !== query
    || cache.regex !== state.regex
    || cache.caseSensitive !== state.caseSensitive
    || typeof cache.matcher !== "function"
  ) {
    let matcher = () => true;
    if (state.regex) {
      try {
        const flags = state.caseSensitive ? "" : "i";
        const pattern = new RegExp(query, flags);
        matcher = (entry) => pattern.test(entry._search_mod_id_raw) || pattern.test(entry._search_mod_name_raw);
      } catch {
        matcher = () => false;
      }
    } else if (state.caseSensitive) {
      matcher = (entry) => entry._search_mod_id_raw.includes(query) || entry._search_mod_name_raw.includes(query);
    } else {
      const lowered = query.toLowerCase();
      matcher = (entry) => entry._search_mod_id.includes(lowered) || entry._search_mod_name.includes(lowered);
    }

    cache.query = query;
    cache.regex = state.regex;
    cache.caseSensitive = state.caseSensitive;
    cache.matcher = matcher;
  }

  return cache.matcher(item);
}

function getFilteredQueue() {
  const query = searchInput.value.trim();
  return state.queue.filter((item) => isFilterMatch(item) && isSearchMatch(item, query));
}

function updateSearchPlaceholder() {
  const total = state.queueStats.total;
  let prefix = `Mods in Queue: ${total}`;
  if (state.filter === "Queued") {
    prefix = `Queued Mods: ${state.queueStats.queued} / ${total}`;
  } else if (state.filter === "Downloaded") {
    prefix = `Downloaded Mods: ${state.queueStats.downloaded} / ${total}`;
  } else if (state.filter === "Failed") {
    prefix = `Failed Mods: ${state.queueStats.failed} / ${total}`;
  }
  searchInput.placeholder = `${prefix}     /     Search by Mod ID or Name`;
  updateQueueStatisticsTooltip();
}

function updateQueueStatisticsTooltip() {
  const total = state.queueStats.total;
  const queued = state.queueStats.queued;
  const downloaded = state.queueStats.downloaded;
  const failed = state.queueStats.failed;
  const downloading = state.queueStats.downloading;

  let tooltip = `Queue Statistics\nAll Mods: ${total}\nQueued: ${queued}\nDownloaded: ${downloaded}\nFailed: ${failed}`;
  if (downloading > 0) {
    tooltip += `\nDownloading: ${downloading}`;
  }
  filterBtn.title = tooltip;
}

function applyWorkshopHelpTooltip() {
  urlHelpBtn.title = [
    "Workshop Input Formats",
    "",
    "• Game AppID (e.g., 108600) or Store URL: Queue all mods for a game",
    "• Mod URL/ID: Queue a specific workshop mod",
    "• Collection URL/ID: Queue all mods in a collection",
    "",
    "You can paste Steam URLs directly from your browser.",
    "URLs are auto-detected from clipboard if enabled in settings."
  ].join("\n");
}

function getDefaultQueueColumnWidths() {
  const configured = Array.isArray(state.config?.queue_tree_default_widths) ? state.config.queue_tree_default_widths : null;
  return QUEUE_COLUMNS.map((column, index) => {
    const value = Number(configured?.[index]);
    return Number.isFinite(value) && value >= 48 ? Math.round(value) : column.defaultWidth;
  });
}

function getQueueColumnWidths() {
  const defaults = getDefaultQueueColumnWidths();
  const configured = Array.isArray(state.config?.queue_tree_column_widths) ? state.config.queue_tree_column_widths : null;
  return QUEUE_COLUMNS.map((_, index) => {
    const value = Number(configured?.[index]);
    return Number.isFinite(value) && value >= 48 ? Math.round(value) : defaults[index];
  });
}

function getQueueColumnHidden() {
  const configured = Array.isArray(state.config?.queue_tree_column_hidden) ? state.config.queue_tree_column_hidden : null;
  return QUEUE_COLUMNS.map((_, index) => Boolean(configured?.[index]));
}

function isHeaderLocked() {
  return state.config?.header_locked !== false;
}

function applyQueueColumnWidths() {
  if (!queueTable) {
    return;
  }
  const widths = getQueueColumnWidths();
  const hiddenColumns = getQueueColumnHidden();
  const showRowNumbers = !!state.config?.show_row_numbers;
  queueTable.style.setProperty("--queue-col-width-game", `${widths[0]}px`);
  queueTable.style.setProperty("--queue-col-width-mod-id", `${widths[1]}px`);
  queueTable.style.setProperty("--queue-col-width-mod-name", `${widths[2]}px`);
  queueTable.style.setProperty("--queue-col-width-status", `${widths[3]}px`);
  queueTable.style.setProperty("--queue-col-width-provider", `${widths[4]}px`);

  let totalWidth = showRowNumbers ? 42 : 0;
  QUEUE_COLUMNS.forEach((_, index) => {
    if (!hiddenColumns[index]) {
      totalWidth += widths[index];
    }
  });
  totalWidth = Math.max(160, totalWidth);
  queueTable.style.setProperty("--queue-table-width", `${totalWidth}px`);
}

function renderQueueHeader() {
  if (!queueHeadRow) {
    return;
  }

  const hiddenColumns = getQueueColumnHidden();
  const showRowNumbers = !!state.config?.show_row_numbers;

  queueHeadRow.innerHTML = "";

  if (showRowNumbers) {
    const numberHeader = document.createElement("th");
    numberHeader.dataset.colKey = "row_number";
    numberHeader.textContent = "#";
    queueHeadRow.appendChild(numberHeader);
  }

  QUEUE_COLUMNS.forEach((column, index) => {
    const th = document.createElement("th");
    th.dataset.colKey = column.key;
    th.dataset.colIndex = String(index);
    th.classList.add("sortable");
    th.textContent = column.label;
    if (hiddenColumns[index]) {
      th.classList.add("col-hidden");
    }
    if (state.sort?.clicked && state.sort?.key === column.key && state.config?.show_sort_indicator !== false) {
      th.classList.add(state.sort.direction === "desc" ? "sort-desc" : "sort-asc");
    }
    if (!hiddenColumns[index]) {
      const resizer = document.createElement("span");
      resizer.className = `col-resizer${isHeaderLocked() ? " disabled" : ""}`;
      resizer.dataset.colIndex = String(index);
      th.appendChild(resizer);
    }
    queueHeadRow.appendChild(th);
  });
}

function compareQueueValues(left, right, key) {
  if (key === "mod_id") {
    const leftNum = Number(left);
    const rightNum = Number(right);
    const leftIsNum = Number.isFinite(leftNum);
    const rightIsNum = Number.isFinite(rightNum);
    if (leftIsNum && rightIsNum) {
      if (leftNum === rightNum) {
        return 0;
      }
      return leftNum < rightNum ? -1 : 1;
    }
  }

  const leftText = String(left ?? "").toLowerCase();
  const rightText = String(right ?? "").toLowerCase();
  if (leftText === rightText) {
    return 0;
  }
  return leftText < rightText ? -1 : 1;
}

function getSortedQueue(items) {
  const sortKey = state.sort?.key || "";
  if (!sortKey) {
    return items;
  }

  const direction = state.sort?.direction === "desc" ? -1 : 1;
  return items
    .map((item, index) => ({ item, index }))
    .sort((left, right) => {
      const result = compareQueueValues(left.item?.[sortKey], right.item?.[sortKey], sortKey);
      if (result !== 0) {
        return result * direction;
      }
      return left.index - right.index;
    })
    .map((entry) => entry.item);
}

function applyQueueSort(columnKey) {
  if (!QUEUE_COLUMNS.some((column) => column.key === columnKey)) {
    return;
  }

  if (state.sort.key === columnKey) {
    state.sort.direction = state.sort.direction === "asc" ? "desc" : "asc";
  } else {
    state.sort.key = columnKey;
    state.sort.direction = "asc";
  }
  state.sort.clicked = true;
  renderQueue();
}

function onColumnResizeMove(event) {
  if (!activeColumnResize) {
    return;
  }
  const delta = event.clientX - activeColumnResize.startX;
  const nextWidth = Math.max(48, Math.round(activeColumnResize.startWidth + delta));
  const widths = activeColumnResize.widths;
  if (widths[activeColumnResize.colIndex] === nextWidth) {
    return;
  }
  widths[activeColumnResize.colIndex] = nextWidth;
  state.config.queue_tree_column_widths = widths.slice();
  applyQueueColumnWidths();
}

async function onColumnResizeEnd() {
  if (!activeColumnResize) {
    return;
  }
  const widths = activeColumnResize.widths.slice();
  activeColumnResize = null;
  document.body.classList.remove("column-resizing");
  document.removeEventListener("mousemove", onColumnResizeMove);
  document.removeEventListener("mouseup", onColumnResizeEnd);

  const result = await callApi("update_settings", { queue_tree_column_widths: widths });
  if (!result?.success) {
    addLog(result?.error || "Failed to save column widths.", "bad");
    return;
  }
  state.config = result.config || state.config;
  applyQueueColumnWidths();
}

function startColumnResize(event, colIndex) {
  if (isHeaderLocked()) {
    return;
  }
  const widths = getQueueColumnWidths();
  if (!Number.isInteger(colIndex) || colIndex < 0 || colIndex >= widths.length) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();

  activeColumnResize = {
    colIndex,
    startX: event.clientX,
    startWidth: widths[colIndex],
    widths: widths.slice()
  };

  document.body.classList.add("column-resizing");
  document.addEventListener("mousemove", onColumnResizeMove);
  document.addEventListener("mouseup", onColumnResizeEnd);
}

async function getModIdsInRange(startIndex, endIndex) {
  const safeStart = Math.max(0, Number(startIndex) || 0);
  const safeEnd = Math.max(safeStart, Number(endIndex) || safeStart);

  if (!virtualBackendEnabled) {
    return virtualItems
      .slice(safeStart, safeEnd + 1)
      .map((item) => String(item.mod_id));
  }

  if (safeStart >= virtualBackendPageStart && safeEnd < virtualBackendPageEnd) {
    const localStart = safeStart - virtualBackendPageStart;
    const localEnd = safeEnd - virtualBackendPageStart + 1;
    return virtualBackendPageItems
      .slice(localStart, localEnd)
      .map((item) => String(item.mod_id));
  }

  const query = getVirtualQueryPayload();
  const ids = [];
  let offset = safeStart;
  while (offset <= safeEnd) {
    const limit = Math.min(VIRTUAL_FETCH_MAX_LIMIT, (safeEnd - offset) + 1);
    const result = await callApi(
      "get_queue_page",
      query.filterName,
      query.searchQuery,
      query.regexEnabled,
      query.caseSensitive,
      query.sortKey,
      query.sortDirection,
      offset,
      limit
    );
    if (!result?.success) {
      break;
    }
    const items = Array.isArray(result.items) ? result.items : [];
    if (!items.length) {
      break;
    }
    for (const item of items) {
      ids.push(String(item.mod_id));
    }
    offset += items.length;
    if (items.length < limit) {
      break;
    }
  }
  return ids;
}

async function handleRowClick(event, row) {
  const modId = String(row?.dataset?.modId || "");
  const rowIndex = Number.parseInt(String(row?.dataset?.listIndex || "-1"), 10);
  if (!modId) {
    return;
  }

  const isToggle = !!(event.ctrlKey || event.metaKey);
  const isRange = !!event.shiftKey && Number.isInteger(rowIndex) && rowIndex >= 0 && state.selectionAnchorIndex !== null;

  if (isRange) {
    const anchor = Number(state.selectionAnchorIndex);
    const start = Math.min(anchor, rowIndex);
    const end = Math.max(anchor, rowIndex);
    const idsInRange = await getModIdsInRange(start, end);
    if (!isToggle) {
      state.selectedModIds.clear();
    }
    idsInRange.forEach((id) => state.selectedModIds.add(String(id)));
  } else if (isToggle) {
    if (state.selectedModIds.has(modId)) {
      state.selectedModIds.delete(modId);
    } else {
      state.selectedModIds.add(modId);
    }
    if (Number.isInteger(rowIndex) && rowIndex >= 0) {
      state.selectionAnchorIndex = rowIndex;
      state.selectionAnchorModId = modId;
    }
  } else {
    state.selectedModIds.clear();
    state.selectedModIds.add(modId);
    if (Number.isInteger(rowIndex) && rowIndex >= 0) {
      state.selectionAnchorIndex = rowIndex;
      state.selectionAnchorModId = modId;
    }
  }

  renderQueueViewport(true);
}

function isTextEditingTarget(target) {
  if (!(target instanceof Element)) {
    return false;
  }
  if (target.isContentEditable) {
    return true;
  }
  const tag = String(target.tagName || "").toUpperCase();
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
    return true;
  }
  return !!target.closest("input, textarea, select, [contenteditable='true']");
}

async function getAllSelectableModIds() {
  if (!virtualBackendEnabled) {
    return virtualItems.map((item) => String(item.mod_id));
  }

  const query = getVirtualQueryPayload();
  const probe = await callApi(
    "get_queue_page",
    query.filterName,
    query.searchQuery,
    query.regexEnabled,
    query.caseSensitive,
    query.sortKey,
    query.sortDirection,
    0,
    1
  );
  if (!probe?.success) {
    return [];
  }

  const total = Math.max(0, Number(probe.total || 0));
  if (total <= 0) {
    return [];
  }
  return getModIdsInRange(0, total - 1);
}

async function selectAllQueueItems() {
  const allIds = await getAllSelectableModIds();
  state.selectedModIds.clear();
  allIds.forEach((id) => state.selectedModIds.add(String(id)));

  const total = virtualBackendEnabled
    ? Math.max(0, Number(virtualBackendTotal || allIds.length))
    : virtualItems.length;

  if (total > 0) {
    state.selectionAnchorIndex = total - 1;
    state.selectionAnchorModId = allIds.length ? String(allIds[allIds.length - 1]) : "";
  } else {
    state.selectionAnchorIndex = null;
    state.selectionAnchorModId = "";
  }

  renderQueueViewport(true);
}

function recomputeQueueStats() {
  const stats = {
    total: state.queue.length,
    queued: 0,
    downloaded: 0,
    failed: 0,
    downloading: 0
  };

  for (const item of state.queue) {
    const status = String(item.status || "");
    if (status === "Queued") {
      stats.queued += 1;
    }
    if (status === "Downloaded") {
      stats.downloaded += 1;
    }
    if (status.includes("Failed")) {
      stats.failed += 1;
    }
    if (status === "Downloading") {
      stats.downloading += 1;
    }
  }

  state.queueStats = stats;
}

function scheduleSearchRender(delay = SEARCH_RENDER_DEBOUNCE_MS) {
  if (searchRenderTimer) {
    window.clearTimeout(searchRenderTimer);
  }
  searchRenderTimer = window.setTimeout(() => {
    searchRenderTimer = null;
    renderQueue();
  }, Math.max(0, Number(delay) || 0));
}

function createQueueRow(modId) {
  const row = document.createElement("tr");
  row.dataset.modId = modId;
  bindQueueRowHandlers(row);

  return row;
}

function getQueueStatusDisplayText(item) {
  const status = String(item?.status || "");
  if (status !== "Queued") {
    return status;
  }
  const retryCount = Math.max(0, Number(item?.retry_count || 0));
  if (retryCount <= 0) {
    return status;
  }
  const maxRetries = Math.max(1, Number(item?.max_retries || 3));
  return `Queued (Retry ${Math.min(retryCount, maxRetries)}/${maxRetries})`;
}

function bindQueueRowHandlers(row) {
  if (!row || row._interactionsBound) {
    return;
  }
  row._interactionsBound = true;

  row.addEventListener("mousedown", (event) => {
    if (event.button !== 0) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    hideHeaderContextMenu();
    hideQueueContextMenu();
    void handleRowClick(event, row).catch((error) => {
      addLog(error?.message || "Failed to select queue item.", "bad");
    });
  });

  row.addEventListener("dblclick", (event) => {
    event.stopPropagation();
    const modId = String(row.dataset.modId || "");
    if (!modId) {
      return;
    }
    event.preventDefault();
    void callApi("open_downloads_folder", modId)
      .then((result) => {
        if (result?.success) {
          addLog(`Opened Downloads folder for ${modId}.`, "good");
        } else {
          addLog(result?.error || "Failed to open Downloads folder.", "bad");
        }
      })
      .catch(() => {
        addLog("Open Downloads Folder is only available from desktop app.", "bad");
      });
  });

  row.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    event.stopPropagation();

    const modId = String(row.dataset.modId || "");
    const rowIndex = Number.parseInt(String(row.dataset.listIndex || "-1"), 10);
    if (!modId) {
      return;
    }

    if (!state.selectedModIds.has(modId)) {
      state.selectedModIds.clear();
      state.selectedModIds.add(modId);
    }

    if (Number.isInteger(rowIndex) && rowIndex >= 0) {
      state.selectionAnchorIndex = rowIndex;
      state.selectionAnchorModId = modId;
    }

    renderQueueViewport(true);
    showQueueContextMenu(event.clientX, event.clientY);
  });
}

function createSpacerRow(className, colSpan) {
  const row = document.createElement("tr");
  row.className = className;
  const cell = document.createElement("td");
  cell.colSpan = colSpan;
  cell.style.height = "0px";
  row.appendChild(cell);
  return row;
}

function buildQueueLayoutKey(showRowNumbers, hiddenColumns) {
  const hiddenKey = hiddenColumns.map((hidden) => (hidden ? "1" : "0")).join("");
  return `${showRowNumbers ? "1" : "0"}|${hiddenKey}`;
}

function ensureQueueRowStructure(row, layoutKey, showRowNumbers, hiddenColumns) {
  if (row.dataset.layoutKey === layoutKey && row._cells) {
    return row._cells;
  }

  row.innerHTML = "";
  const cells = {};

  if (showRowNumbers) {
    const numberCell = document.createElement("td");
    numberCell.dataset.colKey = "row_number";
    row.appendChild(numberCell);
    cells.row_number = numberCell;
  }

  QUEUE_COLUMNS.forEach((column, columnIndex) => {
    const cell = document.createElement("td");
    cell.dataset.colKey = column.key;
    if (hiddenColumns[columnIndex]) {
      cell.classList.add("col-hidden");
    }
    row.appendChild(cell);
    cells[column.key] = cell;
  });

  row.dataset.layoutKey = layoutKey;
  row._cells = cells;
  row._signature = "";
  return cells;
}

function updateQueueRow(row, item, visibleIndex, showRowNumbers, hiddenColumns, layoutKey) {
  const cells = ensureQueueRowStructure(row, layoutKey, showRowNumbers, hiddenColumns);
  const statusDisplay = getQueueStatusDisplayText(item);
  const signature = `${item.game_name}\x1f${item.mod_id}\x1f${item.mod_name}\x1f${item.status}\x1f${item.retry_count}\x1f${item.max_retries}\x1f${item.provider}`;
  row.dataset.listIndex = String(visibleIndex);

  if (showRowNumbers && cells.row_number) {
    const rowNumber = String(visibleIndex + 1);
    if (cells.row_number.textContent !== rowNumber) {
      cells.row_number.textContent = rowNumber;
    }
  }

  if (row._signature !== signature) {
    QUEUE_COLUMNS.forEach((column, columnIndex) => {
      const cell = cells[column.key];
      if (!cell) {
        return;
      }
      const value = column.key === "status"
        ? statusDisplay
        : String(item[column.key] ?? "");
      if (cell.textContent !== value) {
        cell.textContent = value;
      }
      if (cell.title !== value) {
        cell.title = value;
      }
      cell.classList.toggle("col-hidden", !!hiddenColumns[columnIndex]);
    });
    row._signature = signature;
  } else {
    QUEUE_COLUMNS.forEach((column, columnIndex) => {
      const cell = cells[column.key];
      if (cell) {
        cell.classList.toggle("col-hidden", !!hiddenColumns[columnIndex]);
      }
    });
  }

  row.classList.toggle("selected", state.selectedModIds.has(String(item.mod_id)));
}

function pruneRowCacheToVisible(visibleIds) {
  for (const [modId, row] of state.rowCache.entries()) {
    if (!visibleIds.has(modId)) {
      if (row && row.parentNode) {
        row.parentNode.removeChild(row);
      }
      state.rowCache.delete(modId);
    }
  }
}

function getVirtualQueryPayload() {
  return {
    filterName: state.filter || "All",
    searchQuery: searchInput.value.trim(),
    regexEnabled: !!state.regex,
    caseSensitive: !!state.caseSensitive,
    sortKey: state.sort?.key || "",
    sortDirection: state.sort?.direction === "desc" ? "desc" : "asc"
  };
}

function getVirtualQueryKey(payload) {
  return [
    payload.filterName,
    payload.searchQuery,
    payload.regexEnabled ? "1" : "0",
    payload.caseSensitive ? "1" : "0",
    payload.sortKey,
    payload.sortDirection
  ].join("\x1f");
}

function resetVirtualBackendWindow() {
  virtualBackendTotal = 0;
  virtualBackendPageStart = 0;
  virtualBackendPageEnd = 0;
  virtualBackendPageItems = [];
  virtualBackendRegexErrorShownFor = "";
}

function getVirtualItemAt(index) {
  if (!virtualBackendEnabled) {
    return virtualItems[index] || null;
  }
  if (index < virtualBackendPageStart || index >= virtualBackendPageEnd) {
    return null;
  }
  return virtualBackendPageItems[index - virtualBackendPageStart] || null;
}

async function ensureBackendWindowLoaded(startIndex, endIndex, options = {}) {
  if (!state.apiAvailable || !virtualBackendEnabled) {
    return;
  }
  const forceReload = !!options.forceReload;

  const query = getVirtualQueryPayload();
  const queryKey = getVirtualQueryKey(query);
  const queryChanged = queryKey !== virtualBackendQueryKey;
  if (queryChanged) {
    virtualBackendQueryKey = queryKey;
    resetVirtualBackendWindow();
    lastVirtualStart = -1;
    lastVirtualEnd = -1;
  }

  const desiredStart = Math.max(0, startIndex - VIRTUAL_FETCH_BUFFER_ROWS);
  const rawLimit = (endIndex - startIndex) + (VIRTUAL_FETCH_BUFFER_ROWS * 2);
  const desiredLimit = Math.max(80, Math.min(VIRTUAL_FETCH_MAX_LIMIT, rawLimit));
  const coversWindow = desiredStart >= virtualBackendPageStart && (desiredStart + desiredLimit) <= virtualBackendPageEnd;
  if (!forceReload && !queryChanged && coversWindow) {
    return;
  }

  const fetchId = ++virtualBackendFetchId;
  virtualBackendLoading = true;

  try {
    const result = await callApi(
      "get_queue_page",
      query.filterName,
      query.searchQuery,
      query.regexEnabled,
      query.caseSensitive,
      query.sortKey,
      query.sortDirection,
      desiredStart,
      desiredLimit
    );

    if (fetchId !== virtualBackendFetchId) {
      return;
    }
    if (!result?.success) {
      return;
    }

    const total = Number(result.total || 0);
    const offset = Number(result.offset || 0);
    const items = Array.isArray(result.items) ? result.items : [];
    virtualBackendTotal = Math.max(0, total);
    virtualBackendPageStart = Math.max(0, offset);
    virtualBackendPageItems = items.map((item, idx) => normalizeQueueItem(item, virtualBackendPageStart + idx));
    virtualBackendPageEnd = virtualBackendPageStart + virtualBackendPageItems.length;

    if (result.stats && typeof result.stats === "object") {
      state.queueStats = {
        total: Number(result.stats.total || 0),
        queued: Number(result.stats.queued || 0),
        downloaded: Number(result.stats.downloaded || 0),
        failed: Number(result.stats.failed || 0),
        downloading: Number(result.stats.downloading || 0)
      };
    }

    if (result.regex_error) {
      if (virtualBackendRegexErrorShownFor !== queryKey) {
        addLog("Invalid regex pattern.", "bad");
        virtualBackendRegexErrorShownFor = queryKey;
      }
    } else {
      virtualBackendRegexErrorShownFor = "";
    }

    updateSearchPlaceholder();
    renderQueueViewport(true);
  } catch {
    // Ignore transient fetch failures; next refresh/scroll retries.
  } finally {
    if (fetchId === virtualBackendFetchId) {
      virtualBackendLoading = false;
    }
  }
}

function renderQueueViewport(force = false) {
  if (!queueTableWrap) {
    return;
  }

  const total = virtualBackendEnabled ? virtualBackendTotal : virtualItems.length;
  const viewportHeight = Math.max(0, queueTableWrap.clientHeight || 0);
  const scrollTop = Math.max(0, queueTableWrap.scrollTop || 0);
  const rowHeight = Math.max(18, Number(virtualRowHeight) || VIRTUAL_ROW_HEIGHT_FALLBACK);
  const rowsInView = Math.max(1, Math.ceil(viewportHeight / rowHeight));
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - VIRTUAL_OVERSCAN_ROWS);
  const endIndex = Math.min(total, startIndex + rowsInView + (VIRTUAL_OVERSCAN_ROWS * 2));

  if (virtualBackendEnabled) {
    void ensureBackendWindowLoaded(startIndex, endIndex);
  }

  if (!force && startIndex === lastVirtualStart && endIndex === lastVirtualEnd) {
    return;
  }
  lastVirtualStart = startIndex;
  lastVirtualEnd = endIndex;

  const visibleIds = new Set();
  const fragment = document.createDocumentFragment();
  const colSpan = QUEUE_COLUMNS.length + (virtualShowRowNumbers ? 1 : 0);

  const topSpacerHeight = Math.max(0, startIndex * rowHeight);
  const bottomSpacerHeight = Math.max(0, (total - endIndex) * rowHeight);
  const topSpacer = createSpacerRow("virtual-spacer-row top", colSpan);
  const bottomSpacer = createSpacerRow("virtual-spacer-row bottom", colSpan);
  topSpacer.firstElementChild.style.height = `${topSpacerHeight}px`;
  bottomSpacer.firstElementChild.style.height = `${bottomSpacerHeight}px`;
  fragment.appendChild(topSpacer);

  for (let i = startIndex; i < endIndex; i += 1) {
    const item = getVirtualItemAt(i);
    if (!item) {
      continue;
    }
    const modId = String(item.mod_id);
    visibleIds.add(modId);
    let row = state.rowCache.get(modId);
    if (!row) {
      row = createQueueRow(modId);
      state.rowCache.set(modId, row);
    }
    updateQueueRow(row, item, i, virtualShowRowNumbers, virtualHiddenColumns, virtualLayoutKey);
    fragment.appendChild(row);
  }

  fragment.appendChild(bottomSpacer);
  queueBody.replaceChildren(fragment);
  pruneRowCacheToVisible(visibleIds);

  const sampleRow = queueBody.querySelector("tr[data-mod-id]");
  if (sampleRow) {
    const measured = Math.ceil(sampleRow.getBoundingClientRect().height || 0);
    if (measured >= 16 && Math.abs(measured - virtualRowHeight) >= 1) {
      virtualRowHeight = measured;
      lastVirtualStart = -1;
      lastVirtualEnd = -1;
      renderQueueViewport(true);
    }
  }
}

function renderQueue() {
  applyQueueColumnWidths();
  renderQueueHeader();

  virtualHiddenColumns = getQueueColumnHidden();
  virtualShowRowNumbers = !!state.config?.show_row_numbers;
  virtualLayoutKey = buildQueueLayoutKey(virtualShowRowNumbers, virtualHiddenColumns);
  virtualBackendEnabled = !!state.apiAvailable;
  if (virtualBackendEnabled) {
    virtualItems = [];
  } else {
    virtualItems = getSortedQueue(getFilteredQueue());
    virtualBackendTotal = virtualItems.length;
  }
  lastVirtualStart = -1;
  lastVirtualEnd = -1;
  renderQueueViewport(true);
  updateSearchPlaceholder();
}

function wireQueueVirtualization() {
  if (!queueTableWrap) {
    return;
  }
  queueTableWrap.addEventListener("mousedown", (event) => {
    if (event.button !== 0) {
      return;
    }
    if (event.target.closest("tr[data-mod-id]")) {
      return;
    }
    if (!state.selectedModIds.size) {
      return;
    }
    state.selectedModIds.clear();
    state.selectionAnchorIndex = null;
    state.selectionAnchorModId = "";
    renderQueueViewport(true);
  });
  queueTableWrap.addEventListener("scroll", () => {
    if (virtualScrollQueued) {
      return;
    }
    virtualScrollQueued = true;
    window.requestAnimationFrame(() => {
      virtualScrollQueued = false;
      renderQueueViewport(false);
    });
  });
  window.addEventListener("resize", () => {
    renderQueueViewport(true);
  });
}

function wireQueueRowInteractions() {
  if (!queueBody) {
    return;
  }

  queueBody.addEventListener("mousedown", (event) => {
    if (event.button !== 0) {
      return;
    }
    const row = event.target.closest("tr[data-mod-id]");
    if (!row || !queueBody.contains(row)) {
      return;
    }
    event.preventDefault();
    hideHeaderContextMenu();
    hideQueueContextMenu();
    void handleRowClick(event, row).catch((error) => {
      addLog(error?.message || "Failed to select queue item.", "bad");
    });
  });

  queueBody.addEventListener("dblclick", (event) => {
    const row = event.target.closest("tr[data-mod-id]");
    if (!row || !queueBody.contains(row)) {
      return;
    }
    const modId = String(row.dataset.modId || "");
    if (!modId) {
      return;
    }
    event.preventDefault();
    void callApi("open_downloads_folder", modId)
      .then((result) => {
        if (result?.success) {
          addLog(`Opened Downloads folder for ${modId}.`, "good");
        } else {
          addLog(result?.error || "Failed to open Downloads folder.", "bad");
        }
      })
      .catch(() => {
        addLog("Open Downloads Folder is only available from desktop app.", "bad");
      });
  });

  queueBody.addEventListener("contextmenu", (event) => {
    const row = event.target.closest("tr[data-mod-id]");
    if (!row || !queueBody.contains(row)) {
      return;
    }
    event.preventDefault();

    const modId = String(row.dataset.modId || "");
    const rowIndex = Number.parseInt(String(row.dataset.listIndex || "-1"), 10);
    if (!modId) {
      return;
    }

    if (!state.selectedModIds.has(modId)) {
      state.selectedModIds.clear();
      state.selectedModIds.add(modId);
    }

    if (Number.isInteger(rowIndex) && rowIndex >= 0) {
      state.selectionAnchorIndex = rowIndex;
      state.selectionAnchorModId = modId;
    }

    renderQueueViewport(true);
    showQueueContextMenu(event.clientX, event.clientY);
  });
}

function wireGlobalShortcuts() {
  document.addEventListener("keydown", (event) => {
    const rawKey = String(event.key || "");
    const key = rawKey.toLowerCase();
    const hasModifier = event.ctrlKey || event.metaKey;

    if (key !== "shift") {
      lastShiftTapAt = 0;
    }

    if (key === "escape" && isCommandPaletteOpen()) {
      event.preventDefault();
      closeCommandPalette();
      return;
    }

    if (hasModifier && !event.altKey && key === "k") {
      event.preventDefault();
      if (isCommandPaletteOpen()) {
        closeCommandPalette({ restoreFocus: false });
      } else {
        openCommandPalette();
      }
      return;
    }

    if (isCommandPaletteOpen() && commandPaletteInput && event.target !== commandPaletteInput) {
      if (hasModifier && !event.altKey && key === "a") {
        event.preventDefault();
        focusCommandPaletteInput({ selectAll: true });
        return;
      }
      if (!hasModifier && !event.altKey) {
        if (key === "arrowdown") {
          event.preventDefault();
          setCommandPaletteSelection(commandPaletteSelectedIndex + 1);
          focusCommandPaletteInput();
          return;
        }
        if (key === "arrowup") {
          event.preventDefault();
          setCommandPaletteSelection(commandPaletteSelectedIndex - 1);
          focusCommandPaletteInput();
          return;
        }
        if (key === "enter") {
          event.preventDefault();
          executeCommandPaletteAction(commandPaletteSelectedIndex);
          return;
        }
        if (applyCommandPaletteInputKey(rawKey)) {
          event.preventDefault();
          focusCommandPaletteInput();
          return;
        }
      }
    }

    if (!hasModifier || event.altKey) {
      return;
    }
    if (key !== "a") {
      return;
    }
    if (event.repeat) {
      return;
    }
    if (modalOverlay && !modalOverlay.classList.contains("hidden")) {
      return;
    }
    if (isTextEditingTarget(event.target)) {
      return;
    }

    event.preventDefault();
    void selectAllQueueItems().catch((error) => {
      addLog(error?.message || "Failed to select all queue entries.", "bad");
    });
  });

  document.addEventListener("keyup", (event) => {
    const key = String(event.key || "").toLowerCase();
    if (key !== "shift") {
      return;
    }
    if (event.repeat || event.altKey || event.ctrlKey || event.metaKey) {
      lastShiftTapAt = 0;
      return;
    }

    const now = Date.now();
    if (lastShiftTapAt && now - lastShiftTapAt <= DOUBLE_SHIFT_WINDOW_MS) {
      lastShiftTapAt = 0;
      if (!isCommandPaletteOpen()) {
        openCommandPalette();
      } else {
        focusCommandPaletteInput({ selectAll: true });
      }
      return;
    }

    lastShiftTapAt = now;
  });
}

function hideQueueContextMenu() {
  queueContextMenu.classList.add("hidden");
  queueContextMenu.classList.remove("submenu-open-left");
}

function hideLogsContextMenu() {
  if (!logsContextMenu) {
    return;
  }
  logsContextMenu.classList.add("hidden");
  logsContextMenu.classList.remove("submenu-open-left");
  logsContextMenu.classList.remove("submenu-open-up");
}

function measureFloatingElement(element) {
  if (!element) {
    return { width: 0, height: 0 };
  }
  const previousDisplay = element.style.display;
  const previousVisibility = element.style.visibility;
  const previousLeft = element.style.left;
  const previousTop = element.style.top;

  const computedDisplay = window.getComputedStyle(element).display;
  if (computedDisplay === "none") {
    element.style.display = "block";
  }
  element.style.visibility = "hidden";
  element.style.left = "-10000px";
  element.style.top = "-10000px";

  const rect = element.getBoundingClientRect();

  element.style.display = previousDisplay;
  element.style.visibility = previousVisibility;
  element.style.left = previousLeft;
  element.style.top = previousTop;
  return {
    width: Math.ceil(rect.width || 0),
    height: Math.ceil(rect.height || 0)
  };
}

function positionFloatingMenu(menuEl, clientX, clientY, margin = 8) {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const measured = measureFloatingElement(menuEl);
  const menuWidth = Math.max(120, measured.width || 0);
  const menuHeight = Math.max(40, measured.height || 0);

  const maxLeft = Math.max(margin, viewportWidth - menuWidth - margin);
  const maxTop = Math.max(margin, viewportHeight - menuHeight - margin);
  const left = Math.max(margin, Math.min(clientX, maxLeft));
  const top = Math.max(margin, Math.min(clientY, maxTop));

  menuEl.style.left = `${left}px`;
  menuEl.style.top = `${top}px`;
  return { left, top, menuWidth, menuHeight, viewportWidth, viewportHeight };
}

function showQueueContextMenu(clientX, clientY) {
  if (!state.selectedModIds.size) {
    return;
  }
  hideHeaderContextMenu();
  hideLogsContextMenu();
  const margin = 8;

  const placement = positionFloatingMenu(queueContextMenu, clientX, clientY, margin);
  queueContextMenu.classList.remove("hidden");

  const subPopup = queueContextMenu.querySelector(".queue-context-subpopup");
  const subSize = measureFloatingElement(subPopup);
  const subWidth = Math.max(120, subSize.width || 0);
  const availableRight = Math.max(0, placement.viewportWidth - (placement.left + placement.menuWidth) - margin);
  const availableLeft = Math.max(0, placement.left - margin);

  const rightFits = availableRight >= subWidth;
  const leftFits = availableLeft >= subWidth;

  let openLeft = false;
  if (rightFits) {
    openLeft = false;
  } else if (leftFits) {
    openLeft = true;
  } else {
    openLeft = availableLeft > availableRight;
  }

  const needsFlipLeft = !!openLeft;
  queueContextMenu.classList.toggle("submenu-open-left", needsFlipLeft);
}

function showLogsContextMenu(clientX, clientY) {
  if (!logsContextMenu) {
    return;
  }
  hideQueueContextMenu();
  hideHeaderContextMenu();
  updateLogsContextMenuSelection();
  const margin = 8;
  const placement = positionFloatingMenu(logsContextMenu, clientX, clientY, margin);
  logsContextMenu.classList.remove("hidden");

  const subPopup = logsContextMenu.querySelector(".queue-context-subpopup");
  const subSize = measureFloatingElement(subPopup);
  const subWidth = Math.max(120, subSize.width || 0);
  const availableRight = Math.max(0, placement.viewportWidth - (placement.left + placement.menuWidth) - 8);
  const availableLeft = Math.max(0, placement.left - 8);
  const rightFits = availableRight >= subWidth;
  const leftFits = availableLeft >= subWidth;
  const availableBelow = Math.max(0, placement.viewportHeight - placement.top - margin);
  const availableAbove = Math.max(0, placement.top - margin);
  const subHeight = Math.max(40, subSize.height || 0);
  const openUp = subHeight > availableBelow && availableAbove > availableBelow;

  let openLeft = false;
  if (rightFits) {
    openLeft = false;
  } else if (leftFits) {
    openLeft = true;
  } else {
    openLeft = availableLeft > availableRight;
  }

  logsContextMenu.classList.toggle("submenu-open-left", !!openLeft);
  logsContextMenu.classList.toggle("submenu-open-up", !!openUp);
  if (subPopup) {
    const availableForPopup = openUp ? availableAbove : availableBelow;
    const maxPopupHeight = Math.max(120, Math.min(availableForPopup, placement.viewportHeight - (margin * 2)));
    subPopup.style.maxHeight = `${Math.floor(maxPopupHeight)}px`;
  }
}

function updateLogsContextMenuSelection() {
  if (!logsContextMenu) {
    return;
  }
  const selected = getCurrentLogCategoryFilter();
  logsContextMenu.querySelectorAll(".queue-context-item[data-log-category]").forEach((button) => {
    const category = normalizeLogCategoryFilter(button.dataset.logCategory || "");
    button.classList.toggle("active", category === selected);
  });
}

async function setLogCategoryFilter(category, options = {}) {
  const nextCategory = normalizeLogCategoryFilter(category);
  const currentCategory = getCurrentLogCategoryFilter();
  if (!state.config || typeof state.config !== "object") {
    state.config = {};
  }
  state.config.log_category_filter = nextCategory;
  scheduleLogTimelineRender({ preserveScroll: true });
  updateLogsContextMenuSelection();

  const shouldPersist = options.persist !== false;
  if (!shouldPersist || !state.apiAvailable || nextCategory === currentCategory) {
    return true;
  }

  try {
    const result = await callApi("update_settings", { log_category_filter: nextCategory });
    if (!result?.success) {
      addLog(result?.error || "Failed to update log category filter.", "bad");
      return false;
    }
    state.config = result.config || { ...state.config, log_category_filter: nextCategory };
    updateLogsContextMenuSelection();
    return true;
  } catch {
    addLog("Failed to update log category filter.", "bad");
    return false;
  }
}

async function handleLogsContextAction(action, logCategory = "") {
  if (action === "set_log_category") {
    await setLogCategoryFilter(logCategory, { persist: true });
    return;
  }
  if (action === "clear_logs") {
    try {
      const result = await callApi("clear_logs");
      if (!result?.success) {
        addLog(result?.error || "Failed to clear log view.", "bad");
        return;
      }
      suppressNextBackendClearEvent = true;
    } catch {
      // In non-desktop preview mode, still clear local log view.
    }
    clearLogTimeline();
  }
}

async function handleQueueContextAction(action) {
  const selected = Array.from(state.selectedModIds);
  if (!selected.length) {
    return;
  }

  if (action === "remove") {
    const confirmed = await showConfirmDialog({
      title: "Remove Mods",
      message: `Remove ${selected.length} selected mod(s) from queue?`,
      okLabel: "Remove",
      cancelLabel: "Cancel"
    });
    if (!confirmed) {
      return;
    }
    const result = await callApi("remove_mods", selected);
    if (result?.success) {
      addLog(`Removed ${result.removed || 0} mod(s) from queue.`);
      state.selectedModIds.clear();
      await refreshQueue({ forceReload: true });
    } else {
      addLog(result?.error || "Failed to remove selected mods.", "bad");
    }
    return;
  }

  if (action === "move_top" || action === "move_up" || action === "move_down" || action === "move_bottom") {
    const direction = action.replace("move_", "");
    const result = await callApi("move_mods", selected, direction);
    if (result?.success) {
      await refreshQueue({ forceReload: true });
    } else {
      addLog(result?.error || "Failed to move selected mods.", "bad");
    }
    return;
  }

  if (action === "provider_default" || action === "provider_steamcmd" || action === "provider_webapi") {
    const providerMap = {
      provider_default: "Default",
      provider_steamcmd: "SteamCMD",
      provider_webapi: "SteamWebAPI"
    };
    const provider = providerMap[action];
    const result = await callApi("change_provider_for_mods", selected, provider);
    if (result?.success) {
      addLog(`Provider changed for ${result.changed || 0} mod(s).`);
      await refreshQueue({ forceReload: true });
    } else {
      addLog(result?.error || "Failed to change provider.", "bad");
    }
    return;
  }

  if (action === "reset_status") {
    const result = await callApi("reset_status", selected);
    if (result?.success) {
      addLog(`Reset status for ${result.reset || 0} mod(s).`);
      await refreshQueue({ forceReload: true });
    } else {
      addLog(result?.error || "Failed to reset status.", "bad");
    }
    return;
  }

  if (action === "override_appid") {
    const appIdInput = await showInputModal({
      title: "Override AppID",
      message: "Enter AppID or app URL to apply to selected mods.",
      defaultValue: "",
      rows: 3,
      okLabel: "Apply"
    });
    if (!appIdInput) {
      return;
    }
    const result = await callApi("override_appid", selected, appIdInput);
    if (result?.success) {
      addLog(`Overrode AppID for ${result.changed || 0} mod(s) -> ${result.app_id} (${result.game_name}).`);
      await refreshQueue({ forceReload: true });
    } else {
      addLog(result?.error || "Failed to override AppID.", "bad");
    }
  }
}

function setFilter(filterName) {
  state.filter = filterName;
  document.querySelectorAll(".filter-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.filter === filterName);
  });
  filterPopup.classList.add("hidden");
  scheduleSearchRender();
}

function scheduleQueueRefresh(forceReload = false) {
  if (forceReload) {
    queueRefreshForceReload = true;
  }
  if (queueRefreshTimer) {
    return;
  }
  queueRefreshTimer = window.setTimeout(async () => {
    const shouldForceReload = queueRefreshForceReload;
    queueRefreshForceReload = false;
    queueRefreshTimer = null;
    await refreshQueue({ forceReload: shouldForceReload });
  }, 320);
}

async function refreshQueue(options = {}) {
  if (state.apiAvailable) {
    const forceReload = !!options.forceReload;
    const rowHeight = Math.max(18, Number(virtualRowHeight) || VIRTUAL_ROW_HEIGHT_FALLBACK);
    const viewportHeight = Math.max(0, queueTableWrap?.clientHeight || 0);
    const scrollTop = Math.max(0, queueTableWrap?.scrollTop || 0);
    const rowsInView = Math.max(1, Math.ceil(viewportHeight / rowHeight));
    const currentStart = Math.max(0, Math.floor(scrollTop / rowHeight) - VIRTUAL_OVERSCAN_ROWS);
    const currentEnd = Math.max(currentStart + 1, currentStart + rowsInView + (VIRTUAL_OVERSCAN_ROWS * 2));

    await ensureBackendWindowLoaded(currentStart, currentEnd, { forceReload });
    lastVirtualStart = -1;
    lastVirtualEnd = -1;
    renderQueueViewport(true);
    return;
  }

  try {
    const queueItems = await callApi("get_queue");
    state.queue = (queueItems || []).map(normalizeQueueItem);
  } catch {
    try {
      const queueItems = await callApi("get_preview_queue");
      state.queue = (queueItems || []).map(normalizeQueueItem);
    } catch {
      state.queue = browserQueue.map(normalizeQueueItem);
    }
  }

  recomputeQueueStats();
  const currentIds = new Set(state.queue.map((item) => String(item.mod_id)));
  state.selectedModIds.forEach((id) => {
    if (!currentIds.has(id)) {
      state.selectedModIds.delete(id);
    }
  });

  renderQueue();
}

function applyTheme(themeName) {
  const lower = String(themeName || "").toLowerCase();
  document.body.classList.remove("theme-dark", "theme-light");
  if (lower.includes("light")) {
    document.body.classList.add("theme-light");
  } else {
    document.body.classList.add("theme-dark");
  }
}

function normalizeHexColor(value) {
  const text = String(value || "").trim();
  if (/^#[0-9a-fA-F]{6}$/.test(text)) {
    return text.toLowerCase();
  }
  return "";
}

function applyModalTextColor(colorValue) {
  const color = normalizeHexColor(colorValue);
  if (color) {
    document.body.style.setProperty("--modal-text-color", color);
  } else {
    document.body.style.removeProperty("--modal-text-color");
  }
}

function syncLogoStyle() {
  const style = String(state.config.logo_style || "Light");
  let logoPath = "../logo.png";
  if (style === "Dark") {
    logoPath = "../logo_dark.png";
  } else if (style === "Darker") {
    logoPath = "../logo_darker.png";
  }
  if (titlebarLogo) {
    titlebarLogo.src = logoPath;
  }
}

function applyVisibilityConfig(config) {
  searchRow.style.display = config.show_searchbar === false ? "none" : "";
  logWrap.style.display = config.show_logs === false ? "none" : "";
  providerWrap.style.display = config.show_provider === false ? "none" : "";
  regexBtn.style.display = "";
  caseBtn.style.display = "";
  commandPaletteBtn.style.display = "";
  settingsCommandShell?.classList.remove("commands-toggle-hidden");
  const showDownloadButton = config.download_button !== false;
  downloadNowBtn.style.display = showDownloadButton ? "" : "none";
  inputRowActions?.classList.toggle("download-hidden", !showDownloadButton);
  const showImportExport = config.show_export_import_buttons !== false;
  importExportWrap.style.display = showImportExport ? "" : "none";
  importExportSpacer.style.display = showImportExport ? "" : "none";
  applyQueueColumnWidths();
  renderQueueHeader();
}

function syncWindowTitle() {
  const versionPart = state.version ? ` v${state.version}` : "";
  document.title = `Streamline${versionPart}`;
}

async function refreshAccounts(activeFromConfig = "") {
  try {
    const data = await callApi("get_accounts");
    const accounts = data?.accounts || [];
    const active = data?.active || activeFromConfig || "Anonymous";
    accountSelect.innerHTML = "";
    const anonymousOption = document.createElement("option");
    anonymousOption.value = "Anonymous";
    anonymousOption.textContent = "Anonymous";
    anonymousOption.dataset.avatarUrl = "../anonymous.svg";
    accountSelect.appendChild(anonymousOption);
    accounts.forEach((acc) => {
      if (!acc?.username) {
        return;
      }
      const option = document.createElement("option");
      option.value = acc.username;
      option.textContent = acc.username;
      option.dataset.avatarUrl = String(acc.avatar_url || "").trim();
      accountSelect.appendChild(option);
    });
    accountSelect.value = active;
  } catch {
    const active = activeFromConfig || "Anonymous";
    if (!Array.from(accountSelect.options).some((x) => x.value === active)) {
      const option = document.createElement("option");
      option.value = active;
      option.textContent = active;
      option.dataset.avatarUrl = active === "Anonymous" ? "../anonymous.svg" : "";
      accountSelect.appendChild(option);
    }
    accountSelect.value = active;
  }
  syncAnimatedSelect("account-select");
}

async function useBootstrapData(data) {
  const config = data?.config || {};
  state.config = config;
  state.version = String(data?.version || "");
  state.queue = (data?.queue || []).map(normalizeQueueItem);
  const stats = data?.queue_stats;
  if (stats && typeof stats === "object") {
    state.queueStats = {
      total: Number(stats.total || 0),
      queued: Number(stats.queued || 0),
      downloaded: Number(stats.downloaded || 0),
      failed: Number(stats.failed || 0),
      downloading: Number(stats.downloading || 0)
    };
  } else {
    recomputeQueueStats();
  }
  resetVirtualBackendWindow();
  state.isDownloading = !!data?.download_state?.is_downloading;
  state.cancelPending = false;
  syncStartButton();

  applyTheme(config.current_theme || "Dark");
  applyModalTextColor(config.modal_text_color);
  applyVisibilityConfig(config);
  syncLogoStyle();
  syncWindowTitle();
  updateLogsContextMenuSelection();
  scheduleLogTimelineRender({ preserveScroll: true });

  setProviderValue(config.download_provider);

  await refreshAccounts(config.active_account || "Anonymous");

  if (data?.warning) {
    addLog(data.warning, "bad");
  }
  renderQueue();

  const showTutorialOnStartup = config.show_tutorial_on_startup !== false;
  const tutorialWasShownBefore = !!config.tutorial_shown;
  if (!state.tutorialStartupHandled && (!tutorialWasShownBefore || showTutorialOnStartup)) {
    state.tutorialStartupHandled = true;
    window.setTimeout(() => {
      openTutorialDialog({ fromStartup: true });
    }, 350);
  }
}

function createBrowserQueueItem(url, provider) {
  const modId = parseModId(url);
  return {
    game_name: "Unknown",
    mod_id: modId === "N/A" ? String(browserQueue.length + 1) : modId,
    mod_name: url,
    url,
    status: "Queued",
    provider: provider || "Default"
  };
}

function wireQueueContextMenu() {
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".queue-context-menu")) {
      hideQueueContextMenu();
    }
  });

  document.addEventListener("scroll", () => hideQueueContextMenu(), true);
  window.addEventListener("resize", () => hideQueueContextMenu());

  queueContextMenu.querySelectorAll(".queue-context-item").forEach((button) => {
    button.addEventListener("click", async () => {
      hideQueueContextMenu();
      try {
        await handleQueueContextAction(button.dataset.action);
      } catch (error) {
        addLog(error.message || "Queue action failed.", "bad");
      }
    });
  });
}

function wireLogsContextMenu() {
  if (!logWrap || !logsContextMenu) {
    return;
  }

  logWrap.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    showLogsContextMenu(event.clientX, event.clientY);
  });

  logsContextMenu.querySelectorAll(".queue-context-item").forEach((button) => {
    button.addEventListener("click", async () => {
      hideLogsContextMenu();
      try {
        await handleLogsContextAction(button.dataset.action, button.dataset.logCategory || "");
      } catch (error) {
        addLog(error?.message || "Log action failed.", "bad");
      }
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("#logs-context-menu")) {
      hideLogsContextMenu();
    }
  });

  document.addEventListener("scroll", () => hideLogsContextMenu(), true);
  window.addEventListener("resize", () => hideLogsContextMenu());
}

function wireLogToolbar() {
  logCopyBtn?.addEventListener("click", async () => {
    const text = buildLogClipboardText();
    if (!text) {
      return;
    }
    const ok = await copyTextToClipboard(text);
    if (!ok) {
      addLog("Failed to copy logs.", "bad", { source: "ui", action: "copy_logs" });
    }
  });

  logClearBtn?.addEventListener("click", async () => {
    hideLogsContextMenu();
    try {
      await handleLogsContextAction("clear_logs");
    } catch (error) {
      addLog(error?.message || "Log action failed.", "bad");
    }
  });
}

function hideHeaderContextMenu() {
  headerContextMenu?.classList.add("hidden");
}

function buildHeaderContextMenuHtml() {
  const locked = isHeaderLocked();
  const showRowNumbers = !!state.config?.show_row_numbers;
  const hiddenColumns = getQueueColumnHidden();

  const columnItems = QUEUE_COLUMNS.map((column, index) => {
    const checked = !hiddenColumns[index] ? "✓ " : "";
    return `
      <button
        class="header-context-item${locked ? " disabled" : ""}"
        type="button"
        data-header-action="toggle_column"
        data-col-index="${index}"
        ${locked ? "disabled" : ""}
      >${checked}${escapeHtml(column.label)}</button>
    `;
  }).join("");

  return `
    <button class="header-context-item" type="button" data-header-action="toggle_lock">${locked ? "Unlock Header" : "Lock Header"}</button>
    <button class="header-context-item${locked ? " disabled" : ""}" type="button" data-header-action="toggle_row_numbers" ${locked ? "disabled" : ""}>${showRowNumbers ? "Hide Row Numbers" : "Show Row Numbers"}</button>
    <div class="header-context-sep"></div>
    ${columnItems}
    <div class="header-context-sep"></div>
    <button class="header-context-item${locked ? " disabled" : ""}" type="button" data-header-action="reset_layout" ${locked ? "disabled" : ""}>Reset Header Layout</button>
  `;
}

async function applyHeaderLayoutPatch(patch, successMessage) {
  const result = await callApi("update_settings", patch);
  if (!result?.success) {
    addLog(result?.error || "Failed to update header layout.", "bad");
    return false;
  }

  state.config = result.config || state.config;
  applyVisibilityConfig(state.config);
  syncLogoStyle();
  syncWindowTitle();
  renderQueue();
  if (successMessage) {
    addLog(successMessage, "good");
  }
  return true;
}

async function handleHeaderContextAction(button) {
  const action = button?.dataset?.headerAction;
  if (!action) {
    return;
  }

  if (action === "toggle_lock") {
    const nextLocked = !isHeaderLocked();
    if (await applyHeaderLayoutPatch({ header_locked: nextLocked }, `Header ${nextLocked ? "locked" : "unlocked"}.`)) {
      headerContextMenu.innerHTML = buildHeaderContextMenuHtml();
    }
    return;
  }

  if (isHeaderLocked()) {
    return;
  }

  if (action === "toggle_row_numbers") {
    const nextValue = !Boolean(state.config?.show_row_numbers);
    if (await applyHeaderLayoutPatch({ show_row_numbers: nextValue }, `Row numbers ${nextValue ? "enabled" : "disabled"}.`)) {
      headerContextMenu.innerHTML = buildHeaderContextMenuHtml();
    }
    return;
  }

  if (action === "toggle_column") {
    const colIndex = Number(button.dataset.colIndex);
    if (!Number.isInteger(colIndex) || colIndex < 0 || colIndex >= QUEUE_COLUMNS.length) {
      return;
    }
    const hiddenColumns = getQueueColumnHidden();
    hiddenColumns[colIndex] = !hiddenColumns[colIndex];
    if (await applyHeaderLayoutPatch({ queue_tree_column_hidden: hiddenColumns }, `${QUEUE_COLUMNS[colIndex].label} column ${hiddenColumns[colIndex] ? "hidden" : "shown"}.`)) {
      headerContextMenu.innerHTML = buildHeaderContextMenuHtml();
    }
    return;
  }

  if (action === "reset_layout") {
    const defaults = getDefaultQueueColumnWidths();
    if (await applyHeaderLayoutPatch({
      show_row_numbers: SETTINGS_DEFAULTS.show_row_numbers,
      queue_tree_column_hidden: QUEUE_COLUMNS.map(() => false),
      queue_tree_column_widths: defaults
    }, "Header layout reset to defaults.")) {
      headerContextMenu.innerHTML = buildHeaderContextMenuHtml();
    }
  }
}

function showHeaderContextMenu(clientX, clientY) {
  if (!headerContextMenu) {
    return;
  }
  hideQueueContextMenu();
  hideLogsContextMenu();
  headerContextMenu.innerHTML = buildHeaderContextMenuHtml();
  positionFloatingMenu(headerContextMenu, clientX, clientY, 8);
  headerContextMenu.classList.remove("hidden");
}

function wireHeaderContextMenu() {
  if (!queueHeadRow || !headerContextMenu) {
    return;
  }

  queueHeadRow.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    showHeaderContextMenu(event.clientX, event.clientY);
  });

  queueHeadRow.addEventListener("mousedown", (event) => {
    const handle = event.target.closest(".col-resizer");
    if (!handle) {
      return;
    }
    const colIndex = Number(handle.dataset.colIndex);
    startColumnResize(event, colIndex);
  });

  queueHeadRow.addEventListener("click", (event) => {
    if (event.target.closest(".col-resizer")) {
      return;
    }
    const header = event.target.closest("th[data-col-key]");
    if (!header) {
      return;
    }
    const columnKey = String(header.dataset.colKey || "");
    if (!columnKey || columnKey === "row_number") {
      return;
    }
    applyQueueSort(columnKey);
  });

  headerContextMenu.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-header-action]");
    if (!button) {
      return;
    }
    try {
      await handleHeaderContextAction(button);
    } catch (error) {
      addLog(error?.message || "Header action failed.", "bad");
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".header-context-menu")) {
      hideHeaderContextMenu();
    }
  });

  document.addEventListener("scroll", () => hideHeaderContextMenu(), true);
  window.addEventListener("resize", () => hideHeaderContextMenu());
}

function buildSettingsFormHtml(settings) {
  const switchRow = (id, checked, label) => `
    <label class="form-checkbox-row form-switch-row">
      <input id="${id}" type="checkbox" ${checked ? "checked" : ""}>
      <span class="form-switch-track" aria-hidden="true"></span>
      <span class="form-switch-label">${label}</span>
    </label>
  `;
  return `
    <div class="settings-shell">
      <div class="settings-nav">
        <button class="settings-nav-item active" type="button" data-settings-page-btn="appearance">
          <span class="settings-nav-icon settings-nav-icon-appearance" aria-hidden="true"></span>
          <span class="settings-nav-label">Appearance</span>
        </button>
        <button class="settings-nav-item" type="button" data-settings-page-btn="download">
          <span class="settings-nav-icon settings-nav-icon-download" aria-hidden="true"></span>
          <span class="settings-nav-label">Download Options</span>
        </button>
        <button class="settings-nav-item" type="button" data-settings-page-btn="tools">
          <span class="settings-nav-icon settings-nav-icon-tools" aria-hidden="true"></span>
          <span class="settings-nav-label">Tools</span>
        </button>
        <button class="settings-nav-item" type="button" data-settings-page-btn="system">
          <span class="settings-nav-icon settings-nav-icon-system" aria-hidden="true"></span>
          <span class="settings-nav-label">System</span>
        </button>
        <div class="settings-nav-spacer"></div>
        <button id="st-reset-defaults" class="control settings-reset-btn" type="button">Reset to Defaults</button>
      </div>

      <div class="settings-page-wrap">
        <section class="settings-page active" data-settings-page="appearance">
          <div class="form-grid">
            <div class="form-block">
              <label for="st-theme">Theme</label>
              <div class="select-chevron-wrap">
                <select id="st-theme" class="form-control">
                  <option value="Dark" ${settings.current_theme === "Dark" ? "selected" : ""}>Dark</option>
                  <option value="Light" ${settings.current_theme === "Light" ? "selected" : ""}>Light</option>
                </select>
              </div>
            </div>
            <div class="form-block">
              <label for="st-logo">Logo Style</label>
              <div class="select-chevron-wrap">
                <select id="st-logo" class="form-control">
                  <option value="Light" ${settings.logo_style === "Light" ? "selected" : ""}>Light</option>
                  <option value="Dark" ${settings.logo_style === "Dark" ? "selected" : ""}>Dark</option>
                  <option value="Darker" ${settings.logo_style === "Darker" ? "selected" : ""}>Darker</option>
                </select>
              </div>
            </div>
          </div>
          <div class="form-divider"></div>
          <div class="settings-section-subtitle">Show</div>
          <div class="form-grid">
            ${switchRow("st-download-btn", settings.download_button, "Download Button")}
            ${switchRow("st-search-bar", settings.show_searchbar, "Search Bar")}
            ${switchRow("st-import-export", settings.show_export_import_buttons, "Import/Export Buttons")}
            ${switchRow("st-logs", settings.show_logs, "Logs View")}
            ${switchRow("st-provider-show", settings.show_provider, "Download Provider")}
          </div>
        </section>

        <section class="settings-page" data-settings-page="download">
          <div class="form-grid">
            <div class="form-block">
              <label for="st-provider">Default Provider</label>
              <div class="select-chevron-wrap">
                <select id="st-provider" class="form-control">
                  <option value="Default" ${settings.download_provider === "Default" ? "selected" : ""}>Default</option>
                  <option value="SteamCMD" ${settings.download_provider === "SteamCMD" ? "selected" : ""}>SteamCMD</option>
                  <option value="SteamWebAPI" ${settings.download_provider === "SteamWebAPI" ? "selected" : ""}>SteamWebAPI</option>
                </select>
              </div>
            </div>
            <div class="form-block">
              <label for="st-batch" class="settings-inline-note-host">Batch Size <span class="settings-inline-note">&lt;50 Recommended</span></label>
              <input id="st-batch" class="form-control" type="number" min="1" max="500" value="${Number(settings.batch_size || 20)}">
            </div>
            <div class="form-block" style="grid-column: 1 / -1;">
              <label for="st-existing">SteamCMD Existing Mods</label>
              <div class="select-chevron-wrap">
                <select id="st-existing" class="form-control">
                  <option value="Only Redownload if Updated" ${settings.steamcmd_existing_mod_behavior === "Only Redownload if Updated" ? "selected" : ""}>Only Redownload if Updated</option>
                  <option value="Always Redownload" ${settings.steamcmd_existing_mod_behavior === "Always Redownload" ? "selected" : ""}>Always Redownload</option>
                  <option value="Skip Existing Mods" ${settings.steamcmd_existing_mod_behavior === "Skip Existing Mods" ? "selected" : ""}>Skip Existing Mods</option>
                </select>
              </div>
            </div>
            <div class="form-block">
              <label for="st-folder-format">SteamCMD Folder Naming</label>
              <div class="select-chevron-wrap">
                <select id="st-folder-format" class="form-control">
                  <option value="id" ${settings.folder_naming_format === "id" ? "selected" : ""}>Mod ID</option>
                  <option value="name" ${settings.folder_naming_format === "name" ? "selected" : ""}>Mod Name</option>
                  <option value="combined" ${settings.folder_naming_format === "combined" ? "selected" : ""}>ID + Name</option>
                </select>
              </div>
            </div>
          </div>
          <div class="form-divider"></div>
          <div class="form-grid">
            ${switchRow("st-queue-workshop", settings.show_queue_entire_workshop !== false, "Allow Queue Entire Workshop")}
            ${switchRow("st-keep-downloaded", settings.keep_downloaded_in_queue, "Keep Downloaded In Queue")}
            ${switchRow("st-delete-on-cancel", settings.delete_downloads_on_cancel, "Delete Downloads On Cancel")}
          </div>
        </section>

        <section class="settings-page" data-settings-page="tools">
          <div class="form-grid">
            ${switchRow("st-auto-detect", settings.auto_detect_urls, "Auto-detect Clipboard URLs")}
            ${switchRow("st-auto-add", settings.auto_add_to_queue, "Auto-add Detected URLs")}
          </div>
        </section>

        <section class="settings-page" data-settings-page="system">
          <div class="settings-section-subtitle">On Startup</div>
          <div class="form-grid">
            ${switchRow("st-reset-provider", settings.reset_provider_on_startup, "Reset Provider")}
            ${switchRow("st-reset-window", settings.reset_window_size_on_startup, "Reset Window Size")}
            ${switchRow("st-show-tutorial", settings.show_tutorial_on_startup, "Show Tutorial")}
          </div>
        </section>
      </div>
    </div>
  `;
}

async function openSettingsEditor() {
  const settings = await callApi("get_settings");
  await showFormModal({
    title: "Settings",
    message: "",
    html: buildSettingsFormHtml(settings),
    okLabel: "Apply",
    onMount: (root) => {
      if (modalMessage) {
        modalMessage.textContent = "";
      }
      const actionsRow = modalOkBtn?.parentElement;
      if (actionsRow && !actionsRow.querySelector(".settings-modal-actions-brand")) {
        const brandWrap = document.createElement("div");
        brandWrap.className = "settings-modal-actions-brand";

        const banner = document.createElement("img");
        banner.className = "modal-actions-banner settings-modal-actions-banner";
        banner.src = "../banner.png";
        banner.alt = "Streamline banner";

        const version = document.createElement("span");
        version.className = "settings-modal-actions-version";
        version.textContent = state.version ? `v${state.version}` : "";

        brandWrap.appendChild(banner);
        brandWrap.appendChild(version);
        actionsRow.insertBefore(brandWrap, actionsRow.firstChild);
      }
      const pageButtons = Array.from(root.querySelectorAll("[data-settings-page-btn]"));
      const pages = Array.from(root.querySelectorAll("[data-settings-page]"));
      const autoDetect = root.querySelector("#st-auto-detect");
      const autoAdd = root.querySelector("#st-auto-add");
      const resetDefaultsBtn = root.querySelector("#st-reset-defaults");
      const setFieldEnabled = (field, enabled) => {
        if (!field) {
          return;
        }
        field.disabled = !enabled;
        const row = field.closest(".form-checkbox-row");
        if (row) {
          row.style.opacity = enabled ? "1" : "0.55";
        }
      };
      const setSettingsPage = (pageName) => {
        pageButtons.forEach((button) => {
          button.classList.toggle("active", button.dataset.settingsPageBtn === pageName);
        });
        pages.forEach((page) => {
          page.classList.toggle("active", page.dataset.settingsPage === pageName);
        });
      };
      const syncAutoAdd = () => {
        setFieldEnabled(autoAdd, autoDetect.checked);
      };
      const setSelect = (id, value) => {
        const el = root.querySelector(`#${id}`);
        if (el) {
          el.value = String(value);
        }
      };
      const setCheck = (id, value) => {
        const el = root.querySelector(`#${id}`);
        if (el) {
          el.checked = !!value;
        }
      };
      const setNumber = (id, value) => {
        const el = root.querySelector(`#${id}`);
        if (el) {
          el.value = String(Number(value));
        }
      };
      const resetFormToDefaults = () => {
        setSelect("st-theme", SETTINGS_DEFAULTS.current_theme);
        setSelect("st-logo", SETTINGS_DEFAULTS.logo_style);
        setSelect("st-provider", SETTINGS_DEFAULTS.download_provider);
        setNumber("st-batch", SETTINGS_DEFAULTS.batch_size);
        setSelect("st-existing", SETTINGS_DEFAULTS.steamcmd_existing_mod_behavior);
        setSelect("st-folder-format", SETTINGS_DEFAULTS.folder_naming_format);

        setCheck("st-download-btn", SETTINGS_DEFAULTS.download_button);
        setCheck("st-search-bar", SETTINGS_DEFAULTS.show_searchbar);
        setCheck("st-import-export", SETTINGS_DEFAULTS.show_export_import_buttons);
        setCheck("st-logs", SETTINGS_DEFAULTS.show_logs);
        setCheck("st-provider-show", SETTINGS_DEFAULTS.show_provider);
        setCheck("st-queue-workshop", SETTINGS_DEFAULTS.show_queue_entire_workshop);
        setCheck("st-keep-downloaded", SETTINGS_DEFAULTS.keep_downloaded_in_queue);
        setCheck("st-delete-on-cancel", SETTINGS_DEFAULTS.delete_downloads_on_cancel);
        setCheck("st-auto-detect", SETTINGS_DEFAULTS.auto_detect_urls);
        setCheck("st-auto-add", SETTINGS_DEFAULTS.auto_add_to_queue);
        setCheck("st-show-tutorial", SETTINGS_DEFAULTS.show_tutorial_on_startup);
        setCheck("st-reset-provider", SETTINGS_DEFAULTS.reset_provider_on_startup);
        setCheck("st-reset-window", SETTINGS_DEFAULTS.reset_window_size_on_startup);

        syncAutoAdd();
      };
      pageButtons.forEach((button) => {
        button.addEventListener("click", () => {
          setSettingsPage(button.dataset.settingsPageBtn || "appearance");
        });
      });
      autoDetect.addEventListener("change", syncAutoAdd);
      resetDefaultsBtn.addEventListener("click", () => {
        resetFormToDefaults();
        addLog("Settings reset to defaults in the dialog. Click Apply to save.", "good");
      });
      setSettingsPage("appearance");
      syncAutoAdd();
    },
    onSubmit: async (root) => {
      const patch = {
        current_theme: root.querySelector("#st-theme").value,
        logo_style: root.querySelector("#st-logo").value,
        download_provider: root.querySelector("#st-provider").value,
        batch_size: Math.max(1, Number(root.querySelector("#st-batch").value || 20)),
        steamcmd_existing_mod_behavior: root.querySelector("#st-existing").value,
        folder_naming_format: root.querySelector("#st-folder-format").value,
        download_button: root.querySelector("#st-download-btn").checked,
        show_searchbar: root.querySelector("#st-search-bar").checked,
        show_commands_button: true,
        show_regex_button: true,
        show_case_button: true,
        show_export_import_buttons: root.querySelector("#st-import-export").checked,
        show_logs: root.querySelector("#st-logs").checked,
        show_provider: root.querySelector("#st-provider-show").checked,
        show_queue_entire_workshop: root.querySelector("#st-queue-workshop").checked,
        keep_downloaded_in_queue: root.querySelector("#st-keep-downloaded").checked,
        delete_downloads_on_cancel: root.querySelector("#st-delete-on-cancel").checked,
        auto_detect_urls: root.querySelector("#st-auto-detect").checked,
        auto_add_to_queue: root.querySelector("#st-auto-add").checked,
        show_tutorial_on_startup: root.querySelector("#st-show-tutorial").checked,
        reset_provider_on_startup: root.querySelector("#st-reset-provider").checked,
        reset_window_size_on_startup: root.querySelector("#st-reset-window").checked
      };

      const result = await callApi("update_settings", patch);
      if (!result?.success) {
        addLog(result?.error || "Failed to update settings.", "bad");
        return false;
      }
      state.config = result.config || state.config;
      applyTheme(state.config.current_theme || "Dark");
      applyModalTextColor(state.config.modal_text_color);
      applyVisibilityConfig(state.config);
      syncLogoStyle();
      syncWindowTitle();
      setProviderValue(state.config.download_provider);
      renderQueue();
      addLog("Settings updated.", "good");
      return true;
    }
  });
}

async function applySettingsPatch(patch, successMessage = "Settings updated.") {
  const result = await callApi("update_settings", patch);
  if (!result?.success) {
    addLog(result?.error || "Failed to update settings.", "bad");
    return false;
  }
  state.config = result.config || state.config;
  applyTheme(state.config.current_theme || "Dark");
  applyModalTextColor(state.config.modal_text_color);
  applyVisibilityConfig(state.config);
  syncLogoStyle();
  syncWindowTitle();
  setProviderValue(state.config.download_provider);
  renderQueue();
  addLog(successMessage, "good");
  return true;
}

function buildAccountsFormHtml(data, selectedUsername = "") {
  const accounts = Array.isArray(data?.accounts) ? data.accounts : [];
  const activeAccount = String(data?.active || "Anonymous").trim();
  const preferred = String(selectedUsername || "").trim();

  const hasPreferred = preferred && accounts.some((acc) => String(acc?.username || "").trim() === preferred);
  const hasActive = activeAccount && accounts.some((acc) => String(acc?.username || "").trim() === activeAccount);
  const resolvedSelected = hasPreferred
    ? preferred
    : (hasActive ? activeAccount : String(accounts[0]?.username || "").trim());

  const selectedAccount = accounts.find((acc) => String(acc?.username || "").trim() === resolvedSelected) || null;
  const selectedName = selectedAccount ? String(selectedAccount.username || "").trim() : "";
  const selectedSteamId = selectedAccount ? String(selectedAccount.steamid64 || "").trim() : "";

  const rows = accounts.length
    ? accounts.map((acc) => {
      const username = String(acc?.username || "").trim();
      const steamid64 = String(acc?.steamid64 || "").trim();
      const isActive = username === activeAccount;
      const isSelected = username === resolvedSelected;
      return `
        <div class="accounts-manager-row ${isSelected ? "active" : ""}" data-account-username="${escapeHtml(username)}">
          <button
            type="button"
            class="accounts-manager-drag-handle"
            data-account-action="drag"
            data-username="${escapeHtml(username)}"
            title="Drag to reorder"
            aria-label="Drag to reorder ${escapeHtml(username)}"
          >&#8942;&#8942;</button>
          <button
            type="button"
            class="accounts-manager-list-btn"
            data-account-action="select"
            data-username="${escapeHtml(username)}"
          >
            <span class="accounts-manager-row-main">${escapeHtml(username)}</span>
            <span class="accounts-manager-row-meta">
              <span class="accounts-manager-pill ${isActive ? "active" : "saved"}">${isActive ? "Active" : "Saved"}</span>
            </span>
          </button>
        </div>
      `;
    }).join("")
    : `<p style="margin:4px 0;">No accounts configured.</p>`;

  return `
    <div class="form-grid accounts-add-row">
      <input id="acc-username" class="form-control" type="text" placeholder="Steam account username">
      <input id="acc-password" class="form-control" type="password" autocomplete="current-password" placeholder="Steam account password">
      <button id="acc-add" class="control modal-btn primary accounts-add-inline-btn" type="button" disabled>Add Account</button>
    </div>
    <div class="form-divider"></div>
    <div class="accounts-manager-grid">
      <div class="form-block">
        <label>Saved Accounts (${accounts.length})</label>
        <div class="accounts-list">${rows}</div>
      </div>
      <div class="form-block">
        <label>Selected Account</label>
        <input id="acc-selected-username" class="form-control" type="text" readonly value="${escapeHtml(selectedName || "None")}">
        <label style="margin-top: 8px;">SteamID64</label>
        <input id="acc-selected-steamid" class="form-control accounts-copy-field" type="text" readonly value="${escapeHtml(selectedSteamId || "Unavailable")}" title="${selectedName ? "Click to copy SteamID64" : "No account selected"}">
        <label style="margin-top: 8px;">Status</label>
        <input id="acc-selected-status" class="form-control" type="text" readonly value="${escapeHtml(selectedName ? (selectedName === activeAccount ? "Active" : "Saved") : "No selection")}">
        <div class="form-actions-inline accounts-manager-actions" style="margin-top: 10px;">
          <button id="acc-set-active" class="control modal-btn primary" type="button" ${(!selectedName || selectedName === activeAccount) ? "disabled" : ""}>Set Active</button>
          <button id="acc-login-selected" class="control modal-btn" type="button" ${selectedName ? "" : "disabled"}>Re-authenticate</button>
          <button id="acc-remove-selected" class="control modal-btn" type="button" ${selectedName ? "" : "disabled"}>Remove</button>
        </div>
      </div>
    </div>
  `;
}

function buildSteamcmdLoginHtml(username) {
  return `
    <div class="steamcmd-login-shell">
      <div id="steamcmd-login-status" class="steamcmd-login-status">Starting SteamCMD session for ${escapeHtml(username)}...</div>
      <div id="steamcmd-guard-notice" class="steamcmd-guard-notice" role="status" aria-live="polite">
        Steam Guard authentication required. Approve in the Steam app or enter your verification code.
      </div>
      <pre id="steamcmd-login-output" class="steamcmd-login-output" tabindex="0"></pre>
      <div class="steamcmd-login-input-row">
        <input id="steamcmd-login-input" class="form-control" type="text" placeholder="Type Steam Guard code or command and press Send">
        <button id="steamcmd-login-send" class="control modal-btn primary" type="button">Send</button>
      </div>
    </div>
  `;
}

async function openSteamcmdLoginTerminal(username, options = {}) {
  const manualCredentialEntry = Boolean(options?.manualCredentialEntry);
  let pollTimer = null;
  let closeWatch = null;
  let disposed = false;
  let autoCloseTriggered = false;
  let sendUnlocked = manualCredentialEntry;
  const loginResult = {
    authenticated: false,
    failed: false,
    canceled: false,
    account: String(username || "").trim(),
    steamid64: "",
    error: ""
  };

  const cleanup = async (force = true) => {
    if (disposed) {
      return;
    }
    disposed = true;
    if (pollTimer) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
    if (closeWatch) {
      window.clearInterval(closeWatch);
      closeWatch = null;
    }
    try {
      await callApi("close_steamcmd_login_session", force);
    } catch {
      // ignore cleanup failure
    }
  };

  const modalResult = await showFormModal({
    title: `SteamCMD Login: ${username}`,
    message: manualCredentialEntry
      ? "Live SteamCMD terminal. Enter password or Steam Guard code and click Send as prompted."
      : "Live SteamCMD terminal. Account username/password were submitted automatically; send Steam Guard code if prompted.",
    html: buildSteamcmdLoginHtml(username),
    okLabel: "Done",
    cancelLabel: "Abort",
    showCancel: true,
    onMount: (root) => {
      const outputEl = root.querySelector("#steamcmd-login-output");
      const inputEl = root.querySelector("#steamcmd-login-input");
      const sendBtn = root.querySelector("#steamcmd-login-send");
      const statusEl = root.querySelector("#steamcmd-login-status");
      const guardNoticeEl = root.querySelector("#steamcmd-guard-notice");
      sendBtn.disabled = !manualCredentialEntry;
      if (manualCredentialEntry) {
        inputEl.placeholder = "Type password, Steam Guard code, or command and press Send";
        statusEl.textContent = "Manual login input enabled. Enter password and click Send.";
      }
      let followOutput = true;
      let guardNoticeVisible = false;

      const setGuardNoticeVisible = (visible) => {
        const nextVisible = Boolean(visible);
        if (!guardNoticeEl || guardNoticeVisible === nextVisible) {
          return;
        }
        guardNoticeVisible = nextVisible;
        guardNoticeEl.classList.toggle("is-visible", nextVisible);
      };

      const isNearBottom = () => (
        outputEl.scrollTop + outputEl.clientHeight >= outputEl.scrollHeight - 12
      );

      const hasSelectionInsideOutput = () => {
        const selection = window.getSelection();
        if (!selection || selection.rangeCount < 1 || selection.isCollapsed) {
          return false;
        }
        const range = selection.getRangeAt(0);
        return outputEl.contains(range.startContainer) || outputEl.contains(range.endContainer);
      };

      const appendOutput = (text) => {
        if (!text) {
          return;
        }
        const stickToBottom = followOutput || isNearBottom();
        outputEl.textContent += text;
        if (outputEl.textContent.length > 120000) {
          outputEl.textContent = outputEl.textContent.slice(-100000);
        }
        if (stickToBottom && !hasSelectionInsideOutput()) {
          outputEl.scrollTop = outputEl.scrollHeight;
        }
      };

      outputEl.addEventListener("scroll", () => {
        followOutput = isNearBottom();
      });

      outputEl.addEventListener("mousedown", () => {
        followOutput = false;
      });

      outputEl.addEventListener("keydown", async (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "c") {
          const selection = window.getSelection();
          const selectedText = selection ? selection.toString() : "";
          if (selectedText && hasSelectionInsideOutput()) {
            const copied = await copyTextToClipboard(selectedText);
            if (copied) {
              event.preventDefault();
              statusEl.textContent = `Copied ${selectedText.length} characters from SteamCMD output.`;
            }
          }
        }
      });

      const ensureAccountInList = async (candidateName, detectedSteamId64 = "") => {
        const normalized = (candidateName || username || "").trim();
        if (!normalized) {
          return false;
        }
        const steamid64 = String(detectedSteamId64 || "").trim();
        const result = await callApi("add_account", normalized, steamid64);
        if (result?.success) {
          return { success: true };
        }
        const errText = String(result?.error || "").toLowerCase();
        if (errText.includes("already exists")) {
          return { success: true };
        }
        return {
          success: false,
          error: result?.error || `Failed to add account '${normalized}'.`
        };
      };

      const sendInput = async () => {
        if (sendBtn.disabled) {
          return;
        }
        const value = (inputEl.value || "").trim();
        if (!value) {
          return;
        }
        const res = await callApi("send_steamcmd_login_input", value);
        if (!res?.success) {
          addLog(res?.error || "Failed to send input to SteamCMD.", "bad");
          return;
        }
        inputEl.value = "";
        await poll();
      };

      sendBtn.addEventListener("click", async () => {
        await sendInput();
      });

      inputEl.addEventListener("keydown", async (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          await sendInput();
        }
      });

      const poll = async () => {
        if (disposed) {
          return;
        }
        const res = await callApi("poll_steamcmd_login_session");
        if (!res?.success) {
          statusEl.textContent = res?.error || "SteamCMD polling failed.";
          return;
        }
        if (!res?.has_session) {
          statusEl.textContent = "No active SteamCMD session.";
          return;
        }

        appendOutput(res.output || "");
        const guardPromptActive = res.prompt === "steam_guard" || res.status_hint === "steam_guard";
        setGuardNoticeVisible(guardPromptActive);
        if (!sendUnlocked && (res.prompt === "steam_guard" || res.prompt === "command")) {
          sendUnlocked = true;
          sendBtn.disabled = false;
          statusEl.textContent = res.prompt === "steam_guard"
            ? "Prompt detected. Enter Steam Guard code and click Send."
            : "SteamCMD command prompt detected.";
        }
        const accountLabel = (res.detected_username || res.username || username || "").trim();
        const steamidSuffix = res.detected_steamid64 ? ` (SteamID64: ${res.detected_steamid64})` : "";

        if (res.login_failed) {
          loginResult.failed = true;
          statusEl.textContent = "SteamCMD reported a login failure. Check credentials/guard and retry.";
        } else if (res.account_added) {
          loginResult.authenticated = true;
          loginResult.failed = false;
          loginResult.account = accountLabel || loginResult.account;
          loginResult.steamid64 = String(res.detected_steamid64 || "").trim();
          statusEl.textContent = `Login detected for '${accountLabel || "account"}'${steamidSuffix}.`;
          if (!autoCloseTriggered) {
            autoCloseTriggered = true;
            try {
              const saved = await ensureAccountInList(accountLabel || username, res.detected_steamid64 || "");
              if (!saved?.success) {
                loginResult.authenticated = false;
                loginResult.failed = true;
                loginResult.error = String(saved?.error || "").trim();
              }
              await refreshAccounts(accountLabel || username);
            } catch (error) {
              loginResult.authenticated = false;
              loginResult.failed = true;
              loginResult.error = String(error?.message || "Failed to refresh account list after login.").trim();
            }
            statusEl.textContent = `Account '${accountLabel || "account"}' added. Closing...`;
            window.setTimeout(() => modalOkBtn.click(), 0);
            return;
          }
        } else if (res.prompt === "steam_guard") {
          statusEl.textContent = "Prompt: Steam Guard confirmation/code required.";
        } else if (res.login_success) {
          statusEl.textContent = `Authentication progressing for '${accountLabel || "account"}'${steamidSuffix}...`;
        } else if (res.status_hint === "authenticating") {
          statusEl.textContent = `Authenticating '${accountLabel || "account"}'...`;
        } else if (res.status_hint === "waiting_user_info") {
          statusEl.textContent = "Waiting for user info...";
        } else if (res.done) {
          statusEl.textContent = `Session finished (exit code: ${res.exit_code ?? "N/A"}).`;
        } else {
          statusEl.textContent = "SteamCMD session running...";
        }
      };

      poll();
      pollTimer = window.setInterval(() => {
        poll().catch((err) => {
          statusEl.textContent = err?.message || "SteamCMD polling error.";
        });
      }, 350);

      closeWatch = window.setInterval(() => {
        if (modalOverlay.classList.contains("hidden")) {
          cleanup(true);
        }
      }, 250);
    },
    onSubmit: async () => {
      await cleanup(true);
      return true;
    }
  });
  if (modalResult === null && !loginResult.authenticated) {
    loginResult.canceled = true;
  }
  return loginResult;
}

async function openAccountsManager() {
  let accountData = await callApi("get_accounts");
  let footerPurgeBtn = null;
  const resolveSelectedUsername = (data, preferred = "") => {
    const accounts = Array.isArray(data?.accounts) ? data.accounts : [];
    if (!accounts.length) {
      return "";
    }
    const preferredName = String(preferred || "").trim();
    if (preferredName && accounts.some((acc) => String(acc?.username || "").trim() === preferredName)) {
      return preferredName;
    }
    const activeName = String(data?.active || "").trim();
    if (activeName && accounts.some((acc) => String(acc?.username || "").trim() === activeName)) {
      return activeName;
    }
    return String(accounts[0]?.username || "").trim();
  };
  let selectedUsername = resolveSelectedUsername(accountData);

  try {
    await showFormModal({
      title: "Accounts Manager",
      message: "Manage saved accounts, choose the active account, and re-authenticate through SteamCMD.",
      html: buildAccountsFormHtml(accountData, selectedUsername),
      okLabel: "Close",
      showCancel: false,
      onMount: (root, context) => {
        const setFooterPurgeVisible = (visible) => {
          if (footerPurgeBtn) {
            footerPurgeBtn.style.display = visible ? "" : "none";
          }
        };

        const bindActions = () => {
          const usernameInput = root.querySelector("#acc-username");
          const passwordInput = root.querySelector("#acc-password");
          const selectedSteamIdInput = root.querySelector("#acc-selected-steamid");
          const addBtn = root.querySelector("#acc-add");
          const setActiveBtn = root.querySelector("#acc-set-active");
          const reloginBtn = root.querySelector("#acc-login-selected");
          const removeBtn = root.querySelector("#acc-remove-selected");

          const rerenderAccountsModal = () => {
            context.setFormHtml(buildAccountsFormHtml(accountData, selectedUsername));
            root = modalForm;
            bindActions();
          };

          const refreshAccountsModal = async (successMessage = "", preferredSelection = selectedUsername) => {
            accountData = await callApi("get_accounts");
            selectedUsername = resolveSelectedUsername(accountData, preferredSelection);
            rerenderAccountsModal();
            await refreshAccounts(accountData?.active || "Anonymous");
            if (successMessage) {
              addLog(successMessage, "good");
            }
          };

          const runAccountAuthentication = async (username, password, mode = "authenticate") => {
            const normalized = String(username || "").trim();
            const passwordText = String(password || "");
            if (!normalized) {
              addLog("Username is required to authenticate account.", "bad");
              return;
            }
            const isReauth = mode === "reauth";
            if (!isReauth && !passwordText.trim()) {
              addLog("Password is required to authenticate account.", "bad");
              return;
            }

            const actionText = isReauth ? "Re-signing in" : "Signing in";
            addLog(`${actionText} account '${normalized}'...`);

            const launchResult = await callApi("launch_steamcmd_login", normalized, passwordText);
            if (!launchResult?.success) {
              addLog(launchResult?.error || `Failed to start authentication for '${normalized}'.`, "bad");
              return;
            }

            if (launchResult.mode === "conpty") {
              let terminalResult = null;
              setFooterPurgeVisible(false);
              try {
                terminalResult = await openSteamcmdLoginTerminal(normalized, {
                  manualCredentialEntry: isReauth && !passwordText.trim()
                });
              } finally {
                setFooterPurgeVisible(true);
              }

              const resolvedName = String(terminalResult?.account || normalized).trim() || normalized;
              await refreshAccountsModal("", resolvedName);

              if (terminalResult?.authenticated) {
                addLog(`Authentication complete for '${resolvedName}'.`, "good");
                return;
              }
              if (terminalResult?.failed) {
                const detail = String(terminalResult?.error || "").trim();
                if (detail) {
                  addLog(`Authentication failed for '${resolvedName}': ${detail}`, "bad");
                } else {
                  addLog(`Authentication failed for '${resolvedName}'.`, "bad");
                }
                return;
              }
              if (terminalResult?.canceled) {
                addLog(`Authentication canceled for '${resolvedName}'.`);
                return;
              }
              addLog(`Authentication closed for '${resolvedName}'.`);
              return;
            }

            await refreshAccountsModal("", normalized);
            addLog(`SteamCMD login started for '${normalized}'. Complete it in the external terminal.`);
          };

          const updateSignInState = () => {
            const username = String(usernameInput?.value || "").trim();
            const password = String(passwordInput?.value || "");
            addBtn.disabled = !(username && password.trim());
          };

          const reorderAccounts = async (orderedUsernames) => {
            const accounts = Array.isArray(accountData?.accounts) ? accountData.accounts : [];
            const currentOrdered = accounts
              .map((acc) => String(acc?.username || "").trim())
              .filter((name) => !!name);
            if (currentOrdered.length < 2) {
              return;
            }

            const seen = new Set();
            const normalized = [];
            for (const rawName of orderedUsernames || []) {
              const name = String(rawName || "").trim();
              if (!name || seen.has(name)) {
                continue;
              }
              seen.add(name);
              normalized.push(name);
            }
            if (!normalized.length) {
              return;
            }

            const changed = normalized.length !== currentOrdered.length
              || normalized.some((name, index) => name !== currentOrdered[index]);
            if (!changed) {
              return;
            }

            const result = await callApi("reorder_accounts", normalized);
            if (!result?.success) {
              addLog(result?.error || "Failed to reorder accounts.", "bad");
              return;
            }
            await refreshAccountsModal("Reordered accounts.", selectedUsername);
          };

          const selectAccount = (username) => {
            selectedUsername = String(username || "").trim();
            rerenderAccountsModal();
          };

          const listEl = root.querySelector(".accounts-list");
          let pointerDrag = null;

          root.querySelectorAll("[data-account-action='select']").forEach((button) => {
            button.addEventListener("click", () => {
              selectAccount(button.dataset.username || "");
            });
          });

          root.querySelectorAll("[data-account-action='drag']").forEach((handle) => {
            handle.addEventListener("pointerdown", (event) => {
              if (!listEl || event.button !== 0 || pointerDrag) {
                return;
              }
              const row = handle.closest(".accounts-manager-row");
              if (!(row instanceof HTMLElement)) {
                return;
              }
              const username = String(row.dataset.accountUsername || "").trim();
              if (!username) {
                return;
              }

              event.preventDefault();

              const rowRect = row.getBoundingClientRect();
              const rowOffsetTop = row.offsetTop;
              const rowOffsetLeft = row.offsetLeft;
              const rowWidth = row.offsetWidth;
              const placeholder = document.createElement("div");
              placeholder.className = "accounts-manager-row-placeholder";
              placeholder.style.height = `${Math.max(32, Math.round(rowRect.height))}px`;

              listEl.insertBefore(placeholder, row.nextSibling);

              row.classList.add("dragging-live");
              row.style.position = "absolute";
              row.style.left = `${Math.round(rowOffsetLeft)}px`;
              row.style.top = `${Math.round(rowOffsetTop)}px`;
              row.style.width = `${Math.round(rowWidth)}px`;

              listEl.classList.add("is-pointer-dragging");

              const drag = {
                handle,
                row,
                username,
                pointerId: event.pointerId,
                offsetY: event.clientY - rowRect.top,
                placeholder,
                initialOrder: (Array.isArray(accountData?.accounts) ? accountData.accounts : [])
                  .map((acc) => String(acc?.username || "").trim())
                  .filter((name) => !!name),
                onMove: null,
                onUp: null
              };

              const movePlaceholderForY = (clientY) => {
                const siblings = Array.from(listEl.querySelectorAll(".accounts-manager-row"));
                let beforeNode = null;
                for (const sibling of siblings) {
                  if (sibling === drag.row) {
                    continue;
                  }
                  const rect = sibling.getBoundingClientRect();
                  if (clientY < rect.top + (rect.height / 2)) {
                    beforeNode = sibling;
                    break;
                  }
                }
                if (beforeNode) {
                  if (drag.placeholder.nextElementSibling !== beforeNode) {
                    listEl.insertBefore(drag.placeholder, beforeNode);
                  }
                } else if (drag.placeholder !== listEl.lastElementChild) {
                  listEl.appendChild(drag.placeholder);
                }
              };

              const applyPointerPosition = (clientY) => {
                const listRect = listEl.getBoundingClientRect();
                const rawTop = clientY - listRect.top + listEl.scrollTop - drag.offsetY;
                const slotElements = Array.from(listEl.querySelectorAll(".accounts-manager-row, .accounts-manager-row-placeholder"))
                  .filter((el) => el !== drag.row);
                let minTop = 0;
                let maxTop = Math.max(0, listEl.scrollHeight - drag.row.offsetHeight);
                if (slotElements.length) {
                  const slotTops = slotElements.map((el) => el.offsetTop);
                  minTop = Math.min(...slotTops);
                  maxTop = Math.max(...slotTops);
                }
                const nextTop = Math.max(minTop, Math.min(maxTop, rawTop));
                drag.row.style.top = `${Math.round(nextTop)}px`;
              };

              const autoScrollList = (clientY) => {
                const rect = listEl.getBoundingClientRect();
                const edge = 26;
                if (clientY < rect.top + edge) {
                  listEl.scrollTop -= 14;
                } else if (clientY > rect.bottom - edge) {
                  listEl.scrollTop += 14;
                }
              };

              const cleanupDrag = () => {
                if (drag.onMove) {
                  window.removeEventListener("pointermove", drag.onMove);
                }
                if (drag.onUp) {
                  window.removeEventListener("pointerup", drag.onUp);
                  window.removeEventListener("pointercancel", drag.onUp);
                }
                try {
                  if (drag.handle.hasPointerCapture(drag.pointerId)) {
                    drag.handle.releasePointerCapture(drag.pointerId);
                  }
                } catch {
                  // ignore pointer-capture release failures
                }
              };

              drag.onMove = (moveEvent) => {
                if (pointerDrag !== drag) {
                  return;
                }
                moveEvent.preventDefault();
                autoScrollList(moveEvent.clientY);
                applyPointerPosition(moveEvent.clientY);
                movePlaceholderForY(moveEvent.clientY);
              };

              drag.onUp = async (upEvent) => {
                if (pointerDrag !== drag) {
                  return;
                }
                if (upEvent.cancelable) {
                  upEvent.preventDefault();
                }
                cleanupDrag();

                if (drag.placeholder.parentElement) {
                  drag.placeholder.parentElement.insertBefore(drag.row, drag.placeholder);
                } else {
                  listEl.appendChild(drag.row);
                }

                drag.row.classList.remove("dragging-live");
                drag.row.removeAttribute("style");
                drag.placeholder.remove();
                listEl.classList.remove("is-pointer-dragging");

                pointerDrag = null;

                const finalOrder = Array.from(listEl.querySelectorAll(".accounts-manager-row"))
                  .map((el) => String(el.dataset.accountUsername || "").trim())
                  .filter((name) => !!name);
                const changed = finalOrder.length !== drag.initialOrder.length
                  || finalOrder.some((name, index) => name !== drag.initialOrder[index]);
                if (!changed) {
                  return;
                }
                await reorderAccounts(finalOrder);
              };

              pointerDrag = drag;

              try {
                handle.setPointerCapture(event.pointerId);
              } catch {
                // ignore pointer-capture failures
              }
              window.addEventListener("pointermove", drag.onMove);
              window.addEventListener("pointerup", drag.onUp);
              window.addEventListener("pointercancel", drag.onUp);
            });
          });

          addBtn.addEventListener("click", async () => {
            const username = (usernameInput.value || "").trim();
            const password = String(passwordInput?.value || "");
            await runAccountAuthentication(username, password, "add");
          });

          usernameInput?.addEventListener("input", updateSignInState);
          passwordInput?.addEventListener("input", updateSignInState);
          updateSignInState();

          setActiveBtn?.addEventListener("click", async () => {
            const username = String(selectedUsername || "").trim();
            if (!username) {
              addLog("Select an account first.", "bad");
              return;
            }
            const result = await callApi("set_active_account", username);
            if (!result?.success) {
              addLog(result?.error || `Failed to set active account '${username}'.`, "bad");
              return;
            }
            await refreshAccountsModal(`Active account set to '${username}'.`, username);
          });

          reloginBtn?.addEventListener("click", async () => {
            const username = String(selectedUsername || "").trim();
            const password = String(passwordInput?.value || "");
            if (!username) {
              addLog("Select an account first.", "bad");
              return;
            }
            await runAccountAuthentication(username, password, "reauth");
          });

          removeBtn?.addEventListener("click", async () => {
            const username = String(selectedUsername || "").trim();
            if (!username) {
              addLog("Select an account first.", "bad");
              return;
            }
            const confirmed = await showConfirmDialog({
              title: "Remove Account",
              message: `Remove account '${username}'?`,
              okLabel: "Remove",
              cancelLabel: "Cancel"
            });
            if (!confirmed) {
              return;
            }
            const result = await callApi("remove_account", username);
            if (!result?.success) {
              addLog(result?.error || `Failed to remove '${username}'.`, "bad");
              return;
            }
            await refreshAccountsModal(`Removed account '${username}'.`);
          });

          selectedSteamIdInput?.addEventListener("click", async () => {
            const username = String(selectedUsername || "").trim();
            if (!username) {
              addLog("Select an account first.", "bad");
              return;
            }
            const accounts = Array.isArray(accountData?.accounts) ? accountData.accounts : [];
            const selected = accounts.find((acc) => String(acc?.username || "").trim() === username) || null;
            const steamid64 = String(selected?.steamid64 || "").trim();
            const textToCopy = steamid64 || username;
            const copied = await copyTextToClipboard(textToCopy);
            if (!copied) {
              addLog("Failed to copy to clipboard.", "bad");
              return;
            }
            if (steamid64) {
              addLog(`Copied SteamID64 for '${username}'.`, "good");
            } else {
              addLog(`No SteamID64 for '${username}', copied username instead.`, "good");
            }
          });
        };

        bindActions();

        const actionsRow = modalOkBtn?.parentElement;
        if (actionsRow && !actionsRow.querySelector("#acc-footer-purge")) {
          const purgeBtn = document.createElement("button");
          purgeBtn.id = "acc-footer-purge";
          purgeBtn.type = "button";
          purgeBtn.className = "control modal-btn accounts-footer-purge-btn";
          purgeBtn.textContent = "Purge all accounts...";
          purgeBtn.addEventListener("click", async () => {
            const confirmed = await showKeywordConfirmDialog({
              title: "Purge All Accounts",
              message: "Type PURGE to remove all saved accounts and reset active account.",
              keyword: "PURGE",
              okLabel: "Purge",
              cancelLabel: "Cancel"
            });
            if (!confirmed) {
              return;
            }
            const result = await callApi("purge_accounts");
            if (!result?.success) {
              addLog(result?.error || "Failed to purge accounts.", "bad");
              return;
            }
            accountData = await callApi("get_accounts");
            selectedUsername = resolveSelectedUsername(accountData, "");
            context.setFormHtml(buildAccountsFormHtml(accountData, selectedUsername));
            root = modalForm;
            bindActions();
            await refreshAccounts(accountData?.active || "Anonymous");
            addLog("Purged all accounts.", "good");
          });
          actionsRow.insertBefore(purgeBtn, modalOkBtn);
          footerPurgeBtn = purgeBtn;
        }
      },
      onSubmit: () => true
    });
  } finally {
    if (footerPurgeBtn && footerPurgeBtn.parentElement) {
      footerPurgeBtn.parentElement.removeChild(footerPurgeBtn);
    }
  }
}

async function openAppIdsManager() {
  const info = await callApi("get_appids_info");
  const currentCount = Number(info?.count ?? 0);
  const lastUpdated = String(info?.last_updated || "N/A");
  let useHeadlessMode = true;
  let footerHeadlessSwitchEl = null;
  const TYPE_OPTIONS = [
    { key: "game", label: "Game", value: "Game", selected: true },
    { key: "application", label: "Application", value: "Application", selected: false },
    { key: "tool", label: "Tool", value: "Tool", selected: false }
  ];
  const PROGRESS_STEPS = [
    { key: "connect", label: "Connect to source", runningText: "Connecting to SteamDB..." },
    { key: "fetch", label: "Fetch entries", runningText: "Fetching AppID rows..." },
    { key: "parse", label: "Parse payload", runningText: "Parsing AppIDs..." },
    { key: "write", label: "Write AppIDs file", runningText: "Writing AppIDs.txt..." },
    { key: "reload", label: "Reload in app", runningText: "Reloading AppIDs..." }
  ];
  const formattedCount = Number.isFinite(currentCount) ? currentCount.toLocaleString() : "0";

  const html = `
    <div class="appids-modal-shell" data-appids-state="idle">
      <section class="appids-config-pane">
        <div class="appids-stat-grid">
          <div class="appids-stat-card">
            <span class="appids-stat-label">Current Entries</span>
            <span class="appids-stat-value">${formattedCount}</span>
          </div>
          <div class="appids-stat-card">
            <span class="appids-stat-label">Last Updated</span>
            <span class="appids-stat-value appids-stat-subtle">${escapeHtml(lastUpdated)}</span>
          </div>
        </div>
        <div class="appids-type-section">
          <h4 class="appids-section-title">Select Types</h4>
          <div class="appids-type-grid">
            ${TYPE_OPTIONS.map((type) => `
              <button
                type="button"
                class="appids-type-chip${type.selected ? " is-selected" : ""}"
                data-appids-type="${type.key}"
                data-appids-value="${type.value}"
                aria-pressed="${type.selected ? "true" : "false"}"
              >${type.label}</button>
            `).join("")}
          </div>
        </div>
      </section>
      <section class="appids-progress-pane" aria-live="polite">
        <div class="appids-progress-head">
          <span class="appids-progress-title">Update Status</span>
          <span id="appids-progress-badge" class="appids-progress-badge state-idle">Idle</span>
        </div>
        <div class="appids-progress-bar-track">
          <span id="appids-progress-bar-fill" class="appids-progress-bar-fill"></span>
        </div>
        <p id="appids-progress-text" class="appids-progress-text">Ready to update AppIDs.</p>
        <ol class="appids-progress-steps">
          ${PROGRESS_STEPS.map((step) => `
            <li class="appids-progress-step is-pending" data-appids-step="${step.key}">
              <span class="appids-progress-step-dot" aria-hidden="true"></span>
              <span class="appids-progress-step-label">${step.label}</span>
            </li>
          `).join("")}
        </ol>
      </section>
    </div>
  `;

  let updateInFlight = false;
  let progressTimer = null;
  let activeStepIndex = -1;

  const getSelectedTypeButtons = (root) => (
    Array.from(root.querySelectorAll(".appids-type-chip"))
  );
  const getSelectedTypes = (root) => (
    getSelectedTypeButtons(root)
      .filter((button) => button.classList.contains("is-selected"))
      .map((button) => String(button.dataset.appidsValue || "").trim())
      .filter((value) => !!value)
  );
  const setProgressBadge = (root, state, text) => {
    const badge = root.querySelector("#appids-progress-badge");
    if (!badge) {
      return;
    }
    badge.className = `appids-progress-badge state-${state}`;
    badge.textContent = text;
  };
  const setProgressText = (root, text) => {
    const textEl = root.querySelector("#appids-progress-text");
    if (textEl) {
      textEl.textContent = String(text || "");
    }
  };
  const setProgressBar = (root, state, widthPercent = 0) => {
    const fill = root.querySelector("#appids-progress-bar-fill");
    if (!fill) {
      return;
    }
    fill.className = `appids-progress-bar-fill state-${state}`;
    fill.style.width = `${Math.max(0, Math.min(100, Number(widthPercent) || 0))}%`;
  };
  const setStepState = (root, stepKey, state) => {
    const row = root.querySelector(`[data-appids-step='${stepKey}']`);
    if (!row) {
      return;
    }
    row.classList.remove("is-pending", "is-active", "is-done", "is-error");
    row.classList.add(`is-${state}`);
  };
  const resetSteps = (root) => {
    for (const step of PROGRESS_STEPS) {
      setStepState(root, step.key, "pending");
    }
  };
  const updateStepProgress = (root, stepIndex) => {
    activeStepIndex = stepIndex;
    for (let i = 0; i < PROGRESS_STEPS.length; i += 1) {
      const step = PROGRESS_STEPS[i];
      if (i < stepIndex) {
        setStepState(root, step.key, "done");
      } else if (i === stepIndex) {
        setStepState(root, step.key, "active");
      } else {
        setStepState(root, step.key, "pending");
      }
    }
    const active = PROGRESS_STEPS[Math.max(0, Math.min(PROGRESS_STEPS.length - 1, stepIndex))];
    if (active?.runningText) {
      setProgressText(root, active.runningText);
    }
  };
  const stopProgressTimer = () => {
    if (progressTimer) {
      window.clearInterval(progressTimer);
      progressTimer = null;
    }
  };

  try {
    await showFormModal({
      title: "Update AppIDs",
      message: "Refresh local AppIDs from SteamDB.",
      html,
      okLabel: "Update",
      onMount: (root) => {
        setProgressBadge(root, "idle", "Idle");
        setProgressBar(root, "idle", 0);
        setProgressText(root, "Ready to update AppIDs.");
        resetSteps(root);

        const actionsRow = modalOkBtn?.parentElement;
        if (actionsRow && !actionsRow.querySelector("#appids-headless-toggle")) {
          const toggleWrap = document.createElement("label");
          toggleWrap.id = "appids-headless-toggle";
          toggleWrap.className = "appids-footer-headless-switch form-checkbox-row form-switch-row";
          toggleWrap.title = "Disable headless mode to use a visible browser and manually complete Cloudflare checks.";
          toggleWrap.innerHTML = `
            <input id="appids-headless-input" type="checkbox" ${useHeadlessMode ? "checked" : ""}>
            <span class="form-switch-track" aria-hidden="true"></span>
            <span class="form-switch-label">Headless</span>
          `;
          const toggleInput = toggleWrap.querySelector("#appids-headless-input");
          if (toggleInput) {
            toggleInput.checked = useHeadlessMode;
            toggleInput.addEventListener("change", () => {
              if (updateInFlight) {
                toggleInput.checked = useHeadlessMode;
                return;
              }
              useHeadlessMode = !!toggleInput.checked;
            });
          }
          actionsRow.insertBefore(toggleWrap, actionsRow.firstChild);
          footerHeadlessSwitchEl = toggleWrap;
        }

        getSelectedTypeButtons(root).forEach((button) => {
          button.addEventListener("click", () => {
            if (updateInFlight) {
              return;
            }
            const isSelected = button.classList.contains("is-selected");
            const selectedCount = getSelectedTypeButtons(root).filter((item) => item.classList.contains("is-selected")).length;
            if (isSelected && selectedCount <= 1) {
              return;
            }
            button.classList.toggle("is-selected", !isSelected);
            button.setAttribute("aria-pressed", !isSelected ? "true" : "false");
          });
        });
      },
      onSubmit: async (root) => {
        if (updateInFlight) {
          return false;
        }
        const selectedTypes = getSelectedTypes(root);
        if (!selectedTypes.length) {
          addLog("Select at least one type to update AppIDs.", "bad");
          setProgressBadge(root, "error", "Error");
          setProgressBar(root, "error", 100);
          setProgressText(root, "No types selected.");
          return false;
        }

        const headlessInput = footerHeadlessSwitchEl?.querySelector("#appids-headless-input");
        if (headlessInput) {
          useHeadlessMode = !!headlessInput.checked;
        }

        updateInFlight = true;
        modalOkBtn.disabled = true;
        modalCancelBtn.disabled = true;
        if (headlessInput) {
          headlessInput.disabled = true;
        }
        setProgressBadge(root, "running", "Running");
        setProgressBar(root, "running", 28);
        resetSteps(root);
        updateStepProgress(root, 0);

        const startedAt = Date.now();
        progressTimer = window.setInterval(() => {
          const elapsedMs = Date.now() - startedAt;
          const idx = Math.min(PROGRESS_STEPS.length - 1, Math.floor(elapsedMs / 900));
          updateStepProgress(root, idx);
        }, 220);

        try {
          const result = await callApi("update_appids", selectedTypes, useHeadlessMode);
          stopProgressTimer();
          if (result?.success) {
            for (const step of PROGRESS_STEPS) {
              setStepState(root, step.key, "done");
            }
            setProgressBadge(root, "success", "Done");
            setProgressBar(root, "success", 100);
            setProgressText(root, `AppIDs updated successfully (${result.count} entries).`);
            addLog(`AppIDs updated (${result.count} entries).`, "good");
            return true;
          }
          const errorText = String(result?.error || "Failed to update AppIDs.");
          if (activeStepIndex >= 0 && activeStepIndex < PROGRESS_STEPS.length) {
            setStepState(root, PROGRESS_STEPS[activeStepIndex].key, "error");
          }
          setProgressBadge(root, "error", "Failed");
          setProgressBar(root, "error", 100);
          setProgressText(root, errorText);
          addLog(errorText, "bad");
          return false;
        } catch (error) {
          stopProgressTimer();
          const errorText = String(error?.message || "Failed to update AppIDs.");
          if (activeStepIndex >= 0 && activeStepIndex < PROGRESS_STEPS.length) {
            setStepState(root, PROGRESS_STEPS[activeStepIndex].key, "error");
          }
          setProgressBadge(root, "error", "Failed");
          setProgressBar(root, "error", 100);
          setProgressText(root, errorText);
          addLog(errorText, "bad");
          return false;
        } finally {
          updateInFlight = false;
          modalOkBtn.disabled = false;
          modalCancelBtn.disabled = false;
          if (headlessInput) {
            headlessInput.disabled = false;
          }
        }
      }
    });
  } finally {
    stopProgressTimer();
    if (footerHeadlessSwitchEl && footerHeadlessSwitchEl.parentElement) {
      footerHeadlessSwitchEl.parentElement.removeChild(footerHeadlessSwitchEl);
    }
  }
}

async function openTutorialDialog(options = {}) {
  if (tutorialSession) {
    return tutorialSession.done;
  }

  const fromStartup = !!options.fromStartup;
  let showOnStartupSetting = state.config.show_tutorial_on_startup !== false;

  const steps = [
    {
      title: "Welcome To Streamline",
      message: fromStartup
        ? "Welcome back. This guided tour highlights the main controls in the app and what they do."
        : "This guided tour highlights the main controls in the app and what they do.",
      selectors: []
    },
    {
      title: "Command Palette",
      message: "The Command Palette gives you easy access to all actions in Streamline. It can be accessed via the 'Additional Actions' chevron, or via shortcuts: Ctrl+K or double-tap Shift.",
      selectors: ["#open-command-palette-btn", "#commands-split-menu"],
      ensureCommandSplitMenuOpen: true,
      disableAutoScroll: true
    },
    {
      title: "Workshop Input",
      message: "Paste a Game AppID, Workshop Mod URL/ID, or Collection URL/ID here to prepare download targets.",
      selectors: ["#item-url"]
    },
    {
      title: "Queue Actions",
      message: "Use these buttons to add to queue or download immediately.",
      selectors: ["#add-to-queue-btn", "#download-now-btn"]
    },
    {
      title: "Queue Table",
      message: "This table tracks queued items and status. Right-click rows for move, provider, and remove actions.",
      selectors: [".queue-table-wrap"]
    },
    {
      title: "Download Controls",
      message: "'Start Download' begins queue processing. While running, the same button changes to 'Cancel Download'.",
      selectors: ["#start-download-btn"]
    },
    {
      title: "Logs",
      message: "Live activity appears here for troubleshooting and progress checks. Right-click to copy or clear logs.",
      selectors: ["#log-wrap"]
    }
  ];

  let index = 0;
  let pendingTargets = [];
  let finishing = false;

  const done = new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "tutorial-overlay";
    overlay.innerHTML = `
      <div class="tutorial-spotlight hidden"></div>
      <section class="tutorial-card" role="dialog" aria-modal="true" aria-label="Quick Tutorial">
        <div class="tutorial-head">
          <div class="tutorial-step-meta"></div>
          <div class="tutorial-step-context"></div>
        </div>
        <div class="tutorial-progress" aria-hidden="true">
          <span class="tutorial-progress-fill"></span>
        </div>
        <p class="tutorial-message"></p>
        <label class="tutorial-startup-toggle form-checkbox-row tutorial-startup-switch">
          <input id="tutorial-show-startup-checkbox" type="checkbox">
          <span class="form-switch-track" aria-hidden="true"></span>
          <span class="form-switch-label">Show tutorial on startup</span>
        </label>
        <div class="tutorial-actions">
          <button type="button" class="control modal-btn" data-tutorial-action="skip">Skip</button>
          <button type="button" class="control modal-btn" data-tutorial-action="prev">Previous</button>
          <button type="button" class="control modal-btn primary" data-tutorial-action="next">Next</button>
        </div>
      </section>
    `;
    document.body.appendChild(overlay);

    const spotlight = overlay.querySelector(".tutorial-spotlight");
    const card = overlay.querySelector(".tutorial-card");
    const stepMeta = overlay.querySelector(".tutorial-step-meta");
    const stepContext = overlay.querySelector(".tutorial-step-context");
    const progressFill = overlay.querySelector(".tutorial-progress-fill");
    const messageEl = overlay.querySelector(".tutorial-message");
    const startupCheckbox = overlay.querySelector("#tutorial-show-startup-checkbox");
    const prevBtn = overlay.querySelector("[data-tutorial-action='prev']");
    const nextBtn = overlay.querySelector("[data-tutorial-action='next']");
    const skipBtn = overlay.querySelector("[data-tutorial-action='skip']");
    card.setAttribute("tabindex", "-1");

    const isElementVisible = (el) => {
      if (!(el instanceof HTMLElement) || !el.isConnected) {
        return false;
      }
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") {
        return false;
      }
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    };

    const findStepTargets = (step) => {
      const selectors = Array.isArray(step?.selectors) ? step.selectors : [];
      const targets = [];
      for (const selector of selectors) {
        if (!selector) {
          continue;
        }
        const node = document.querySelector(selector);
        if (node instanceof HTMLElement) {
          targets.push(node);
        }
      }
      return targets;
    };

    const clamp = (value, min, max) => Math.max(min, Math.min(value, max));
    const ensureCommandSplitMenuOpen = () => {
      if (!commandPaletteBtn || !commandsSplitMenu) {
        return;
      }
      if (commandPaletteBtn.style.display === "none") {
        return;
      }
      hideCommandSplitMenu();
      commandsSplitMenu.classList.remove("hidden");
      commandPaletteBtn.classList.add("active");
    };

    const placeCard = (targetRect) => {
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const margin = 12;
      const cardRect = card.getBoundingClientRect();
      const cardWidth = Math.ceil(cardRect.width || 360);
      const cardHeight = Math.ceil(cardRect.height || 220);

      if (!targetRect) {
        const centerLeft = clamp((viewportWidth - cardWidth) / 2, margin, viewportWidth - cardWidth - margin);
        const centerTop = clamp((viewportHeight - cardHeight) / 2, margin, viewportHeight - cardHeight - margin);
        card.style.left = `${centerLeft}px`;
        card.style.top = `${centerTop}px`;
        return;
      }

      const belowTop = targetRect.bottom + 10;
      const aboveTop = targetRect.top - cardHeight - 10;
      const rightLeft = targetRect.left;
      const leftLeft = targetRect.right - cardWidth;
      let top = belowTop;
      let left = rightLeft;

      if (belowTop + cardHeight > viewportHeight - margin && aboveTop >= margin) {
        top = aboveTop;
      }
      if (left + cardWidth > viewportWidth - margin) {
        left = leftLeft;
      }

      top = clamp(top, margin, viewportHeight - cardHeight - margin);
      left = clamp(left, margin, viewportWidth - cardWidth - margin);
      card.style.left = `${left}px`;
      card.style.top = `${top}px`;
    };

    const positionStep = ({ allowFallback = true } = {}) => {
      const visibleTargets = pendingTargets.filter((target) => isElementVisible(target));
      if (!visibleTargets.length) {
        if (allowFallback) {
          spotlight.classList.add("hidden");
          placeCard(null);
        }
        return false;
      }

      const rects = visibleTargets.map((target) => target.getBoundingClientRect());
      const left = Math.min(...rects.map((rect) => rect.left));
      const top = Math.min(...rects.map((rect) => rect.top));
      const right = Math.max(...rects.map((rect) => rect.right));
      const bottom = Math.max(...rects.map((rect) => rect.bottom));
      const rect = {
        left,
        top,
        right,
        bottom,
        width: Math.max(0, right - left),
        height: Math.max(0, bottom - top)
      };
      const pad = 6;
      spotlight.classList.remove("hidden");
      spotlight.style.left = `${Math.max(0, rect.left - pad)}px`;
      spotlight.style.top = `${Math.max(0, rect.top - pad)}px`;
      spotlight.style.width = `${Math.max(12, rect.width + pad * 2)}px`;
      spotlight.style.height = `${Math.max(12, rect.height + pad * 2)}px`;
      placeCard(rect);
      return true;
    };

    const getFocusableElements = () => {
      const selector = "button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex='-1'])";
      return Array.from(card.querySelectorAll(selector)).filter((node) => isElementVisible(node));
    };

    const persistTutorialSettings = async () => {
      const patch = {
        tutorial_shown: true,
        show_tutorial_on_startup: !!showOnStartupSetting
      };
      try {
        const result = await callApi("update_settings", patch);
        if (result?.success) {
          state.config = result.config || state.config;
        } else {
          state.config = { ...state.config, ...patch };
        }
      } catch {
        state.config = { ...state.config, ...patch };
      }
    };

    let onKeyDown = null;
    const finish = async () => {
      if (finishing) {
        return;
      }
      finishing = true;
      if (onKeyDown) {
        document.removeEventListener("keydown", onKeyDown, true);
      }
      closeMenuPopups();
      window.removeEventListener("resize", positionStep);
      window.removeEventListener("scroll", positionStep, true);
      overlay.remove();
      tutorialSession = null;
      await persistTutorialSettings();
      resolve(true);
    };

    const renderStep = () => {
      hideQueueContextMenu();
      hideHeaderContextMenu();
      hideLogsContextMenu();
      closeMenuPopups();

      index = clamp(index, 0, steps.length - 1);
      const step = steps[index] || steps[0];
      stepMeta.textContent = `Step ${index + 1} of ${steps.length}`;
      stepContext.textContent = String(step.title || "Tutorial");
      if (progressFill) {
        progressFill.style.width = `${((index + 1) / Math.max(1, steps.length)) * 100}%`;
      }
      messageEl.textContent = String(step.message || "");
      prevBtn.disabled = index === 0;
      nextBtn.textContent = index >= (steps.length - 1) ? "Finish" : "Next";
      startupCheckbox.checked = !!showOnStartupSetting;

      const resolveTargetsAndPosition = (attempt = 0) => {
        if (!overlay.isConnected || finishing) {
          return;
        }
        if (step.ensureCommandSplitMenuOpen) {
          ensureCommandSplitMenuOpen();
        }
        pendingTargets = findStepTargets(step);
        if (!step.disableAutoScroll && pendingTargets[0] && typeof pendingTargets[0].scrollIntoView === "function") {
          pendingTargets[0].scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
        }
        const highlighted = positionStep({ allowFallback: !step.ensureCommandSplitMenuOpen });
        if (!highlighted && attempt < 8) {
          window.setTimeout(() => resolveTargetsAndPosition(attempt + 1), 40);
          return;
        }
        if (!highlighted) {
          positionStep({ allowFallback: true });
        }
        window.setTimeout(() => {
          positionStep({ allowFallback: true });
        }, 120);
      };

      if (step.ensureCommandSplitMenuOpen) {
        window.setTimeout(() => {
          if (!overlay.isConnected || finishing) {
            return;
          }
          ensureCommandSplitMenuOpen();
          resolveTargetsAndPosition();
        }, 0);
        return;
      }

      resolveTargetsAndPosition();
    };

    const goToPreviousStep = () => {
      if (index <= 0) {
        return;
      }
      index -= 1;
      renderStep();
    };

    const goToNextStep = async () => {
      if (index >= (steps.length - 1)) {
        await finish();
        return;
      }
      index += 1;
      renderStep();
    };

    onKeyDown = async (event) => {
      if (!overlay.isConnected || finishing) {
        return;
      }

      if (event.key === "Tab") {
        const focusables = getFocusableElements();
        if (!focusables.length) {
          event.preventDefault();
          card.focus();
          return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement;
        if (event.shiftKey) {
          if (active === first || !card.contains(active)) {
            event.preventDefault();
            last.focus();
          }
        } else if (active === last || !card.contains(active)) {
          event.preventDefault();
          first.focus();
        }
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        await finish();
        return;
      }

      if (event.key === "ArrowLeft") {
        if (event.target === startupCheckbox) {
          return;
        }
        event.preventDefault();
        goToPreviousStep();
        return;
      }

      if (event.key === "ArrowRight") {
        if (event.target === startupCheckbox) {
          return;
        }
        event.preventDefault();
        await goToNextStep();
        return;
      }

      if (event.key === "Enter") {
        if (event.target instanceof HTMLInputElement && event.target.type === "checkbox") {
          return;
        }
        if (event.target instanceof HTMLButtonElement) {
          return;
        }
        event.preventDefault();
        await goToNextStep();
      }
    };

    startupCheckbox.addEventListener("change", () => {
      showOnStartupSetting = !!startupCheckbox.checked;
    });

    prevBtn.addEventListener("click", goToPreviousStep);
    nextBtn.addEventListener("click", async () => {
      await goToNextStep();
    });
    skipBtn.addEventListener("click", async () => {
      await finish();
    });

    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) {
        event.preventDefault();
      }
    });

    window.addEventListener("resize", positionStep);
    window.addEventListener("scroll", positionStep, true);
    document.addEventListener("keydown", onKeyDown, true);
    renderStep();
    window.setTimeout(() => {
      nextBtn.focus();
    }, 0);
  });

  tutorialSession = { done };
  return done;
}

async function openAboutDialog() {
  const data = await callApi("get_bootstrap_data");
  const version = data?.version || "Unknown";
  const queueCountSource = data?.queue_total ?? data?.queue_stats?.total ?? (data?.queue || []).length;
  const queueCount = Number(queueCountSource || 0);
  const appIdsCount = data?.appids_count ?? 0;
  const logoStyle = state.config.logo_style || "Light";
  const logoPath = logoStyle === "Dark" ? "../logo_dark.png" : (logoStyle === "Darker" ? "../logo_darker.png" : "../logo.png");
  const html = `
    <div style="text-align:center; margin-bottom: 10px;">
      <img src="${logoPath}" alt="Streamline logo" style="width:64px; height:64px;">
    </div>
    <p style="margin: 0 0 8px; text-align:center;"><strong>Streamline - Steam Workshop Downloader</strong></p>
    <p style="margin: 0 0 10px; text-align:center;">Version ${escapeHtml(version)} | Created by dane-9</p>
    <p style="margin: 0 0 8px; text-align:center;">A modern downloader supporting SteamCMD and SteamWebAPI.</p>
    <div class="form-grid">
      <div class="form-block">
        <label>Queued Items</label>
        <input class="form-control" type="text" value="${queueCount}" readonly>
      </div>
      <div class="form-block">
        <label>Known AppIDs</label>
        <input class="form-control" type="text" value="${appIdsCount}" readonly>
      </div>
    </div>
    <div class="form-actions-inline" style="justify-content:center;">
      <button id="about-open-repo" class="control modal-btn" type="button">GitHub Repository</button>
      <button id="about-open-docs" class="control modal-btn" type="button">Documentation</button>
      <button id="about-open-issues" class="control modal-btn" type="button">Report Issue</button>
    </div>
  `;

  await showFormModal({
    title: "About",
    message: "Streamline Workshop Downloader",
    html,
    okLabel: "Close",
    showCancel: false,
    onMount: (root) => {
      root.querySelector("#about-open-repo")?.addEventListener("click", async () => {
        const result = await callApi("launch_repository");
        if (!result?.success) {
          addLog(result?.error || "Failed to open repository.", "bad");
        }
      });
      root.querySelector("#about-open-docs")?.addEventListener("click", async () => {
        const result = await callApi("launch_documentation");
        if (!result?.success) {
          addLog(result?.error || "Failed to open documentation.", "bad");
        }
      });
      root.querySelector("#about-open-issues")?.addEventListener("click", async () => {
        const result = await callApi("launch_report_issue");
        if (!result?.success) {
          addLog(result?.error || "Failed to open issues page.", "bad");
        }
      });
    },
    onSubmit: () => true
  });
}

async function openWorkshopInputHelpDialog() {
  const html = `
    <div class="form-grid">
      <div class="form-block" style="grid-column: 1 / -1;">
        <p style="margin: 0 0 6px;"><strong>Workshop Input Formats</strong></p>
        <p style="margin: 0 0 6px;">• Game AppID (example: <code>108600</code>) or Store URL: queue all mods for a game.</p>
        <p style="margin: 0 0 6px;">• Mod URL/ID: queue a specific workshop mod.</p>
        <p style="margin: 0 0 10px;">• Collection URL/ID: queue all mods in a collection.</p>
      </div>
      <div class="form-block" style="grid-column: 1 / -1;">
        <p style="margin: 0 0 6px;"><strong>Examples</strong></p>
        <p style="margin: 0 0 4px;"><code>108600</code></p>
        <p style="margin: 0 0 4px;"><code>https://store.steampowered.com/app/108600/Project_Zomboid/</code></p>
        <p style="margin: 0 0 4px;"><code>https://steamcommunity.com/sharedfiles/filedetails/?id=123456789</code></p>
        <p style="margin: 0;"><code>https://steamcommunity.com/workshop/filedetails/?id=123456789</code></p>
      </div>
      <div class="form-block" style="grid-column: 1 / -1;">
        <p style="margin: 0;">You can paste Steam URLs directly from your browser. URLs are auto-detected from clipboard when enabled in settings.</p>
      </div>
    </div>
  `;

  await showFormModal({
    title: "Workshop URL/ID Help",
    message: "Use these formats when adding items to the queue.",
    html,
    okLabel: "Close",
    showCancel: false,
    onSubmit: () => true
  });
}

async function wireControlButtons() {
  bindCommandToButton(settingsBtn, "open_settings", { closeMenus: true });
  bindCommandToButton(accountsBtn, "manage_accounts");
  bindCommandToButton(appidsBtn, "manage_appids");
  bindCommandToButton(importBtn, "import_queue");
  bindCommandToButton(exportBtn, "export_queue");
}

function wireFilterControls() {
  filterBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    filterPopup.classList.toggle("hidden");
  });

  filterPopup.querySelectorAll(".filter-item").forEach((item) => {
    item.addEventListener("click", () => setFilter(item.dataset.filter));
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".line-input-wrap")) {
      filterPopup.classList.add("hidden");
    }
  });

  caseBtn.addEventListener("click", () => {
    state.caseSensitive = !state.caseSensitive;
    caseBtn.classList.toggle("active", state.caseSensitive);
    state.searchMatcherCache.matcher = null;
    scheduleSearchRender(0);
  });

  regexBtn.addEventListener("click", () => {
    state.regex = !state.regex;
    regexBtn.classList.toggle("active", state.regex);
    state.searchMatcherCache.matcher = null;
    scheduleSearchRender(0);
  });

  searchInput.addEventListener("input", () => {
    state.searchMatcherCache.matcher = null;
    scheduleSearchRender();
  });
}

async function handleAddToQueue(event) {
  event.preventDefault();
  const itemUrl = itemUrlInput.value.trim();
  const provider = providerSelect.value || "Default";

  if (!itemUrl) {
    addLog("No workshop URL/ID entered.", "bad");
    return;
  }

  try {
    const request = callApi("add_workshop_item", itemUrl, "", provider);
    void pollEvents();
    const result = await request;
    void pollEvents();
    if (!result?.success) {
      addLog(result?.error || "Failed to add to queue.", "bad");
      return;
    }
  } catch {
    browserQueue.push(createBrowserQueueItem(itemUrl, provider));
    addLog("Queued in preview mode (local browser state).", "good");
  }

  queueForm.reset();
  setProviderValue(provider);
  await refreshQueue({ forceReload: true });
}

function getQueueStatusBucket(statusValue) {
  const status = String(statusValue || "");
  if (status === "Queued") {
    return "queued";
  }
  if (status === "Downloaded") {
    return "downloaded";
  }
  if (status === "Downloading") {
    return "downloading";
  }
  if (status.includes("Failed")) {
    return "failed";
  }
  return "";
}

function applyQueueStatusDelta(previousStatus, nextStatus) {
  const previousBucket = getQueueStatusBucket(previousStatus);
  const nextBucket = getQueueStatusBucket(nextStatus);
  if (!previousBucket && !nextBucket) {
    return;
  }
  if (previousBucket === nextBucket) {
    return;
  }

  if (previousBucket) {
    const previousValue = Number(state.queueStats[previousBucket] || 0);
    state.queueStats[previousBucket] = Math.max(0, previousValue - 1);
  }
  if (nextBucket) {
    const nextValue = Number(state.queueStats[nextBucket] || 0);
    state.queueStats[nextBucket] = Math.max(0, nextValue + 1);
  }
}

function applyQueueStatusEvent(payload) {
  const modId = String(payload?.mod_id || "").trim();
  if (!modId) {
    return;
  }

  const nextStatus = String(payload?.status || "Queued");
  const invalidateQueueView = !!payload?.invalidate_queue_view;
  const retryCount = Math.max(0, Number(payload?.retry_count || 0));
  const maxRetries = Math.max(1, Number(payload?.max_retries || 3));
  let previousStatus = payload?.previous_status !== undefined && payload?.previous_status !== null
    ? String(payload.previous_status)
    : "";
  let touched = false;

  const updateItemStatus = (item) => {
    if (!item || String(item.mod_id) !== modId) {
      return false;
    }
    if (!previousStatus) {
      previousStatus = String(item.status || "");
    }
    item.status = nextStatus;
    item.retry_count = retryCount;
    item.max_retries = maxRetries;
    return true;
  };

  if (Array.isArray(state.queue) && state.queue.length) {
    for (const item of state.queue) {
      if (updateItemStatus(item)) {
        touched = true;
        break;
      }
    }
  }

  if (Array.isArray(virtualBackendPageItems) && virtualBackendPageItems.length) {
    for (const item of virtualBackendPageItems) {
      if (updateItemStatus(item)) {
        touched = true;
        break;
      }
    }
  }

  if (previousStatus || touched) {
    applyQueueStatusDelta(previousStatus, nextStatus);
  }

  if (invalidateQueueView) {
    scheduleQueueRefresh(true);
    return;
  }

  if (virtualBackendEnabled) {
    renderQueueViewport(true);
    updateSearchPlaceholder();
    return;
  }

  if (touched) {
    renderQueue();
  } else {
    updateSearchPlaceholder();
  }
}

async function handleEvent(event) {
  if (!event || typeof event.id !== "number") {
    return;
  }
  state.lastEventId = Math.max(state.lastEventId, event.id);

  const type = event.type;
  const payload = event.payload || {};

  if (type === "log") {
    addLog(payload.message || "", payload.tone || "", {
      source: payload.source || "system",
      action: payload.action || "",
      operationId: payload.operation_id || payload.operationId || "",
      context: payload.context,
      timestamp: event.timestamp
    });
    return;
  }

  if (type === "queue") {
    scheduleQueueRefresh(true);
    return;
  }
  if (type === "queue_status") {
    applyQueueStatusEvent(payload);
    return;
  }

  if (type === "download") {
    const status = payload.state;
    if (status === "started") {
      state.isDownloading = true;
      state.cancelPending = false;
    } else if (status === "finished") {
      state.isDownloading = false;
      state.cancelPending = false;
    } else if (status === "canceled") {
      state.isDownloading = false;
      state.cancelPending = false;
    } else if (status === "error") {
      state.isDownloading = false;
      state.cancelPending = false;
      addLog(payload.error || "Download error.", "bad", {
        source: "download",
        action: "error",
        operationId: payload.operation_id || ""
      });
    }
    syncStartButton();
    return;
  }

  if (type === "settings") {
    state.config = payload.config || state.config;
    applyTheme(state.config.current_theme || "Dark");
    applyModalTextColor(state.config.modal_text_color);
    applyVisibilityConfig(state.config);
    syncLogoStyle();
    syncWindowTitle();
    updateLogsContextMenuSelection();
    scheduleLogTimelineRender({ preserveScroll: true });
    setProviderValue(state.config.download_provider);
    renderQueue();
    return;
  }

  if (type === "clear_logs") {
    if (suppressNextBackendClearEvent) {
      suppressNextBackendClearEvent = false;
      return;
    }
    clearLogTimeline();
    return;
  }

  if (type === "clipboard" && payload.url) {
    itemUrlInput.value = payload.url;
    addLog("Detected workshop URL from clipboard.", "info", {
      source: "clipboard",
      action: "detected_url"
    });
  }
}

async function pollEvents() {
  if (!state.apiAvailable) {
    return;
  }
  if (eventPollInFlight) {
    eventPollRequested = true;
    return;
  }
  eventPollInFlight = true;
  try {
    do {
      eventPollRequested = false;
      const result = await callApi("poll_events", state.lastEventId);
      const events = result?.events || [];
      for (const event of events) {
        await handleEvent(event);
      }
    } while (eventPollRequested && state.apiAvailable && !appShuttingDown);
  } catch {
    // Ignore polling failures; init flow handles no-bridge mode separately.
  } finally {
    eventPollInFlight = false;
  }
}

function startEventPolling() {
  if (appShuttingDown) {
    return;
  }
  if (eventPollTimer) {
    return;
  }
  eventPollTimer = window.setInterval(() => {
    if (appShuttingDown) {
      return;
    }
    pollEvents();
  }, EVENT_POLL_INTERVAL_MS);
}

function revealAppWindow() {
  window.requestAnimationFrame(() => {
    document.body.style.opacity = "1";
  });
}

function beginWindowResize(mode, cursorClass) {
  if (!state.apiAvailable) {
    return;
  }

  if (cursorClass) {
    document.body.classList.add(cursorClass);
  }

  callApi("begin_window_resize", mode)
    .then((result) => {
      if (result && result.success === false && result.error) {
        addLog(result.error, "bad");
      }
    })
    .catch(() => {
      addLog("Window resize failed.", "bad");
    })
    .finally(() => {
      document.body.classList.remove("window-resizing");
      document.body.classList.remove("window-resizing-ew");
      document.body.classList.remove("window-resizing-ns");
    });
}

function wireWindowResizeGrip() {
  const hasAnyHandle = windowResizeEast || windowResizeSouth;
  if (!hasAnyHandle) {
    return;
  }

  if (windowResizeEast) {
    windowResizeEast.addEventListener("mousedown", (event) => {
      if (event.button !== 0) {
        return;
      }
      event.preventDefault();
      beginWindowResize("east", "window-resizing-ew");
    });
  }

  if (windowResizeSouth) {
    windowResizeSouth.addEventListener("mousedown", (event) => {
      if (event.button !== 0) {
        return;
      }
      event.preventDefault();
      beginWindowResize("south", "window-resizing-ns");
    });
  }
}

async function init() {
  if (started) {
    return;
  }
  started = true;
  renderLogTimeline();
  initAllAnimatedSelects(document);
  applyWorkshopHelpTooltip();
  updateQueueStatisticsTooltip();

  wireCommandPalette();
  wireCommandSplitMenu();
  wireQueueContextMenu();
  wireLogsContextMenu();
  wireLogToolbar();
  wireHeaderContextMenu();
  wireQueueVirtualization();
  wireQueueRowInteractions();
  wireGlobalShortcuts();
  wireWindowResizeGrip();
  window.addEventListener("resize", () => {
    scheduleLogTimelineRender({ preserveScroll: true });
  });
  await wireControlButtons();
  wireFilterControls();

  try {
    const data = await callApi("get_bootstrap_data");
    state.apiAvailable = true;
    await useBootstrapData(data);
    addLog("Connected to Python API.", "good");
    startEventPolling();
  } catch (error) {
    applyTheme("Dark");
    applyModalTextColor("");
    state.apiAvailable = false;
    addLog(`Running without PyWebView bridge: ${error.message}`, "bad");
  }
  emitStartupLogToneTests();

  queueForm.addEventListener("submit", handleAddToQueue);

  downloadNowBtn.addEventListener("click", async () => {
    const itemUrl = itemUrlInput.value.trim();
    const provider = providerSelect.value || "Default";
    if (!itemUrl) {
      addLog("No workshop URL/ID entered.", "bad");
      return;
    }
    try {
      const request = callApi("download_workshop_item_now", itemUrl, "", provider);
      void pollEvents();
      const result = await request;
      void pollEvents();
      if (!result?.success) {
        addLog(result?.error || "Download-now failed.", "bad");
        return;
      }
      state.isDownloading = true;
      syncStartButton();
      addLog("Queued for immediate download.", "good");
      queueForm.reset();
      await refreshQueue({ forceReload: true });
    } catch {
      addLog("Download-now is only available from desktop app.", "bad");
    }
  });

  urlHelpBtn.addEventListener("click", async () => {
    try {
      await openWorkshopInputHelpDialog();
    } catch (error) {
      addLog(error?.message || "Failed to open workshop input help.", "bad");
    }
  });

  openDownloadsBtn.addEventListener("click", async () => {
    try {
      const selected = Array.from(state.selectedModIds);
      const targetModId = selected.length === 1 ? selected[0] : null;
      const result = await callApi("open_downloads_folder", targetModId);
      if (!result.success) {
        addLog(result.error || "Failed to open Downloads folder.", "bad");
      }
    } catch {
      addLog("Open Downloads Folder is only available from desktop app.", "bad");
    }
  });

  startDownloadBtn.addEventListener("click", async () => {
    try {
      if (state.cancelPending) {
        return;
      }
      if (state.isDownloading) {
        const result = await callApi("cancel_download");
        if (!result?.success) {
          addLog(result?.error || "Failed to cancel download.", "bad");
          return;
        }
        if (result.mode === "after_batch") {
          state.cancelPending = true;
          syncStartButton();
          addLog("Cancellation requested. Waiting for current batch to complete.");
        } else {
          state.isDownloading = false;
          state.cancelPending = false;
          syncStartButton();
          addLog("Cancellation requested.");
        }
        return;
      }
      const request = callApi("start_download");
      void pollEvents();
      const result = await request;
      void pollEvents();
      if (!result?.success) {
        addLog(result?.error || "Failed to start download.", "bad");
        return;
      }
      state.isDownloading = true;
      state.cancelPending = false;
      syncStartButton();
    } catch {
      addLog("Start/Cancel download is only available from desktop app.", "bad");
    }
  });

  providerSelect.addEventListener("change", async () => {
    try {
      const provider = providerSelect.value || "Default";
      syncProviderDisplay();
      const shouldOverride = state.queueStats.total > 0
        ? await showConfirmDialog({
          title: "Apply Provider Change",
          message: "Apply provider change to existing queue items?",
          okLabel: "Apply",
          cancelLabel: "Only New"
        })
        : false;
      const result = await callApi("set_global_provider", provider, shouldOverride);
      if (!result?.success) {
        addLog(result?.error || "Failed to set provider.", "bad");
        return;
      }
      state.config.download_provider = provider;
      if (shouldOverride) {
        await refreshQueue({ forceReload: true });
        addLog(`Provider updated for ${result.changed || 0} queued mods.`);
      }
    } catch {
      addLog("Provider update failed.", "bad");
    }
  });

  accountSelect.addEventListener("change", async () => {
    try {
      const result = await callApi("set_active_account", accountSelect.value);
      if (!result?.success) {
        addLog(result?.error || "Failed to set active account.", "bad");
        return;
      }
      addLog(`Active account set to '${accountSelect.value}'.`, "good");
    } catch {
      addLog("Failed to set active account.", "bad");
    }
  });

  minimizeBtn.addEventListener("click", async () => {
    try {
      const result = await callApi("minimize_window");
      if (!result?.success) {
        addLog(result?.error || "Failed to minimize window.", "bad");
      }
    } catch {
      addLog("Minimize is only available from desktop app.", "bad");
    }
  });

  closeBtn.addEventListener("click", async () => {
    try {
      beginAppShutdown();
      const result = await callApi("close_window");
      if (!result?.success) {
        addLog(result?.error || "Failed to close window.", "bad");
      }
    } catch {
      addLog("Close is only available from desktop app.", "bad");
    }
  });

  setFilter("All");
  await refreshQueue({ forceReload: true });
  revealAppWindow();
}

window.addEventListener("pywebviewready", init);
window.addEventListener("DOMContentLoaded", () => setTimeout(init, 200));
window.addEventListener("beforeunload", beginAppShutdown);
