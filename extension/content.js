/**
 * Content script for AI Career Agent LinkedIn Extension.
 * Runs on LinkedIn job pages to enable job data extraction.
 *
 * Implements:
 * - LinkedIn job detail page detection (URL matching /jobs/view/*)
 * - Multi-strategy DOM extraction for title, company, location, description, salary, seniority
 * - Floating "Capture Job" button on job pages
 * - Message handling for popup/background communication
 *
 * Requirements: 4.1, 4.2, 4.6, 4.7
 */

(function () {
  "use strict";

  let captureButton = null;

  /**
   * Check if current page is a LinkedIn job detail page.
   * @returns {boolean}
   */
  function isJobDetailPage() {
    return /linkedin\.com\/jobs\/view\//.test(window.location.href);
  }

  /**
   * Try multiple selectors and return the first non-empty text content.
   * @param {string[]} selectors - CSS selectors to try in order
   * @returns {string} Extracted text or empty string
   */
  function extractWithFallback(selectors) {
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el) {
        const text = el.textContent.trim();
        if (text) {
          return text;
        }
      }
    }
    return "";
  }

  /**
   * Strip query parameters and fragments from URL to produce a canonical URL.
   * @param {string} url - Full URL with possible query/fragment
   * @returns {string} Clean URL path only
   */
  function canonicalizeUrl(url) {
    try {
      const parsed = new URL(url);
      return parsed.origin + parsed.pathname;
    } catch {
      // Fallback: strip everything after ? or #
      return url.split("?")[0].split("#")[0];
    }
  }

  /**
   * Extract seniority level from job criteria list.
   * LinkedIn displays seniority in a list of job criteria items.
   * @returns {string|undefined}
   */
  function extractSeniority() {
    const criteriaElements = document.querySelectorAll(
      ".description__job-criteria-text"
    );
    for (const el of criteriaElements) {
      const listItem = el.closest("li");
      if (listItem && listItem.textContent.includes("Seniority")) {
        return el.textContent.trim();
      }
    }
    return undefined;
  }

  /**
   * Extract salary information using multiple strategies.
   * @returns {string|undefined}
   */
  function extractSalary() {
    const salarySelectors = [
      ".salary-main-rail__salary-range",
      '[class*="salary"]',
    ];

    for (const selector of salarySelectors) {
      const el = document.querySelector(selector);
      if (el) {
        const text = el.textContent.trim();
        if (text) {
          return text;
        }
      }
    }
    return undefined;
  }

  /**
   * Extract job data from the current LinkedIn page DOM.
   * Uses multiple selector strategies for each field since LinkedIn
   * frequently changes their DOM structure.
   *
   * @returns {object|null} Extracted job data or null if extraction fails.
   */
  function extractJobData() {
    if (!isJobDetailPage()) {
      return null;
    }

    // Extract title using multiple selector strategies
    const title = extractWithFallback([
      ".job-details-jobs-unified-top-card__job-title",
      ".t-24.t-bold",
      "h1",
    ]);

    // Extract company name
    const company = extractWithFallback([
      ".job-details-jobs-unified-top-card__company-name",
      ".jobs-unified-top-card__company-name",
    ]);

    // Return null if title or company cannot be extracted (Requirement 4.6)
    if (!title || !company) {
      return null;
    }

    // Extract location
    const location = extractWithFallback([
      ".job-details-jobs-unified-top-card__bullet",
      ".jobs-unified-top-card__bullet",
    ]);

    // Extract description
    const description = extractWithFallback([
      ".jobs-description__content",
      "#job-details",
    ]);

    // Extract optional salary
    const salaryRange = extractSalary();

    // Extract optional seniority level
    const seniorityLevel = extractSeniority();

    // Build canonical URL without query params/fragments (Requirement 4.7)
    const url = canonicalizeUrl(window.location.href);

    return {
      title,
      company,
      location: location || undefined,
      description: description || "",
      url,
      salary_range: salaryRange,
      seniority_level: seniorityLevel,
    };
  }

  /**
   * Create and inject the floating "Capture Job" button on LinkedIn job pages.
   */
  function injectCaptureButton() {
    // Remove existing button if present
    if (captureButton) {
      captureButton.remove();
      captureButton = null;
    }

    if (!isJobDetailPage()) {
      return;
    }

    captureButton = document.createElement("button");
    captureButton.id = "ai-career-agent-capture-btn";
    captureButton.textContent = "📋 Capture Job";
    captureButton.title = "Capture this job for AI Career Agent";

    // Inline styles for the floating button (avoids CSS conflicts with LinkedIn)
    Object.assign(captureButton.style, {
      position: "fixed",
      bottom: "24px",
      right: "24px",
      zIndex: "9999",
      padding: "12px 20px",
      backgroundColor: "#0a66c2",
      color: "#ffffff",
      border: "none",
      borderRadius: "24px",
      fontSize: "14px",
      fontWeight: "600",
      cursor: "pointer",
      boxShadow: "0 4px 12px rgba(0, 0, 0, 0.2)",
      transition: "background-color 0.2s, transform 0.1s, box-shadow 0.2s",
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    });

    captureButton.addEventListener("mouseenter", () => {
      captureButton.style.backgroundColor = "#004182";
      captureButton.style.boxShadow = "0 6px 16px rgba(0, 0, 0, 0.3)";
    });

    captureButton.addEventListener("mouseleave", () => {
      captureButton.style.backgroundColor = "#0a66c2";
      captureButton.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.2)";
    });

    captureButton.addEventListener("mousedown", () => {
      captureButton.style.transform = "scale(0.95)";
    });

    captureButton.addEventListener("mouseup", () => {
      captureButton.style.transform = "scale(1)";
    });

    captureButton.addEventListener("click", handleCaptureClick);

    document.body.appendChild(captureButton);
  }

  /**
   * Handle the capture button click — extract job data and send to background.
   */
  async function handleCaptureClick() {
    const jobData = extractJobData();

    if (!jobData) {
      showFloatingNotification(
        "error",
        "Could not extract job data from this page."
      );
      return;
    }

    // Update button to show loading state
    const originalText = captureButton.textContent;
    captureButton.textContent = "⏳ Sending...";
    captureButton.disabled = true;
    captureButton.style.opacity = "0.7";

    try {
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage(
          { action: "sendToApi", data: jobData },
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
          showFloatingNotification("success", "Job captured successfully!");
        } else if (response.status === "duplicate") {
          showFloatingNotification("duplicate", "Job already captured.");
        } else {
          showFloatingNotification("success", response.message || "Done!");
        }
      } else {
        const errorMsg =
          response && response.error ? response.error : "Failed to send job.";
        showFloatingNotification("error", errorMsg);
      }
    } catch (err) {
      showFloatingNotification("error", "Extension error: " + err.message);
    } finally {
      // Restore button state
      captureButton.textContent = originalText;
      captureButton.disabled = false;
      captureButton.style.opacity = "1";
    }
  }

  /**
   * Show a floating notification near the capture button.
   * @param {"success"|"duplicate"|"error"} type
   * @param {string} message
   */
  function showFloatingNotification(type, message) {
    // Remove any existing notification
    const existing = document.getElementById("ai-career-agent-notification");
    if (existing) {
      existing.remove();
    }

    const notification = document.createElement("div");
    notification.id = "ai-career-agent-notification";

    const colors = {
      success: { bg: "#d4edda", text: "#155724", icon: "✅" },
      duplicate: { bg: "#fff3cd", text: "#856404", icon: "⚠️" },
      error: { bg: "#f8d7da", text: "#721c24", icon: "❌" },
    };

    const style = colors[type] || colors.error;

    Object.assign(notification.style, {
      position: "fixed",
      bottom: "76px",
      right: "24px",
      zIndex: "10000",
      padding: "10px 16px",
      backgroundColor: style.bg,
      color: style.text,
      borderRadius: "8px",
      fontSize: "13px",
      fontWeight: "500",
      boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      maxWidth: "280px",
      animation: "fadeIn 0.2s ease-in",
    });

    notification.textContent = `${style.icon} ${message}`;
    document.body.appendChild(notification);

    // Auto-remove after 4 seconds
    setTimeout(() => {
      if (notification.parentNode) {
        notification.style.opacity = "0";
        notification.style.transition = "opacity 0.3s ease-out";
        setTimeout(() => notification.remove(), 300);
      }
    }, 4000);
  }

  /**
   * Listen for messages from the background script or popup.
   */
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "captureJob") {
      const jobData = extractJobData();
      if (jobData) {
        sendResponse({ success: true, data: jobData });
      } else {
        sendResponse({
          success: false,
          error: "Could not extract job data from this page.",
        });
      }
    }

    if (message.action === "ping") {
      sendResponse({ success: true, isJobPage: isJobDetailPage() });
    }

    return true; // Keep message channel open for async response
  });

  /**
   * Observe URL changes (LinkedIn uses SPA navigation) and re-inject button.
   */
  function setupNavigationObserver() {
    let lastUrl = window.location.href;

    const observer = new MutationObserver(() => {
      if (window.location.href !== lastUrl) {
        lastUrl = window.location.href;
        // Delay to allow DOM to update after navigation
        setTimeout(() => {
          injectCaptureButton();
        }, 1000);
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Initialize: inject button and set up navigation observer
  function init() {
    // Wait for page to be ready
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => {
        injectCaptureButton();
        setupNavigationObserver();
      });
    } else {
      injectCaptureButton();
      setupNavigationObserver();
    }
  }

  init();

  console.log("[AI Career Agent] Content script loaded on LinkedIn job page.");
})();
