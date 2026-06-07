/**
 * Popup script for AI Career Agent LinkedIn Extension.
 * Handles saving/loading settings from chrome.storage.sync, testing API connection,
 * and triggering job capture from the currently active LinkedIn tab.
 *
 * Requirements: 12.1, 12.3
 */

const STORAGE_KEYS = {
  API_URL: "apiBaseUrl",
  AUTH_TOKEN: "authToken",
};

// DOM Elements — Settings
const form = document.getElementById("settingsForm");
const apiUrlInput = document.getElementById("apiUrl");
const authTokenInput = document.getElementById("authToken");
const saveBtn = document.getElementById("saveBtn");
const testBtn = document.getElementById("testBtn");
const messageEl = document.getElementById("message");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

// DOM Elements — Capture
const captureBtn = document.getElementById("captureBtn");
const captureResult = document.getElementById("captureResult");
const captureSection = document.getElementById("captureSection");

/**
 * Load saved settings from chrome.storage.sync and populate the form.
 */
async function loadSettings() {
  try {
    const data = await chrome.storage.sync.get([
      STORAGE_KEYS.API_URL,
      STORAGE_KEYS.AUTH_TOKEN,
    ]);

    if (data[STORAGE_KEYS.API_URL]) {
      apiUrlInput.value = data[STORAGE_KEYS.API_URL];
    }
    if (data[STORAGE_KEYS.AUTH_TOKEN]) {
      authTokenInput.value = data[STORAGE_KEYS.AUTH_TOKEN];
    }

    // Auto-test connection if settings exist
    if (data[STORAGE_KEYS.API_URL] && data[STORAGE_KEYS.AUTH_TOKEN]) {
      await testConnection(data[STORAGE_KEYS.API_URL], data[STORAGE_KEYS.AUTH_TOKEN]);
    }
  } catch (error) {
    showMessage("Failed to load settings", "error");
  }
}

/**
 * Save settings to chrome.storage.sync.
 */
async function saveSettings(apiUrl, authToken) {
  try {
    await chrome.storage.sync.set({
      [STORAGE_KEYS.API_URL]: apiUrl.replace(/\/+$/, ""), // Remove trailing slash
      [STORAGE_KEYS.AUTH_TOKEN]: authToken,
    });
    showMessage("Settings saved successfully", "success");
  } catch (error) {
    showMessage("Failed to save settings: " + error.message, "error");
  }
}

/**
 * Test connection to the API by making a health check request.
 */
async function testConnection(apiUrl, authToken) {
  setStatus("checking");

  try {
    const url = apiUrl.replace(/\/+$/, "");
    const response = await fetch(`${url}/api/health`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });

    if (response.ok) {
      setStatus("connected");
      showMessage("Connected to API successfully", "success");
    } else if (response.status === 401) {
      setStatus("error");
      showMessage("Authentication failed — check your token", "error");
    } else {
      setStatus("error");
      showMessage(`API returned status ${response.status}`, "error");
    }
  } catch (error) {
    setStatus("error");
    showMessage("Cannot reach API — check the URL", "error");
  }
}

/**
 * Update the connection status indicator.
 * @param {"connected" | "error" | "checking" | "disconnected"} status
 */
function setStatus(status) {
  statusDot.className = "status-dot";
  switch (status) {
    case "connected":
      statusDot.classList.add("status-connected");
      statusText.textContent = "Connected";
      break;
    case "error":
      statusDot.classList.add("status-error");
      statusText.textContent = "Connection error";
      break;
    case "checking":
      statusDot.classList.add("status-checking");
      statusText.textContent = "Checking...";
      break;
    default:
      statusText.textContent = "Not connected";
  }
}

/**
 * Display a temporary message to the user.
 * @param {string} text
 * @param {"success" | "error" | "info"} type
 */
function showMessage(text, type = "info") {
  messageEl.textContent = text;
  messageEl.className = `message message-${type}`;
  messageEl.style.display = "block";

  setTimeout(() => {
    messageEl.style.display = "none";
  }, 4000);
}

/**
 * Show capture result in the popup.
 * @param {"success" | "duplicate" | "error"} type
 * @param {string} message
 */
function showCaptureResult(type, message) {
  const colors = {
    success: { bg: "#d4edda", text: "#155724" },
    duplicate: { bg: "#fff3cd", text: "#856404" },
    error: { bg: "#f8d7da", text: "#721c24" },
  };

  const style = colors[type] || colors.error;

  captureResult.textContent = message;
  captureResult.style.display = "block";
  captureResult.style.backgroundColor = style.bg;
  captureResult.style.color = style.text;

  // Auto-hide after 6 seconds
  setTimeout(() => {
    captureResult.style.display = "none";
  }, 6000);
}

/**
 * Handle the "Capture Current Job" button click.
 * Sends a message to the background script to orchestrate extraction and API submission.
 */
async function handleCaptureClick() {
  // Update button to loading state
  captureBtn.textContent = "⏳ Capturing...";
  captureBtn.disabled = true;
  captureResult.style.display = "none";

  try {
    const response = await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { action: "captureCurrentTab" },
        (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(response);
          }
        }
      );
    });

    if (response && response.success) {
      if (response.status === "created") {
        showCaptureResult("success", "✅ Job captured successfully!");
      } else if (response.status === "duplicate") {
        showCaptureResult("duplicate", "⚠️ Job already in your list.");
      } else {
        showCaptureResult("success", response.message || "✅ Done!");
      }
    } else {
      const errorMsg =
        response && response.error ? response.error : "Failed to capture job.";
      showCaptureResult("error", "❌ " + errorMsg);
    }
  } catch (err) {
    showCaptureResult("error", "❌ " + err.message);
  } finally {
    // Restore button state
    captureBtn.textContent = "📋 Capture Current Job";
    captureBtn.disabled = false;
  }
}

/**
 * Check if the active tab is a LinkedIn job page and update capture button state.
 */
async function updateCaptureButtonState() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs.length > 0) {
      const tab = tabs[0];
      const isJobPage =
        tab.url && tab.url.includes("linkedin.com/jobs/view/");

      if (isJobPage) {
        captureBtn.disabled = false;
        captureBtn.title = "Capture the job on this page";
      } else {
        captureBtn.disabled = true;
        captureBtn.title = "Navigate to a LinkedIn job page to capture";
        captureBtn.style.opacity = "0.5";
      }
    }
  } catch (error) {
    // If we can't query tabs, leave button enabled
    console.log("[AI Career Agent] Could not query active tab:", error);
  }
}

// Event Listeners
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const apiUrl = apiUrlInput.value.trim();
  const authToken = authTokenInput.value.trim();

  if (!apiUrl || !authToken) {
    showMessage("Both fields are required", "error");
    return;
  }

  await saveSettings(apiUrl, authToken);
});

testBtn.addEventListener("click", async () => {
  const apiUrl = apiUrlInput.value.trim();
  const authToken = authTokenInput.value.trim();

  if (!apiUrl || !authToken) {
    showMessage("Enter API URL and token first", "error");
    return;
  }

  await testConnection(apiUrl, authToken);
});

captureBtn.addEventListener("click", handleCaptureClick);

// Initialize on popup open
document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  updateCaptureButtonState();
});
