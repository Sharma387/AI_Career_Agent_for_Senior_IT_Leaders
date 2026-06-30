# RAG Implementation Guide

## AI Career Agent for Senior IT Leaders

This document explains how Retrieval-Augmented Generation (RAG) is implemented across the system, covering architecture, data flow, embedding strategy, and how retrieved context feeds into LLM-powered agents.

---

## 1. High-Level RAG Architecture

The system uses **three independent RAG knowledge bases**, each stored as a separate ChromaDB collection with its own embedding space:

```
                         ┌─────────────────────────┐
                         │   User Query / Context   │
                         └────────────┬────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                  │
                    ▼                 ▼                  ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
            │  Career RAG  │  │   Job RAG    │  │  Application RAG │
            │  (GRANULAR)  │  │  (DYNAMIC)   │  │  (ANALYTICS)     │
            └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
                   │                 │                    │
                   ▼                 ▼                    ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
            │  ChromaDB    │  │  ChromaDB    │  │  ChromaDB        │
            │  /career     │  │  /jobs       │  │  /applications   │
            └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
                   │                 │                    │
                   └─────────────────┼────────────────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │   LLM Agent Layer   │
                          │  (Ollama / OpenAI / │
                          │   Anthropic)        │
                          └─────────────────────┘
```

Each RAG module is independent — no cross-contamination between knowledge bases. The agents receive **retrieved chunks from multiple RAGs** as context and generate responses grounded in those chunks.

---

## 2. The Three RAG Knowledge Bases

### 2.1 Career RAG (Granular Knowledge Base)

**Purpose:** Stores everything about the user's professional history — resume, projects, skills, certifications — with per-section granularity for precise retrieval.

**File:** `app/rag/career_rag.py`

**Granular Ingestion (v2):**

The career RAG now uses granular ingestion via `ingest_granular()` instead of a single monolithic document:

| Data Type | Source | Ingestion Method | Metadata Tag |
|-----------|--------|------------------|--------------|
| Each work experience entry | AI Parser v1.0 | Individual document per role | `type: "experience"` |
| Each project | Career Expander / fallback | Individual document per project | `type: "project"` |
| Skills summary | AI Parser | Combined skills document | `type: "skills"` |
| Certifications | AI Parser | Combined certs document | `type: "certification"` |
| Resume overview | Raw text (chunked) | Split into 500-char chunks | `type: "resume"` |

**Ingestion flow:**

```
Resume Upload
        │
        ▼
┌──────────────────┐
│ AI Resume Parser │  Chunked extraction → v1.0 schema
│ (Stage 2)        │  
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Career Expander  │  Expands into STAR stories, detailed projects
│ (Stage 4)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  CareerRAG       │  Granular ingestion: one document per
│ .ingest_granular │  experience, project, skill group, cert
└──────────────────┘
```

**Why granular:** When matching against a job that requires "Kubernetes experience", the retriever can pull back just the specific experience entry mentioning Kubernetes — not a 5000-char resume chunk that might bury the relevant detail.

---

### 2.2 Job RAG (Dynamic Knowledge Base)

**Purpose:** Stores job descriptions for matching and retrieval.

**File:** `app/rag/job_rag.py`

**What gets ingested:**

| Data Type | Source | Ingestion Method |
|-----------|--------|------------------|
| Full job descriptions | Manual paste ("My Jobs") | Split into 500-char chunks |
| Adzuna snippets | API search ("Discover") | NOT ingested (snippets only) |
| LinkedIn captures | Browser extension | Full JD ingested |

**Note:** Adzuna returns only snippets (~200 chars). For full matching, users must paste the complete JD into "My Jobs" manually.

---

### 2.3 Application RAG (Analytics Knowledge Base)

**Purpose:** Stores the user's application history for pattern analysis and insights.

**File:** `app/rag/application_rag.py`

**What gets ingested:**

| Data Type | Source | Ingestion Method |
|-----------|--------|------------------|
| Application records | Tracking service | Individual documents |
| Status updates | Manual or API | Appended as new documents |
| Feedback/rejection notes | Manual input | Included in document text |

Each status update creates a **new document** — accumulates complete history for pattern analysis.

---

## 3. Embedding Strategy

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)

**Why this model:**
- 384-dimensional embeddings — fast and efficient
- Good semantic understanding for English text
- Runs locally — no API calls needed
- 512 token input limit — sufficient for chunked documents

**Vector store:** ChromaDB (persistent, local)

**Configuration:**
```python
# app/core/config.py
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K_RETRIEVAL = 5
CHROMA_PERSIST_DIR = "app/data/embeddings"
```

