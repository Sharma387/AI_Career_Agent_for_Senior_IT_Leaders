# AI Career Agent — LinkedIn Job Capture Extension

A Chrome Manifest V3 browser extension that captures job postings from LinkedIn and sends them to your AI Career Agent API for matching and analysis.

## Features

- One-click job capture from LinkedIn job detail pages
- Extracts title, company, location, description, salary, and seniority level
- Sends captured jobs to your local AI Career Agent API
- Duplicate detection — won't re-capture jobs you already have
- Settings popup for configuring API URL and auth token
- Connection status indicator

## Installation (Load Unpacked)

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top-right corner)
3. Click **Load unpacked**
4. Select this `extension/` folder
5. The extension icon will appear in your Chrome toolbar

## Configuration

1. Click the extension icon in the toolbar to open the settings popup
2. Enter your **API URL** (default: `http://localhost:8000`)
3. Enter your **Auth Token** (JWT token from the Career Agent app)
4. Click **Save**
5. Click **Test Connection** to verify connectivity

## Usage

1. Navigate to any LinkedIn job posting page (URL matching `/jobs/view/*`)
2. Click the extension icon or use the capture button on the page
3. The extension extracts job details and sends them to your API
4. You'll see a notification confirming the job was captured (or if it's a duplicate)

## Permissions

This extension requests minimal permissions:

- `activeTab` — Access the current tab's content when you interact with the extension
- `storage` — Store your API URL and auth token securely in Chrome's encrypted storage
- Host permissions for `localhost:8000` and `localhost:5173` — Communicate with your local Career Agent API

## Development

This extension uses plain JavaScript (no build step required). Files can be edited directly and changes are reflected after clicking "Reload" on the extensions page.

### File Structure

```
extension/
├── manifest.json    — Chrome Manifest V3 configuration
├── popup.html       — Settings popup UI
├── popup.js         — Settings logic (save/load/test)
├── content.js       — Content script for LinkedIn pages
├── background.js    — Service worker for API communication
├── styles.css       — Styling for popup and injected UI
├── icons/           — Extension icons (placeholder)
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md        — This file
```

## Troubleshooting

- **"Cannot reach API"** — Ensure your Career Agent backend is running on the configured URL
- **"Authentication failed"** — Your JWT token may be expired; generate a new one from the app
- **No capture button on LinkedIn** — Make sure you're on a job detail page (`/jobs/view/...`)
- **Extension not loading** — Check Chrome DevTools console for errors (right-click extension icon → "Inspect popup")

## Requirements

- Google Chrome (or Chromium-based browser) version 88+
- AI Career Agent backend running locally
- Valid JWT authentication token
