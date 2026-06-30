# Resume Parsing Architecture Refactoring Plan

## Status: ✅ COMPLETED

All tasks from this refactoring plan have been implemented.

---

## Executive Summary

Refactored the resume parsing pipeline from a slow, monolithic regex-based approach to a fast, validated, multi-stage AI architecture with chunking, robust JSON extraction, OCR fallback, multi-model support, and granular RAG embeddings.

**Result:** Parse time reduced from ~5 minutes → 30-90 seconds (local) or 5-10 seconds (cloud).

---

## Implementation Status

| # | Task | File(s) | Status |
|---|------|---------|--------|
| 1 | Parse Audit Table (DB model) | `app/db/models.py` | ✅ Done |
| 2 | Profile Validator | `app/ingestion/profile_validator.py` | ✅ Done |
| 3 | OCR Fallback | `app/ingestion/ocr_extractor.py` | ✅ Done |
| 4 | Chunked AI Parser | `app/ingestion/ai_resume_parser.py` | ✅ Done |
| 5 | Multi-Model Support | Parser + API route + Frontend dropdown | ✅ Done |
| 6 | Robust JSON Extraction | `app/agents/json_parser.py` | ✅ Done |
| 7 | Career Expander (refactor) | `app/ingestion/career_expander.py` | ✅ Done |
| 8 | Granular RAG | `app/rag/career_rag.py` | ✅ Done |
| 9 | Profile Service Integration | `app/services/profile_service.py` | ✅ Done |
| 10 | v1.0 Schema + DB Columns | `app/db/models.py` | ✅ Done |
| 11 | Frontend Model Selector | `frontend-react/src/pages/Resume.tsx` | ✅ Done |
| 12 | Testing & Verification | 86 tests passing | ✅ Done |

---

## Key Design Decisions Made During Implementation

### JSON Extraction (Critical Fix)
Local models (gemma4, qwen3.5) frequently wrap JSON in markdown blocks and/or produce truncated output. The `json_parser.py` now handles:
- `<think>...</think>` blocks (qwen3.5 reasoning mode)
- ` ```json ... ``` ` wrappers (with or without closing ```)
- Truncated JSON repair (tracks string boundaries, progressively trims)
- Brace-matching fallback

### Model Parameters
```python
temperature=0       # Deterministic extraction (no creativity)
num_predict=16000   # Generous limit to avoid truncation
num_ctx=32768       # Fits 4000-char chunk + prompt + full response
```

### Chunking Strategy
- 4000 chars per chunk (paragraph boundaries)
- Never splits mid-paragraph
- Typical 10K-char resume → 3 chunks
- Dedup on merge: role+company for experience, name.lower() for skills/certs

### Projects Fallback
If the Career Expander produces no projects (common when parsed data is minimal), the system creates project entries from work_experience entries. This preserves the original CV structure.

### Prompt Design
```
"Output ONLY raw JSON — no markdown, no code blocks, no explanation."
"Do NOT wrap in ```json blocks"
"/no_think"  (suppresses reasoning in qwen3.5)
```

---

## Performance Comparison (Achieved)

| Metric | Before | After |
|--------|--------|-------|
| Total parse time (local) | 3-5 min | 30-90s |
| Total parse time (cloud) | N/A | 5-10s |
| AI calls per resume | 2 (parser + expander) | 3-4 (chunks + expander) |
| Tokens per call | ~12K input | ~4K input |
| Response quality | Truncated for long resumes | Complete, no data loss |
| Truncation handling | ❌ Failed | ✅ Auto-repair |
| Validation | None | Full field validation |
| Model selection | Hardcoded | User-selectable per upload |
| OCR support | No | Yes (Tesseract fallback) |
| RAG granularity | 1 doc per profile | Per-section embeddings |
| Schema | Flat dict | v1.0 structured JSON |
| Resume template | Basic | Robert Half NZ format |

---

## Files Modified/Created

### New Files
- `app/ingestion/ai_resume_parser.py` — Chunked AI parser
- `app/ingestion/ocr_extractor.py` — OCR fallback
- `app/ingestion/profile_validator.py` — Validation layer
- `app/agents/json_parser.py` — Robust JSON extraction

### Modified Files
- `app/db/models.py` — v1.0 schema columns, ResumeParseRun table
- `app/services/profile_service.py` — Full pipeline integration
- `app/rag/career_rag.py` — Granular ingestion
- `app/ingestion/career_expander.py` — Takes parsed data (not raw text)
- `app/api/routes.py` — Model selection endpoint, upload with model param
- `app/core/config.py` — OLLAMA_HQ_MODEL setting
- `frontend-react/src/pages/Resume.tsx` — Model dropdown, API key input
- `frontend-react/src/api/client.ts` — uploadResume with model/key params
