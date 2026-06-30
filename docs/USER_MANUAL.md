# AI Career Agent — User Manual

**For Senior IT Leaders**

---

## Table of Contents

1. [Welcome](#1-welcome)
2. [Getting Started](#2-getting-started)
3. [Resume Management](#3-resume-management)
4. [Discovering Jobs](#4-discovering-jobs)
5. [My Jobs & Matching](#5-my-jobs--matching)
6. [Application Tracking](#6-application-tracking)
7. [Career Insights](#7-career-insights)
8. [Interview Preparation](#8-interview-preparation)
9. [Settings & Configuration](#9-settings--configuration)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Welcome

### What is AI Career Agent

AI Career Agent is a local-first career intelligence platform built for senior IT leaders. It uses AI (large language models + RAG) to:

- Parse your resume into a structured career profile
- Discover relevant jobs from multiple sources (Adzuna, Seek, LinkedIn)
- Score your fit against specific job descriptions
- Generate tailored resumes and cover letters
- Prepare interview strategies
- Track applications and identify patterns

Everything runs on your machine. Your data stays local except for LLM API calls (which you control).

### Who is it for

- Senior Project Managers
- IT Directors and VPs of Engineering
- CTOs and Engineering Managers
- Anyone targeting senior technology leadership roles in NZ/AU

---

## 2. Getting Started

### Prerequisites

| Requirement | Minimum |
|---|---|
| Python | 3.11+ (tested on 3.14) |
| Node.js | 18+ |
| Ollama | Installed and running |
| Model | `gemma4:e4b` pulled |
| RAM | 8 GB+ (for local model inference) |

### Installation

```bash
# Clone
git clone https://github.com/Sharma387/AI_Career_Agent_for_Senior_IT_Leaders.git
cd AI_Career_Agent_for_Senior_IT_Leaders

# Backend setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Environment config
cp .env.example .env
# Edit .env: set ADZUNA keys, JWT_SECRET_KEY

# Frontend setup
cd frontend-react
npm install
cd ..
```

### Running the Application

**Terminal 1 — Backend (port 8000):**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend (port 5173):**
```bash
cd frontend-react
npm run dev
```

Open **http://localhost:5173** in your browser.

### First-Time Setup

1. Register an account (email + password)
2. Upload your resume (PDF, DOCX, or TXT)
3. Wait for AI parsing (~1-3 minutes with local model)
4. Review your parsed profile (skills, experience, certifications)

---

## 3. Resume Management

### Uploading Your Resume

1. Navigate to **Resume** in the sidebar
2. Select a parsing model from the dropdown:
   - **Local models** (free): gemma4:e4b, qwen3.5, llama3.1, etc.
   - **Cloud models** (faster, requires API key): GPT-4o, Claude Sonnet 4
3. If using a cloud model, enter your API key in the field that appears
4. Click **Upload Resume** and select your file
5. Wait for processing (progress indicator shows status)

### What Happens During Upload

The system:
1. Extracts text from your file (PDF/DOCX/TXT)
2. Splits into chunks (~4000 chars each)
3. Sends each chunk to the selected AI model
4. Extracts structured data: name, email, skills, experience, certifications
5. Merges chunks (deduplicates roles and skills)
6. Expands into STAR stories and project narratives
7. Generates a formatted resume (Robert Half NZ template)
8. Stores everything in the database

### After Upload

You can:
- **View** original text vs. generated resume (side-by-side)
- **Download** as HTML or Word (DOCX)
- **Edit** basic info, summary, skills, certifications, interests
- **Add projects** manually with STAR stories
- **Replace** resume by uploading a new file

### Editing Your Profile

All sections are editable after upload:
- **Basic Info:** Name, phone, LinkedIn URL
- **Summary:** Professional summary paragraph
- **Skills:** Add/remove with categories (Edit button)
- **Projects:** Add, edit, delete with technologies and impact
- **Certifications:** Add/remove certifications
- **Interests:** Comma-separated list

---

## 4. Discovering Jobs

### The Discover Page

The **Discover** page connects to Adzuna API to browse jobs:

1. Enter keywords (e.g., "Project Manager") and location (e.g., "Auckland")
2. Or use quick role presets: PM, Sr PM, IT Manager, Engineering Manager, IT Director, CTO
3. Choose country: NZ, AU, UK, US
4. Click **Search**

**Important:** Adzuna returns snippets only (not full descriptions). These are for browsing — you'll need the full JD for matching.

### API Usage

- Free tier: 250 API calls/month
- Same search on same day = 1 call (cached)
- Usage shown in the UI: "API: X/250 remaining"
- When exhausted: Jobicy + Arbeitnow fallback (free, no key needed)

### LinkedIn Extension

For full job descriptions from LinkedIn:
1. Install the Chrome extension (from `extension/` folder)
2. Navigate to any LinkedIn job page
3. Click "Capture Job" in the extension popup
4. The full JD is sent to your local backend and stored

---

## 5. My Jobs & Matching

### Adding Full Job Descriptions

From the **My Jobs** page:
1. Click **Add Job**
2. Paste the full job description text
3. The system parses: title, company, location, seniority, skills
4. Job is stored and available for matching

### Running a Match

On a job's detail page:
1. Click the **Match** tab
2. Click **Run Match Analysis**
3. Wait ~30-60 seconds (AI retrieves your career data and scores)

### Understanding Match Results

| Score | Color | Meaning |
|-------|-------|---------|
| 75-100 | Green | Strong match — apply with confidence |
| 50-74 | Yellow | Moderate — review gaps, address in application |
| 0-49 | Red | Weak — significant gaps exist |

Scoring dimensions:
- **Skills Match (30%)** — Technical and soft skills alignment
- **Experience Level (25%)** — Seniority and years match
- **Industry Relevance (20%)** — Domain experience alignment
- **Leadership Signals (25%)** — Strategic thinking, team leadership evidence

Results include: **Strengths**, **Gaps**, **Evidence** (citations from your career data), and **Recommendation**.

### Skill Articulation

For each gap identified, you can:
- Mark "I have this skill" and provide evidence
- This feedback is stored and used in future matching

### Generating Application Materials

1. Click the **Materials** tab on a job
2. Click **Generate Resume & Cover Letter**
3. Wait ~30-60 seconds
4. Download as HTML or Word (Robert Half NZ format)

Materials are tailored to the specific job — only using data from your actual career profile.

---

## 6. Application Tracking

### Tracking an Application

After generating materials or applying to a job:
1. Click **Track Application** on the job detail page
2. Status defaults to "Applied"

### Updating Status

On the Applications page, update status through the pipeline:
- Applied → Phone Screen → Technical Interview → Final Interview → Offered/Rejected/Withdrawn → Accepted

Add feedback notes at each stage — these feed into the Insights engine.

### Application Statistics

The Applications page shows:
- Total applications by status
- Interview conversion rate
- Rejection stage distribution
- Timeline view

---

## 7. Career Insights

The **Insights** page analyzes your application history:

- **Rejection Patterns:** At which stages do rejections happen? What's in common?
- **Success Patterns:** What types of roles convert to interviews/offers?
- **Improvement Suggestions:** Actionable recommendations based on your data
- **Interview Conversion Rate:** How many applications lead to conversations?

Insights improve with more data — add feedback notes and track all applications.

---

## 8. Interview Preparation

For any job in "My Jobs":
1. Navigate to the **Interview** tab
2. Click **Generate Strategy**
3. Receive:
   - Likely interview questions (tailored to role + seniority)
   - STAR-format answers drawn from YOUR experience
   - Key talking points
   - Gap mitigation strategies

All answers reference your actual career data — nothing fabricated.

---

## 9. Settings & Configuration

### LLM Configuration

In `.env`:
```bash
LLM_PROVIDER=ollama              # For job matching, materials, insights
OLLAMA_MODEL=gemma4:e4b          # Default model
OLLAMA_BASE_URL=http://localhost:11434
```

Resume parsing model is selected per-upload in the UI (not from .env).

### Job Search Configuration

```bash
ADZUNA_APP_ID=your_app_id       # Free: https://developer.adzuna.com/signup
ADZUNA_APP_KEY=your_app_key
ADZUNA_COUNTRY=nz               # nz, au, gb, us
```

### Authentication

```bash
JWT_SECRET_KEY=any-random-string-here
```

Default credentials after registration. Password reset via secret questions.

---

## 10. Troubleshooting

### Backend won't start

| Error | Fix |
|-------|-----|
| "No module named 'fastapi'" | Activate venv: `source .venv/bin/activate` |
| "Address already in use" | Kill old process: `lsof -ti:8000 \| xargs kill -9` |
| Database errors | Reset: `rm -f app/data/career_agent.db` then restart |

### Frontend won't start

| Error | Fix |
|-------|-----|
| "package.json not found" | Run from correct folder: `cd frontend-react && npm run dev` |
| Port 5173 in use | Kill: `lsof -ti:5173 \| xargs kill -9` |

### Resume parsing issues

| Symptom | Fix |
|---------|-----|
| "Processing" hangs forever | Check Ollama is running: `ollama serve` |
| Empty parse result | Check `/tmp/chunk_*_response.txt` for raw output |
| Takes > 3 minutes | Normal for gemma4 on M1. Use GPT-4o-mini for speed |
| "Failed to extract JSON" | Usually truncation — now auto-repaired. Try cloud model if persists |

### General

| Issue | Fix |
|-------|-----|
| Login fails | Reset DB: `rm -f app/data/career_agent.db`, re-register |
| Ollama model missing | Pull it: `ollama pull gemma4:e4b` |
| Slow first request | Model loading into RAM — wait 30s, try again |

---

## Quick Reference

| Action | Command / Location |
|--------|-------------------|
| Start backend | `source .venv/bin/activate && uvicorn app.main:app --reload` |
| Start frontend | `cd frontend-react && npm run dev` |
| Run tests | `source .venv/bin/activate && python -m pytest tests/ -v` |
| Kill stuck port | `lsof -ti:8000 \| xargs kill -9` |
| Reset database | `rm -f app/data/career_agent.db` |
| API docs | http://localhost:8000/docs |
| App URL | http://localhost:5173 |
| Pull Ollama model | `ollama pull gemma4:e4b` |
