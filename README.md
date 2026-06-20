# AI Career Agent for Senior IT Leaders

An AI-powered career intelligence platform that helps senior IT professionals (Project Managers, IT Directors, CTOs) discover relevant job opportunities, match against their profile, and generate tailored application materials using RAG and local LLMs.

## Features

- **Multi-Source Job Search** — Adzuna API (NZ/AU jobs), Seek automation (Playwright), LinkedIn browser extension
- **AI Job Matching** — RAG-based scoring with skills, experience, industry, and leadership dimensions
- **Resume & Cover Letter Generation** — LLM-generated materials tailored per job
- **Interview Strategy** — AI-prepared talking points, potential questions, and gap analysis
- **Application Tracking** — Status management, insights, and analytics
- **Smart Deduplication** — URL + title/company matching prevents duplicate entries
- **API Usage Management** — Daily dedup, monthly quota tracking, automatic fallback to free APIs
- **Scheduled Scraping** — Daily automated Seek searches with configurable role presets

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│             React Frontend (TypeScript + shadcn/ui + Tailwind)          │
│  Dashboard │ Jobs │ Applications │ Profile │ Insights │ Interview Prep │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ REST API
┌──────────────────────────────────▼─────────────────────────────────────┐
│                         FastAPI Backend                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ API Routes  │  │ Job Ingestion│  │  LLM Agents  │  │ Scheduler │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘  │
│         │                │                  │                │        │
│  ┌──────▼──────────────▼──────────────────▼────────────────▼──────┐  │
│  │              Service Layer (Profile, Job, Tracking)              │  │
│  └──────┬─────────────────────────────────────────────────┬───────┘  │
│         │                                                 │          │
│  ┌──────▼───────────┐  ┌─────────────────────────────────▼───────┐  │
│  │ SQLite (aiosqlite)│  │ ChromaDB (RAG Embeddings)               │  │
│  └───────────────────┘  └────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘

Job Sources:
  • Adzuna API (primary, 250 calls/month free) → aggregates Seek, Trade Me, etc.
  • Seek.co.nz Playwright automation (when Cloudflare allows)
  • LinkedIn Browser Extension (manual capture, zero ban risk)
  • Jobicy + Arbeitnow (free fallback when Adzuna quota exhausted)
```

## Tech Stack

| Layer           | Technology                                                    |
|-----------------|---------------------------------------------------------------|
| Frontend        | React 18, TypeScript, Vite, shadcn/ui, Tailwind CSS, Lucide  |
| Backend         | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy (async)        |
| LLM             | Ollama (llama3.1:8b local, free) or Anthropic/NVIDIA          |
| Embeddings      | sentence-transformers (all-MiniLM-L6-v2)                      |
| Vector Store    | ChromaDB                                                      |
| Database        | SQLite (via aiosqlite)                                        |
| Job APIs        | Adzuna, Jobicy, Arbeitnow                                     |
| Browser Automation | Playwright (Seek), Chrome Extension (LinkedIn)             |
| Scheduler       | APScheduler (async)                                           |
| Auth            | JWT (python-jose) + bcrypt                                    |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed and running (`ollama serve`)
- llama3.1:8b model pulled (`ollama pull llama3.1:8b`)

### 1. Clone & Setup Backend

```bash
git clone https://github.com/Sharma387/AI_Career_Agent_for_Senior_IT_Leaders.git
cd AI_Career_Agent_for_Senior_IT_Leaders

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set:
# - ADZUNA_APP_ID and ADZUNA_APP_KEY (free: https://developer.adzuna.com/signup)
# - JWT_SECRET_KEY (any random string)
# - LLM_PROVIDER=ollama (default)
```

### 3. Setup Frontend

```bash
cd frontend-react
npm install
cd ..
```

### 4. Run the Application

**Terminal 1 — Backend API:**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend Dev Server:**
```bash
cd frontend-react
npm run dev
```

Open **http://localhost:5173** in your browser.

### 5. (Optional) Install Playwright for Seek Scraping

```bash
pip install playwright
playwright install chromium
```

### 6. (Optional) Load LinkedIn Browser Extension

1. Open Chrome → `chrome://extensions/`
2. Enable Developer mode
3. Click "Load unpacked" → select the `extension/` folder
4. Configure API URL (`http://localhost:8000`) and JWT token in the extension popup

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM backend: `ollama`, `nvidia`, or `anthropic` | `ollama` |
| `OLLAMA_MODEL` | Ollama model name | `llama3.1:8b` |
| `ADZUNA_APP_ID` | Adzuna API app ID (free tier) | — |
| `ADZUNA_APP_KEY` | Adzuna API key | — |
| `ADZUNA_COUNTRY` | Job search country code | `nz` |
| `JWT_SECRET_KEY` | Secret for JWT auth tokens | — |
| `SEEK_SCRAPING_ENABLED` | Enable Seek Playwright automation | `true` |
| `SEEK_HEADLESS` | Run Playwright headless | `true` |
| `SEEK_DAILY_SCRAPE_HOUR` | Daily scrape time (NZ, 24h) | `7` |
| `SEEK_ROLE_PRESETS` | Comma-separated role IDs for scheduled search | `project-manager,sr-project-manager,...` |

