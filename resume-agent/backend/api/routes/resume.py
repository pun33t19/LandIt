# backend/api/routes/resume.py
"""
Resume routes:
  POST /api/resume/upload              - Upload + parse PDF/DOCX
  POST /api/resume/optimize/start      - Start HITL optimization session
  POST /api/resume/optimize/review     - Submit user review decision
  GET  /api/resume/optimize/{id}       - Get current session status
  GET  /api/resume/health              - Health check
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional

from parsers.pdf_parser import parse_resume
from agents.optimizer import (
    start_optimization,
    resume_optimization,
    get_session_status
)
from models.resume import ResumeData

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain"
}


# ── Request / Response models ─────────────────────────────────────────────────

class ReviewDecision(BaseModel):
    """
    User's review decision submitted after seeing the diff.

    action:
      "approve"             - Accept the rewritten resume as-is
      "approve_with_edits"  - Accept but with manual edits applied
      "reject"              - Reject changes, keep original

    edited_resume:
      Only required when action = "approve_with_edits"
      The frontend sends back the full ResumeData with the
      user's manual edits merged in
    """
    action: str                           # "approve" | "approve_with_edits" | "reject"
    edited_resume: Optional[dict] = None  # only for approve_with_edits


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=ResumeData,
    summary="Upload and parse a resume"
)
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload a PDF, DOCX, or TXT resume.
    Returns structured ResumeData with ATS score and improvement gaps.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Use PDF, DOCX, or TXT."
        )

    suffix = Path(file.filename).suffix
    save_path = UPLOAD_DIR / f"{uuid.uuid4()}{suffix}"

    try:
        with save_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        resume_data = await parse_resume(save_path)
        return resume_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always delete uploaded file after parsing — no files linger on disk
        if save_path.exists():
            save_path.unlink()


@router.post(
    "/optimize/start",
    summary="Start a Human-in-the-Loop optimization session"
)
async def start_optimize(resume: ResumeData):
    """
    Starts the optimization process for a parsed resume.

    Runs analyze + rewrite, then PAUSES and returns:
    - session_id     → use this in all subsequent /review calls
    - diff           → word-level diff of every changed bullet
    - pending_resume → rewritten version awaiting user approval
    - suggestions    → list of issues the agent found
    - original_ats_score → ATS score before any changes
    - status         → always "awaiting_review" at this stage

    The graph does NOT proceed until the user submits a review decision.
    """
    try:
        result = await start_optimization(resume)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/optimize/review",
    summary="Submit user review decision to continue or finish optimization"
)
async def review_optimize(session_id: str, decision: ReviewDecision):
    """
    Submits the user's decision after reviewing the highlighted diff.

    Pass session_id as a query parameter:
      POST /api/resume/optimize/review?session_id=abc-123

    Request body:
      { "action": "approve" }
      { "action": "approve_with_edits", "edited_resume": { ...ResumeData... } }
      { "action": "reject" }

    Returns one of two shapes:

    Still iterating (status = "awaiting_review"):
      {
        "session_id": "abc-123",
        "iteration": 2,
        "diff": { ...next round of diffs... },
        "current_ats_score": 71,
        "pending_resume": { ...next rewrite... },
        "status": "awaiting_review"
      }

    Done (status = "complete"):
      {
        "status": "complete",
        "optimized_resume": { ...final ResumeData... },
        "original_ats_score": 45,
        "final_ats_score": 83,
        "score_improvement": 38,
        "iterations_run": 2,
        "diff_summary": { ...full before/after diff... },
        "history": [ ...per-iteration change log... ]
      }
    """
    try:
        result = await resume_optimization(session_id, decision.model_dump())
        return result
    except ValueError as e:
        # Session not found or expired
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/optimize/{session_id}",
    summary="Get current status of an optimization session"
)
async def get_optimize_status(session_id: str):
    """
    Retrieves the current state of an in-progress optimization session.

    Useful when the frontend needs to re-render the review screen
    after a page refresh without losing progress.

    Sessions expire after 30 minutes of inactivity.
    Returns 404 if session_id is invalid or expired.
    """
    try:
        return await get_session_status(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/health")
async def resume_health():
    return {"status": "ok"}