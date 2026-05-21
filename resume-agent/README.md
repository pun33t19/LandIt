# Resume AI Agent

An end-to-end AI agent that parses your resume, optimises it, searches for matching jobs, and tailors your resume per job description.

## Architecture

```
Resume Input → Parse + ATS Score → Optimize (LangGraph loop) → Job Search → Tailor per JD → Export PDF
```

## Stack

| Layer | Tool |
|---|---|
| LLM | GPT-4o / Claude 3.5 Sonnet |
| Agent framework | LangGraph |
| Backend | FastAPI (Python 3.11) |
| PDF parsing | pdfplumber + python-docx |
| Job API | JSearch (RapidAPI) |
| Vector DB | Pinecone |
| Database | Supabase (Postgres) |
| Cache | Redis (Upstash) |
| Frontend | Next.js 14 + shadcn/ui |
| Deploy | Railway (backend) + Vercel (frontend) |

## Project Structure

```
resume-agent/
├── backend/
│   ├── api/
│   │   ├── config.py          # Pydantic settings (env vars)
│   │   ├── main.py            # FastAPI app entry point
│   │   └── routes/
│   │       ├── resume.py      # Upload + parse endpoints
│   │       ├── jobs.py        # Job search endpoints (Phase 4)
│   │       └── tailor.py      # Resume tailor endpoints (Phase 5)
│   ├── agents/                # LangGraph agents (Phase 3, 4, 5)
│   ├── models/
│   │   ├── resume.py          # ResumeData, WorkExperience, Education
│   │   └── job.py             # JobListing, JobSearchFilters
│   ├── parsers/
│   │   └── pdf_parser.py      # PDF/DOCX/TXT → ResumeData via GPT-4o
│   ├── prompts/               # Prompt templates (Phase 3+)
│   ├── tools/                 # LangChain tools (Phase 4+)
│   ├── utils/
│   │   └── embeddings.py      # OpenAI embeddings + cosine similarity
│   ├── .env.example           # Copy to .env and fill in your keys
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # Next.js 14 app (Phase 6)
├── docker-compose.yml
└── README.md
```

## Quick Start

### 1. Setup

```bash
cd resume-agent/backend
cp .env.example .env
# Edit .env — add at minimum: OPENAI_API_KEY
```

### 2. Install

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Start Redis

```bash
# Option A: Docker one-liner
docker run -d -p 6379:6379 redis:7-alpine

# Option B: Full stack
docker-compose up
```

### 4. Run

```bash
uvicorn api.main:app --reload --port 8000
```

Open http://localhost:8000/docs — Swagger UI.

### 5. Test the parser

```bash
curl -X POST http://localhost:8000/api/resume/upload \
  -F "file=@your_resume.pdf"
```

## API Keys Needed

| Service | URL | Free Tier |
|---|---|---|
| OpenAI | https://platform.openai.com | Pay-per-use (~$0.01/parse) |
| JSearch | https://rapidapi.com/letscrape | 200 req/mo free |
| Supabase | https://supabase.com | 500MB free |
| Pinecone | https://pinecone.io | 1 free index |
| Upstash Redis | https://upstash.com | 10K req/day free |

## Build Phases

- **Phase 1** — Project setup, models, parser, FastAPI skeleton ✅
- **Phase 2** — Resume Optimizer (LangGraph loop, ATS scoring)
- **Phase 3** — Job Search Agent (JSearch API + embedding match)
- **Phase 4** — Resume Tailor Agent (per-JD customization + cover letter)
- **Phase 5** — Frontend (Next.js 14 wizard UI with streaming)
- **Phase 6** — Deploy (Railway + Vercel + GitHub Actions CI/CD)

## Deploy

### Backend → Railway

```bash
npm install -g @railway/cli
railway login && railway init
railway up
```

### Frontend → Vercel

```bash
cd frontend
npx vercel --prod
```

## License

MIT
