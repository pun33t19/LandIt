<div align="center">

# 🎯 LandIt

### AI-Powered Resume Tailoring Platform

*Stop sending the same resume to every job. Let AI tailor it for each one.*

</div>

***

## 📌 What is LandIt?

**LandIt** is a full-stack AI application that takes your resume and a job description, and produces a tailored version of your resume that is optimised for that specific role — complete with ATS score analysis, keyword injection, bullet rewriting, and cover letter generation.

Unlike pasting your resume into ChatGPT, LandIt provides:

- **Persistent sessions** — every tailored resume is saved and versioned
- **Human-in-the-loop (HITL) review** — you approve or reject every AI suggestion
- **Content-addressable caching** — same resume file never parsed twice
- **Structured diff view** — see exactly what changed, line by line
- **Job search + ranking** — find jobs ranked by how well they match your resume

***

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Resume Parsing** | Upload a PDF — extracts name, skills, experience, education into structured JSON |
| 🔍 **ATS Scoring** | Scores your resume against industry benchmarks (0–100) |
| 🤖 **AI Optimisation** | LangChain agent suggests improvements with HITL approval loop |
| 💼 **Job Search** | Searches live job listings ranked by resume match score |
| ✂️ **Resume Tailoring** | Rewrites bullets, reorders skills, injects keywords for a specific JD |
| 📝 **Cover Letter** | Generates a personalised cover letter matching the tailored resume |
| ⚡ **Smart Caching** | SHA-256 content-addressable cache — same file loads instantly |
| 🌗 **Dark / Light Mode** | Full dark mode support with system preference detection |

***

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 14)                 │
│                                                          │
│  Upload → Optimise → Job Search → Tailor → Review       │
│                                                          │
│  Zustand (state) + TanStack Query (server state)         │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / REST
┌──────────────────────▼──────────────────────────────────┐
│                   BACKEND (FastAPI)                      │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │ Resume API  │  │   Jobs API   │  │  Tailor API   │   │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘   │
│         │                │                   │           │
│  ┌──────▼──────────────────────────────────▼───────┐    │
│  │              LangChain Agent Graph               │    │
│  │                                                  │    │
│  │  Parser → Scorer → Optimiser → Tailor → Writer   │    │
│  └──────────────────────┬───────────────────────────┘    │
│                         │                                │
│                    ┌────▼────┐                           │
│                    │  LLM    │                           │
│                    │(OpenAI) │                           │
│                    └─────────┘                           │
└─────────────────────────────────────────────────────────┘
```

***

## 🔄 Application Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  PHASE 1 │     │  PHASE 2 │     │  PHASE 3 │     │  PHASE 4 │     │  PHASE 5 │
│          │     │          │     │          │     │          │     │          │
│  Upload  │────▶│ Optimise │────▶│  Search  │────▶│  Tailor  │────▶│  Review  │
│  Resume  │     │ & Review │     │   Jobs   │     │  Resume  │     │ & Export │
│          │     │          │     │          │     │          │     │          │
│ PDF→JSON │     │ HITL Loop│     │ Rank by  │     │ JD-aware │     │ Diff view│
│ ATS Score│     │ Approve/ │     │ match    │     │ rewrite  │     │ Download │
│          │     │ Reject   │     │ score    │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
```

***

## 🧠 LangChain Agent Flow

LandIt uses a **LangChain multi-agent graph** built with LangGraph. Each phase is a node in the graph with defined state transitions.

