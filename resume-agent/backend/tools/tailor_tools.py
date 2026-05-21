# backend/tools/tailor_tools.py

import re
import json
from typing import List, Dict, Tuple
from langchain_openai import ChatOpenAI
from models.tailor import JDAnalysis, BulletRewrite
from api.config import get_settings

settings = get_settings()


async def analyse_jd(job: dict) -> JDAnalysis:
    description = job.get("description", "")
    title       = job.get("title", "")
    company     = job.get("company", "")

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=0,
        api_key=settings.openai_api_key
    )

    prompt = (
        "Analyse this job description and return a JSON object with these exact fields:\n\n"
        "{\n"
        '  "required_skills": ["list of must-have technical skills"],\n'
        '  "preferred_skills": ["list of nice-to-have skills"],\n'
        '  "key_keywords": ["important domain phrases, max 15"],\n'
        '  "responsibilities": ["top 5 day-to-day responsibilities"],\n'
        '  "seniority_level": "junior|mid|senior|lead",\n'
        '  "domain_focus": "one phrase e.g. backend APIs",\n'
        '  "tone": "formal|startup|technical",\n'
        '  "keyword_frequency": {"keyword": 1}\n'
        "}\n\n"
        "Return ONLY the JSON, no explanation.\n\n"
        f"JOB TITLE: {title}\n"
        f"COMPANY: {company}\n"
        f"DESCRIPTION:\n{description[:4000]}"
    )

    response = await llm.ainvoke(prompt)

    raw = response.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*',     '', raw)
    raw = re.sub(r'```\s*$',     '', raw)
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except Exception:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except Exception:
                data = {}
        else:
            data = {}

    raw_kw_freq = data.get("keyword_frequency", {})
    keyword_frequency = {}
    if isinstance(raw_kw_freq, dict):
        for k, v in raw_kw_freq.items():
            try:
                keyword_frequency[str(k)] = int(v)
            except Exception:
                keyword_frequency[str(k)] = 1

    return JDAnalysis(
        required_skills   = data.get("required_skills",  []),
        preferred_skills  = data.get("preferred_skills", []),
        key_keywords      = data.get("key_keywords",     []),
        responsibilities  = data.get("responsibilities", []),
        seniority_level   = data.get("seniority_level",  "mid"),
        domain_focus      = data.get("domain_focus",     ""),
        tone              = data.get("tone",              "formal"),
        keyword_frequency = keyword_frequency
    )


async def mirror_keywords(resume: dict, jd_analysis: JDAnalysis) -> Tuple[dict, List[str]]:
    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=0.2,
        api_key=settings.openai_api_key
    )

    original_summary = resume.get("summary", "")
    top_keywords = sorted(
        jd_analysis.keyword_frequency.items(),
        key=lambda x: -x[1]
    )[:8]
    top_keyword_list = [k for k, _ in top_keywords]

    summary_prompt = (
        "Rewrite this professional summary to naturally include the following keywords "
        "where they fit. Keep all facts identical. Do not add skills or experience "
        "that is not implied by the original. Do not make it longer than the original. "
        "Return ONLY the rewritten summary.\n\n"
        f"ORIGINAL SUMMARY: {original_summary}\n\n"
        f"KEYWORDS TO WEAVE IN: {', '.join(top_keyword_list)}\n\n"
        f"ROLE APPLYING FOR: {jd_analysis.domain_focus} ({jd_analysis.seniority_level})"
    )

    summary_response = await llm.ainvoke(summary_prompt)
    new_summary      = summary_response.content.strip()

    keywords_added = [
        kw for kw in top_keyword_list
        if kw.lower() in new_summary.lower()
        and kw.lower() not in original_summary.lower()
    ]

    current_skills   = resume.get("skills", [])
    jd_skills        = jd_analysis.required_skills + jd_analysis.preferred_skills
    jd_skills_lower  = [s.lower() for s in jd_skills]
    priority_skills  = [s for s in current_skills if s.lower() in jd_skills_lower]
    other_skills     = [s for s in current_skills if s.lower() not in jd_skills_lower]
    reordered_skills = priority_skills + other_skills

    updated_resume = dict(resume)
    updated_resume["summary"] = new_summary
    updated_resume["skills"]  = reordered_skills

    return updated_resume, keywords_added


