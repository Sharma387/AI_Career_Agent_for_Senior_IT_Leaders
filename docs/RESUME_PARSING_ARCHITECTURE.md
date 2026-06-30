# Resume Parsing Architecture

## Overview

When a user uploads a resume (PDF/DOCX/TXT), the system goes through a multi-stage pipeline to extract, understand, and store the information. The pipeline supports multiple LLM backends and handles truncated/malformed model responses gracefully.

---

## The Flow (Step by Step)

```
User uploads resume.pdf (+ selects model from dropdown)
        │
        ▼
┌─────────────────────────────────────────┐
│  STAGE 1: File Extraction + OCR         │  (~1-5s)
│  app/ingestion/resume_parser.py         │
│  app/ingestion/ocr_extractor.py         │
│                                         │
│  PDF → pypdf → raw text                 │
│  DOCX → docx2txt → raw text            │
│  TXT → read directly                    │
│  IF text < 300 chars → OCR fallback     │
└─────────────┬───────────────────────────┘
              │ raw_text (any length, no truncation)
              ▼
┌─────────────────────────────────────────┐
│  STAGE 2: Chunked AI Parser             │  (~30-90s)
│  app/ingestion/ai_resume_parser.py      │
│                                         │
│  1. Split into ~4000 char chunks        │
│     (paragraph boundaries, never        │
│      mid-paragraph)                     │
│  2. Parse each chunk with selected      │
│     model (Ollama/OpenAI/Anthropic)     │
│  3. Robust JSON extraction handles:     │
│     - ```json blocks                    │
│     - <think> blocks                    │
│     - Truncated responses (repair)      │
│  4. Merge chunks (dedup by             │
│     role+company, skill name)           │
│  5. Output: v1.0 schema JSON            │
│                                         │
│  Settings (Ollama):                     │
│    temperature=0                        │
│    num_predict=16000                    │
│    num_ctx=32768                        │
└─────────────┬───────────────────────────┘
              │ v1.0 ParsedResume
              ▼
┌─────────────────────────────────────────┐
│  STAGE 3: Validation Layer              │  (~10ms)
│  app/ingestion/profile_validator.py     │
│                                         │
│  Validates: email format, phone format, │
│  LinkedIn URL, date consistency,        │
│  duplicate skills, empty required fields│
│  Returns: { is_valid, warnings, errors }│
└─────────────┬───────────────────────────┘
              │ Validated ParsedResume
              ▼
┌─────────────────────────────────────────┐
│  STAGE 4: Career Expander               │  (~10-30s)
│  app/ingestion/career_expander.py       │
│                                         │
│  INPUT: Structured ParsedResume         │
│  (NOT raw text — fewer tokens, faster)  │
│  OUTPUT: Projects with STAR stories,    │
│    skills_by_category, achievements     │
│                                         │
│  FALLBACK: If no projects from expander,│
│  creates project entries from work      │
│  experience (preserves CV structure)    │
└─────────────┬───────────────────────────┘
              │ ExpandedProfile
              ▼
┌─────────────────────────────────────────┐
│  STAGE 5: Database Storage + Audit      │
│  app/services/profile_service.py        │
│                                         │
│  Stores:                                │
│  • career_profiles (v1.0 schema JSON +  │
│    flat fields for backward compat)     │
│  • projects (from expander or fallback) │
│  • skills (categorized)                 │
│  • certifications                       │
│  • resume_parse_runs (audit: model,     │
│    time, status, chunks, validation)    │
│  • formatted_resume_html (Robert Half)  │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  STAGE 6: Granular RAG Ingestion        │
│  app/rag/career_rag.py                  │
│                                         │
│  Separate embeddings for:               │
│  - Each experience entry                │
│  - Each project                         │
│  - Each achievement                     │
│  - Skills summary                       │
│  - Certifications                       │
│  Each with metadata: profile_id, type   │
└─────────────────────────────────────────┘
```

---

## Model Selection

Users choose their parsing model from a dropdown on the Resume page:

### Local Models (Ollama — free, private)
| Model | Speed | Quality | Notes |
|-------|-------|---------|-------|
| `gemma4:e4b` | ~60s/chunk | High | Default. Best for multi-column PDFs |
| `qwen3.5:latest` | ~30s/chunk | Good | Faster but sometimes wraps JSON in think blocks |
| `llama3.1:8b` | ~20s/chunk | Moderate | Fastest local option |

### Cloud Models (requires API key)
| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| `openai:gpt-4o` | ~5s/chunk | Excellent | ~$0.01/resume |
| `openai:gpt-4o-mini` | ~3s/chunk | Very Good | ~$0.001/resume |
| `anthropic:claude-sonnet-4-20250514` | ~5s/chunk | Excellent | ~$0.01/resume |
| `anthropic:claude-3-haiku-20240307` | ~3s/chunk | Good | ~$0.001/resume |

The model list is loaded dynamically from Ollama's `/api/tags` endpoint on page load. Cloud models are always available as options.

---

## JSON Extraction (The Critical Piece)

**File:** `app/agents/json_parser.py`

Local models (especially gemma4) often wrap their output in markdown code blocks or produce truncated JSON. The extraction engine handles all these cases:

### Strategy 1: Direct Parse
Content is already clean JSON → `json.loads()` succeeds.

### Strategy 2: Markdown Extraction
Strips ` ```json ... ``` ` wrappers. Handles truncated responses where the closing ` ``` ` is missing.

### Strategy 3: Brace Matching
Finds first `{` and last `}` in the content, extracts between them.

