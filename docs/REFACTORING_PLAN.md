# Resume Parsing Architecture Refactoring Plan

## Executive Summary

Refactoring the resume parsing pipeline from a slow, monolithic AI-first approach to a fast, validated, multi-stage architecture with confidence scoring, chunking, OCR fallback, and granular RAG embeddings.

**Target:** Parse time from ~3 minutes → <30 seconds for most resumes.

---

## Updated Architecture Diagram

```
User uploads resume.pdf/docx/txt
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 1: Text Extraction + OCR Fallback             │  (~1-5s)
│  app/ingestion/resume_parser.py                      │
│  app/ingestion/ocr_extractor.py (NEW)                │
│                                                      │
│  1. Extract text via pypdf/docx2txt                  │
│  2. IF text < 300 chars → run OCR (Tesseract)        │
│  3. Return: raw_text (full, no truncation)           │
└────────────────────┬─────────────────────────────────┘
                     │ raw_text (any length)
                     ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 2: Chunked AI Parser                          │  (~15-25s)
│  app/ingestion/ai_resume_parser.py (REFACTORED)      │
│                                                      │
│  1. Split resume into logical chunks (~3000 chars)   │
│  2. Parse each chunk in parallel or sequence         │
│  3. Merge results (dedup experience, skills, etc.)   │
│  4. Add confidence scores to each field              │
│  5. Return: ParsedResume (with confidence)           │
│                                                      │
│  Settings: temperature=0, num_predict=3000,          │
│            num_ctx=8192                              │
└────────────────────┬─────────────────────────────────┘
                     │ ParsedResume (with confidence scores)
                     ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 3: Validation Layer (NEW)                     │  (~10ms)
│  app/ingestion/profile_validator.py                   │
│                                                      │
│  Validates: email, phone, LinkedIn URL format,       │
│  date consistency, duplicate skills, empty fields    │
│  Returns: { is_valid, warnings[], errors[] }         │
└────────────────────┬─────────────────────────────────┘
                     │ Validated ParsedResume
                     ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 4: Career Expander (REFACTORED)               │  (~10-15s)
│  app/ingestion/career_expander.py                    │
│                                                      │
│  INPUT: Structured ParsedResume (NOT raw text)       │
│  OUTPUT: Projects with STAR, achievements            │
│  Benefits: fewer tokens, faster, less hallucination  │
└────────────────────┬─────────────────────────────────┘
                     │ ExpandedProfile
                     ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 5: Database Storage + Audit                   │
│  app/services/profile_service.py                     │
│                                                      │
│  1. Map confidence-scored fields to DB columns       │
│  2. Store parse audit record (NEW table)             │
│  3. Store profile, skills, certs, projects           │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  STAGE 6: Granular RAG Ingestion (REFACTORED)        │
│  app/rag/career_rag.py                               │
│                                                      │
│  Separate embeddings for:                            │
│  - Each experience entry                            │
│  - Each project                                     │
│  - Each achievement                                 │
│  - Skills summary                                   │
│  - Certifications                                   │
│  Each with metadata: candidate_id, section, title    │
└──────────────────────────────────────────────────────┘
```

---

## Implementation Order

| # | Task | File(s) | Est. Time |
|---|------|---------|-----------|
| 1 | Parse Audit Table (DB model) | `app/db/models.py` | 10 min |
| 2 | Profile Validator | `app/ingestion/profile_validator.py` | 20 min |
| 3 | OCR Fallback | `app/ingestion/ocr_extractor.py` | 15 min |
| 4 | Chunked AI Parser (refactor) | `app/ingestion/ai_resume_parser.py` | 30 min |
| 5 | Confidence Scoring | Parser prompt + output schema | 15 min |
| 6 | Career Expander (refactor) | `app/ingestion/career_expander.py` | 20 min |
| 7 | Granular RAG | `app/rag/career_rag.py` | 20 min |
| 8 | Profile Service Integration | `app/services/profile_service.py` | 20 min |
| 9 | Testing & Verification | Tests + manual | 15 min |

---

## Detailed Specifications

### 1. Parse Audit Table