**Storage layout:**
```
app/data/embeddings/
├── career/          # Career profile embeddings (granular)
├── jobs/            # Job description embeddings
└── applications/    # Application history embeddings
```

---

## 4. Retrieval Flow

### 4.1 Job Matching Pipeline

```
User clicks "Match" on a job
        │
        ▼
┌─────────────────────────────┐
│  JobService.match_job()     │
│                             │
│  1. Fetch job from DB       │
│  2. Fetch profile from DB   │
│  3. Get ALL career chunks   │ ◄── CareerRAG.get_all_chunks()
│  4. Ingest job into JobRAG  │ ◄── JobRAG.ingest_job()
│  5. Query JobRAG with       │ ◄── JobRAG.query(job_text)
│     job text (top 5)        │
│  6. Pass both to agent      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  JobMatcherAgent            │
│                             │
│  Prompt includes:           │
│  - All career chunks        │
│  - Top 5 job chunks         │
│  - Scoring criteria:        │
│    • Skills (30%)           │
│    • Experience (25%)       │
│    • Industry (20%)         │
│    • Leadership (25%)       │
│                             │
│  Returns: score, strengths, │
│  gaps, evidence,            │
│  recommendation             │
└─────────────────────────────┘
```

### 4.2 Why `get_all_chunks()` for Career RAG

The career RAG uses `get_all_chunks()` (returns everything) instead of `query()` (semantic search) for matching because:

1. **Complete picture:** A senior IT leader's profile is typically <100 chunks — small enough for full context
2. **No query bias:** Semantic search might miss relevant experience that doesn't match keywords
3. **LLM does the filtering:** The LLM is better at determining relevance for nuanced career matching

For **job RAG**, `query()` is used because job descriptions are larger and we want the most relevant sections.

---

## 5. How Agents Use Retrieved Context

### 5.1 JobMatcherAgent

**Anti-hallucination rules:**
- Only reference what appears in retrieved chunks
- Each strength/gap must cite specific evidence from chunks
- Missing information is reported as a gap, not fabricated
- Scores clamped to 0-100 by code (not trusted from LLM)

### 5.2 ResumeAgent (Materials Generation)

Takes career chunks + job chunks and generates:
- Tailored resume (only from actual career data)
- Cover letter (aligned to job requirements)
- Uses Robert Half NZ template format

### 5.3 InsightAgent (Application Analytics)

Takes application history chunks and identifies:
- Rejection patterns (at which stage, for what reasons)
- Success patterns (what types of roles convert)
- Improvement suggestions based on data

---

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **3 separate ChromaDB collections** | Prevents cross-contamination; each KB has different update patterns |
| **Granular career ingestion** | Per-section embeddings enable precise retrieval for specific skills/experience |
| **500-char chunk size** | Balance between context richness and retrieval precision |
| **50-char overlap** | Prevents losing sentence context at chunk boundaries |
| **`get_all_chunks()` for career** | User profile is small; full context gives LLM better matching |
| **`all-MiniLM-L6-v2` embeddings** | Fast, local, no API dependency, good semantic quality |
| **New document per status update** | Accumulates history for pattern analysis over time |
| **Lazy LLM initialization** | Avoids crashes at import time when providers aren't configured |

---

## 7. Anti-Hallucination Safeguards

1. **Prompt-level:** Every agent prompt includes "ONLY reference retrieved chunks"
2. **Evidence tracking:** Match results include `evidence` field citing specific chunks
3. **Gap identification:** Missing info is reported as a gap, not fabricated
4. **Score clamping:** LLM output scores are clamped to 0-100 by code logic
5. **Recommendation override:** Final recommendation determined by code, not LLM

---

## 8. Performance Notes

| Operation | Time | Notes |
|-----------|------|-------|
| Embedding generation | ~100ms per chunk | Local sentence-transformers |
| Career RAG full retrieval | ~50ms | Returns all chunks (typically <100) |
| Job RAG semantic query | ~100ms | Top-5 similarity search |
| ChromaDB persistence | Automatic | Writes to disk on each ingest |
| First load (cold start) | ~3s | sentence-transformers model load |

---

## 9. Future Enhancements (Designed, Not Implemented)

| Enhancement | Description |
|-------------|-------------|
| **Hybrid search** | Combine semantic + BM25 keyword search |
| **Re-ranking** | Cross-encoder re-ranking of retrieved chunks |
| **Incremental ingestion** | Only re-embed changed sections on profile update |
| **Query expansion** | LLM-expanded queries before retrieval |
| **Multi-modal RAG** | Ingest PDF layouts, company reports |
