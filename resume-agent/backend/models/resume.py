from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from enum import Enum


class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


class WorkExperience(BaseModel):
    role: str
    company: str
    location: Optional[str] = None
    start_date: str  # "Jan 2022"
    end_date: str    # "Mar 2024" or "Present"
    duration_months: Optional[int] = None
    bullets: List[str] = []
    tech_used: List[str] = []


class Education(BaseModel):
    degree: str
    institution: str
    field: Optional[str] = None
    graduation_year: Optional[str] = None
    gpa: Optional[float] = None


class ResumeData(BaseModel):
    # Personal
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

    # Content
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[WorkExperience] = []
    education: List[Education] = []
    certifications: List[str] = []
    projects: List[dict] = []

    # Agent-computed
    ats_score: int = Field(default=0, ge=0, le=100)
    gaps: List[str] = []
    strengths: List[str] = []
    experience_level: Optional[ExperienceLevel] = None
    total_years_experience: Optional[float] = None
    primary_tech_stack: List[str] = []


class TailoredResume(BaseModel):
    original_resume: ResumeData
    tailored_resume: ResumeData
    job_id: str
    job_title: str
    company: str
    match_score: float
    keywords_added: List[str]
    match_analysis: str
    cover_letter: str
    improvements: List[str]
