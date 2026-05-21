# backend/tools/filter_tool.py
"""
Hard filter logic for job listings.
Runs BEFORE any AI/embedding work to eliminate irrelevant jobs cheaply.
Every filter here is pure Python — no LLM calls, no API calls.
"""

from typing import List, Optional
from models.job import JobSearchFilters


def apply_filters(jobs: List[dict], filters: JobSearchFilters) -> List[dict]:
    filtered  = []
    removed   = []   # ← NEW: track what was removed and why

    for job in jobs:
        reason = _filter_reason(job, filters)
        if reason:
            removed.append({ "job_id": job["job_id"], "reason": reason })
            continue
        filtered.append(job)

    # Log removals so you can debug filter aggressiveness
    if removed:
        import logging
        logging.info(f"Filter removed {len(removed)} jobs: {removed[:3]}...")

    return filtered


def _filter_reason(job: dict, filters: JobSearchFilters) -> Optional[str]:
    """
    Returns the FIRST reason a job fails filters, or None if it passes.
    Same logic as _passes_all_filters but returns a string reason.
    """
    if filters.salary_min is not None:
        job_max = job.get("salary_max")
        if job_max is not None and job_max < filters.salary_min:
            return f"salary_max {job_max} < salary_min {filters.salary_min}"

    if filters.work_mode and filters.work_mode != "any":
        job_mode = (job.get("work_mode") or "").lower()
        if job_mode and job_mode != filters.work_mode.lower():
            return f"work_mode '{job_mode}' != '{filters.work_mode}'"

    if filters.tech_stack:
        text = (job.get("description","") + job.get("title","")).lower()
        if not any(s.lower() in text for s in filters.tech_stack):
            return f"none of {filters.tech_stack} found in JD"

    irrelevant = ["sales","marketing","hr ","accountant","legal"]
    if any(kw in (job.get("title","")).lower() for kw in irrelevant):
        return "irrelevant title"

    if len(job.get("description","")) < 50:
        return "description too short"

    return None  # passed all filters


def _passes_all_filters(job: dict, filters: JobSearchFilters) -> bool:
    """Returns True only if job passes every active filter."""

    # ── Salary filter ───────────────────────────────────────────────────────
    # Only filter if the job HAS salary data AND user set a range
    if filters.salary_min is not None:
        job_max = job.get("salary_max")
        if job_max is not None and job_max < filters.salary_min:
            return False  # job pays less than your minimum

    if filters.salary_max is not None:
        job_min = job.get("salary_min")
        if job_min is not None and job_min > filters.salary_max:
            return False  # job pays more than your maximum (overqualified risk)

    # ── Work mode filter ─────────────────────────────────────────────────────
    # Only filter if user explicitly specified a work mode
    if filters.work_mode:
        job_mode = (job.get("work_mode") or "").lower()
        filter_mode = filters.work_mode.lower()
        # remote jobs pass remote filter; hybrid passes hybrid;
        # if user wants remote, onsite jobs fail
        if filter_mode != "any" and job_mode != filter_mode:
            return False

    # ── Employment type filter ───────────────────────────────────────────────
    if filters.employment_type:
        job_type   = (job.get("employment_type") or "").lower()
        filter_type = filters.employment_type.lower()
        # "fulltime" and "full_time" are both valid — normalise
        job_type    = job_type.replace("_", "").replace("-", "")
        filter_type = filter_type.replace("_", "").replace("-", "")
        if job_type and job_type != filter_type:
            return False

    # ── Tech stack filter ────────────────────────────────────────────────────
    # Job must mention AT LEAST ONE of the required skills in its description
    if filters.tech_stack:
        description = (job.get("description") or "").lower()
        title       = (job.get("title") or "").lower()
        text        = description + " " + title

        skill_found = any(
            skill.lower() in text
            for skill in filters.tech_stack
        )
        if not skill_found:
            return False

    # ── Title relevance filter ───────────────────────────────────────────────
    # Reject jobs with obviously irrelevant titles
    irrelevant_keywords = [
        "sales", "marketing", "hr ", "human resources",
        "accountant", "finance", "legal", "content writer",
        "graphic design", "customer support"
    ]
    title_lower = (job.get("title") or "").lower()
    if any(kw in title_lower for kw in irrelevant_keywords):
        return False

    # ── Empty description filter ─────────────────────────────────────────────
    # Jobs with no description can't be semantically matched — skip them
    if not job.get("description") or len(job.get("description", "")) < 50:
        return False

    return True


def extract_skills_from_jd(description: str, resume_skills: List[str]) -> dict:
    """
    Compares job description against resume skills.
    Returns which skills match and which are missing.

    Used for the skills_matched / skills_missing fields on each job card.
    """
    description_lower = description.lower()

    matched = []
    missing = []

    for skill in resume_skills:
        if skill.lower() in description_lower:
            matched.append(skill)

    # Also scan for common tech skills NOT in resume
    # (to surface what the JD wants that you don't have)
    common_tech_skills = [
        "kubernetes", "terraform", "docker", "go", "rust", "scala",
        "kafka", "elasticsearch", "mongodb", "redis", "graphql",
        "typescript", "react", "vue", "angular", "spring boot",
        "django", "flask", "fastapi", "express", "nestjs",
        "aws", "gcp", "azure", "ci/cd", "jenkins", "github actions",
        "microservices", "grpc", "rabbitmq", "celery",
        "machine learning", "pytorch", "tensorflow"
    ]

    # Count how many times each missing skill appears (priority indicator)
    missing_priority = {}
    for skill in common_tech_skills:
        if skill.lower() not in [s.lower() for s in resume_skills]:
            count = description_lower.count(skill.lower())
            if count > 0:
                missing.append(skill)
                missing_priority[skill] = count

    # Sort missing by frequency — most mentioned = most important
    missing_sorted = sorted(missing_priority.keys(), key=lambda s: -missing_priority[s])

    return {
        "skills_matched":          matched,
        "skills_missing":          missing_sorted[:8],    # cap at 8
        "skills_missing_priority": missing_priority
    }
