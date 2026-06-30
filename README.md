# AI Career Agent for Senior IT Leaders

An AI-powered career intelligence platform that helps senior IT professionals (Project Managers, IT Directors, CTOs) discover relevant job opportunities, match against their profile, and generate tailored application materials using RAG and local LLMs.

## Features

- **Multi-Source Job Search** — Adzuna API (NZ/AU jobs), Seek automation (Playwright), LinkedIn browser extension
- **AI Resume Parsing** — Multi-model support (local Ollama + cloud OpenAI/Anthropic) with chunked extraction, truncation repair, and v1.0 schema
- **AI Job Matching** — RAG-based scoring with skills, experience, industry, and leadership dimensions
- **Resume & Cover Letter Generation** — LLM-generated materials tailored per job (Robert Half NZ template)
- **Interview Strategy** — AI-prepared talking points, potential questions, and gap analysis
- **Application Tracking** — Status management, insights, and analytics
- **Smart Deduplication** — URL + title/company matching prevents duplicate entries
- **API Usage Management** — Daily dedup, monthly quota tracking, automatic fallback to free APIs
- **Scheduled Scraping** — Daily automated Seek searches with configurable role presets
- **Dark Premium UI** — shadcn/ui + Tailwind with dark navy theme, score rings, and Framer Motion animations
- **Model Selection** — Choose parsing model per upload (local Ollama models or cloud APIs with key input)

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│        React Frontend (TypeScript + shadcn/ui + Tailwind + Vite)        │
│  Discover │ My Jobs │ Applications │ Resume │ Insights │ Interview     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ REST API (proxy via Vite → :8000)
┌──────────────────────────────────▼─────────────────────────────────────┐
│                         FastAPI Backend (async)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ API Routes  │  │ Job Ingestion│  │  LLM Agents  │  │ Scheduler │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘  │
│         │                │                  │                │        │
│  ┌──────▼──────────────▼──────────────────▼────────────────▼──────┐  │
│  │              Service Layer (Profile, Job, Tracking, Document)    │  │
│  └──────┬─────────────────────────────────────────────────┬───────┘  │
│         │                                                 │          │
│  ┌──────▼───────────┐  ┌─────────────────────────────────▼───────┐  │
│  │ SQLite (aiosqlite)│  │ ChromaDB (Granular RAG Embeddings)      │  │
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
| Frontend        | React 18, TypeScript, Vite, shadcn/ui, Tailwind CSS, Lucide, Framer Motion |
| Backend         | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy (async)        |
| LLM (default)   | Ollama (gemma4:e4b local, free)                              |
| LLM (optional)  | OpenAI (GPT-4o), Anthropic (Claude Sonnet 4), NVIDIA NIM     |
| Embeddings      | sentence-transformers (all-MiniLM-L6-v2)                      |
| Vector Store    | ChromaDB (granular per-section embeddings)                    |
| Database        | SQLite (via aiosqlite)                                        |
| Job APIs        | Adzuna, Jobicy, Arbeitnow                                     |
| Browser Automation | Playwright (Seek), Chrome Extension (LinkedIn)             |
| Scheduler       | APScheduler (async)                                           |
| Auth            | JWT (python-jose) + bcrypt/passlib                            |
| Resume Templates | Robert Half NZ IT format (HTML + DOCX)                      |

## Quick Start

### Prerequisites

- Python 3.11+ (tested with 3.14)
- Node.js 18+
- Ollama installed and running (`ollama serve`)
- gemma4:e4b model pulled (`ollama pull gemma4:e4b`)

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
# - OLLAMA_MODEL=gemma4:e4b (default parser model)
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
| `OLLAMA_MODEL` | Default Ollama model for parsing | `gemma4:e4b` |
| `OLLAMA_HQ_MODEL` | High-quality model for rewrites (optional) | `gemma4:e4b` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `ADZUNA_APP_ID` | Adzuna API app ID (free tier) | — |
| `ADZUNA_APP_KEY` | Adzuna API key | — |
| `ADZUNA_COUNTRY` | Job search country code | `nz` |
| `JWT_SECRET_KEY` | Secret for JWT auth tokens | — |
| `SEEK_SCRAPING_ENABLED` | Enable Seek Playwright automation | `true` |
| `SEEK_HEADLESS` | Run Playwright headless | `true` |
| `SEEK_DAILY_SCRAPE_HOUR` | Daily scrape time (NZ, 24h) | `7` |
| `SEEK_ROLE_PRESETS` | Comma-separated role IDs for scheduled search | `project-manager,sr-project-manager,...` |

