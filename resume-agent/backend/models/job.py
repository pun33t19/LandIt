"""
Data models for job search — filters, listings, and search responses.
All fields validated by Pydantic automatically.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class EmploymentType(str, Enum):
    FULLTIME   = "fulltime"
    PARTTIME   = "parttime"
    CONTRACT   = "contract"
    INTERNSHIP = "internship"


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    ANY    = "any"


class ExperienceLevel(str, Enum):
    ENTRY     = "entry"
    MID       = "mid"
    SENIOR    = "senior"
    LEAD      = "lead"
    PRINCIPAL = "principal"


class JobSearchFilters(BaseModel):
    """
    All the filters a user can set when searching for jobs.
    Every field has a sensible default so only query is required.
    """
    query:            str                          # e.g. "Backend Engineer Python"
    location:         str       = "remote"         # city name or "remote"
    country:          str       = "IN"             # ISO country code
    employment_type:  Optional[EmploymentType] = EmploymentType.FULLTIME
    work_mode:        Optional[WorkMode]       = WorkMode.ANY
    salary_min:       Optional[int]            = None  # annual, in local currency
    salary_max:       Optional[int]            = None
    experience_level: Optional[ExperienceLevel]= None
    tech_stack:       List[str]                = []    # must appear in JD
    date_posted:      int                      = 7     # last N days
    num_results:      int       = Field(default=20, ge=1, le=50)


class JobListing(BaseModel):
    """A single job listing — raw fields + AI-computed match fields."""

    # ── Raw fields from JSearch API ─────────────────────────────────────────
    job_id:              str
    title:               str
    company:             str
    location:            str                = "Not specified"
    country:             str                = ""
    work_mode:           str                = "onsite"
    employment_type:     str                = "fulltime"
    salary_min:          Optional[int]      = None
    salary_max:          Optional[int]      = None
    salary_currency:     str                = "INR"
    date_posted:         str                = "Unknown"
    apply_link:          str                = ""
    description:         str                = ""
    description_snippet: str                = ""
    outside_filters:     bool               = False
    required_skills:     List[str]          = []
    source:              str                = ""     # "LinkedIn", "Indeed", etc.

    # ── AI-computed fields (filled during match step) ────────────────────────
    match_score:             Optional[float]       = None  # 0-100
    match_label:             Optional[str]         = None  # "Excellent match"
    match_explanation:       Optional[str]         = None  # GPT explanation
    skills_matched:          List[str]             = []
    skills_missing:          List[str]             = []
    skills_missing_priority: Dict[str, int]        = {}   # skill → count in JD


class JobSearchRequest(BaseModel):
    """The full request body for POST /api/jobs/search."""
    resume:  dict              # ResumeData as dict (from Phase 1/2 output)
    filters: JobSearchFilters


class JobMatchRequest(BaseModel):
    """Request body for POST /api/jobs/match — score a single job."""
    resume:      dict   # ResumeData as dict
    job:         dict   # JobListing as dict
    explain:     bool = True  # whether to generate a text explanation


class JobSearchResponse(BaseModel):
    """The full response from POST /api/jobs/search."""
    total_found:  int
    cache_id:     str
    cached:       bool
    search_query: str
    fallback_used:   bool         = False
    fallback_reason: Optional[str] = None
    results:      List[dict]