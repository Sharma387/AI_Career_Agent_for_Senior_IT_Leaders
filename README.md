# AI_Career_Agent_for_Senior_IT_Leaders

An AI-powered career intelligence system that uses RAG (Retrieval-Augmented Generation) to match senior IT leaders with job opportunities, generate tailored application materials, and provide career insights.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    React Frontend (TypeScript)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │Dashboard │  │ Job Board│  │ Tracker  │  │ Insights         │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
└───────┼──────────────┼──────────────┼─────────────────┼─────────────┘
        │              │              │                 │
        ▼              ▼              ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    API Router Layer                           │   │
│  └──────────┬───────────────────────────────────────┬──────────┘   │
│             │                                       │              │
│  ┌──────────▼───────────────────────────────────────▼──────────┐   │
│  │                   Service Layer                              │   │
│  │  ProfileService  JobService  TrackingService                │   │
│  └──────────┬───────────────────────────────────────┬──────────┘   │
│             │                                       │              │
│  ┌──────────▼───────────────────────────────────────▼──────────┐   │
│  │                   Agent Layer                                │   │
│  │  LLM Matching Agent  Insight Agent  Career Strategy Agent    │   │
│  └──────────┬───────────────────────────────────────┬──────────┘   │
│             │                                       │              │
│  ┌──────────▼───────────────────────────────────────▼──────────┐   │
│  │                   RAG Layer                                  │   │
│  │  CareerRAG  JobRAG  ApplicationRAG                          │   │
│  └──────────┬───────────────────────────────────────┬──────────┘   │
│             │                                       │              │
│  ┌──────────▼───────────────────────────────────────▼──────────┐   │
│  │                   Data Layer                                 │   │
│  │  SQLite (profiles, jobs, applications)                      │   │
│  │  ChromaDB (career, job, application embeddings)             │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer          | Technology                                    |
|----------------|-----------------------------------------------|
| Frontend       | React (TypeScript) with Tailwind CSS          |
| Backend        | Python 3.11+, FastAPI, Pydantic               |
| RAG Framework  | LangChain + ChromaDB                          |
| LLM            | Nvidia NIM (meta/llama-3.1-8b-instruct)       |
| Embeddings     | sentence-transformers (all-MiniLM-L6-v2)      |
| Vector Store   | ChromaDB (persistent, local)                  |
| Database       | SQLite via SQLAlchemy (async)                 |
| Document Parsing | PyPDF, docx2txt                            |

## Project Structure

```
ai-career-agent/
├── app/
│   ├── main.py                    # FastAPI application entry
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Settings and environment config
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # All API endpoints
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── career_rag.py          # Career knowledge base RAG
│   │   ├── job_rag.py             # Job knowledge base RAG
│   │   └── application_rag.py     # Application history RAG
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── llm_matcher_agent.py   # LLM-powered job matching
│   │   ├── resume_agent.py        # Resume/cover letter generation
│   │   └── insight_agent.py       # Career insights analysis
│   ├── services/
│   │   ├── __init__.py
│   │   ├── profile_service.py     # Profile management
│   │   ├── job_service.py         # Job and matching operations
│   │   └── tracking_service.py    # Application tracking
│   ├── db/
│   │   ├── __init__.py
│   │   └── models.py              # SQLAlchemy models
│   └── ingestion/
│       ├── __init__.py
│       ├── linkedin_scraper.py    # LinkedIn job scraping
│       ├── seek_scraper.py        # Seek job scraping
│       └── job_scraper.py         # Unified job scraping interface
├── frontend-react/
│   ├── public/
│   └── src/
│       ├── api/
│       │   └── client.ts          # API client with scheduler endpoints
│       ├── components/
│       │   └── ...                # Reusable components
│       ├── context/
│       │   └── AuthContext.tsx    # Authentication context
│       ├── pages/
│       │   ├── Applications.tsx   # Application tracking
│       │   ├── Dashboard.tsx      # Main dashboard
│       │   ├── InterviewPrep.tsx  # Interview preparation
│       │   ├── Jobs.tsx           # Job board with scrape controls
│       │   ├── Register.tsx       # User registration
│       │   ├── Resume.tsx         # Profile resume management
│       │   └── Settings.tsx       # User settings with scheduler monitoring
│       ├── types/                 # TypeScript type definitions
│       └── App.tsx                # Main application component
├── data/
│   ├── resumes/                   # Resume files
│   ├── jobs/                      # Job descriptions
│   └── embeddings/                # ChromaDB persistent storage
├── prompts/
│   ├── match_prompt.txt           # Job matching prompt template
│   └── resume_prompt.txt          # Resume generation prompt
├── .env.example
├── requirements.txt
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- Nvidia NIM API key (get one at https://build.nvidia.com/)
- Git

### 1. Clone and Navigate

```bash
cd AI_Career_Agent_for_Senior_IT_Leaders
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 5. Run the Application

