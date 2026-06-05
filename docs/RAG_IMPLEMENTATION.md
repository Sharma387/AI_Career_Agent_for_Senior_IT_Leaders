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
            │  (STATIC)    │  │  (DYNAMIC)   │  │  (ANALYTICS)     │
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
                          │  (Nvidia NIM /      │
                          │   Ollama)           │
                          └─────────────────────┘
```

Each RAG module is independent — no cross-contamination between knowledge bases. The agents receive **retrieved chunks from multiple RAGs** as context and generate responses grounded in those chunks.

---

## 2. The Three RAG Knowledge Bases

### 2.1 Career RAG (Static Knowledge Base)

**Purpose:** Stores everything about the user's professional history — resume, projects, skills, certifications.

**File:** `app/rag/career_rag.py`

**What gets ingested:**

| Data Type | Source | Ingestion Method | Metadata Tag |
|-----------|--------|------------------|--------------|
| Resume text | Uploaded file (PDF/DOCX/TXT) | Split into 500-char chunks | `type: "resume"` |
| Project narratives | Career Expander (LLM) or manual form | Split into 500-char chunks | `type: "project"` |
| Individual skills | Extracted from resume | Single document per skill | `type: "skill"` |
| Certifications | Extracted from resume | Single document per cert | `type: "cert"` |

**Ingestion flow:**

```
Resume File (PDF/DOCX/TXT)
        │
        ▼
┌──────────────────┐
│  ResumeParser    │  Extracts raw text + structured sections
│  .parse()        │  (contact, summary, experience, skills, certs)
│  .extract_sections()
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  CareerExpander  │  LLM-powered expansion of resume bullets
│  .expand_profile │  into detailed project narratives, STAR stories,
│                  │  and categorized skills
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  CareerRAG       │  Chunks and embeds all data into ChromaDB
│  .ingest_profile │  with type metadata for filtering
└──────────────────┘
```

**Chunking strategy:**
- **Text splitter:** `RecursiveCharacterTextSplitter`
- **Chunk size:** 500 characters
- **Chunk overlap:** 50 characters (preserves context across boundaries)
- **Why these values:** 500 chars is large enough for meaningful context but small enough for precise retrieval. 50-char overlap prevents losing sentence context at split points.

**Example of what gets stored:**

```
Chunk 1 (type: "resume"):
"Sharma Rajasekar\n\nProject Manager\n\nHighly Skilled Customer 
Focused Project Manager with 20+ years of experience in delivering 
strategic projects in the Healthcare, Airline, and Retail sectors..."

Chunk 2 (type: "project"):
"Project: SAP Implementation\nRole: Delivery Lead\nDescription: 
Led end-to-end delivery of SAP S/4HANA migration for 3 business 
units...\nTechnologies: SAP, ABAP, Fiori, Azure DevOps..."

Chunk 3 (type: "skill"):
"Skill: Kubernetes\nCategory: technical\nLevel: expert\nYears: 8"

Chunk 4 (type: "cert"):
"Certification: AWS Solutions Architect Professional\nIssuer: AWS\n
Date: 2022-01-01\nExpiry: 2025-01-01"
```

---

### 2.2 Job RAG (Dynamic Knowledge Base)

**Purpose:** Stores job descriptions the user is interested in, extracted and chunked for matching.

**File:** `app/rag/job_rag.py`

**What gets ingested:**

| Data Type | Source | Ingestion Method |
|-----------|--------|------------------|
| Job descriptions | Manual paste or future email parsing | Split into 500-char chunks |

**Ingestion flow:**

```
Job Description Text
        │
        ▼
┌──────────────────┐
│  JobParser       │  Extracts: title, company, seniority,
│  .parse_job_     │  requirements, skills, salary range
│  description()   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  JobRAG          │  Combines parsed fields into structured text,
│  .ingest_job()   │  chunks, embeds with job metadata
└──────────────────┘
```

**What gets stored per job:**

```
Chunk (type: "job", job_id: 1, company: "FinServe Global", 
       title: "Senior Director of Platform Engineering"):
"Job ID: 1\nTitle: Senior Director of Platform Engineering\n
Company: FinServe Global\nSeniority Level: senior\n
Description: We are looking for a leader to head our platform 
engineering organization...\nRequirements: 10+ years experience, 
team leadership, cloud architecture...\nSkills: Kubernetes, AWS, 
microservices, CI/CD"
```

**Metadata includes:** `job_id`, `company`, `title` — enables filtering and attribution during retrieval.

---

### 2.3 Application RAG (Analytics Knowledge Base)

**Purpose:** Stores the user's application history for pattern analysis and insights.

**File:** `app/rag/application_rag.py`

**What gets ingested:**

| Data Type | Source | Ingestion Method |
|-----------|--------|------------------|
| Application records | Tracking service | Split into 500-char chunks |
| Status updates | Manual or API | Appended as new documents |
| Feedback/rejection notes | Manual input | Included in document text |

**Ingestion flow:**

```
Application Event (track/update)
        │
        ▼