See `.env.example` for the full list.

## Resume Parsing Pipeline

The system uses a multi-stage AI pipeline for resume parsing:

1. **Text Extraction** — pypdf/docx2txt with OCR fallback (Tesseract)
2. **Chunked AI Parsing** — Resume split into ~4000 char chunks, each parsed independently
3. **Robust JSON Extraction** — Handles markdown blocks, truncated responses, think-blocks
4. **Chunk Merging** — Deduplicates experience, skills, certifications across chunks
5. **Validation** — Email, phone, date format, completeness checks
6. **Career Expansion** — LLM expands parsed data into STAR stories and projects
7. **Granular RAG Ingestion** — Per-section embeddings for precise retrieval

**Model Selection:** Users can choose per-upload:
- Local: Any Ollama model (gemma4:e4b, qwen3.5, llama3.1, etc.)
- Cloud: OpenAI GPT-4o/Mini, Anthropic Claude Sonnet 4/Haiku (requires API key)

## Job Search Features

### Adzuna (Primary)
- Free API with 250 calls/month
- Covers NZ, AU, UK, US job markets
- Aggregates from Seek, Trade Me Jobs, and more
- Role presets: PM, Sr PM, IT Manager, Engineering Manager, IT Director, CTO
- Returns snippets only — user pastes full JDs for matching

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

## Testing

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Currently **86 tests** covering: API routes, database models, job parser, job scraper, LLM factory, resume parser, agents, deduplication, bug fixes, and LinkedIn ingest endpoint.

## Project Structure

```
├── app/
│   ├── agents/          # LLM-powered agents (matcher, resume, insight, json_parser)
│   ├── api/             # FastAPI routes + JWT auth
│   ├── core/            # Config, LLM factory, scheduler, rate limiting
│   ├── db/              # SQLAlchemy models + async session (v1.0 schema)
│   ├── ingestion/       # AI resume parser, job parsers, scrapers, adapters
│   ├── rag/             # ChromaDB vector stores (career, job, application)
│   ├── services/        # Business logic (profile, job, tracking, document)
│   └── templates/       # HTML/DOCX templates (Robert Half NZ format)
├── extension/           # LinkedIn Chrome extension (Manifest V3)
├── frontend-react/      # React frontend (Vite + shadcn/ui + Tailwind)
├── tests/               # pytest test suite (86 tests)
├── docs/                # Architecture docs, user manual
├── .env.example         # Environment variable template
├── requirements.txt     # Python dependencies
└── pyproject.toml       # Pytest + Ruff configuration
```

## Troubleshooting

### "Address already in use" (port 8000)

```bash
lsof -ti:8000 | xargs kill -9
uvicorn app.main:app --reload
```

### Frontend "npm run dev" fails with package.json not found

You need to be in the `frontend-react` folder:
```bash
cd frontend-react
npm run dev
```

### "No module named 'fastapi'" on backend start

You forgot to activate the virtual environment:
```bash
source .venv/bin/activate    # Note: .venv (with dot), not venv
uvicorn app.main:app --reload
```

### PDF resume upload takes too long or fails

- Ensure Ollama is running: `ollama serve`
- Ensure the model is pulled: `ollama pull gemma4:e4b`
- The system uses `num_predict=16000` and `num_ctx=32768` — first call loads model into RAM (~30s)
- If JSON extraction fails, check `/tmp/chunk_*_response.txt` for raw model output
- Try a cloud model (OpenAI GPT-4o) for faster, more reliable parsing

### Reset database (fresh start)

```bash
rm -f app/data/career_agent.db
# Restart backend — tables recreated automatically
```

## License

Private project.