**Terminal 1 - Backend:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd frontend-react
npm install
npm run dev
```

Backend API docs: http://localhost:8000/docs
Frontend UI: http://localhost:5173

## API Endpoints

### Profile

| Method | Endpoint                         | Description                    |
|--------|----------------------------------|--------------------------------|
| POST   | `/api/profile/upload-resume`     | Upload and parse resume file   |
| GET    | `/api/profile/{profile_id}`      | Get profile and career chunks  |
| POST   | `/api/profile/{profile_id}/project` | Add detailed project       |

### Jobs

| Method | Endpoint                         | Description                    |
|--------|----------------------------------|--------------------------------|
| POST   | `/api/jobs/add`                  | Add job description            |
| GET    | `/api/jobs`                      | List all jobs                  |
| POST   | `/api/jobs/{job_id}/match`       | Run job matching analysis      |
| POST   | `/api/jobs/{job_id}/generate-materials` | Generate resume/cover letter |
| POST   | `/api/jobs/scrape/trigger`       | Trigger job scraping (manual/external) |
| POST   | `/api/jobs/scrape/incremental`   | Trigger incremental job scraping |
| POST   | `/api/jobs/scrape/full`          | Trigger full job scraping      |

### Scheduler

| Method | Endpoint                         | Description                    |
|--------|----------------------------------|--------------------------------|
| GET    | `/api/scheduler/status`          | Get scheduler status and next run times |
| POST   | `/api/scheduler/trigger-incremental` | Manually trigger incremental scrape |
| POST   | `/api/scheduler/trigger-full`    | Manually trigger full scrape   |

### Applications

| Method | Endpoint                              | Description                 |
|--------|---------------------------------------|-----------------------------|
| POST   | `/api/applications/track`             | Track new application       |
| PUT    | `/api/applications/{id}/status`       | Update application status   |
| GET    | `/api/applications/stats/{profile_id}` | Get application statistics |
| GET    | `/api/applications/{profile_id}`      | List all applications       |
| GET    | `/api/applications/{profile_id}/insights` | Get career insights    |

### Health

| Method | Endpoint      | Description      |
|--------|---------------|------------------|
| GET    | `/api/health` | Health check     |

## Sample Usage Workflow

### 1. Upload Resume

```bash
curl -X POST http://localhost:8000/api/profile/upload-resume \
  -F "file=@data/resumes/sample_resume.txt"
```

### 2. Add Job Description

```bash
curl -X POST http://localhost:8000/api/jobs/add \
  -H "Content-Type: application/json" \
  -d '{"text": "Senior Director of Platform Engineering at FinServe Global..."}'
```

### 3. Run Job Match

```bash
curl -X POST "http://localhost:8000/api/jobs/1/match?profile_id=1"
```

### 4. Generate Application Materials

```bash
curl -X POST "http://localhost:8000/api/jobs/1/generate-materials?profile_id=1"
```

### 5. Track Application

```bash
curl -X POST http://localhost:8000/api/applications/track \
  -H "Content-Type: application/json" \
  -d '{"job_id": 1, "profile_id": 1, "status": "applied"}'
