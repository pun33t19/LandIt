"""
Resume tailoring routes:
  POST /api/tailor/resume              - Start tailoring (runs nodes 1-4, pauses)
  POST /api/tailor/review              - Approve or reject the tailored resume
  POST /api/tailor/cover-letter        - Generate cover letter standalone
  GET  /api/tailor/session/{id}        - Get current state of a tailor session
"""

from fastapi import APIRouter, HTTPException, Query
from models.tailor import TailorRequest, CoverLetterRequest
from agents.tailor_agent import (
    start_tailoring,
    approve_tailoring,
    reject_tailoring,
    tailor_graph
)
from tools.tailor_tools import analyse_jd, generate_cover_letter

router = APIRouter()


@router.post(
    "/resume",
    summary="Tailor your resume for a specific job"
)
async def tailor_resume_endpoint(request: TailorRequest):
    """
    Tailors your resume for one specific job in 4 steps:
    1. Analyses the job description (extracts skills, keywords, tone)
    2. Mirrors JD keywords into your summary, reorders your skills
    3. Rewrites top 3 experience bullets per role to match JD language
    4. Scores tailored resume against the JD specifically (not generic ATS)

    Then PAUSES and returns the diff + score for your review.
    You must call POST /api/tailor/review to approve or reject.

    Request body:
    {
      "resume": { ...your ResumeData from Phase 1 or 2... },
      "job":    { ...one job from Phase 3 results... },
      "options": {
        "mirror_keywords":       true,
        "reorder_skills":        true,
        "rewrite_bullets":       true,
        "generate_cover_letter": false
      }
    }

    Response (status: "awaiting_review"):
    {
      "session_id":       "uuid-string",
      "status":           "awaiting_review",
      "tailored_resume":  { ...your tailored resume... },
      "original_resume":  { ...your original for comparison... },
      "diff":             { ...word-level changes... },
      "jd_ats_score":     88.5,
      "jd_ats_breakdown": { required_skills: {...}, keyword_match: {...}, ... },
      "generic_ats_score": 79,
      "keywords_added":   ["distributed systems", "event-driven"],
      "keywords_missed":  ["Terraform"],
      "bullet_rewrites":  [{ role, original, tailored, keywords_added }...]
    }
    """
    try:
        result = await start_tailoring(request)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()   # ← prints full traceback to terminal
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/review",
    summary="Approve or reject the tailored resume"
)
async def review_tailoring_endpoint(
    session_id: str = Query(..., description="Session ID from POST /tailor/resume"),
    action:     str = Query(..., description="approve or reject")
):
    """
    Called after reviewing the diff from POST /api/tailor/resume.

    ?action=approve
      - Marks the tailored resume as accepted
      - Runs cover_letter_node if options.generate_cover_letter=True
      - Returns final tailored resume with cover letter (if requested)
      - Status: "complete"

    ?action=reject
      - Discards all tailoring changes
      - Returns original resume unchanged
      - Status: "rejected"

    Example:
    POST /api/tailor/review?session_id=abc-123&action=approve
    POST /api/tailor/review?session_id=abc-123&action=reject
    """
    if action not in ("approve", "reject"):
        raise HTTPException(
            status_code=400,
            detail="action must be 'approve' or 'reject'"
        )

    try:
        if action == "approve":
            result = await approve_tailoring(session_id)
        else:
            result = await reject_tailoring(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cover-letter",
    summary="Generate a tailored cover letter for a job"
)
async def cover_letter_endpoint(request: CoverLetterRequest):
    """
    Generates a tailored cover letter standalone — without running the full
    tailoring pipeline. Use this if you already have a tailored resume and
    just need the letter.

    Or if you called POST /api/tailor/resume with generate_cover_letter=false
    and changed your mind after approving.

    Request body:
    {
      "resume": { ...your resume (tailored or original)... },
      "job":    { ...the job listing... },
      "tone":   "professional"  // "professional" | "startup" | "concise"
    }

    Returns:
    {
      "cover_letter": "Dear Hiring Manager,\\n\\n..."
    }
    """
    try:
        jd_analysis = await analyse_jd(request.job)
        letter      = await generate_cover_letter(
            request.resume,
            request.job,
            jd_analysis,
            request.tone
        )
        return {"cover_letter": letter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/session/{session_id}",
    summary="Get current state of a tailoring session"
)
async def get_tailor_session(session_id: str):
    """
    Returns the current state of a tailoring session from Redis.
    Useful for:
    - Re-rendering the review screen after a page refresh
    - Checking if a session is still active

    Returns 404 if session doesn\'t exist or has expired.
    """
    try:
        config      = {"configurable": {"thread_id": session_id}}
        state_snap  = await tailor_graph.aget_state(config)

        if not state_snap or not state_snap.values:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired"
            )

        state = state_snap.values
        return {
            "session_id":       session_id,
            "status":           "complete" if state.get("finished") else "awaiting_review",
            "tailored_resume":  state.get("tailored_resume"),
            "jd_ats_score":     state.get("jd_ats_score"),
            "keywords_added":   state.get("keywords_added", []),
            "keywords_missed":  state.get("keywords_missed", []),
            "diff":             state.get("diff"),
            "cover_letter":     state.get("cover_letter")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def tailor_health():
    return {"status": "ok", "phase": "4"}