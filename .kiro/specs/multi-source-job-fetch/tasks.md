# Implementation Plan: Multi-Source Job Fetching

## Overview

This implementation plan covers three phases: (1) Seek.co.nz automation via Playwright, (2) LinkedIn Browser Extension with ingest API, and (3) Scheduled daily Seek scraping with role presets. Each phase extends the existing adapter pattern and storage pipeline without modifying existing functionality.

## Tasks

- [x] 1. Configuration and Data Models
  - [x] 1.1 Add Seek and LinkedIn configuration settings to `app/core/config.py`
    - Add `SEEK_CHROME_PROFILE_PATH`, `SEEK_HEADLESS`, `SEEK_MAX_PAGES_PER_SEARCH`, `SEEK_REQUEST_DELAY_MIN`, `SEEK_REQUEST_DELAY_MAX`, `SEEK_DAILY_SCRAPE_HOUR`, `SEEK_DAILY_SCRAPE_MINUTE`, `SEEK_ROLE_PRESETS`, `LINKEDIN_EXTENSION_ENABLED` settings
    - Update `.env.example` with new environment variables
    - _Requirements: 3.1, 9.1, 12.1_

  - [x] 1.2 Create Pydantic data models in `app/ingestion/seek_models.py`
    - Implement `SeekSearchParams`, `SeekJobCard`, `SeekJobDetail`, `SeekScrapeResult`, `RolePreset` models
    - Add validation rules: non-empty keywords, max_pages 1-10, salary_min < salary_max, valid date_range values
    - _Requirements: 1.2, 1.4, 9.1, 11.1_

  - [x] 1.3 Create LinkedIn ingest models in `app/ingestion/linkedin_models.py`
    - Implement `LinkedInJobIngestRequest` with URL pattern validation, min-length description, required title/company
    - Implement `LinkedInJobIngestResponse` with status/job_id/message fields
    - _Requirements: 5.3, 5.4, 5.5_

  - [ ]* 1.4 Write property tests for data model validation
    - **Property 5: Seek Search URL Construction** — valid SeekSearchParams always produce correctly formatted URLs
    - **Property 9: LinkedIn URL Validation** — URLs not matching LinkedIn pattern are rejected by model validation
    - **Property 14: Input Validation Rejection** — descriptions < 10 chars and empty title/company are rejected
    - **Validates: Requirements 1.2, 5.4, 5.5**

- [x] 2. Deduplication Engine
  - [x] 2.1 Implement deduplication logic in `app/ingestion/deduplication.py`
    - Create `is_duplicate(url, title, company, db_session)` async function
    - Primary check: exact URL match on active JobPostings
    - Secondary check: title + company combination on active JobPostings (is_active=True)
    - Ensure read-only operation with no side effects
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 2.2 Write property tests for deduplication
    - **Property 1: No Duplicate Jobs** — ingesting same data twice results in exactly one DB record
    - **Property 12: Deduplication Has No Side Effects** — database state unchanged after dedup check
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

- [x] 3. Seek Page Parser
  - [x] 3.1 Implement `SeekPageParser` in `app/ingestion/seek_parser.py`
    - `build_search_url(params: SeekSearchParams, page: int)` — constructs seek.co.nz URL with keywords, location, classification, salary, work_type, date_range, page
    - `parse_search_results(page_html: str) -> list[SeekJobCard]` — extracts job cards from search results HTML
    - `parse_job_detail(page_html: str, job_url: str) -> SeekJobDetail` — extracts full job details from detail page
    - Extract external_id as `seek_{numeric_id}` from URL
    - Strip HTML tags and normalize whitespace from descriptions
    - Use multiple fallback selectors for resilience
    - _Requirements: 1.3, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 3.2 Write property tests for SeekPageParser
    - **Property 10: External ID Format** — Seek URLs with numeric IDs always produce "seek_{numeric_id}"
    - **Property 11: HTML Stripping Idempotence** — cleaned description contains no HTML, applying cleaner again produces identical output
    - **Validates: Requirements 2.3, 2.5**

  - [ ]* 3.3 Write unit tests for SeekPageParser
    - Test with saved HTML fixtures for search results and detail pages
    - Test malformed HTML graceful handling
    - Test URL construction with all parameter combinations
    - _Requirements: 1.2, 1.3, 2.2, 2.3_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Seek Scraping Service
  - [x] 5.1 Implement `SeekScrapingService` in `app/ingestion/seek_scraper_service.py`
    - `__init__(chrome_profile_path, headless)` — configure Playwright settings
    - `scrape_jobs(search_params: SeekSearchParams) -> SeekScrapeResult` — main scrape flow
    - Launch Playwright with `launch_persistent_context`, Chrome profile, `--disable-blink-features=AutomationControlled`
    - Paginate through results up to max_pages, stop when no cards found
    - For each non-duplicate card, navigate to detail page and extract full description
    - Implement random delay between `SEEK_REQUEST_DELAY_MIN` and `SEEK_REQUEST_DELAY_MAX`
    - Close browser context in `finally` block regardless of success/failure
    - Handle CAPTCHA detection: log warning, abort, return partial results
    - Handle Chrome profile lock: raise appropriate error
    - Maintain result counting invariant: `scraped == new_jobs + duplicates + errors`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 3.1, 3.2, 3.3, 3.4, 11.1, 11.2, 11.3_

  - [x] 5.2 Implement `scrape_and_store(params, db_session)` method
    - Integrate deduplication engine (check before fetching detail)
    - Store new jobs via `JobService.add_job()` with source="seek_nz"
    - Update job metadata (URL, salary_range) on stored records
    - Handle database errors gracefully, return partial results
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 5.3 Write property tests for SeekScrapingService
    - **Property 7: Result Counting Invariant** — scraped == new_jobs + duplicates + errors for every operation
    - **Property 4: Source Attribution Correctness** — all Seek jobs stored with source="seek_nz"
    - **Property 6: Rate Limiting Delay Bounds** — delays between requests are within configured min/max
    - **Property 15: Pagination Respects Max Pages** — never fetches more than max_pages pages
    - **Validates: Requirements 3.1, 7.2, 11.1, 11.2, 1.4**