```

## Configuration

Environment variables in `.env`:

| Variable                        | Default                                     | Description                                                                 |
|---------------------------------|---------------------------------------------|-----------------------------------------------------------------------------|
| `LLM_PROVIDER`                  | `nvidia`                                    | `nvidia` (remote) or `ollama` (local)                                       |
| `NVIDIA_API_KEY`                | —                                           | Required if provider=nvidia                                                 |
| `NVIDIA_BASE_URL`               | `https://integrate.api.nvidia.com/v1`       | Nvidia NIM API endpoint                                                     |
| `NVIDIA_MODEL`                  | `meta/llama-3.1-8b-instruct`                | Nvidia NIM model                                                            |
| `OLLAMA_BASE_URL`               | `http://localhost:11434`                    | Ollama server URL (local fallback)                                          |
| `OLLAMA_MODEL`                  | `llama3.1:8b`                               | Ollama model to use                                                         |
| `EMBEDDING_MODEL`               | `all-MiniLM-L6-v2`                          | Sentence-transformer model for RAG                                          |
| `DEBUG`                         | `true`                                      | Enable debug logging                                                        |
| `LINKEDIN_SCRAPING_ENABLED`     | `false`                                     | Enable LinkedIn job scraping                                                |
| `LINKEDIN_EMAIL`                | —                                           | LinkedIn email for authentication (if scraping enabled)                     |
| `LINKEDIN_PASSWORD`             | —                                           | LinkedIn password for authentication (if scraping enabled)                  |
| `SEEK_SCRAPING_ENABLED`         | `false`                                     | Enable Seek job scraping                                                    |
| `SEEK_DEFAULT_KEYWORDS`         | —                                           | Default keywords for Seek scraping                                          |
| `SEEK_DEFAULT_LOCATION`         | —                                           | Default location for Seek scraping                                          |
| `SCHEDULER_TIMEZONE`            | `Pacific/Auckland`                          | Timezone for scheduler (NZ time)                                            |
| `BUSINESS_HOURS_START`          | `8`                                         | Start hour for business hours scraping (NZ time, 24-hour format)            |
| `BUSINESS_HOURS_END`            | `18`                                        | End hour for business hours scraping (NZ time, 24-hour format)              |
| `INCREMENTAL_SCRAPE_HOURS`      | `2`                                         | Hours back for incremental scrape during business hours                     |
| `FULL_SCRAPE_TIME_HOUR`         | `2`                                         | Hour for daily full scrape (NZ time, 24-hour format)                        |
| `FULL_SCRAPE_TIME_MINUTE`       | `0`                                         | Minute for daily full scrape (NZ time)                                      |
| `SCHEDULER_INCREMENTAL_ENABLED` | `true`                                      | Enable incremental scraping scheduler                                       |
| `SCHEDULER_FULL_ENABLED`        | `true`                                      | Enable full scraping scheduler                                              |

### Job Scraping Scheduler Configuration

The AI Career Agent includes an internal scheduler for automated job scraping from LinkedIn and Seek. The scheduler runs two types of jobs:

1. **Incremental Scraping**: Runs every 2 hours during business hours to capture recently posted jobs
2. **Full Scraping**: Runs once daily at 2 AM NZ time for comprehensive job collection

To enable job scraping:
- Set `LINKEDIN_SCRAPING_ENABLED=true` and provide LinkedIn credentials
- Set `SEEK_SCRAPING_ENABLED=true` (once Seek scraping is implemented)
- Adjust scheduling parameters as needed (business hours, scrape intervals, etc.)

The scheduler automatically starts when the application begins and shuts down gracefully when the application stops.

### Using Local LLM (Ollama)

1. Install Ollama: https://ollama.ai
2. Start server: `ollama serve`
3. Pull a model: `ollama pull llama3.1:8b`
4. Set in `.env`:
   ```
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=llama3.1:8b
   ```

**Token considerations for local models:**
- `llama3.1:8b` has 128K context window — sufficient for most career matching tasks
- Smaller models (3B, 7B) may struggle with complex JSON extraction
- For best results with local LLMs, use `llama3.1:8b` or `llama3.1:70b`

## Roadmap

### Phase 2: Production Hardening

- React/TypeScript frontend with Tailwind CSS (replacing Streamlit)
- User authentication (JWT + OAuth)
- PostgreSQL migration (replacing SQLite)
- Redis caching for RAG queries
- Rate limiting and request validation

### Phase 3: Intelligence Expansion

- Job scraping agents (Seek, LinkedIn)
- Email ingestion (Gmail API)
- Daily job recommendations engine
- Auto-apply assistant (optional)
- Career trend analysis across market data

### Phase 4: Enterprise Features

- Multi-user support for executive coaching firms
- Custom knowledge base ingestion (company-specific data)
- Integration with ATS systems (Greenhouse, Lever)
- White-label deployment options

### Phase 5: AI Agent Autonomy

- Autonomous job application monitoring and alerting
- Proactive career opportunity identification
- Automated outreach drafting and follow-up
- Real-time market intelligence dashboard

### Why Streamlit First, React Later

Streamlit was chosen for the MVP because:
- Python end-to-end (no JS/TS context switching)
- RAG libraries are Python-native (LangChain, ChromaDB)
- 200 lines of Streamlit vs 2000+ lines of React for same functionality
- Faster iteration for validating core RAG and matching logic

The backend is a clean FastAPI REST API — swapping Streamlit for React is a frontend-only change. All 13 API endpoints stay the same.
