const queueBody = document.getElementById("queue-body");
const queueForm = document.getElementById("queue-form");
const eventLog = document.getElementById("event-log");
const searchInput = document.getElementById("search-input");
const filterBtn = document.getElementById("filter-btn");
const filterPopup = document.getElementById("filter-popup");
const caseBtn = document.getElementById("case-btn");
const regexBtn = document.getElementById("regex-btn");
const caseIcon = document.getElementById("case-icon");
const regexIcon = document.getElementById("regex-icon");
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
const importExportWrap = document.getElementById("import-export-wrap");
const importExportSpacer = document.getElementById("import-export-spacer");
const itemUrlInput = document.getElementById("item-url");
const settingsBtn = document.getElementById("settings-btn");
const accountsBtn = document.getElementById("accounts-btn");
const appidsBtn = document.getElementById("appids-btn");
const commandPaletteBtn = document.getElementById("command-palette-btn");
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
let queueRefreshTimer = null;
let browserQueue = [];
let activeColumnResize = null;
let searchRenderTimer = null;
let appShuttingDown = false;
let tutorialSession = null;
let commandPaletteActions = [];
let commandPaletteResults = [];
let commandPaletteSelectedIndex = 0;
let commandPaletteLastFocusedElement = null;

const MAX_LOG_LINES = 500;
const SEARCH_RENDER_DEBOUNCE_MS = 180;
const VIRTUAL_ROW_HEIGHT_FALLBACK = 18;
const VIRTUAL_OVERSCAN_ROWS = 14;
const VIRTUAL_FETCH_BUFFER_ROWS = 80;
const VIRTUAL_FETCH_MAX_LIMIT = 1200;

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
  show_regex_button: true,
  show_case_button: true,
  show_export_import_buttons: true,
  show_sort_indicator: true,
  show_row_numbers: false,
  header_locked: true,
  queue_tree_default_widths: [115, 90, 230, 100, 95],
  queue_tree_column_widths: null,
  queue_tree_column_hidden: null,
  reset_provider_on_startup: false,
  download_provider: "Default",
  reset_window_size_on_startup: true,
  show_tutorial_on_startup: true
};

const QUEUE_COLUMNS = [
  { key: "game_name", label: "Game", defaultWidth: 115 },
  { key: "mod_id", label: "Mod ID", defaultWidth: 90 },
  { key: "mod_name", label: "Mod Name", defaultWidth: 230 },
  { key: "status", label: "Status", defaultWidth: 100 },
  { key: "provider", label: "Provider", defaultWidth: 95 }
];