```python
class ResumeParseRun(Base):
    __tablename__ = "resume_parse_runs"
    
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"))
    model_name = Column(String(100))  # e.g., "gemma4:e4b"
    prompt_version = Column(String(50))  # e.g., "v2_chunked"
    processing_time_seconds = Column(Float)
    parse_status = Column(String(50))  # "success", "partial", "failed"
    validation_status = Column(String(50))  # "valid", "warnings", "errors"
    validation_details = Column(JSON)  # full validation output
    confidence_scores = Column(JSON)  # field-level confidence
    chunks_processed = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 2. Validation Layer Output

```json
{
  "is_valid": true,
  "warnings": [
    {"field": "phone", "message": "Non-standard format, parsed as +64-224510637"}
  ],
  "errors": [],
  "field_status": {
    "email": "valid",
    "phone": "valid_with_warning",
    "linkedin": "valid",
    "name": "valid",
    "experience": "valid",
    "certifications": "valid"
  }
}
```

### 3. Confidence Score Schema

```json
{
  "full_name": {"value": "Sharma Rajasekar", "confidence": 0.99},
  "email": {"value": "sharma.rajasekar@gmail.com", "confidence": 0.99},
  "phone": {"value": "+64-224510637", "confidence": 0.95},
  "location": {"value": "Auckland, New Zealand", "confidence": 0.90},
  "linkedin": {"value": "linkedin.com/in/sharma-rajasekar", "confidence": 0.85},
  "summary": {"value": "Highly skilled PM...", "confidence": 0.92},
  "certifications": [
    {"value": "Prince2 Practitioner", "confidence": 0.98},
    {"value": "Scrum Master", "confidence": 0.97}
  ],
  "experience": [
    {
      "title": {"value": "Senior PM", "confidence": 0.95},
      "company": {"value": "Air NZ", "confidence": 0.98},
      "dates": {"value": "2019-Present", "confidence": 0.90},
      "confidence_overall": 0.94
    }
  ]
}
```

### 4. Chunking Strategy

```python
def chunk_resume(raw_text: str, max_chunk_size: int = 3000) -> list[str]:
    """
    Split resume into logical chunks for parallel processing.
    
    Strategy:
    1. Split by double newlines (paragraph boundaries)
    2. Group paragraphs until chunk_size reached
    3. Never split mid-paragraph
    4. Each chunk gets full context header (name + current section)
    """
```

### 5. Optimized Parser Prompt

Key changes for speed:
- Shorter system prompt (fewer instructions = faster)
- `temperature=0` (deterministic, no sampling overhead)
- `num_predict=3000` (enough for one chunk's JSON)
- `num_ctx=8192` (fits 3000 char chunk + prompt + response)
- Request ONLY the fields present in this chunk

### 6. Career Expander New Input

```python
# OLD (slow, re-parses everything):
expanded = self.expander.expand_profile(raw_text)

# NEW (fast, uses pre-parsed data):
expanded = self.expander.expand_from_parsed(parsed_resume)
```

### 7. Granular RAG Chunks

```python
# Instead of one big document:
career_rag.ingest_profile(profile_data)  # OLD

# New: separate embeddings per item
career_rag.ingest_experience(profile_id, experience_entry)
career_rag.ingest_project(profile_id, project)
career_rag.ingest_skills(profile_id, skills_summary)
career_rag.ingest_certifications(profile_id, certs)
```

---

## Performance Comparison

| Metric | Before | After (Target) |
|--------|--------|----------------|
| Total parse time | 3-5 min | 20-30s |
| AI calls | 2 (parser + expander) | 2-3 (chunks + expander) |
| Tokens per call | ~12K input | ~4K input |
| Response quality | Truncated for long resumes | Complete, no data loss |
| Validation | None | Full field validation |
| Confidence | None | Per-field scoring |
| OCR support | No | Yes (fallback) |
| RAG granularity | 1 doc per profile | N chunks per profile |

---

## Migration Strategy

1. Add new `resume_parse_runs` table (additive, no breaking change)
2. New columns added via `create_all()` (SQLite handles this on fresh DB)
3. Existing profiles continue working (old data remains valid)
4. New uploads go through the new pipeline
5. API response format unchanged (confidence scores stored internally, not exposed unless requested)

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Chunked parsing produces duplicates | Dedup merge step with title+company matching |
| OCR adds Tesseract dependency | Make it optional, graceful fallback |
| Confidence scores add complexity | Store as JSON, expose only when useful |
| Speed regression from more stages | Parallel chunk processing, optimized prompts |
| Model changes break parsing | Prompt version tracked in audit table |
