"""
Resume parser: PDF/DOCX → raw text → structured ResumeData via LLM.
"""
import pdfplumber
import json
import re
from pathlib import Path
from typing import Union
from docx import Document

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from models.resume import ResumeData, WorkExperience, Education
from api.config import get_settings

settings = get_settings()


# ── Text extraction ──────────────────────────────────────────────────────────

def extract_text_from_pdf(path: Union[str, Path]) -> str:
    """Extract all text from a PDF, preserving rough layout."""
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True) or ""
            pages.append(text)
    return "\n\n--- PAGE BREAK ---\n\n".join(pages)


def extract_text_from_docx(path: Union[str, Path]) -> str:
    """Extract text from a .docx file."""
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx is required: pip install python-docx")
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_resume_text(path: Union[str, Path]) -> str:
    """Auto-detect file type and extract text."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(path)
    elif suffix == ".txt":
        return path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use PDF, DOCX, or TXT.")


# ── LLM-based structured extraction ─────────────────────────────────────────

PARSE_SYSTEM_PROMPT = PARSE_SYSTEM_PROMPT = """You are an expert resume parser. Extract structured data from the resume text below.

Return a valid JSON object matching this exact schema:
{{
  "name": "string",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "linkedin": "url or null",
  "github": "url or null",
  "portfolio": "url or null",
  "summary": "string or null",
  "skills": ["skill1", "skill2"],
  "experience": [
    {{
      "role": "string",
      "company": "string",
      "location": "string or null",
      "start_date": "Mon YYYY",
      "end_date": "Mon YYYY or Present",
      "duration_months": "integer or null",
      "bullets": ["bullet1"],
      "tech_used": ["tech1"]
    }}
  ],
  "education": [
    {{
      "degree": "string",
      "institution": "string",
      "field": "string or null",
      "graduation_year": "YYYY or null",
      "gpa": "float or null"
    }}
  ],
  "certifications": ["cert1"],
  "projects": [
    {{"name": "string", "description": "string", "tech": ["tech1"], "url": "string or null"}}
  ],
  "ats_score": "integer 0-100",
  "gaps": ["gap description 1"],
  "strengths": ["strength 1"],
  "experience_level": "entry|mid|senior|lead|principal",
  "total_years_experience": "float",
  "primary_tech_stack": ["top 5-8 skills"]
}}

ATS Score criteria (0-100):
- 20pts: Quantified achievements (%, $, scale numbers in bullets)
- 20pts: Action verbs starting each bullet (Led, Built, Reduced, Shipped)
- 15pts: Skills section completeness and keyword density
- 15pts: Clear section structure (Summary, Experience, Education, Skills)
- 15pts: No spelling/grammar issues, consistent date formats
- 15pts: Contact info completeness (email, phone, LinkedIn, GitHub)

Gaps: List specific, actionable improvements needed.
Return ONLY the JSON. No explanation, no markdown fences."""

PARSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", PARSE_SYSTEM_PROMPT),
    ("human", "Parse this resume:\n\n{resume_text}")
])


def get_llm():
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=0,
        api_key=settings.openai_api_key
    )


async def parse_resume(file_path: Union[str, Path]) -> ResumeData:
    """
    Full pipeline: file → text → LLM → ResumeData.
    Usage:
        resume = await parse_resume("uploads/john_doe.pdf")
    """
    # 1. Extract raw text
    raw_text = extract_resume_text(file_path)
    if not raw_text.strip():
        raise ValueError("Could not extract text from the file. Is the PDF image-based?")

    # 2. LLM structured extraction
    llm = get_llm()
    chain = PARSE_PROMPT | llm

    response = await chain.ainvoke({"resume_text": raw_text[:12000]})  # ~3k tokens max

    # 3. Parse JSON response
    content = response.content.strip()
    # Strip markdown fences if model added them anyway
    content = re.sub(r"^```(?:json)?\n?", "", content)
    content = re.sub(r"\n?```$", "", content)

    data = json.loads(content)
    return ResumeData(**data)
