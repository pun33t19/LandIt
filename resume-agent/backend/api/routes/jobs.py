"""
Job search routes:
  POST /api/jobs/search          - Search + filter + rank jobs
  POST /api/jobs/match           - Score a single job vs resume
  GET  /api/jobs/search/{id}     - Get cached search results
  GET  /api/jobs/health          - Health check
"""

from fastapi import APIRouter, HTTPException, Query
from models.job import JobSearchRequest, JobMatchRequest
from agents.job_search_agent import search_jobs, match_single_job
from utils.cache import get_cached_results, invalidate_cache

router = APIRouter()


@router.post(
    "/search",
    summary="Search, filter, and rank jobs against your resume"
)
async def search_jobs_endpoint(request: JobSearchRequest):
    """
    The main job search endpoint. Does 4 things in sequence:
    1. Fetches jobs from JSearch API (LinkedIn + Indeed + Glassdoor)
    2. Applies hard filters (salary, work mode, tech stack)
    3. Ranks results by semantic similarity to your resume
    4. Generates match explanation for top 5 results

    Request body:
    {
      "resume": { ...ResumeData from Phase 1 or 2... },
      "filters": {
        "query":           "Backend Engineer Python",
        "location":        "Bangalore",
        "country":         "IN",
        "employment_type": "fulltime",
        "work_mode":       "hybrid",
        "salary_min":      1500000,
        "salary_max":      4000000,
        "tech_stack":      ["Python", "FastAPI", "AWS"],
        "date_posted":     7,
        "num_results":     20
      }
    }

    Response includes match_score (0-100), match_label, skills_matched,
    skills_missing, and match_explanation for top jobs.
    Results are cached for 1 hour — same search returns instantly.
    """
    try:
        result = await search_jobs(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/match",
    summary="Score and explain a single job against your resume"
)
async def match_job_endpoint(request: JobMatchRequest):
    """
    Scores one specific job against your resume.
    Used for the "Tailor for this job" button on each job card
    and for the Chrome extension\'s contextual matching.

    Request body:
    {
      "resume": { ...ResumeData... },
      "job": {
        "title": "Senior Backend Engineer",
        "company": "Razorpay",
        "description": "We are looking for...",
        ...
      },
      "explain": true   // set false to skip GPT explanation (faster)
    }

    Returns the job dict enriched with:
    - match_score (0-100)
    - match_label ("Excellent match" / "Good match" / etc.)
    - skills_matched (skills you have that appear in JD)
    - skills_missing (skills in JD you don\'t have, sorted by frequency)
    - match_explanation (2-sentence GPT explanation, if explain=true)
    """
    try:
        result = await match_single_job(
            request.resume,
            request.job,
            request.explain
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/search/{cache_id}",
    summary="Retrieve a cached job search result"
)
async def get_cached_search(
    cache_id: str,
    refresh: bool = Query(default=False, description="Force a fresh search")
):
    """
    Returns a previously cached search result by its cache_id.
    The cache_id is returned in every /search response.

    Use this to:
    - Re-render results after a page refresh without re-running the search
    - Share a search result URL with someone

    Pass ?refresh=true to invalidate the cache and force a fresh search
    (you\'ll need to call /search again after this).

    Cache entries expire after 1 hour automatically.
    """
    if refresh:
        await invalidate_cache(cache_id)
        return {"status": "cache_cleared", "message": "Run /search again for fresh results"}

    result = await get_cached_results(cache_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Cache not found or expired. Run a new search."
        )
    result["cached"] = True
    return result


@router.get("/health")
async def jobs_health():
    return {"status": "ok", "phase": "3"}