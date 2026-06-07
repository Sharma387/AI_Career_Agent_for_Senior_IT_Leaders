# Requirements Document

## Introduction

This document defines the requirements for the Multi-Source Job Fetching feature, which adds Seek.co.nz automation via Playwright and a LinkedIn browser extension/bookmarklet for manual job capture to the existing AI Career Agent application. A third phase adds scheduled daily Seek scraping with configurable role presets. The target user is a senior IT professional in New Zealand searching for PM, IT Manager, Director, and CTO roles.

## Glossary

- **Seek_Scraper**: The Playwright-based automation component that browses seek.co.nz using the user's Chrome profile to extract job listings
- **LinkedIn_Extension**: A Chrome browser extension that captures job data from the current LinkedIn job detail page and sends it to the application API
- **Deduplication_Engine**: The component that checks whether a job already exists in the database before storing it, using URL and title+company matching
- **Job_Pipeline**: The existing storage flow from `JobService.add_job()` through to SQLite storage and ChromaDB RAG ingestion
- **Role_Preset**: A configured search template containing keywords, location, and filters for a specific senior role type (e.g., Project Manager, CTO)
- **Scheduled_Scraper**: The APScheduler-driven component that triggers Seek scraping daily using the configured role presets
- **Chrome_Profile**: The user's existing Chrome browser data directory containing cookies and session state for seek.co.nz
- **Search_Results_Page**: A Seek.co.nz page listing multiple job cards matching a keyword and location search
- **Job_Detail_Page**: A single Seek.co.nz page containing the full description of a specific job posting

## Requirements

### Requirement 1: Seek Job Search Execution

**User Story:** As a senior IT job seeker in New Zealand, I want to automate Seek.co.nz browsing using my existing Chrome session, so that I can discover relevant job postings without manually searching every day.

#### Acceptance Criteria

1. WHEN a user triggers a Seek scrape with keywords and location parameters, THE Seek_Scraper SHALL launch a Playwright browser using the configured Chrome profile path
2. WHEN the Seek_Scraper navigates to seek.co.nz, THE Seek_Scraper SHALL construct a search URL from the provided keywords, location, and optional filters (classification, salary range, work type, date range)
3. WHEN search results are returned, THE Seek_Scraper SHALL extract job cards containing title, company, location, salary range, URL, and posted date from each results page
4. WHEN multiple pages of results exist, THE Seek_Scraper SHALL paginate through results up to the configured maximum page limit (between 1 and 10 pages)
5. WHEN no job cards are found on a page, THE Seek_Scraper SHALL stop pagination and return results collected so far
6. WHEN scraping completes, THE Seek_Scraper SHALL close the Playwright browser context regardless of whether the scrape succeeded or failed

### Requirement 2: Seek Job Detail Extraction

**User Story:** As a senior IT job seeker, I want full job descriptions extracted from Seek, so that the AI agent can accurately match jobs against my profile.

#### Acceptance Criteria

1. WHEN a job card is identified as not a duplicate, THE Seek_Scraper SHALL navigate to the job detail page to extract the full description
2. WHEN parsing a Seek job detail page, THE Seek_Scraper SHALL extract title, company, location, full description, salary range, classification, work type, and external ID
3. WHEN the external ID is derived from a Seek URL, THE Seek_Scraper SHALL format it as "seek_{numeric_id}"
4. WHEN a job detail page cannot be parsed due to unexpected HTML structure, THE Seek_Scraper SHALL skip that job, increment the error count, and continue processing remaining jobs
5. WHEN job description HTML is extracted, THE Seek_Scraper SHALL strip HTML tags and normalize whitespace before storage

### Requirement 3: Seek Rate Limiting and Bot Avoidance

**User Story:** As a job seeker using automation, I want the scraper to behave naturally, so that my Seek account is not blocked or flagged.

#### Acceptance Criteria

1. WHILE the Seek_Scraper is navigating between pages, THE Seek_Scraper SHALL introduce a random delay between the configured minimum and maximum delay settings (default 2-5 seconds)
2. THE Seek_Scraper SHALL launch Playwright with anti-detection flags including disabling automation-controlled blink features
3. WHEN the Seek_Scraper is run in headless mode, THE Seek_Scraper SHALL use the user's Chrome profile to maintain realistic session cookies and browsing state
4. IF Seek returns a CAPTCHA page or blocks the automated browser, THEN THE Seek_Scraper SHALL log a warning, abort the current scrape, and return partial results collected so far

### Requirement 4: LinkedIn Browser Extension Job Capture

