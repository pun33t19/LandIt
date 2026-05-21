# backend/tools/jsearch_tool.py
"""
JSearch API wrapper.
JSearch aggregates jobs from LinkedIn, Indeed, Glassdoor, ZipRecruiter
via a single RapidAPI endpoint.
"""

import httpx
from typing import List
from models.job import JobListing, JobSearchFilters
from api.config import get_settings

settings = get_settings()

JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HEADERS = {
    "X-RapidAPI-Key": settings.jsearch_api_key,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
}


async def fetch_jobs_from_api(filters: JobSearchFilters) -> List[dict]:
    """
    Calls JSearch API and returns raw job listing dicts.
    Handles pagination and error cases.
    """
    # Build query string — JSearch accepts natural language queries
    query = filters.query
    if filters.location and filters.location.lower() != "remote":
        query += f" in {filters.location}"

    params = {
        "query":          query,
        "page":           "1",
        "num_pages":      "1",
        "date_posted":    _date_posted_param(filters.date_posted),
        "remote_jobs_only": "true" if filters.work_mode == "remote" else "false",
        "employment_types": filters.employment_type.upper() if filters.employment_type else "FULLTIME",
        "country":        filters.country or "IN",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                JSEARCH_BASE_URL,
                headers=JSEARCH_HEADERS,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except httpx.HTTPStatusError as e:
            raise ValueError(f"JSearch API error {e.response.status_code}: {e.response.text}")
        except httpx.TimeoutException:
            raise ValueError("JSearch API timed out. Try again.")


def _date_posted_param(days: int) -> str:
    """Convert days integer to JSearch date_posted parameter string."""
    if days <= 1:   return "today"
    elif days <= 3: return "3days"
    elif days <= 7: return "week"
    else:           return "month"


def normalize_job(raw: dict) -> dict:
    """
    Converts raw JSearch API response into our clean JobListing format.
    JSearch returns inconsistent field names — this normalises them.
    """
    # Salary extraction — JSearch has multiple salary fields
    salary_min = (
        raw.get("job_min_salary") or
        raw.get("job_salary_period_min") or
        None
    )
    salary_max = (
        raw.get("job_max_salary") or
        raw.get("job_salary_period_max") or
        None
    )

    # Work mode detection from job description and flags
    is_remote = raw.get("job_is_remote", False)
    description = (raw.get("job_description") or "").lower()
    if is_remote or "fully remote" in description:
        work_mode = "remote"
    elif "hybrid" in description:
        work_mode = "hybrid"
    else:
        work_mode = "onsite"

    # Date posted — convert to human-readable
    posted_at = raw.get("job_posted_at_datetime_utc", "")
    date_posted = _format_date_posted(posted_at)

    return {
        "job_id":           raw.get("job_id", ""),
        "title":            raw.get("job_title", ""),
        "company":          raw.get("employer_name", ""),
        "location":         _format_location(raw),
        "country":          raw.get("job_country", ""),
        "work_mode":        work_mode,
        "employment_type":  (raw.get("job_employment_type") or "FULLTIME").lower(),
        "salary_min":       salary_min,
        "salary_max":       salary_max,
        "salary_currency":  raw.get("job_salary_currency", "INR"),
        "date_posted":      date_posted,
        "apply_link":       raw.get("job_apply_link", ""),
        "description":      raw.get("job_description", "")[:3000],  # cap at 3000 chars
        "description_snippet": (raw.get("job_description") or "")[:300],
        "required_skills":  raw.get("job_required_skills") or [],
        "source":           raw.get("job_publisher", ""),
        # These get filled later by filter + match steps
        "match_score":      None,
        "match_label":      None,
        "match_explanation": None,
        "skills_matched":   [],
        "skills_missing":   [],
        "skills_missing_priority": {}
    }


def _format_location(raw: dict) -> str:
    """Build readable location string from JSearch location fields."""
    parts = []
    city    = raw.get("job_city")
    state   = raw.get("job_state")
    country = raw.get("job_country")
    if city:    parts.append(city)
    if state:   parts.append(state)
    if country: parts.append(country)
    return ", ".join(parts) if parts else "Location not specified"


def _format_date_posted(iso_date: str) -> str:
    """Convert ISO date string to human-readable 'X days ago'."""
    if not iso_date:
        return "Unknown"
    try:
        from datetime import datetime, timezone
        posted = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        now    = datetime.now(timezone.utc)
        days   = (now - posted).days
        if days == 0:  return "Today"
        if days == 1:  return "Yesterday"
        return f"{days} days ago"
    except Exception:
        return "Recently"