┌──────────────────┐
│  ApplicationRAG  │  Creates a document with job title, company,
│  .ingest_        │  status, date, rejection stage, and feedback
│  application()   │  Chunks and embeds with status metadata
└──────────────────┘
```

**What gets stored:**

```
Chunk (type: "application", company: "FinServe Global", 
       status: "rejected", job_title: "Senior Director"):
"Job Title: Senior Director of Platform Engineering\n
Company: FinServe Global\nStatus: rejected\n
Date Applied: 2026-05-15\nRejection Stage: technical_interview\n
Feedback: Strong technical skills but lacked fintech domain 
experience in regulatory compliance."
```

**Key design decision:** Each status update creates a **new document** in the collection. This means the RAG store accumulates a complete history of every application lifecycle event, enabling the Insight Agent to analyze patterns over time.

---

## 3. Embedding Strategy

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)

**Why this model:**
- 384-dimensional embeddings — fast and efficient
- Good semantic understanding for English text
- Runs locally via sentence-transformers — no API calls needed
- 512 token input limit — sufficient for 500-char chunks

**Vector store:** ChromaDB (persistent, local)

**Configuration:**
```python
# app/core/config.py
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # HuggingFace model
TOP_K_RETRIEVAL = 5                    # Return top 5 matches
CHROMA_PERSIST_DIR = "data/embeddings" # Storage location
```

**Separate collections per knowledge base:**
```
data/embeddings/
├── career/          # Career profile embeddings
├── jobs/            # Job description embeddings
└── applications/    # Application history embeddings
```

---

## 4. Retrieval Flow

### 4.1 Query Execution

When a query is made against any RAG module:

```python
# Example: CareerRAG.query()
def query(self, query_text: str, k: int = 5):
    return self.client.similarity_search_with_relevance_scores(
        query_text, k=k
    )
```

This returns a list of `(Document, score)` tuples, where:
- `Document.page_content` = the chunk text
- `Document.metadata` = type, job_id, company, etc.
- `score` = relevance score (0-1, higher = more relevant)

### 4.2 Full Retrieval Pipeline (Job Matching Example)

```
User clicks "Match Job"
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
│     job text                │     Returns top 5 job chunks
│  6. Pass both chunk sets    │
│     to JobMatcherAgent      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  JobMatcherAgent.match_job()│
│                             │
│  1. Join career chunks      │
│     into single context     │
│  2. Join job chunks         │
│     into single context     │
│  3. Build prompt with both  │
│     contexts + scoring      │
│     criteria                │
│  4. Call LLM                │
│  5. Parse JSON response     │
│  6. Clamp scores, assign    │
│     recommendation          │
└─────────────────────────────┘
```

### 4.3 Why `get_all_chunks()` for Career RAG

The career RAG uses `get_all_chunks()` (returns everything) instead of `query()` (semantic search) for matching because:

1. **Complete picture:** The user's career is small enough (typically <100 chunks) that retrieving everything gives the LLM full context
2. **No query bias:** A semantic query might miss relevant experience that doesn't match keywords
3. **LLM does the filtering:** The LLM is better at determining relevance than vector similarity for nuanced career matching

For **job RAG**, `query()` is used because job descriptions are larger and we want the most relevant sections.

---

## 5. How Agents Use Retrieved Context

### 5.1 JobMatcherAgent

**Input:** `career_chunks` (list), `job_chunks` (list), `job_data` (dict)

**Process:**
```python
# Join all career chunks into one context block
career_context = "\n\n".join(
    [chunk.get("content", str(chunk)) for chunk in career_chunks]
)

# Join all job chunks into one context block  
job_context = "\n\n".join(
    [chunk.get("content", str(chunk)) for chunk in job_chunks]
)