**User Story:** As a senior IT job seeker browsing LinkedIn, I want to capture interesting job postings with one click, so that they are automatically added to my career agent for matching and analysis.

#### Acceptance Criteria

1. WHEN a user is on a LinkedIn job detail page (URL matching `/jobs/view/*`), THE LinkedIn_Extension SHALL detect the page and enable the capture action
2. WHEN the user triggers the capture action, THE LinkedIn_Extension SHALL extract job title, company, location, description, URL (without tracking parameters), salary range, and seniority level from the page DOM
3. WHEN job data is extracted, THE LinkedIn_Extension SHALL POST the data to the application API endpoint `/api/jobs/ingest/linkedin` with a JWT authentication token
4. WHEN the API responds with status "created", THE LinkedIn_Extension SHALL display a success notification to the user
5. WHEN the API responds with status "duplicate", THE LinkedIn_Extension SHALL display a notification indicating the job was already captured
6. IF extraction fails due to insufficient data (missing title or company), THEN THE LinkedIn_Extension SHALL display an error notification and not send the request
7. WHEN extracting the job URL, THE LinkedIn_Extension SHALL strip query parameters and fragments to produce a clean canonical URL

### Requirement 5: LinkedIn Ingest API Endpoint

**User Story:** As a system operator, I want a secure API endpoint that receives job data from the LinkedIn extension, so that captured jobs are stored reliably.

#### Acceptance Criteria

1. THE LinkedIn ingest endpoint SHALL accept POST requests at `/api/jobs/ingest/linkedin`
2. WHEN a request is received without a valid JWT token, THE LinkedIn ingest endpoint SHALL return HTTP 401 Unauthorized
3. WHEN a request is received with a valid JWT token, THE LinkedIn ingest endpoint SHALL validate the request body against the LinkedInJobIngestRequest schema
4. WHEN the URL field does not match the pattern `^https://(www\.)?linkedin\.com/jobs/`, THE LinkedIn ingest endpoint SHALL return HTTP 422 with a validation error
5. WHEN the description field contains fewer than 10 characters, THE LinkedIn ingest endpoint SHALL return HTTP 422 with a validation error
6. WHEN a valid non-duplicate job is received, THE LinkedIn ingest endpoint SHALL store it via the Job_Pipeline with source "linkedin_ext" and return HTTP 201 with status "created" and the job_id
7. WHEN a duplicate job is detected, THE LinkedIn ingest endpoint SHALL return HTTP 200 with status "duplicate" and a descriptive message

### Requirement 6: Job Deduplication

**User Story:** As a job seeker using multiple sources, I want the system to prevent duplicate job entries, so that my job list remains clean and accurate.

#### Acceptance Criteria

1. WHEN a new job is about to be stored, THE Deduplication_Engine SHALL first check for an existing active JobPosting with the same URL (exact match)
2. WHEN no URL match is found, THE Deduplication_Engine SHALL check for an existing active JobPosting with the same title AND company combination
3. WHEN a duplicate is detected by either method, THE Deduplication_Engine SHALL skip storage and report the job as a duplicate in the scrape results
4. THE Deduplication_Engine SHALL perform checks without modifying any existing database records
5. WHEN checking title and company, THE Deduplication_Engine SHALL only match against jobs where `is_active` is True

### Requirement 7: Job Storage Pipeline Integration

**User Story:** As a system architect, I want all new job sources to integrate through the existing storage pipeline, so that jobs from any source are immediately available for matching and RAG queries.

#### Acceptance Criteria

1. WHEN a new job passes deduplication, THE Job_Pipeline SHALL store it in both the SQLite `job_postings` table and the ChromaDB job embeddings collection
2. THE Job_Pipeline SHALL set the `source` field to "seek_nz" for Seek-originated jobs and "linkedin_ext" for LinkedIn extension-originated jobs
3. WHEN a job is stored via the Job_Pipeline, THE Job_Pipeline SHALL parse the job text to extract title, company, location, seniority level, salary range, requirements, and skills
4. WHEN a Seek job is stored, THE Job_Pipeline SHALL persist the original Seek URL and salary range as metadata on the JobPosting record
5. IF the database becomes unavailable during a scrape operation, THEN THE Job_Pipeline SHALL log the error and return partial results for jobs already committed

### Requirement 8: Scheduled Daily Seek Scraping

**User Story:** As a senior IT job seeker, I want my system to automatically search Seek every day for new job postings matching my target roles, so that I never miss relevant opportunities.

#### Acceptance Criteria