```
                         ┌─────────────────────────────────┐
                         │         AGENT GRAPH              │
                         └─────────────────────────────────┘

  ┌──────────────┐
  │ INPUT        │   PDF file bytes
  │ resume_bytes │──────────────────────────────────────────┐
  └──────────────┘                                          │
                                                            ▼
                                               ┌────────────────────┐
                                               │   PARSE NODE        │
                                               │                     │
                                               │  • Extract text     │
                                               │    from PDF         │
                                               │  • LLM structured   │
                                               │    extraction       │
                                               │  • Output:          │
                                               │    ResumeData JSON  │
                                               └─────────┬──────────┘
                                                         │
                                                         ▼
                                               ┌────────────────────┐
                                               │   SCORE NODE        │
                                               │                     │
                                               │  • ATS keyword      │
                                               │    analysis         │
                                               │  • Section scoring  │
                                               │  • Gap detection    │
                                               │  • Output:          │
                                               │    ats_score (0-100)│
                                               └─────────┬──────────┘
                                                         │
                              ┌──────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │        OPTIMISE NODE           │
              │                               │
              │  • Analyse all sections       │
              │  • Generate suggestions[]     │
              │  • Format: [context] issue    │
              │            → fix              │
              │  • Output: session_id         │
              │            status: awaiting   │
              └──────────────┬────────────────┘
                             │
                             ▼
              ┌───────────────────────────────┐
              │      HUMAN REVIEW (HITL)       │   ◀── User approves/rejects
              │                               │        in frontend
              │  action: "approve" | "reject" │
              │  edited_resume: {}            │
              └──────────────┬────────────────┘
                             │
                    ┌────────┴──────────┐
                    │                   │
              approve                reject
                    │                   │
                    ▼                   ▼
         ┌──────────────┐     ┌──────────────────┐
         │  JOB SEARCH  │     │ ORIGINAL RESUME  │
         │    NODE      │     │   (unchanged)    │
         │              │     └──────────────────┘
         │  • Search    │
         │    live JDs  │
         │  • Rank by   │
         │    match     │
         │  • Score     │
         │    each job  │
         └──────┬───────┘
                │
                ▼
         ┌──────────────────────────────┐
         │         TAILOR NODE           │
         │                              │
         │  Inputs:                     │
         │    resume: ResumeData        │
         │    job: JobData              │
         │    options: {                │
         │      mirror_keywords: true   │
         │      reorder_skills: true    │
         │      rewrite_bullets: true   │
         │      generate_cover_letter   │
         │    }                         │
         │                              │
         │  Steps:                      │
         │  1. Extract JD keywords      │
         │  2. Gap analysis vs resume   │
         │  3. Rewrite experience       │
         │     bullets with metrics     │
         │  4. Reorder skills by        │
         │     JD relevance             │
         │  5. Inject missing keywords  │
         │  6. Recalculate ATS score    │
         │  7. Generate cover letter    │
         │                              │
         │  Output: session_id          │
         │          diff {}             │
         │          jd_ats_score        │
         └─────────────┬────────────────┘
                       │
                       ▼
         ┌──────────────────────────────┐
         │      HUMAN REVIEW (HITL)      │   ◀── User reviews diff
         │                              │        in frontend
         │  action: "approve" | "reject"│
         └─────────────┬────────────────┘
                       │
                       ▼
         ┌──────────────────────────────┐
         │         OUTPUT NODE           │
         │                              │
         │  • Final tailored resume     │
         │  • Cover letter (optional)   │
         │  • PDF export                │
         └──────────────────────────────┘
```

***

## 🛠️ Tech Stack

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| **Next.js** | 14.2.3 | Framework — App Router, file-based routing |
| **React** | 18 | UI runtime |
| **TypeScript** | 5 | Type safety |
| **Tailwind CSS** | 3.4.3 | Utility-first styling |
| **Zustand** | 4.5.2 | Global state management |
| **TanStack Query** | 5.40.0 | Server state, caching, polling |
| **Framer Motion** | 11.2.10 | Animations and transitions |
| **Lucide React** | 0.379.0 | Icon library |

### Backend

| Technology | Version | Purpose |
|---|---|---|
| **FastAPI** | 0.110 | REST API framework |
| **Python** | 3.11 | Runtime |
| **LangChain** | 0.2 | LLM orchestration |
| **LangGraph** | 0.1 | Multi-agent graph execution |
| **OpenAI GPT-4o** | latest | LLM for all AI tasks |
| **Pydantic** | v2 | Request/response validation |
| **PyMuPDF** | 1.24 | PDF text extraction |
| **Uvicorn** | 0.29 | ASGI server |

***

## 📁 Project Structure