### Strategy 4: Truncated JSON Repair
When the model hits `num_predict` limit and produces incomplete JSON:
1. Tracks string boundaries (handles unclosed quotes)
2. Truncates to last complete value
3. Removes trailing incomplete key-value pairs
4. Closes all open brackets/braces
5. Progressively trims back if first attempt fails

Also handles `<think>...</think>` blocks from reasoning models (qwen3.5).

---

## v1.0 Schema

The full parsed resume is stored as JSON in `career_profiles.parsed_resume_v1`:

```json
{
  "schema_version": "1.0",
  "resume": {
    "personal_info": {
      "full_name": "", "preferred_name": null, "headline": "",
      "email": "", "phone": "",
      "location": {"city": "", "state": "", "country": ""},
      "linkedin": "", "github": ""
    },
    "professional_summary": {
      "summary_text": "", "years_experience": null,
      "seniority_level": "", "industries": []
    },
    "core_skills": {
      "technical_skills": [], "functional_skills": [],
      "tools_platforms": [], "methodologies": [], "domains": []
    },
    "work_experience": [{
      "company": "", "role_title": "", "employment_type": "full-time",
      "location": "", "start_date": "", "end_date": "",
      "responsibilities": [],
      "achievements": [{"statement": "", "impact_metrics": {"type": "", "value": "", "unit": ""}}],
      "tech_stack": []
    }],
    "projects": [{"project_name": "", "description": "", "role": "", "technologies": [], "outcomes": []}],
    "education": [{"institution": "", "degree": "", "field_of_study": "", "end_year": ""}],
    "certifications": [{"name": "", "issuing_body": ""}],
    "languages": [{"language": "", "proficiency": ""}],
    "ats_metadata": {"keywords": [], "completeness_score": 0, "last_updated": ""}
  }
}
```

---

## Chunking Strategy

**File:** `app/ingestion/ai_resume_parser.py` → `chunk_resume()`

```python
def chunk_resume(raw_text: str, max_chunk_size: int = 4000) -> list[str]:
    """
    Split resume into chunks at paragraph boundaries.
    
    Strategy:
    1. Split by double newlines (paragraph boundaries)
    2. Group paragraphs until 4000 chars reached
    3. Never split mid-paragraph
    4. Oversized paragraphs get truncated at max_chunk_size
    """
```

For a typical 10K-char resume → 3 chunks → each parsed independently → merged with dedup.

---

## Merge Logic

When merging chunks, the system prevents duplicates:
- **Personal info:** First non-empty value wins
- **Work experience:** Dedup by `(role_title.lower(), company.lower())`
- **Skills:** Dedup by `skill_name.lower()` across all categories
- **Certifications:** Dedup by `name.lower()`
- **Education:** Dedup by `(degree.lower(), institution.lower())`

Experience is sorted by end_date descending (current roles first).

---

## Parse Audit Trail

Every parse is recorded in `resume_parse_runs`:

| Column | Purpose |
|--------|---------|
| `model_name` | Which model was used (e.g., "gemma4:e4b") |
| `prompt_version` | Parser version (currently "v2_chunked") |
| `processing_time_seconds` | Total wall-clock time |
| `parse_status` | "success", "partial", or "failed" |
| `validation_status` | "valid", "warnings", or "errors" |
| `validation_details` | Full validation output (JSON) |
| `chunks_processed` | Number of chunks the resume was split into |

---

## What Gets Stored Where

| Data | Source | DB Location |
|------|--------|-------------|
| Name, email, phone, linkedin | AI Parser (v1.0) | career_profiles flat columns |
| Full v1.0 schema JSON | AI Parser | career_profiles.parsed_resume_v1 |
| Professional summary | AI Parser | career_profiles.summary |
| Original file (PDF/DOCX binary) | Direct upload | career_profiles.original_file_data |
| Extracted raw text | pypdf/docx2txt | career_profiles.raw_resume_text |
| Skills (categorized) | AI Parser | skills table |
| Certifications | AI Parser | certifications table |
| Education | AI Parser | career_profiles.education (JSON) |
| Projects (with STAR) | Career Expander / Fallback | projects table |
| Formatted HTML resume | Template rendering | career_profiles.formatted_resume_html |
| Headline, years_exp, seniority | AI Parser (v1.0) | career_profiles columns |
| Languages, preferences, ATS | AI Parser (v1.0) | career_profiles JSON columns |

---

## Configuration

In `.env`:
```bash
OLLAMA_MODEL=gemma4:e4b          # Default parsing model
OLLAMA_HQ_MODEL=gemma4:e4b       # Optional high-quality model for rewrites
OLLAMA_BASE_URL=http://localhost:11434
LLM_PROVIDER=ollama              # Used for job matching, materials generation
```

Parser settings (hardcoded in `ai_resume_parser.py`):
```python
temperature=0       # Deterministic extraction
num_predict=16000   # Generous token limit to avoid truncation
num_ctx=32768       # Large context window for resume + prompt + response
```

---

## Troubleshooting

### "Failed to extract JSON from LLM response"
- Check `/tmp/chunk_*_response.txt` for the raw model output
- Usually means the model hit its token limit — try a cloud model or increase `num_predict`
- The repair engine now handles most truncated responses automatically

### Parsing takes > 3 minutes
- gemma4:e4b on Apple Silicon M1/M2 takes ~60s per chunk
- A 3-chunk resume = ~3 minutes total
- For faster parsing: use `openai:gpt-4o-mini` (3-5 seconds total)

### Skills from wrong sections appearing
- The prompt instructs "Skills ONLY from skills sections"
- If this still happens with your model, try a different model or manually edit after upload

### Empty projects after upload
- The Career Expander may not produce projects if the parsed data is minimal
- Fallback creates project entries from work_experience automatically
- You can always add projects manually via the UI