- [x] 6. Seek Scrape API Endpoint
  - [x] 6.1 Add `/api/jobs/scrape/seek` POST endpoint in `app/api/routes.py`
    - Accept `SeekSearchParams` (keywords, location, optional filters)
    - Require JWT authentication (return 401 if missing/invalid)
    - Invoke `SeekScrapingService.scrape_and_store()` and return result counts
    - Handle Chrome profile lock → return HTTP 409 Conflict
    - Handle Playwright not installed → return HTTP 503 with installation instructions
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 6.2 Write unit tests for Seek scrape endpoint
    - Test 401 without auth token
    - Test 409 on profile lock
    - Test 503 when Playwright missing
    - Test successful scrape returns correct result structure
    - _Requirements: 10.1, 10.2, 10.4, 10.5_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. LinkedIn Ingest API Endpoint
  - [x] 8.1 Add `/api/jobs/ingest/linkedin` POST endpoint in `app/api/routes.py`
    - Accept `LinkedInJobIngestRequest` body with JWT authentication
    - Validate URL matches LinkedIn pattern (422 if not)
    - Validate description >= 10 chars (422 if not)
    - Run deduplication check (URL match, then title+company)
    - If duplicate: return HTTP 200 with status="duplicate" and message
    - If new: store via `JobService.add_job()` with source="linkedin_ext", return HTTP 201 with status="created" and job_id
    - Enforce rate limit: max 10 requests per minute per user
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 12.4_

  - [ ]* 8.2 Write property tests for LinkedIn ingest endpoint
    - **Property 3: Authentication Required** — requests without valid JWT always get 401
    - **Property 18: Valid Job Storage Round-Trip** — ingested jobs are queryable by returned job_id with matching fields
    - **Property 19: Rate Limit Enforcement** — >10 requests in 60s are rejected
    - **Validates: Requirements 5.2, 5.6, 12.4**

  - [ ]* 8.3 Write unit tests for LinkedIn ingest endpoint
    - Test successful creation returns 201
    - Test duplicate returns 200 with status="duplicate"
    - Test invalid URL returns 422
    - Test short description returns 422
    - Test missing auth returns 401
    - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.6, 5.7_

