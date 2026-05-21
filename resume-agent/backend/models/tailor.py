# backend/models/tailor.py
"""
Data models for Phase 4 — Resume Tailoring.
Covers the request, response, and all intermediate states.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class TailorOptions(BaseModel):
    """
    Controls which tailoring steps to run.
    All True by default — user can turn off individual steps.
    """
    mirror_keywords:        bool = True   # inject JD keywords into resume
    reorder_skills:         bool = True   # move JD-matching skills to top
    rewrite_bullets:        bool = True   # rewrite bullets to match JD language
    generate_cover_letter:  bool = False  # off by default — opt-in


class TailorRequest(BaseModel):
    """
    Full request body for POST /api/tailor/resume.
    Requires the optimised resume from Phase 2 and one job from Phase 3.
    """
    resume:  dict          # ResumeData from Phase 1 or Phase 2
    job:     dict          # JobListing from Phase 3 results
    options: TailorOptions = TailorOptions()


class CoverLetterRequest(BaseModel):
    """Request body for POST /api/tailor/cover-letter."""
    resume: dict
    job:    dict
    tone:   str = "professional"  # "professional" | "friendly" | "concise"


class JDAnalysis(BaseModel):
    """
    Structured analysis of the job description.
    Built by analyze_jd_node — used by all downstream nodes.
    """
    required_skills:    List[str]        # must-have skills from JD
    preferred_skills:   List[str]        # nice-to-have skills
    key_keywords:       List[str]        # important phrases to mirror
    responsibilities:   List[str]        # what the role does day-to-day
    seniority_level:    str              # "junior" | "mid" | "senior" | "lead"
    domain_focus:       str              # e.g. "backend APIs", "data pipelines"
    tone:               str              # "formal" | "startup" | "technical"
    keyword_frequency:  Dict[str, int]   # keyword → how many times in JD


class BulletRewrite(BaseModel):
    """Tracks one bullet rewrite — original vs tailored."""
    role:              str
    company:           str
    original:          str
    tailored:          str
    keywords_added:    List[str]
    reason:            str   # why this rewrite was made


class TailorState(BaseModel):
    """
    The LangGraph state — the notepad passed between all 4 nodes.
    Every field starts empty/None and gets filled as nodes run.
    """
    # Inputs — set at start, never changed
    original_resume:   dict
    job:               dict
    options:           TailorOptions

    # Node outputs — filled as graph progresses
    jd_analysis:       Optional[JDAnalysis]  = None  # filled by analyze_jd_node
    tailored_resume:   Optional[dict]        = None  # filled progressively
    bullet_rewrites:   List[BulletRewrite]   = []    # filled by rewrite_bullets_node
    keywords_added:    List[str]             = []    # filled by mirror_keywords_node
    keywords_missed:   List[str]             = []    # filled by score_against_jd_node
    jd_ats_score:      Optional[float]       = None  # filled by score_against_jd_node
    jd_ats_breakdown:  Optional[dict]        = None  # category scores
    cover_letter:      Optional[str]         = None  # filled if options.generate_cover_letter
    diff:              Optional[dict]        = None  # word-level diff for UI
    approved:          bool                  = False # set True when user approves
    finished:          bool                  = False # set True at end


class TailorResponse(BaseModel):
    """Final response from POST /api/tailor/resume."""
    session_id:        str
    status:            str              # "complete" | "awaiting_review"

    tailored_resume:   dict
    original_resume:   dict
    diff:              dict

    jd_ats_score:      float
    jd_ats_breakdown:  dict
    generic_ats_score: float            # from original resume for comparison

    keywords_added:    List[str]
    keywords_missed:   List[str]
    bullet_rewrites:   List[dict]

    cover_letter:      Optional[str]  = None