See `.env.example` for the full list.

## Job Search Features

### Adzuna (Primary)
- Free API with 250 calls/month
- Covers NZ, AU, UK, US job markets
- Aggregates from Seek, Trade Me Jobs, and more
- Role presets: PM, Sr PM, IT Manager, Engineering Manager, IT Director, CTO

### LinkedIn Extension
- Chrome Manifest V3 extension
- Navigate to any LinkedIn job → click "Capture Job" button
- Extracts title, company, description, salary, seniority
- Posts to your local API — stored and available for matching
- Zero risk of LinkedIn account restrictions

### Seek Automation
- Playwright-based browser automation
- Uses dedicated Chrome profile (not your personal one)
- Human-like delays (2-5s) between requests
- CAPTCHA detection with graceful abort
- Note: Seek uses Cloudflare — may not work consistently in headless mode

### Fallback (Free, No Key)
- Jobicy (remote IT/tech/management jobs)
- Arbeitnow (European tech jobs)
- Automatically activated when Adzuna quota is exhausted

## API Usage Tracking

- Each unique search per day counts as 1 API call
- Same search on the same day won't hit the API again
- Monthly usage displayed in the UI (e.g., "API: 248/250 remaining")
- When quota is exhausted, fallback providers are used automatically

## Testing

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Currently 78 tests covering: API routes, database models, job parser, job scraper, LLM factory, resume parser, agents, deduplication, and LinkedIn ingest endpoint.

## Project Structure

```
├── app/
│   ├── agents/          # LLM-powered agents (matcher, resume, insight)
│   ├── api/             # FastAPI routes + auth
│   ├── core/            # Config, LLM factory, scheduler, rate limiting
│   ├── db/              # SQLAlchemy models + async session
│   ├── ingestion/       # Job parsers, scrapers, adapters (Adzuna, Seek, LinkedIn)
│   ├── rag/             # ChromaDB vector stores (career, job, application)
│   ├── services/        # Business logic (profile, job, tracking, document)
│   └── templates/       # HTML/DOCX templates for resume/cover letter
├── extension/           # LinkedIn Chrome extension (Manifest V3)
├── frontend-react/      # React frontend (Vite + shadcn/ui + Tailwind)
├── tests/               # pytest test suite
├── .env.example         # Environment variable template
├── requirements.txt     # Python dependencies
└── pyproject.toml       # Pytest + Ruff configuration
```

## Troubleshooting

### "Address already in use" (port 8000)

A previous server instance is still running. Kill it first:

```bash
lsof -ti:8000 | xargs kill -9
uvicorn app.main:app --reload
```

Or use a different port:

```bash
uvicorn app.main:app --reload --port 8001
```

### Frontend "npm run dev" fails with package.json not found

You need to be in the `frontend-react` folder:

```bash
cd frontend-react
npm run dev
```

### PDF resume upload fails

- Ensure Ollama is running: `ollama serve`
- Ensure the model is pulled: `ollama pull llama3.1:8b`
- If Ollama is slow on first call (loading model), wait 30 seconds and try again
- The upload will still succeed even if the LLM is unavailable (basic profile created)

### "Module not found" errors on backend start

Make sure you're using the correct virtual environment:

```bash
source .venv/bin/activate    # Note: .venv (with dot), not venv
uvicorn app.main:app --reload
```

## License

Private project.
