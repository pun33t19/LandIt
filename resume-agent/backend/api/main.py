"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import get_settings
from api.routes import resume, jobs, tailor

settings = get_settings()

app = FastAPI(
    title="Resume AI Agent API",
    description="Parse, optimize, search jobs, and tailor resumes with AI.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — allow frontend dev server to connect with backend server 
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (added in later phases)
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(jobs.router,   prefix="/api/jobs",   tags=["Jobs"])
app.include_router(tailor.router, prefix="/api/tailor", tags=["Tailor"])


#A simple heartbeat endpoint. Railway and Vercel ping this every 30 seconds — if it returns 200, the server is alive. If it fails, they restart the container automatically.
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