1. WHEN the scheduler fires at the configured daily time (default 7:00 AM NZ time), THE Scheduled_Scraper SHALL execute a Seek scrape for each enabled Role_Preset
2. WHILE processing multiple role presets, THE Scheduled_Scraper SHALL introduce a delay of 30-60 seconds between each preset search
3. WHEN a scheduled scrape runs, THE Scheduled_Scraper SHALL filter Seek results to jobs posted within the last 24 hours (date_range=1)
4. IF one role preset scrape fails, THEN THE Scheduled_Scraper SHALL log the error and continue executing the remaining presets
5. WHEN all presets have been processed, THE Scheduled_Scraper SHALL aggregate results into a summary containing total new jobs, total duplicates, total errors, and per-preset breakdowns
6. WHILE the SEEK_SCRAPING_ENABLED setting is False, THE Scheduled_Scraper SHALL skip execution and return a disabled status

### Requirement 9: Role Preset Configuration

**User Story:** As a senior IT job seeker, I want to configure multiple role search presets (PM, IT Manager, Director, CTO), so that the scheduler covers all my target role types.

#### Acceptance Criteria

1. THE Role_Preset configuration SHALL support fields for ID, label, keywords, location (default "New Zealand"), classification, enabled flag, and minimum salary filter
2. WHEN the Scheduled_Scraper requests active presets, THE configuration SHALL return only presets where the enabled flag is True
3. THE system SHALL provide default presets for: Project Manager, Senior Project Manager, IT Manager, Engineering Manager, IT Director, and CTO
4. WHEN a user modifies role preset configuration via environment settings, THE system SHALL apply the changes on the next scheduled run without restart

### Requirement 10: Seek Scrape API Endpoint

**User Story:** As a job seeker, I want to manually trigger Seek scraping via the API, so that I can search for specific roles on demand outside the scheduled times.

#### Acceptance Criteria

1. THE Seek scrape endpoint SHALL accept POST requests at `/api/jobs/scrape/seek`
2. WHEN a request is received without a valid JWT token, THE Seek scrape endpoint SHALL return HTTP 401 Unauthorized
3. WHEN a valid request is received with keywords, location, and optional filters, THE Seek scrape endpoint SHALL invoke the Seek_Scraper and return a result containing counts of new jobs, duplicates, and errors
4. IF the Chrome profile is locked (already in use), THEN THE Seek scrape endpoint SHALL return HTTP 409 Conflict with a message indicating the profile is in use
5. IF Playwright is not installed, THEN THE Seek scrape endpoint SHALL return HTTP 503 Service Unavailable with installation instructions

### Requirement 11: Result Counting Integrity

**User Story:** As a system operator, I want scrape results to have accurate counts, so that I can monitor the health and effectiveness of automated job fetching.

#### Acceptance Criteria

1. THE Seek_Scraper SHALL maintain the invariant that `scraped == new_jobs + duplicates + errors` for every scrape operation
2. WHEN a job card is processed (regardless of outcome), THE Seek_Scraper SHALL increment the `scraped` counter exactly once
3. WHEN a scrape completes, THE Seek_Scraper SHALL include the number of pages actually scraped and the search parameters used in the result

### Requirement 12: Extension Configuration and Security

**User Story:** As a security-conscious user, I want the LinkedIn extension to securely store its configuration, so that my authentication tokens are not exposed.

#### Acceptance Criteria

1. THE LinkedIn_Extension SHALL store the API base URL and authentication token in Chrome's `chrome.storage.sync` (encrypted by the browser)
2. THE LinkedIn_Extension SHALL request only minimal Chrome permissions: `activeTab`, `storage`, and host permission for the application API URL only
3. WHEN the authentication token expires or is invalid, THE LinkedIn_Extension SHALL display a session-expired notification and prompt the user to re-authenticate
4. THE LinkedIn ingest endpoint SHALL enforce a rate limit (maximum 10 requests per minute) to prevent abuse even with valid tokens

### Requirement 13: Existing Functionality Preservation

**User Story:** As a user of the existing career agent, I want all current features (Adzuna scraping, manual job entry, job matching, RAG queries) to continue working unchanged after this feature is added.

#### Acceptance Criteria

1. THE system SHALL preserve the existing `/api/jobs/scrape/trigger` endpoint behavior without modification
2. THE system SHALL preserve the existing `/api/jobs/add` endpoint behavior without modification
3. THE system SHALL preserve the existing `/api/jobs/{id}/match` endpoint behavior without modification
4. THE system SHALL not modify the `JobPosting` database model schema
5. WHEN running existing integration tests, THE system SHALL pass all tests without regression