```
landit/
│
├── frontend/                          # Next.js application
│   ├── app/
│   │   ├── layout.tsx                 # Root layout, fonts, theme
│   │   ├── page.tsx                   # Dashboard
│   │   ├── resume/
│   │   │   └── upload/
│   │   │       └── page.tsx           # Phase 1: Upload + parse
│   │   │   └── [id]/
│   │   │       └── optimize/
│   │   │           └── page.tsx       # Phase 2: HITL optimise
│   │   ├── jobs/
│   │   │   └── search/
│   │   │       └── page.tsx           # Phase 3: Job search
│   │   └── tailor/
│   │       └── [sessionId]/
│   │           ├── review/
│   │           │   └── page.tsx       # Phase 4: Diff review
│   │           └── result/
│   │               └── page.tsx       # Final result + export
│   │
│   ├── components/
│   │   ├── ui/                        # Button, Card, Badge, Spinner
│   │   ├── ATSScoreGauge.tsx          # Circular ATS score display
│   │   ├── JobCard.tsx                # Job listing card
│   │   ├── ResumePreview.tsx          # Parsed resume display
│   │   └── DiffViewer.tsx             # Token-level diff renderer
│   │
│   └── lib/
│       ├── api.ts                     # All fetch calls (HTTP only)
│       ├── resumeCache.ts             # localStorage + SHA-256 hashing
│       ├── resumeUpload.ts            # Upload orchestration
│       └── store.ts                   # Zustand global store
│
└── backend/                           # FastAPI application
    ├── main.py                        # App entry point
    ├── api/
    │   └── routers/
    │       ├── resume.py              # /api/resume/*
    │       ├── jobs.py                # /api/jobs/*
    │       └── tailor.py              # /api/tailor/*
    │
    ├── agents/
    │   ├── graph.py                   # LangGraph agent graph
    │   ├── parse_node.py              # PDF → ResumeData
    │   ├── score_node.py              # ATS scoring
    │   ├── optimise_node.py           # Generic optimisation
    │   ├── search_node.py             # Job search + ranking
    │   ├── tailor_node.py             # JD-specific tailoring
    │   └── write_node.py              # Cover letter generation
    │
    └── models/
        ├── resume.py                  # ResumeData, CacheEntry
        ├── job.py                     # JobData, SearchFilters
        └── session.py                 # SessionState, DiffResult
```

***

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- OpenAI API key

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/yourusername/landit.git
cd landit
```

**2. Set up the backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

**3. Set up the frontend**

```bash
cd frontend
npm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

**4. Start both servers**

```bash
# Terminal 1 — Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

**5. Open the app**

```
http://localhost:3000
```

***

## 🔌 API Reference

### Resume

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/resume/upload` | Upload PDF, returns parsed `ResumeData` |
| `POST` | `/api/resume/optimize/start` | Start optimisation agent, returns `session_id` |
| `POST` | `/api/resume/optimize/review` | Submit approve/reject for HITL loop |

### Jobs

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/jobs/search` | Search jobs ranked by resume match |

### Tailor

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/tailor/resume` | Start tailoring session, returns diff + session_id |
| `POST` | `/api/tailor/review` | Submit approve/reject for tailored resume |

***

## ⚡ Caching Strategy

LandIt uses a **Content-Addressable Cache** in `localStorage` to avoid re-parsing the same resume.

```
Upload file
     │
     ▼
SHA-256(file bytes) ──▶ hash = "a3f9c2d1..."
     │
     ▼
localStorage["resume_cache"][hash] exists?
     │                    │
    YES                   NO
     │                    │
     ▼                    ▼
Return cached        POST /api/resume/upload
ResumeData           Store result in cache
(0ms, no API call)   (keyed by hash)
```

- Same file content → instant load regardless of filename
- Modified file → different hash → fresh parse
- Max 5 entries, oldest evicted automatically
- Persists across page refreshes and browser restarts

***

## 🗺️ Roadmap

- [ ] Resume version history — track all tailored versions
- [ ] Application tracker — Kanban board for job pipeline
- [ ] Live JD paste — paste any JD for instant match score
- [ ] Interview prep — role-specific questions from JD + resume gaps
- [ ] Skill gap radar — visual chart of market demand vs your skills
- [ ] Bulk apply — tailor top N jobs from a single search
- [ ] Auth — user accounts with NextAuth.js
- [ ] PDF export — download final tailored resume as formatted PDF

***

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

***

<div align="center">

Built with ❤️ using Next.js, FastAPI, and LangChain

</div>