async def rewrite_bullets(
    resume: dict,
    jd_analysis: JDAnalysis,
    job: dict
) -> Tuple[dict, List[BulletRewrite]]:

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=0.3,
        api_key=settings.openai_api_key
    )

    updated_experience = []
    all_rewrites       = []

    for exp in resume.get("experience", []):
        bullets           = exp.get("bullets", [])
        rewritten_bullets = list(bullets)
        role_rewrites     = []

        relevance_scores = _score_bullets_for_relevance(bullets, jd_analysis)
        top_3_indices    = sorted(
            range(len(bullets)),
            key=lambda i: -relevance_scores[i]
        )[:3]

        for idx in top_3_indices:
            original_bullet = bullets[idx]

            prompt = (
                "Rewrite this resume bullet to better match a job description.\n\n"
                "RULES:\n"
                "1. Keep ALL metrics from the original\n"
                "2. Keep ALL technologies from the original\n"
                "3. Use stronger action verbs if original is weak\n"
                "4. Weave in 1-2 JD keywords naturally\n"
                "5. Keep same length as original\n"
                "6. Return ONLY the rewritten bullet\n\n"
                f"ORIGINAL BULLET: {original_bullet}\n\n"
                f"JD DOMAIN FOCUS: {jd_analysis.domain_focus}\n"
                f"JD KEY KEYWORDS: {', '.join(jd_analysis.key_keywords[:6])}\n"
                f"ROLE: {exp.get('role')} at {exp.get('company')}"
            )

            response         = await llm.ainvoke(prompt)
            rewritten_bullet = response.content.strip()

            if rewritten_bullet != original_bullet:
                rewritten_bullets[idx] = rewritten_bullet
                kw_added = [
                    kw for kw in jd_analysis.key_keywords
                    if kw.lower() in rewritten_bullet.lower()
                    and kw.lower() not in original_bullet.lower()
                ]
                role_rewrites.append(BulletRewrite(
                    role           = exp.get("role", ""),
                    company        = exp.get("company", ""),
                    original       = original_bullet,
                    tailored       = rewritten_bullet,
                    keywords_added = kw_added,
                    reason         = f"Aligned with JD focus: {jd_analysis.domain_focus}"
                ))

        updated_exp = dict(exp)
        updated_exp["bullets"] = rewritten_bullets
        updated_experience.append(updated_exp)
        all_rewrites.extend(role_rewrites)

    updated_resume = dict(resume)
    updated_resume["experience"] = updated_experience
    return updated_resume, all_rewrites


def _score_bullets_for_relevance(bullets: List[str], jd: JDAnalysis) -> List[float]:
    scores    = []
    all_jd_kw = [k.lower() for k in (
        jd.required_skills + jd.preferred_skills + jd.key_keywords
    )]
    for bullet in bullets:
        bullet_lower = bullet.lower()
        matches      = sum(1 for kw in all_jd_kw if kw in bullet_lower)
        score        = min(matches / max(len(all_jd_kw), 1), 1.0)
        scores.append(score)
    return scores