- [x] 9. LinkedIn Browser Extension
  - [x] 9.1 Create extension directory structure in `extension/`
    - Create `manifest.json` (Manifest V3) with permissions: `activeTab`, `storage`, host permission for API URL
    - Create `content.ts` — content script for LinkedIn job pages
    - Create `popup.html` and `popup.ts` — extension popup UI with settings
    - Create `background.ts` — service worker for message handling
    - _Requirements: 4.1, 12.1, 12.2_

  - [x] 9.2 Implement job data extraction in `extension/content.ts`
    - Detect LinkedIn job detail page (URL matching `/jobs/view/*`)
    - Extract title, company, location, description, salary_range, seniority_level from DOM
    - Use multiple selector strategies for LinkedIn DOM variations
    - Strip query parameters and fragments from URL to produce canonical URL
    - Return null if title or company cannot be extracted
    - _Requirements: 4.1, 4.2, 4.6, 4.7_

  - [x] 9.3 Implement API communication in `extension/background.ts`
    - POST extracted data to `/api/jobs/ingest/linkedin` with JWT from `chrome.storage.sync`
    - Handle response statuses: "created" → success notification, "duplicate" → duplicate notification
    - Handle auth errors: show "session expired" notification, prompt re-authentication
    - _Requirements: 4.3, 4.4, 4.5, 12.3_

  - [x] 9.4 Implement settings UI in `extension/popup.ts`
    - Allow user to configure API base URL and authentication token
    - Store in `chrome.storage.sync` (encrypted by browser)
    - Show connection status indicator
    - _Requirements: 12.1, 12.3_

  - [ ]* 9.5 Write unit tests for extension content script extraction
    - **Property 13: LinkedIn URL Canonicalization** — URLs with query params produce clean path-only URLs
    - Test extraction from mock LinkedIn DOM structures
    - Test null return when title/company missing
    - **Validates: Requirements 4.2, 4.6, 4.7**

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Scheduled Seek Scraping
  - [x] 11.1 Implement role presets configuration in `app/ingestion/role_presets.py`
    - Define default presets: Project Manager, Senior Project Manager, IT Manager, Engineering Manager, IT Director, CTO
    - `get_active_presets()` → return only presets where enabled=True
    - Load presets from `SEEK_ROLE_PRESETS` environment setting
    - Support runtime changes without restart (re-read on each scheduled run)
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 11.2 Implement `SeekScheduledScraper` in `app/ingestion/seek_scheduled.py`
    - `run_daily_scrape()` — iterate through active presets, call scrape_and_store for each
    - Set `date_range=1` for daily scrapes (only last 24 hours)
    - Introduce 30-60 second random delay between preset searches
    - If one preset fails, log error and continue to next
    - Skip execution if `SEEK_SCRAPING_ENABLED` is False (return disabled status)
    - Aggregate results: total_new_jobs, total_duplicates, total_errors, per-preset breakdowns
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 11.3 Integrate with existing APScheduler in `app/core/scheduler/job_scheduler.py`
    - Add daily Seek scrape job triggered at `SEEK_DAILY_SCRAPE_HOUR:SEEK_DAILY_SCRAPE_MINUTE` NZ time
    - Wire `SeekScheduledScraper.run_daily_scrape()` as the job function
    - Ensure existing scheduler jobs (incremental, full) remain unchanged
    - _Requirements: 8.1, 13.1_

  - [ ]* 11.4 Write property tests for scheduled scraping
    - **Property 8: Scheduler Preset Isolation** — failure in one preset doesn't prevent execution of remaining
    - **Property 16: Active Preset Filtering** — only enabled presets are returned by get_active_presets()
    - **Property 17: Scheduled Scrape Result Aggregation** — totals equal sum of per-preset results
    - **Validates: Requirements 8.4, 8.5, 9.2**

- [x] 12. Pipeline Integration and Storage
  - [x] 12.1 Update `JobService` to support Seek and LinkedIn sources
    - Ensure `add_job()` correctly handles source="seek_nz" and source="linkedin_ext"
    - Verify jobs are stored in both SQLite and ChromaDB
    - Ensure URL and salary_range metadata is persisted on JobPosting records
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 12.2 Write property tests for pipeline integration
    - **Property 2: Pipeline Dual-Write Integrity** — stored jobs exist in both SQLite and ChromaDB
    - **Property 4: Source Attribution Correctness** — source fields are correctly set
    - **Validates: Requirements 7.1, 7.2**

- [x] 13. Existing Functionality Preservation
  - [x] 13.1 Verify existing endpoints remain unchanged
    - Confirm `/api/jobs/scrape/trigger` behavior is preserved
    - Confirm `/api/jobs/add` behavior is preserved
    - Confirm `/api/jobs/{id}/match` behavior is preserved
    - Confirm `JobPosting` model schema is not modified
    - Run existing test suite to verify no regressions
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [x] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The extension (Phase 2) is built as a standalone TypeScript artifact in `extension/` directory
- Playwright must be installed separately: `playwright install chromium`
- Existing Adzuna, manual entry, and matching flows remain completely untouched

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "3.2", "3.3"] },
    { "id": 3, "tasks": ["5.1", "9.1"] },
    { "id": 4, "tasks": ["5.2", "9.2", "9.4", "11.1"] },
    { "id": 5, "tasks": ["5.3", "6.1", "8.1", "9.3"] },
    { "id": 6, "tasks": ["6.2", "8.2", "8.3", "9.5", "11.2"] },
    { "id": 7, "tasks": ["11.3", "11.4", "12.1"] },
    { "id": 8, "tasks": ["12.2", "13.1"] }
  ]
}
```
