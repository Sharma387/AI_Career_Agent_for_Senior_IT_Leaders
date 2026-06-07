/**
 * Background service worker for AI Career Agent LinkedIn Extension.
 * Handles message routing between content script and API.
 *
 * Implements:
 * - POST job data to /api/jobs/ingest/linkedin with JWT authentication
 * - Handle response statuses: "created" (badge/notification), "duplicate" (notification)
 * - Handle auth errors (401): show "session expired" notification
 * - Handle network errors gracefully
 *
 * Requirements: 4.3, 4.4, 4.5, 12.3
 */

const STORAGE_KEYS = {
  API_URL: "apiBaseUrl",
  AUTH_TOKEN: "authToken",
};

/**
 * Handle extension installation.
 */
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    console.log("[AI Career Agent] Extension installed.");
  } else if (details.reason === "update") {
    console.log("[AI Career Agent] Extension updated.");
  }
});

/**
 * Retrieve stored API settings from chrome.storage.sync.
 * @returns {Promise<{apiUrl: string, authToken: string}>}
 */
async function getApiSettings() {
  return new Promise((resolve, reject) => {
    chrome.storage.sync.get(
      [STORAGE_KEYS.API_URL, STORAGE_KEYS.AUTH_TOKEN],
      (data) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve({
          apiUrl: data[STORAGE_KEYS.API_URL] || "",
          authToken: data[STORAGE_KEYS.AUTH_TOKEN] || "",
        });
      }
    );
  });
}

/**
 * Send job data to the API endpoint.
 * @param {object} jobData - Extracted job data from the content script
 * @returns {Promise<object>} Response from the API
 */
async function sendJobToApi(jobData) {
  const { apiUrl, authToken } = await getApiSettings();

  if (!apiUrl || !authToken) {
    return {
      success: false,
      error: "Extension not configured. Please set API URL and token in settings.",
    };
  }

  const url = `${apiUrl.replace(/\/+$/, "")}/api/jobs/ingest/linkedin`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify(jobData),
    });

    // Handle authentication errors (Requirement 12.3)
    if (response.status === 401) {
      showNotification(
        "Session Expired",
        "Your authentication token has expired. Please update it in extension settings."
      );
      return {
        success: false,
        error: "Session expired. Please re-authenticate in extension settings.",
        authError: true,
      };
    }

    // Handle validation errors
    if (response.status === 422) {
      const errorData = await response.json().catch(() => null);
      const errorMsg = errorData && errorData.detail
        ? typeof errorData.detail === "string"
          ? errorData.detail
          : "Validation error — check job data."
        : "Validation error — check job data.";
      return { success: false, error: errorMsg };
    }

    // Handle rate limiting
    if (response.status === 429) {
      return {
        success: false,
        error: "Rate limit exceeded. Please wait before capturing more jobs.",
      };
    }

    // Handle server errors
    if (response.status >= 500) {
      return {
        success: false,
        error: "Server error. Please try again later.",
      };
    }

    // Parse successful response
    const result = await response.json();

    // Handle "created" status (Requirement 4.4)
    if (result.status === "created") {
      updateBadge("✓", "#28a745");
      showNotification(
        "Job Captured",
        `"${jobData.title}" at ${jobData.company} has been saved.`
      );
      return {
        success: true,
        status: "created",
        jobId: result.job_id,
        message: result.message || "Job captured successfully.",
      };
    }

    // Handle "duplicate" status (Requirement 4.5)
    if (result.status === "duplicate") {
      showNotification(
        "Already Captured",
        `"${jobData.title}" at ${jobData.company} was already in your list.`
      );
      return {
        success: true,
        status: "duplicate",
        message: result.message || "Job already captured.",
      };
    }

    // Handle other statuses
    return {
      success: true,
      status: result.status,
      message: result.message || "Operation completed.",
    };
  } catch (error) {
    // Handle network errors gracefully
    console.error("[AI Career Agent] Network error:", error);

    if (error.message.includes("Failed to fetch") || error.name === "TypeError") {
      return {
        success: false,
        error: "Cannot reach API. Check your connection and API URL in settings.",
      };
    }

    return {
      success: false,
      error: `Network error: ${error.message}`,
    };
  }
}

/**
 * Test the API connection using a health check endpoint.
 * @returns {Promise<object>} Connection test result
 */
async function testApiConnection() {
  const { apiUrl, authToken } = await getApiSettings();

  if (!apiUrl || !authToken) {
    return {
      success: false,
      error: "Extension not configured. Please set API URL and token.",
    };
  }

  const url = `${apiUrl.replace(/\/+$/, "")}/api/health`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });

    if (response.ok) {
      return { success: true, message: "Connected to API successfully." };
    } else if (response.status === 401) {
      return { success: false, error: "Authentication failed — check your token." };
    } else {
      return { success: false, error: `API returned status ${response.status}.` };
    }
  } catch (error) {
    return {
      success: false,
      error: "Cannot reach API — check the URL.",
    };
  }
}

/**
 * Update the extension badge to show status.
 * @param {string} text - Badge text (short, 1-4 chars)
 * @param {string} color - Badge background color
 */
function updateBadge(text, color) {
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color });

  // Clear badge after 5 seconds
  setTimeout(() => {
    chrome.action.setBadgeText({ text: "" });
  }, 5000);
}

/**
 * Show a browser notification to the user.
 * @param {string} title - Notification title
 * @param {string} message - Notification body
 */
function showNotification(title, message) {
  // Use chrome.notifications if available, otherwise log
  if (chrome.notifications && chrome.notifications.create) {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon48.png",
      title,
      message,
    });
  } else {
    console.log(`[AI Career Agent] ${title}: ${message}`);
  }
}

/**
 * Listen for messages from content scripts or popup.
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "sendToApi") {
    // Handle job data submission to API
    sendJobToApi(message.data)
      .then((result) => sendResponse(result))
      .catch((error) => {
        sendResponse({
          success: false,
          error: error.message || "Unexpected error occurred.",
        });
      });
    return true; // Keep message channel open for async response
  }

  if (message.action === "testConnection") {
    // Handle connection test request
    testApiConnection()
      .then((result) => sendResponse(result))
      .catch((error) => {
        sendResponse({
          success: false,
          error: error.message || "Connection test failed.",
        });
      });
    return true; // Keep message channel open for async response
  }

  if (message.action === "captureCurrentTab") {
    // Capture from the currently active tab by messaging the content script
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || tabs.length === 0) {
        sendResponse({ success: false, error: "No active tab found." });
        return;
      }

      const tab = tabs[0];

      // Check if we're on a LinkedIn job page
      if (!tab.url || !tab.url.includes("linkedin.com/jobs/view/")) {
        sendResponse({
          success: false,
          error: "Not on a LinkedIn job page.",
        });
        return;
      }

      // Send message to content script to extract job data
      chrome.tabs.sendMessage(
        tab.id,
        { action: "captureJob" },
        async (extractResponse) => {
          if (chrome.runtime.lastError) {
            sendResponse({
              success: false,
              error: "Content script not loaded. Try refreshing the page.",
            });
            return;
          }

          if (!extractResponse || !extractResponse.success) {
            sendResponse({
              success: false,
              error:
                extractResponse && extractResponse.error
                  ? extractResponse.error
                  : "Could not extract job data.",
            });
            return;
          }

          // Now send the extracted data to the API
          const apiResult = await sendJobToApi(extractResponse.data);
          sendResponse(apiResult);
        }
      );
    });
    return true; // Keep message channel open for async response
  }

  return true;
});
