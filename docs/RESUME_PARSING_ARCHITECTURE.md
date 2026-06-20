# Resume Parsing Architecture

## Overview

When a user uploads a resume (PDF/DOCX/TXT), the system goes through a multi-stage pipeline to extract, understand, and store the information. Here's how it works:

---

## The Flow (Step by Step)

```
User uploads resume.pdf
        │
        ▼
┌─────────────────────────────┐
│  STAGE 1: File Extraction   │  (~1 second)
│  app/ingestion/resume_parser.py
│                             │
│  PDF → pypdf → raw text     │
│  DOCX → docx2txt → raw text│
│  TXT → read directly        │
└─────────────┬───────────────┘
              │ raw_text (10,000+ chars)
              ▼
┌─────────────────────────────────────────┐
│  STAGE 2: AI Section Parser             │  (~2-3 minutes)
│  app/ingestion/ai_resume_parser.py      │
│                                         │
│  Model: gemma4:e4b (via Ollama)         │
│  Settings: temperature=0.1              │
│            num_predict=8192             │
│            num_ctx=16384                │
│                                         │
│  Input: Full raw text                   │
│  Output: Structured JSON with:          │
│    - full_name                          │
│    - email, phone, location, linkedin   │
│    - summary (professional paragraph)   │
│    - experience[] (title, company,      │
│      dates, location, bullets)          │
│    - skills{} (categorized)             │
│    - certifications[]                   │
│    - interests[]                        │
│    - education[]                        │
└─────────────┬───────────────────────────┘
              │ parsed (structured dict)
              ▼
┌─────────────────────────────────────────┐
│  STAGE 3: Career Expander (AI)          │  (~1-2 minutes)
│  app/ingestion/career_expander.py       │
│                                         │
│  Model: gemma4:e4b (same model)         │
│                                         │
│  Input: Same raw text                   │
│  Output: Enriched profile with:         │
│    - Enhanced summary                   │
│    - detailed_projects[] (with STAR     │
│      stories, technologies, impact)     │
│    - skills_by_category{}               │
│    - key_achievements[]                 │
│    - interview_stories[]                │
└─────────────┬───────────────────────────┘
              │ expanded (enriched dict)
              ▼
┌─────────────────────────────────────────┐
│  STAGE 4: Database Storage              │
│  app/services/profile_service.py        │
│                                         │
│  Stores into these tables:              │
│  ┌─────────────────────────────────┐    │
│  │ career_profiles                  │    │
│  │  - full_name (from AI parser)    │    │
│  │  - email, phone, linkedin_url    │    │
│  │  - summary (from AI parser)      │    │
│  │  - raw_resume_text (original)    │    │
│  │  - original_file_data (binary)   │    │
│  │  - interests (from AI parser)    │    │
│  │  - education (from AI parser)    │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ projects (from Career Expander)  │    │
│  │  - title, description, role      │    │
│  │  - technologies, impact          │    │
│  │  - STAR stories                  │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ skills (from AI parser)          │    │
│  │  - name, category                │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ certifications (from AI parser)  │    │
│  │  - name, issuer                  │    │
│  └─────────────────────────────────┘    │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  STAGE 5: RAG Ingestion                 │
│  app/rag/career_rag.py                  │
│                                         │
│  Embeds the profile data into ChromaDB  │
│  vector store for later retrieval       │
│  during job matching                    │
└─────────────────────────────────────────┘
```

---

## What Each Stage Does

### Stage 1: File Extraction
**File:** `app/ingestion/resume_parser.py`
**Time:** ~1 second

Simply extracts raw text from the file. For PDFs with multi-column layouts, the text may come out interleaved (left column mixed with right column from different pages). This is a known limitation of PDF extraction.

### Stage 2: AI Section Parser (NEW — replaces old regex parser)
**File:** `app/ingestion/ai_resume_parser.py`
**Time:** ~2-3 minutes
**Model:** gemma4:e4b via Ollama

This is the KEY improvement. Previously, a regex-based parser tried to detect sections by matching keywords like "Certifications" or "Experience" — which failed badly on multi-column PDFs where text from different columns gets interleaved.

Now, the FULL raw text is sent to the AI model with a structured prompt asking it to return JSON. The AI **understands context** — it knows "NTT Data" is a company name (experience), not a certification, regardless of where it appears in the text stream.