function syncProviderDisplay() {
  if (!providerDisplayName) {
    return;
  }
  providerDisplayName.textContent = providerSelect?.value || "Default";
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

function addLog(text, tone = "") {
  const line = document.createElement("p");
  line.className = `log-line ${tone}`.trim();
  line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
  eventLog.prepend(line);
  while (eventLog.childElementCount > MAX_LOG_LINES) {
    const last = eventLog.lastElementChild;
    if (!last) {
      break;
    }
    eventLog.removeChild(last);
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
    modalTitle.textContent = title || "Dialog";
    modalMessage.textContent = message || "";
    modalInput.classList.add("hidden");
    modalInput.value = "";
    modalForm.classList.remove("hidden");
    modalForm.innerHTML = html || "";
    modalOkBtn.textContent = okLabel;
    modalCancelBtn.textContent = cancelLabel;
    modalCancelBtn.style.display = showCancel ? "" : "none";
    modalOverlay.classList.remove("hidden");

    const context = {
      setFormHtml: (newHtml) => {
        modalForm.innerHTML = newHtml || "";
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
}

function isCommandPaletteOpen() {
  return !!commandPaletteOverlay && !commandPaletteOverlay.classList.contains("hidden");
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
          await refreshQueue();
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
  commandPaletteInput.focus();
}

function wireCommandPalette() {
  if (!commandPaletteOverlay || !commandPaletteInput || !commandPaletteList) {
    return;
  }

  commandPaletteBtn?.addEventListener("click", () => {
    if (isCommandPaletteOpen()) {
      closeCommandPalette();
    } else {
      openCommandPalette();
    }
  });

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
  return {
    game_name: gameName,
    mod_id: modId,
    mod_name: modName,
    status,
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
  const signature = `${item.game_name}\x1f${item.mod_id}\x1f${item.mod_name}\x1f${item.status}\x1f${item.provider}`;
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
      const value = String(item[column.key] ?? "");
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
    const key = String(event.key || "").toLowerCase();
    const hasModifier = event.ctrlKey || event.metaKey;

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
  positionFloatingMenu(logsContextMenu, clientX, clientY, 8);
  logsContextMenu.classList.remove("hidden");
}

async function handleLogsContextAction(action) {
  if (action !== "clear_logs") {
    return;
  }
  try {
    const result = await callApi("clear_logs");
    if (!result?.success) {
      addLog(result?.error || "Failed to clear log view.", "bad");
      return;
    }
  } catch {
    // In non-desktop preview mode, still clear local log view.
  }
  eventLog.innerHTML = "";
  addLog("Log view cleared.");
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
      await refreshQueue();
    } else {
      addLog(result?.error || "Failed to remove selected mods.", "bad");
    }
    return;
  }

  if (action === "move_top" || action === "move_up" || action === "move_down" || action === "move_bottom") {
    const direction = action.replace("move_", "");
    const result = await callApi("move_mods", selected, direction);
    if (result?.success) {
      await refreshQueue();
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
      await refreshQueue();
    } else {
      addLog(result?.error || "Failed to change provider.", "bad");
    }
    return;
  }

  if (action === "reset_status") {
    const result = await callApi("reset_status", selected);
    if (result?.success) {
      addLog(`Reset status for ${result.reset || 0} mod(s).`);
      await refreshQueue();
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
      await refreshQueue();
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

function scheduleQueueRefresh() {
  if (queueRefreshTimer) {
    return;
  }
  queueRefreshTimer = window.setTimeout(async () => {
    queueRefreshTimer = null;
    await refreshQueue();
  }, 320);
}

async function refreshQueue() {
  if (state.apiAvailable) {
    const rowHeight = Math.max(18, Number(virtualRowHeight) || VIRTUAL_ROW_HEIGHT_FALLBACK);
    const viewportHeight = Math.max(0, queueTableWrap?.clientHeight || 0);
    const scrollTop = Math.max(0, queueTableWrap?.scrollTop || 0);
    const rowsInView = Math.max(1, Math.ceil(viewportHeight / rowHeight));
    const currentStart = Math.max(0, Math.floor(scrollTop / rowHeight) - VIRTUAL_OVERSCAN_ROWS);
    const currentEnd = Math.max(currentStart + 1, currentStart + rowsInView + (VIRTUAL_OVERSCAN_ROWS * 2));

    await ensureBackendWindowLoaded(currentStart, currentEnd, { forceReload: true });
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
  regexBtn.style.display = config.show_regex_button === false ? "none" : "";
  caseBtn.style.display = config.show_case_button === false ? "none" : "";
  downloadNowBtn.style.display = config.download_button === false ? "none" : "";
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
    accountSelect.appendChild(anonymousOption);
    accounts.forEach((acc) => {
      if (!acc?.username) {
        return;
      }
      const option = document.createElement("option");
      option.value = acc.username;
      option.textContent = acc.username;
      accountSelect.appendChild(option);
    });
    accountSelect.value = active;
  } catch {
    const active = activeFromConfig || "Anonymous";
    if (!Array.from(accountSelect.options).some((x) => x.value === active)) {
      const option = document.createElement("option");
      option.value = active;
      option.textContent = active;
      accountSelect.appendChild(option);
    }
    accountSelect.value = active;
  }
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
        await handleLogsContextAction(button.dataset.action);
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
  return `
    <div class="settings-shell">
      <div class="settings-nav">
        <button class="settings-nav-item active" type="button" data-settings-page-btn="appearance">Appearance</button>
        <button class="settings-nav-item" type="button" data-settings-page-btn="download">Download Options</button>
        <button class="settings-nav-item" type="button" data-settings-page-btn="tools">Tools</button>
        <button class="settings-nav-item" type="button" data-settings-page-btn="system">System</button>
        <div class="settings-nav-spacer"></div>
        <button id="st-reset-defaults" class="control settings-reset-btn" type="button">Reset to Defaults</button>
      </div>

      <div class="settings-page-wrap">
        <section class="settings-page active" data-settings-page="appearance">
          <div class="form-grid">
            <div class="form-block">
              <label for="st-theme">Theme</label>
              <select id="st-theme" class="form-control">
                <option value="Dark" ${settings.current_theme === "Dark" ? "selected" : ""}>Dark</option>
                <option value="Light" ${settings.current_theme === "Light" ? "selected" : ""}>Light</option>
              </select>
            </div>
            <div class="form-block">
              <label for="st-logo">Logo Style</label>
              <select id="st-logo" class="form-control">
                <option value="Light" ${settings.logo_style === "Light" ? "selected" : ""}>Light</option>
                <option value="Dark" ${settings.logo_style === "Dark" ? "selected" : ""}>Dark</option>
                <option value="Darker" ${settings.logo_style === "Darker" ? "selected" : ""}>Darker</option>
              </select>
            </div>
          </div>
          <div class="form-divider"></div>
          <div class="settings-section-subtitle">Show</div>
          <div class="form-grid">
            <label class="form-checkbox-row"><input id="st-download-btn" type="checkbox" ${settings.download_button ? "checked" : ""}>Download Button</label>
            <label class="form-checkbox-row"><input id="st-search-bar" type="checkbox" ${settings.show_searchbar ? "checked" : ""}>Search Bar</label>
            <label class="form-checkbox-row"><input id="st-regex-btn" type="checkbox" ${settings.show_regex_button ? "checked" : ""}>Regex Button</label>
            <label class="form-checkbox-row"><input id="st-case-btn" type="checkbox" ${settings.show_case_button ? "checked" : ""}>Case Button</label>
            <label class="form-checkbox-row"><input id="st-import-export" type="checkbox" ${settings.show_export_import_buttons ? "checked" : ""}>Import/Export Buttons</label>
            <label class="form-checkbox-row"><input id="st-logs" type="checkbox" ${settings.show_logs ? "checked" : ""}>Logs View</label>
            <label class="form-checkbox-row"><input id="st-provider-show" type="checkbox" ${settings.show_provider ? "checked" : ""}>Download Provider</label>
          </div>
        </section>

        <section class="settings-page" data-settings-page="download">
          <div class="form-grid">
            <div class="form-block">
              <label for="st-provider">Default Provider</label>
              <select id="st-provider" class="form-control">
                <option value="Default" ${settings.download_provider === "Default" ? "selected" : ""}>Default</option>
                <option value="SteamCMD" ${settings.download_provider === "SteamCMD" ? "selected" : ""}>SteamCMD</option>
                <option value="SteamWebAPI" ${settings.download_provider === "SteamWebAPI" ? "selected" : ""}>SteamWebAPI</option>
              </select>
            </div>
            <div class="form-block">
              <label for="st-batch">Batch Size</label>
              <input id="st-batch" class="form-control" type="number" min="1" max="500" value="${Number(settings.batch_size || 20)}">
            </div>
            <div class="form-block" style="grid-column: 1 / -1;">
              <label for="st-existing">SteamCMD Existing Mods</label>
              <select id="st-existing" class="form-control">
                <option value="Only Redownload if Updated" ${settings.steamcmd_existing_mod_behavior === "Only Redownload if Updated" ? "selected" : ""}>Only Redownload if Updated</option>
                <option value="Always Redownload" ${settings.steamcmd_existing_mod_behavior === "Always Redownload" ? "selected" : ""}>Always Redownload</option>
                <option value="Skip Existing Mods" ${settings.steamcmd_existing_mod_behavior === "Skip Existing Mods" ? "selected" : ""}>Skip Existing Mods</option>
              </select>
            </div>
            <div class="form-block">
              <label for="st-folder-format">SteamCMD Folder Naming</label>
              <select id="st-folder-format" class="form-control">
                <option value="id" ${settings.folder_naming_format === "id" ? "selected" : ""}>Mod ID</option>
                <option value="name" ${settings.folder_naming_format === "name" ? "selected" : ""}>Mod Name</option>
                <option value="combined" ${settings.folder_naming_format === "combined" ? "selected" : ""}>ID + Name</option>
              </select>
            </div>
          </div>
          <div class="form-divider"></div>
          <div class="form-grid">
            <label class="form-checkbox-row"><input id="st-queue-workshop" type="checkbox" ${settings.show_queue_entire_workshop !== false ? "checked" : ""}>Allow Queue Entire Workshop</label>
            <label class="form-checkbox-row"><input id="st-keep-downloaded" type="checkbox" ${settings.keep_downloaded_in_queue ? "checked" : ""}>Keep Downloaded In Queue</label>
            <label class="form-checkbox-row"><input id="st-delete-on-cancel" type="checkbox" ${settings.delete_downloads_on_cancel ? "checked" : ""}>Delete Downloads On Cancel</label>
          </div>
        </section>

        <section class="settings-page" data-settings-page="tools">
          <div class="form-grid">
            <label class="form-checkbox-row"><input id="st-auto-detect" type="checkbox" ${settings.auto_detect_urls ? "checked" : ""}>Auto-detect Clipboard URLs</label>
            <label class="form-checkbox-row"><input id="st-auto-add" type="checkbox" ${settings.auto_add_to_queue ? "checked" : ""}>Auto-add Detected URLs</label>
          </div>
        </section>

        <section class="settings-page" data-settings-page="system">
          <div class="settings-section-subtitle">On Startup</div>
          <div class="form-grid">
            <label class="form-checkbox-row"><input id="st-reset-provider" type="checkbox" ${settings.reset_provider_on_startup ? "checked" : ""}>Reset Provider</label>
            <label class="form-checkbox-row"><input id="st-reset-window" type="checkbox" ${settings.reset_window_size_on_startup ? "checked" : ""}>Reset Window Size</label>
            <label class="form-checkbox-row"><input id="st-show-tutorial" type="checkbox" ${settings.show_tutorial_on_startup ? "checked" : ""}>Show Tutorialp</label>
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
    message: "Update Streamline settings.",
    html: buildSettingsFormHtml(settings),
    okLabel: "Apply",
    onMount: (root) => {
      const pageButtons = Array.from(root.querySelectorAll("[data-settings-page-btn]"));
      const pages = Array.from(root.querySelectorAll("[data-settings-page]"));
      const autoDetect = root.querySelector("#st-auto-detect");
      const autoAdd = root.querySelector("#st-auto-add");
      const showSearchbar = root.querySelector("#st-search-bar");
      const showRegex = root.querySelector("#st-regex-btn");
      const showCase = root.querySelector("#st-case-btn");
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
      const syncSearchDependents = () => {
        const enabled = !!showSearchbar.checked;
        setFieldEnabled(showRegex, enabled);
        setFieldEnabled(showCase, enabled);
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
        setCheck("st-regex-btn", SETTINGS_DEFAULTS.show_regex_button);
        setCheck("st-case-btn", SETTINGS_DEFAULTS.show_case_button);
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
        syncSearchDependents();
      };
      pageButtons.forEach((button) => {
        button.addEventListener("click", () => {
          setSettingsPage(button.dataset.settingsPageBtn || "appearance");
        });
      });
      autoDetect.addEventListener("change", syncAutoAdd);
      showSearchbar.addEventListener("change", syncSearchDependents);
      resetDefaultsBtn.addEventListener("click", () => {
        resetFormToDefaults();
        addLog("Settings reset to defaults in the dialog. Click Apply to save.", "good");
      });
      setSettingsPage("appearance");
      syncAutoAdd();
      syncSearchDependents();
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
        show_regex_button: root.querySelector("#st-regex-btn").checked,
        show_case_button: root.querySelector("#st-case-btn").checked,
        show_export_import_buttons: root.querySelector("#st-import-export").checked,
        show_logs: root.querySelector("#st-logs").checked,
        show_provider: root.querySelector("#st-provider-show").checked,
        show_queue_entire_workshop: root.querySelector("#st-queue-workshop").checked,
        keep_downloaded_in_queue: root.querySelector("#st-keep-downloaded").checked,
        delete_downloads_on_cancel: root.querySelector("#st-delete-on-cancel").checked,
        auto_detect_urls: root.querySelector("#st-auto-detect").checked,
        auto_add_to_queue: root.querySelector("#st-auto-add").checked,
        show_tutorial_on_startup: root.querySelector("#st-show-tutorial").checked,
        tutorial_shown: true,
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

function buildAccountsFormHtml(data) {
  const accounts = data?.accounts || [];
  const rows = accounts.length
    ? accounts.map((acc) => `
      <div class="accounts-item">
        <span class="accounts-name">${escapeHtml(acc.username)}</span>
        <div class="form-actions-inline">
          <button class="control modal-btn" type="button" data-account-action="remove" data-username="${escapeHtml(acc.username)}">Remove</button>
        </div>
      </div>
    `).join("")
    : `<p style="margin:4px 0;">No accounts configured.</p>`;

  return `
    <div class="form-grid">
      <div class="form-block">
        <label for="acc-username">Username</label>
        <input id="acc-username" class="form-control" type="text" placeholder="Steam username">
      </div>
    </div>
    <div class="form-actions-inline">
      <button id="acc-add" class="control modal-btn primary" type="button">Add Account</button>
      <button id="acc-purge" class="control modal-btn" type="button">Purge All</button>
    </div>
    <div class="form-divider"></div>
    <div class="accounts-list">${rows}</div>
  `;
}

function buildSteamcmdLoginHtml(username) {
  return `
    <div class="steamcmd-login-shell">
      <div id="steamcmd-login-status" class="steamcmd-login-status">Starting SteamCMD session for ${escapeHtml(username)}...</div>
      <pre id="steamcmd-login-output" class="steamcmd-login-output" tabindex="0"></pre>
      <div class="steamcmd-login-input-row">
        <input id="steamcmd-login-input" class="form-control" type="text" placeholder="Type password, Steam Guard code, or command and press Send">
        <button id="steamcmd-login-send" class="control modal-btn primary" type="button">Send</button>
      </div>
    </div>
  `;
}

async function openSteamcmdLoginTerminal(username) {
  let pollTimer = null;
  let closeWatch = null;
  let disposed = false;
  let autoCloseTriggered = false;
  let sendUnlocked = false;

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

  await showFormModal({
    title: `SteamCMD Login: ${username}`,
    message: "Live SteamCMD terminal. Send password/Steam Guard code when prompted.",
    html: buildSteamcmdLoginHtml(username),
    okLabel: "Done",
    cancelLabel: "Abort",
    showCancel: true,
    onMount: (root) => {
      const outputEl = root.querySelector("#steamcmd-login-output");
      const inputEl = root.querySelector("#steamcmd-login-input");
      const sendBtn = root.querySelector("#steamcmd-login-send");
      const statusEl = root.querySelector("#steamcmd-login-status");
      sendBtn.disabled = true;
      let followOutput = true;

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

      const copyText = async (text) => {
        if (!text) {
          return false;
        }
        try {
          await navigator.clipboard.writeText(text);
          return true;
        } catch {
          try {
            const temp = document.createElement("textarea");
            temp.value = text;
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
            const copied = await copyText(selectedText);
            if (copied) {
              event.preventDefault();
              statusEl.textContent = `Copied ${selectedText.length} characters from SteamCMD output.`;
            }
          }
        }
      });

      const ensureAccountInList = async (candidateName) => {
        const normalized = (candidateName || username || "").trim();
        if (!normalized) {
          return false;
        }
        const result = await callApi("add_account", normalized);
        if (result?.success) {
          addLog(`Added account '${normalized}'.`, "good");
          return true;
        }
        const errText = String(result?.error || "").toLowerCase();
        if (errText.includes("already exists")) {
          return true;
        }
        addLog(result?.error || `Failed to add account '${normalized}'.`, "bad");
        return false;
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
        if (!sendUnlocked && (res.prompt === "password" || res.prompt === "steam_guard")) {
          sendUnlocked = true;
          sendBtn.disabled = false;
          statusEl.textContent = "Prompt detected. Enter password/code and click Send.";
        }
        const accountLabel = (res.detected_username || res.username || username || "").trim();
        const steamidSuffix = res.detected_steamid64 ? ` (SteamID64: ${res.detected_steamid64})` : "";

        if (res.login_failed) {
          statusEl.textContent = "SteamCMD reported a login failure. Check credentials/guard and retry.";
        } else if (res.account_added) {
          statusEl.textContent = `Login detected for '${accountLabel || "account"}'${steamidSuffix}.`;
          if (!autoCloseTriggered) {
            autoCloseTriggered = true;
            try {
              await ensureAccountInList(accountLabel || username);
              await refreshAccounts(accountLabel || username);
            } catch (error) {
              addLog(error?.message || "Failed to refresh account list after login.", "bad");
            }
            statusEl.textContent = `Account '${accountLabel || "account"}' added. Closing...`;
            window.setTimeout(() => modalOkBtn.click(), 0);
            return;
          }
        } else if (res.prompt === "password") {
          statusEl.textContent = "Prompt: Password required.";
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
}

async function openAccountsManager() {
  let accountData = await callApi("get_accounts");

  await showFormModal({
    title: "Accounts Manager",
    message: "Manage Steam accounts. Add Account opens SteamCMD authentication for the entered username.",
    html: buildAccountsFormHtml(accountData),
    okLabel: "Close",
    showCancel: false,
    onMount: (root, context) => {
      const bindActions = () => {
        const usernameInput = root.querySelector("#acc-username");
        const addBtn = root.querySelector("#acc-add");
        const purgeBtn = root.querySelector("#acc-purge");

        const refreshAccountsModal = async (successMessage = "") => {
          accountData = await callApi("get_accounts");
          context.setFormHtml(buildAccountsFormHtml(accountData));
          root = modalForm;
          bindActions();
          await refreshAccounts(accountData?.active || "Anonymous");
          if (successMessage) {
            addLog(successMessage, "good");
          }
        };

        addBtn.addEventListener("click", async () => {
          const username = (usernameInput.value || "").trim();
          if (!username) {
            addLog("Username is required to add account.", "bad");
            return;
          }
          const result = await callApi("launch_steamcmd_login", username);
          if (!result?.success) {
            addLog(result?.error || `Failed to open SteamCMD login for '${username}'.`, "bad");
            return;
          }
          if (result.mode === "conpty") {
            addLog(`Opened embedded SteamCMD terminal for '${username}'.`, "good");
            await openSteamcmdLoginTerminal(username);
            await refreshAccountsModal(`Completed SteamCMD login flow for '${username}'.`);
            return;
          }
          await refreshAccountsModal(`Opened SteamCMD login for '${username}'.`);
        });

        purgeBtn.addEventListener("click", async () => {
          const confirmed = await showConfirmDialog({
            title: "Purge Accounts",
            message: "Purge all configured accounts?",
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
          await refreshAccountsModal("Purged all accounts.");
        });

        root.querySelectorAll("[data-account-action='remove']").forEach((button) => {
          button.addEventListener("click", async () => {
            const username = button.dataset.username || "";
            const result = await callApi("remove_account", username);
            if (!result?.success) {
              addLog(result?.error || `Failed to remove '${username}'.`, "bad");
              return;
            }
            await refreshAccountsModal(`Removed account '${username}'.`);
          });
        });

      };

      bindActions();
    },
    onSubmit: () => true
  });
}

async function openAppIdsManager() {
  const info = await callApi("get_appids_info");
  const currentCount = info?.count ?? 0;
  const lastUpdated = info?.last_updated || "N/A";
  const html = `
    <div class="form-grid">
      <div class="form-block">
        <label>Current AppIDs</label>
        <input class="form-control" type="text" value="${currentCount}" readonly>
      </div>
      <div class="form-block">
        <label>Last Updated</label>
        <input class="form-control" type="text" value="${escapeHtml(lastUpdated)}" readonly>
      </div>
    </div>
    <div class="form-divider"></div>
    <div class="form-grid">
      <label class="form-checkbox-row"><input id="appid-game" type="checkbox" checked>Game</label>
      <label class="form-checkbox-row"><input id="appid-application" type="checkbox">Application</label>
      <label class="form-checkbox-row"><input id="appid-tool" type="checkbox">Tool</label>
    </div>
  `;

  await showFormModal({
    title: "Update AppIDs",
    message: "Select entry types to refresh from SteamDB.",
    html,
    okLabel: "Update",
    onSubmit: async (root) => {
      const selectedTypes = [];
      if (root.querySelector("#appid-game").checked) {
        selectedTypes.push("Game");
      }
      if (root.querySelector("#appid-application").checked) {
        selectedTypes.push("Application");
      }
      if (root.querySelector("#appid-tool").checked) {
        selectedTypes.push("Tool");
      }
      if (!selectedTypes.length) {
        addLog("Select at least one type to update AppIDs.", "bad");
        return false;
      }

      const result = await callApi("update_appids", selectedTypes);
      if (result?.success) {
        addLog(`AppIDs updated (${result.count} entries).`, "good");
        return true;
      }
      addLog(result?.error || "Failed to update AppIDs.", "bad");
      return false;
    }
  });
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
        ? "Welcome back. This guided tour highlights the main controls in the app."
        : "This guided tour highlights the main controls in the app.",
      selectors: []
    },
    {
      title: "Command Palette",
      message: "Use Commands for quick access to appearance, tools, and help actions.",
      selectors: ["#command-palette-btn"]
    },
    {
      title: "Workshop Input",
      message: "Paste a Game AppID, Mod URL/ID, or Collection URL/ID here.",
      selectors: ["#item-url"]
    },
    {
      title: "Queue Actions",
      message: "Use these buttons to add to queue or download immediately.",
      selectors: ["#add-to-queue-btn", "#download-now-btn"]
    },
    {
      title: "Queue Table",
      message: "Review queued mods here. Right-click rows for move/provider/remove actions.",
      selectors: [".queue-table-wrap"]
    },
    {
      title: "Download Controls",
      message: "Start download here. Press again during active download to request cancellation.",
      selectors: ["#start-download-btn"]
    },
    {
      title: "Logs",
      message: "Live events appear here. Right-click this area to clear logs.",
      selectors: ["#log-wrap"]
    }
  ];

  let index = 0;
  let pendingTarget = null;

  const done = new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "tutorial-overlay";
    overlay.innerHTML = `
      <div class="tutorial-spotlight hidden"></div>
      <section class="tutorial-card" role="dialog" aria-modal="true" aria-label="Quick Tutorial">
        <div class="tutorial-step-meta"></div>
        <h3 class="tutorial-title"></h3>
        <p class="tutorial-message"></p>
        <label class="tutorial-startup-toggle">
          <input id="tutorial-show-startup-checkbox" type="checkbox">
          Show tutorial on startup
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
    const titleEl = overlay.querySelector(".tutorial-title");
    const messageEl = overlay.querySelector(".tutorial-message");
    const startupCheckbox = overlay.querySelector("#tutorial-show-startup-checkbox");
    const prevBtn = overlay.querySelector("[data-tutorial-action='prev']");
    const nextBtn = overlay.querySelector("[data-tutorial-action='next']");
    const skipBtn = overlay.querySelector("[data-tutorial-action='skip']");

    const isElementVisible = (el) => {
      if (!el) {
        return false;
      }
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") {
        return false;
      }
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    };

    const findStepTarget = (step) => {
      const selectors = Array.isArray(step?.selectors) ? step.selectors : [];
      for (const selector of selectors) {
        if (!selector) {
          continue;
        }
        const node = document.querySelector(selector);
        if (node && isElementVisible(node)) {
          return node;
        }
      }
      return null;
    };

    const clamp = (value, min, max) => Math.max(min, Math.min(value, max));

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

    const positionStep = () => {
      const target = pendingTarget;
      if (!target || !isElementVisible(target)) {
        spotlight.classList.add("hidden");
        placeCard(null);
        return;
      }

      const rect = target.getBoundingClientRect();
      const pad = 6;
      spotlight.classList.remove("hidden");
      spotlight.style.left = `${Math.max(0, rect.left - pad)}px`;
      spotlight.style.top = `${Math.max(0, rect.top - pad)}px`;
      spotlight.style.width = `${Math.max(12, rect.width + pad * 2)}px`;
      spotlight.style.height = `${Math.max(12, rect.height + pad * 2)}px`;
      placeCard(rect);
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

    const finish = async () => {
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
      titleEl.textContent = String(step.title || "Tutorial");
      messageEl.textContent = String(step.message || "");
      prevBtn.disabled = index === 0;
      nextBtn.textContent = index >= (steps.length - 1) ? "Finish" : "Next";
      startupCheckbox.checked = !!showOnStartupSetting;

      pendingTarget = findStepTarget(step);
      if (pendingTarget && typeof pendingTarget.scrollIntoView === "function") {
        pendingTarget.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
      }
      window.setTimeout(positionStep, 120);
    };

    startupCheckbox.addEventListener("change", () => {
      showOnStartupSetting = !!startupCheckbox.checked;
    });

    prevBtn.addEventListener("click", () => {
      index -= 1;
      renderStep();
    });

    nextBtn.addEventListener("click", async () => {
      if (index >= (steps.length - 1)) {
        await finish();
        return;
      }
      index += 1;
      renderStep();
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
    renderStep();
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
  bindCommandToButton(settingsBtn, "open_settings");
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
    caseIcon.src = state.caseSensitive ? "../case_enabled.png" : "../case_disabled.png";
    state.searchMatcherCache.matcher = null;
    scheduleSearchRender(0);
  });

  regexBtn.addEventListener("click", () => {
    state.regex = !state.regex;
    regexBtn.classList.toggle("active", state.regex);
    regexIcon.src = state.regex ? "../regex_enabled.png" : "../regex_disabled.png";
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
    const result = await callApi("add_workshop_item", itemUrl, "", provider);
    if (!result?.success) {
      addLog(result?.error || "Failed to add to queue.", "bad");
      return;
    }
    if (result.queued_in_background) {
      addLog("Building entire workshop queue in background. Items will appear progressively.", "good");
    } else if (typeof result.added === "number") {
      addLog(`Queue updated: ${result.added} added, ${result.skipped || 0} skipped.`, "good");
    } else if (result.queue_item) {
      addLog(`Queued ${result.queue_item.mod_id}.`, "good");
    } else {
      addLog("Item queued.", "good");
    }
  } catch {
    browserQueue.push(createBrowserQueueItem(itemUrl, provider));
    addLog("Queued in preview mode (local browser state).", "good");
  }

  queueForm.reset();
  setProviderValue(provider);
  await refreshQueue();
}

async function handleEvent(event) {
  if (!event || typeof event.id !== "number") {
    return;
  }
  state.lastEventId = Math.max(state.lastEventId, event.id);

  const type = event.type;
  const payload = event.payload || {};

  if (type === "log") {
    addLog(payload.message || "", payload.tone || "");
    return;
  }

  if (type === "queue" || type === "queue_status") {
    scheduleQueueRefresh();
    return;
  }

  if (type === "download") {
    const status = payload.state;
    if (status === "started") {
      state.isDownloading = true;
      state.cancelPending = false;
      addLog("Download started.", "good");
    } else if (status === "finished") {
      state.isDownloading = false;
      state.cancelPending = false;
      addLog("Download finished.", "good");
    } else if (status === "canceled") {
      state.isDownloading = false;
      state.cancelPending = false;
      addLog("Download canceled.");
    } else if (status === "error") {
      state.isDownloading = false;
      state.cancelPending = false;
      addLog(payload.error || "Download error.", "bad");
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
    setProviderValue(state.config.download_provider);
    renderQueue();
    return;
  }

  if (type === "clear_logs") {
    eventLog.innerHTML = "";
    return;
  }

  if (type === "clipboard" && payload.url) {
    itemUrlInput.value = payload.url;
    addLog("Detected workshop URL from clipboard.");
  }
}

async function pollEvents() {
  if (!state.apiAvailable) {
    return;
  }
  try {
    const result = await callApi("poll_events", state.lastEventId);
    const events = result?.events || [];
    for (const event of events) {
      await handleEvent(event);
    }
  } catch {
    // Ignore polling failures; init flow handles no-bridge mode separately.
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
  }, 1000);
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
  applyWorkshopHelpTooltip();
  updateQueueStatisticsTooltip();

  wireCommandPalette();
  wireQueueContextMenu();
  wireLogsContextMenu();
  wireHeaderContextMenu();
  wireQueueVirtualization();
  wireQueueRowInteractions();
  wireGlobalShortcuts();
  wireWindowResizeGrip();
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

  queueForm.addEventListener("submit", handleAddToQueue);

  downloadNowBtn.addEventListener("click", async () => {
    const itemUrl = itemUrlInput.value.trim();
    const provider = providerSelect.value || "Default";
    if (!itemUrl) {
      addLog("No workshop URL/ID entered.", "bad");
      return;
    }
    try {
      const result = await callApi("download_workshop_item_now", itemUrl, "", provider);
      if (!result?.success) {
        addLog(result?.error || "Download-now failed.", "bad");
        return;
      }
      state.isDownloading = true;
      syncStartButton();
      addLog("Queued and started download.", "good");
      queueForm.reset();
      await refreshQueue();
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
      if (result.success) {
        addLog(`Opened Downloads folder: ${result.message}`, "good");
      } else {
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
      const result = await callApi("start_download");
      if (!result?.success) {
        addLog(result?.error || "Failed to start download.", "bad");
        return;
      }
      state.isDownloading = true;
      state.cancelPending = false;
      syncStartButton();
      addLog("Download started.", "good");
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
        await refreshQueue();
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
      addLog(`Active account set to ${accountSelect.value}.`);
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
  await refreshQueue();
  revealAppWindow();
}

window.addEventListener("pywebviewready", init);
window.addEventListener("DOMContentLoaded", () => setTimeout(init, 200));
window.addEventListener("beforeunload", beginAppShutdown);