# Build prompt with both contexts
prompt = f"""
CANDIDATE CAREER PROFILE (retrieved context):
---
{career_context}
---

JOB REQUIREMENTS (retrieved context):
---
{job_context}
---

SCORING CRITERIA:
1. Skills Match (30%)
2. Experience Level Match (25%)
3. Industry Relevance (20%)
4. Leadership Signals (25%)

CRITICAL RULES:
- NEVER fabricate experience not in the chunks
- Only reference what appears in retrieved chunks
"""
```

**Output:** JSON with `match_score`, `strengths`, `gaps`, `evidence`, `explanation`, `recommendation`

**Anti-hallucination rule:** The prompt explicitly instructs the LLM to ONLY reference what appears in the retrieved chunks. If information is missing, it's noted as a gap.

### 5.2 ResumeAgent

**Input:** Same as JobMatcherAgent

**Process:** Retrieves career chunks and job chunks, builds a prompt asking the LLM to generate a tailored resume using only the provided career context, aligned with job requirements.

**Key constraint:** Generated resume must only contain experience found in the retrieved career chunks.

### 5.3 InsightAgent

**Input:** `application_chunks` (from ApplicationRAG), `career_chunks` (from CareerRAG)

**Process:** Analyzes application history patterns (rejection rates, success patterns, stage-specific failures) using the retrieved application history context.

**Output:** Rejection patterns, success patterns, improvement suggestions, interview conversion rate.

---

## 6. Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USER ACTIONS                                  │
├──────────────────────────────────────────────────────────────────────┤
│  Upload Resume  │  Add Job  │  Track Application  │  Match/Generate  │
└────────┬────────┴─────┬─────┴─────────┬───────────┴────────┬────────┘
         │              │               │                    │
         ▼              ▼               ▼                    ▼
┌────────────────┐ ┌──────────┐ ┌──────────────┐ ┌────────────────────┐
│ ResumeParser   │ │ JobParser│ │ DB INSERT    │ │ CareerRAG          │
│ CareerExpander │ │          │ │              │ │ .get_all_chunks()  │
└───────┬────────┘ └────┬─────┘ └──────────────┘ │                    │
        │               │                        │ JobRAG             │
        ▼               ▼                        │ .query(job_text)   │
┌────────────────┐ ┌──────────┐                   │                    │
│ CareerRAG      │ │ JobRAG   │                   └─────────┬──────────┘
│ .ingest_       │ │ .ingest_ │                             │
│  profile()     │ │  job()   │                             ▼
└────────────────┘ └──────────┘                   ┌────────────────────┐
                                                  │ Agent Layer        │
┌────────────────────────────────────────┐        │ (LLM with retrieved│
│ ApplicationRAG                         │        │  context as input) │
│ .ingest_application()                  │        └─────────┬──────────┘
│ .get_analytics_chunks()                │                  │
└────────────────────────────────────────┘                  ▼
                                                  ┌────────────────────┐
                                                  │ Structured Output  │
                                                  │ (JSON with scores, │
                                                  │  strengths, gaps,  │
                                                  │  evidence)         │
                                                  └────────────────────┘
```

---

## 7. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **3 separate ChromaDB collections** | Prevents cross-contamination; each KB has different update patterns and query semantics |
| **500-char chunk size** | Balance between context richness and retrieval precision |
| **50-char overlap** | Prevents losing sentence context at chunk boundaries |
| **`get_all_chunks()` for career** | User profile is small; full context gives LLM better matching capability |
| **Semantic query for jobs** | Job descriptions are larger; need most relevant sections |
| **`all-MiniLM-L6-v2` embeddings** | Fast, local, good semantic understanding, no API dependency |
| **Metadata tagging per chunk** | Enables filtering (e.g., only project chunks, only rejected applications) |
| **New document per status update** | Accumulates history for pattern analysis over time |
| **Lazy LLM initialization** | Avoids crashes at import time when API keys aren't configured |

---

## 8. Anti-Hallucination Safeguards

1. **Prompt-level:** Every agent prompt includes explicit instructions to ONLY reference retrieved chunks
2. **Evidence tracking:** JobMatcherAgent returns `evidence` field citing which chunks support each claim
3. **Gap identification:** Missing information is reported as a gap, not fabricated
4. **Score clamping:** LLM output scores are clamped to 0-100 to prevent hallucinated extreme values
5. **Recommendation override:** Final recommendation is determined by code logic, not LLM output

---

## 9. Future Enhancements (Designed, Not Implemented)

| Enhancement | Description |
|-------------|-------------|
| **Hybrid search** | Combine semantic search with BM25 keyword search for better retrieval |
| **Re-ranking** | Use a cross-encoder model to re-rank retrieved chunks by relevance |
| **Chunk summarization** | Pre-summarize long chunks before ingestion for better retrieval |
| **Incremental ingestion** | Only re-embed changed sections when profile is updated |
| **Query expansion** | Use LLM to expand user queries before retrieval |
| **Multi-modal RAG** | Ingest PDF layouts, LinkedIn profiles, company reports |