**Prompt tells the model:**
- Parse into specific sections (name, email, experience, skills, certifications, interests, education)
- Handle interleaved multi-column text
- Only extract what's actually there (no hallucination)
- Return pure JSON

**Settings:**
- `temperature=0.1` — factual extraction, minimal creativity
- `num_predict=8192` — allow long JSON response (your resume produces ~3000 chars of JSON)
- `num_ctx=16384` — context window large enough for 10K char resume + prompt

### Stage 3: Career Expander
**File:** `app/ingestion/career_expander.py`
**Time:** ~1-2 minutes
**Model:** gemma4:e4b

Takes the same raw text and produces an ENRICHED version:
- Expands bullet points into fuller narratives
- Creates STAR stories from achievements
- Categorizes skills more granularly
- Identifies key projects from experience descriptions

This is used for the "projects" you see on the Resume page and for generating tailored materials later.

### Stage 4: Database Storage
**File:** `app/services/profile_service.py`

Combines outputs from Stage 2 (AI Parser) and Stage 3 (Career Expander):
- Contact info, summary, certifications, interests → from AI Parser (Stage 2)
- Projects with STAR stories → from Career Expander (Stage 3)
- Skills → from AI Parser (prefers its categorization)
- Original file binary → stored for download

### Stage 5: RAG Ingestion
**File:** `app/rag/career_rag.py`

Converts the profile data into vector embeddings stored in ChromaDB. These are used later when matching against job descriptions — the system retrieves relevant chunks of your career profile that are most similar to a job's requirements.

---

## Why AI Parsing Instead of Regex?

| Aspect | Old Regex Parser | New AI Parser |
|--------|-----------------|---------------|
| Multi-column PDFs | ❌ Fails (text interleaved) | ✅ Understands context |
| "NTT Data" company | ❌ Might match "data" keyword | ✅ Knows it's a company |
| Section detection | ❌ Needs exact headers | ✅ Infers from context |
| Different resume formats | ❌ Breaks on non-standard | ✅ Adapts to any format |
| Speed | Fast (< 1 second) | Slow (2-3 minutes) |
| Accuracy | ~60% for complex resumes | ~95% |

---

## Configuration

In `.env`:
```
OLLAMA_MODEL=gemma4:e4b     # The model used for all AI tasks
OLLAMA_BASE_URL=http://localhost:11434
```

The AI parser uses these Ollama settings (in `ai_resume_parser.py`):
```python
num_predict=8192   # Max response tokens (for full JSON output)
num_ctx=16384      # Context window (input + output together)
temperature=0.1    # Low creativity, high accuracy
```

---

## What Gets Stored Where

| Data | Source | DB Table/Column |
|------|--------|-----------------|
| Name, email, phone, location, linkedin | AI Parser | career_profiles |
| Professional summary | AI Parser | career_profiles.summary |
| Original file (PDF/DOCX binary) | Direct upload | career_profiles.original_file_data |
| Extracted raw text | pypdf/docx2txt | career_profiles.raw_resume_text |
| Skills (categorized) | AI Parser | skills table |
| Certifications | AI Parser | certifications table |
| Interests | AI Parser | career_profiles.interests (JSON) |
| Education | AI Parser | career_profiles.education (JSON) |
| Projects (with STAR) | Career Expander | projects table |
| Formatted HTML resume | Template rendering | career_profiles.formatted_resume_html |

---

## Known Limitations

1. **Speed:** Upload takes 3-5 minutes total (AI processing). The UI shows "Processing with AI..." during this time.
2. **Model dependency:** Requires Ollama running with gemma4:e4b loaded. First call may be slower as model loads into RAM.
3. **Very long resumes:** Resumes over 8000 characters are truncated before sending to AI (last 2000+ chars may be lost).
4. **PDF extraction quality:** For heavily formatted PDFs with tables/graphics, pypdf may not extract text perfectly. The AI then works with imperfect input.

---

## If You Want to Change Anything

- **Switch models:** Change `OLLAMA_MODEL` in `.env` (e.g., `llama3.1:70b` for better quality but slower)
- **Faster but less accurate:** Reduce `num_predict` or switch to a smaller model
- **Better extraction for complex PDFs:** Could add OCR (Tesseract) or use a PDF-to-text service
- **Skip AI parsing:** If you want instant upload with manual section editing, the Career Expander alone provides projects/skills