async def score_against_jd(
    tailored_resume: dict,
    job: dict,
    jd_analysis: JDAnalysis
) -> Tuple[float, dict, List[str]]:

    resume_text = _resume_to_plain_text(tailored_resume).lower()

    required  = jd_analysis.required_skills
    req_found = [s for s in required if s.lower() in resume_text]
    req_score = (len(req_found) / max(len(required), 1)) * 35

    keywords = jd_analysis.key_keywords
    kw_found = [k for k in keywords if k.lower() in resume_text]
    kw_score = (len(kw_found) / max(len(keywords), 1)) * 25

    seniority_map   = {"junior": 1, "mid": 3, "senior": 5, "lead": 8}
    required_years  = seniority_map.get(jd_analysis.seniority_level, 3)
    exp_count       = len(tailored_resume.get("experience", []))
    estimated_years = exp_count * 1.5
    sen_score       = min((estimated_years / required_years), 1.0) * 15

    domain_words = jd_analysis.domain_focus.lower().split()
    domain_found = sum(1 for w in domain_words if w in resume_text)
    dom_score    = (domain_found / max(len(domain_words), 1)) * 15

    preferred  = jd_analysis.preferred_skills
    pref_found = [s for s in preferred if s.lower() in resume_text]
    pref_score = (len(pref_found) / max(len(preferred), 1)) * 10

    total = round(req_score + kw_score + sen_score + dom_score + pref_score, 1)

    breakdown = {
        "required_skills_coverage": {
            "score":   round(req_score, 1),
            "max":     35,
            "found":   req_found,
            "missing": [s for s in required if s.lower() not in resume_text]
        },
        "keyword_match": {
            "score":   round(kw_score, 1),
            "max":     25,
            "found":   kw_found,
            "missing": [k for k in keywords if k.lower() not in resume_text]
        },
        "seniority_alignment": {
            "score":          round(sen_score, 1),
            "max":            15,
            "required_level": jd_analysis.seniority_level
        },
        "domain_relevance": {
            "score":  round(dom_score, 1),
            "max":    15,
            "domain": jd_analysis.domain_focus
        },
        "preferred_skills_coverage": {
            "score": round(pref_score, 1),
            "max":   10,
            "found": pref_found
        }
    }

    keywords_missed = [
        k for k in (required + keywords)
        if k.lower() not in resume_text
    ]

    return total, breakdown, keywords_missed


async def generate_cover_letter(
    resume: dict,
    job: dict,
    jd_analysis: JDAnalysis,
    tone: str = "professional"
) -> str:

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=0.5,
        api_key=settings.openai_api_key
    )

    tone_map = {
        "professional": "Formal and structured. Traditional business letter tone.",
        "startup":      "Conversational and energetic. Show genuine excitement.",
        "concise":      "3 very short paragraphs. Maximum 60 words each."
    }

    top_achievements = []
    for exp in resume.get("experience", [])[:2]:
        for bullet in exp.get("bullets", [])[:2]:
            top_achievements.append(
                f"{exp.get('role')} at {exp.get('company')}: {bullet}"
            )

    achievements_text = "\n".join(f"- {a}" for a in top_achievements)

    prompt = (
        f"Write a cover letter for this job application.\n\n"
        f"TONE: {tone_map.get(tone, tone_map['professional'])}\n\n"
        "STRUCTURE:\n"
        "Paragraph 1: Why this company, state the position, one sentence on fit\n"
        "Paragraph 2: 2-3 specific achievements matching JD requirements\n"
        "Paragraph 3: Interest + call to action\n\n"
        f"APPLICANT: {resume.get('name', 'Applicant')}\n"
        f"ROLE: {job.get('title')} at {job.get('company')}\n"
        f"JD FOCUS: {jd_analysis.domain_focus}\n"
        f"REQUIRED SKILLS: {', '.join(jd_analysis.required_skills[:6])}\n\n"
        f"ACHIEVEMENTS:\n{achievements_text}\n\n"
        "Return ONLY the cover letter text."
    )

    response = await llm.ainvoke(prompt)
    return response.content.strip()


def _resume_to_plain_text(resume: dict) -> str:
    lines = []
    if resume.get("summary"):
        lines.append(resume["summary"])
    if resume.get("skills"):
        lines.append(" ".join(resume["skills"]))
    for exp in resume.get("experience", []):
        lines.append(f"{exp.get('role', '')} {exp.get('company', '')}")
        lines.extend(exp.get("bullets", []))
        if exp.get("tech_used"):
            lines.append(" ".join(exp["tech_used"]))
    for edu in resume.get("education", []):
        lines.append(f"{edu.get('degree', '')} {edu.get('institution', '')}")
    return " ".join(lines)