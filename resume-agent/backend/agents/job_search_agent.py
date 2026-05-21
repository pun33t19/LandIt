# backend/agents/job_search_agent.py
"""
LangChain Tool-Calling Agent for Job Search.

This agent coordinates 4 tools in sequence:
  1. search_jobs_tool     → hits JSearch API, gets raw listings
  2. filter_jobs_tool     → applies hard filters (salary, mode, stack)
  3. embed_and_rank_tool  → semantic matching via embeddings
  4. explain_matches_tool → GPT writes match explanation per job

Unlike Phase 2's LangGraph (fixed route), this agent DECIDES the order.
If search returns 0 results, it can retry with broader parameters automatically.
"""

import json
from typing import List
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tools.jsearch_tool import fetch_jobs_from_api, normalize_job
from tools.filter_tool import apply_filters, extract_skills_from_jd
from utils.embeddings import embed_text, cosine_similarity, match_score_to_label
from utils.cache import make_cache_key, get_cached_results, cache_results
from models.job import JobSearchFilters, JobSearchRequest
from api.config import get_settings

settings = get_settings()


# ── Tool Definitions ──────────────────────────────────────────────────────────
# Each @tool decorated function becomes a "button" the LLM can press.
# The docstring is what the LLM reads to understand what the tool does.

@tool
async def search_jobs_tool(query: str, location: str, country: str,
                           employment_type: str, work_mode: str,
                           date_posted: int, num_results: int) -> str:
    """
    Search for job listings using the JSearch API.
    Aggregates results from LinkedIn, Indeed, Glassdoor simultaneously.
    Returns a JSON string of raw job listings.
    Call this FIRST before any filtering or ranking.
    """
    filters = JobSearchFilters(
        query=query,
        location=location,
        country=country,
        employment_type=employment_type,
        work_mode=work_mode,
        date_posted=date_posted,
        num_results=num_results
    )

    raw_jobs = await fetch_jobs_from_api(filters)

    if not raw_jobs:
        return json.dumps({
            "status": "no_results",
            "message": "No jobs found. Try broader query or different location.",
            "jobs": []
        })

    # Normalise raw JSearch response to our clean format
    normalised = [normalize_job(job) for job in raw_jobs]

    return json.dumps({
        "status": "success",
        "count": len(normalised),
        "jobs": normalised
    })


@tool
async def filter_jobs_tool(jobs_json: str, filters_json: str) -> str:
    """
    Apply hard filters to a list of job listings.
    Filters: salary range, work mode, employment type, tech stack keywords.
    Call this AFTER search_jobs_tool and BEFORE embed_and_rank_tool.
    Input jobs_json: JSON string from search_jobs_tool output.
    Input filters_json: JSON string of filter parameters.
    Returns filtered list as JSON string.
    """
    jobs_data    = json.loads(jobs_json)
    filters_data = json.loads(filters_json)

    jobs = jobs_data.get("jobs", [])
    if not jobs:
        return json.dumps({"status": "no_jobs", "jobs": []})

    filters = JobSearchFilters(**filters_data)
    filtered = apply_filters(jobs, filters)

    return json.dumps({
        "status": "success",
        "original_count": len(jobs),
        "filtered_count": len(filtered),
        "jobs": filtered
    })


@tool
async def embed_and_rank_tool(resume_text: str, jobs_json: str,
                               resume_skills: str,
                               pre_filter_jobs_json: str = "{}") -> str:
    """
    Rank job listings by semantic similarity to the resume.
    If filtered jobs list is empty, falls back to pre-filter jobs automatically.
    Always returns ranked results — never an empty list.
    """
    data = json.loads(jobs_json)
    jobs = data.get("jobs", [])

    # ── FALLBACK: if filter removed everything, use pre-filter jobs ──────────
    if not jobs:
        pre_filter_data = json.loads(pre_filter_jobs_json)
        fallback_jobs   = pre_filter_data.get("jobs", [])

        if not fallback_jobs:
            return json.dumps({
                "status":   "no_results",
                "fallback": False,
                "jobs":     []
            })

        # Use the pre-filter jobs but mark them so UI can show a banner
        jobs          = fallback_jobs
        used_fallback = True
    else:
        used_fallback = False

    skills_list   = [s.strip() for s in resume_skills.split(",") if s.strip()]
    resume_vector = await embed_text(resume_text[:8000])

    ranked_jobs = []
    for job in jobs:
        jd_text   = f"{job['title']} {job['company']} {job['description']}"
        jd_vector = await embed_text(jd_text[:6000])

        similarity = cosine_similarity(resume_vector, jd_vector)
        score      = round(similarity * 100, 1)

        skill_analysis = extract_skills_from_jd(
            job.get("description", ""),
            skills_list
        )

        ranked_jobs.append({
            **job,
            "match_score":             score,
            "match_label":             match_score_to_label(score),
            "outside_filters":         used_fallback,  # ← flag for UI
            "skills_matched":          skill_analysis["skills_matched"],
            "skills_missing":          skill_analysis["skills_missing"],
            "skills_missing_priority": skill_analysis["skills_missing_priority"]
        })

    ranked_jobs.sort(key=lambda j: j["match_score"], reverse=True)

    return json.dumps({
        "status":   "success",
        "fallback": used_fallback,
        "count":    len(ranked_jobs),
        "jobs":     ranked_jobs
    })


@tool
async def explain_matches_tool(resume_json: str, top_jobs_json: str) -> str:
    """
    Generate a human-readable explanation of why each top job matches
    or doesn't match the resume. Also highlights key skill gaps.
    Call this LAST, only on the top 5 jobs after ranking.
    Input resume_json: full resume as JSON string.
    Input top_jobs_json: JSON string of top ranked jobs (max 5).
    Returns jobs with explanation field added, as JSON string.
    """
    resume    = json.loads(resume_json)
    jobs_data = json.loads(top_jobs_json)
    top_jobs  = jobs_data.get("jobs", [])[:5]  # enforce max 5

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=0,
        api_key=settings.openai_api_key
    )

    explained_jobs = []
    for job in top_jobs:
        prompt = f"""You are a career coach. Given this resume and job description,
write a 2-sentence explanation of why this is a {job['match_label']} ({job['match_score']}% match).
Mention specific matching skills, and if there are gaps, name them and suggest how to bridge them.
Be direct and specific. No fluff.

RESUME SKILLS: {", ".join(resume.get("skills", []))}
RESUME EXPERIENCE: {" | ".join(
    f"{e['role']} at {e['company']}"
    for e in resume.get("experience", [])
)}

JOB TITLE: {job['title']} at {job['company']}
JOB DESCRIPTION (first 800 chars): {job['description'][:800]}
SKILLS MATCHED: {", ".join(job['skills_matched'])}
SKILLS MISSING: {", ".join(job['skills_missing'][:5])}

Write ONLY the 2-sentence explanation. No labels, no JSON."""
 
        response = await llm.ainvoke(prompt)
        explained_jobs.append({
            **job,
            "match_explanation": response.content.strip()
        })

    return json.dumps({
        "status": "success",
        "jobs": explained_jobs
    })


# ── Agent System Prompt ───────────────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = """You are a Job Search Agent. Your job is to find and rank
the best matching jobs for a software engineer.

Follow this EXACT sequence every time:
1. Call search_jobs_tool with the provided query and filters
2. Call filter_jobs_tool with the results and filters
3. Call embed_and_rank_tool with the filtered jobs and resume text
4. Call explain_matches_tool with the TOP 5 ranked jobs only

If search returns 0 results, try ONE retry with a simpler query
(remove location, broaden the role name). If still 0, return empty results.

Do not skip any step. Do not call tools out of order."""


# ── Agent Builder ─────────────────────────────────────────────────────────────

def build_job_search_agent() -> AgentExecutor:
    """
    Builds and returns the LangChain tool-calling agent.
    Called once at startup — expensive to rebuild per request.
    """
    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=0,
        api_key=settings.openai_api_key
    )

    tools = [
        search_jobs_tool,
        filter_jobs_tool,
        embed_and_rank_tool,
        explain_matches_tool
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", AGENT_SYSTEM_PROMPT),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad")  # where tool calls/results go
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,        # logs each tool call to console — helpful during dev
        max_iterations=10,   # safety cap — prevents infinite loops
        return_intermediate_steps=False
    )


# Compile once at module load — reused for every search request
job_agent = build_job_search_agent()


# ── Public Interface ──────────────────────────────────────────────────────────

async def search_jobs(request: JobSearchRequest) -> dict:
    filters      = request.filters
    resume       = request.resume
    resume_text  = _resume_to_text(resume)
    resume_skills = resume.get("skills", [])

    # Cache check — unchanged
    cache_key = make_cache_key(filters.query, filters.model_dump())
    cached    = await get_cached_results(cache_key)
    if cached:
        cached["cached"] = True
        return cached

    # ── Step 1: Search ────────────────────────────────────────────────────────
    raw_jobs = await fetch_jobs_from_api(filters)

    # ── FALLBACK A: If API returns nothing, retry with broader query ──────────
    if not raw_jobs:
        broader_filters        = filters.model_copy()
        broader_filters.query  = _simplify_query(filters.query)  # strip extra words
        broader_filters.location = "remote"                       # open up location
        raw_jobs               = await fetch_jobs_from_api(broader_filters)

    # Still nothing after retry — return structured empty with message
    if not raw_jobs:
        return {
            "total_found":    0,
            "cache_id":       cache_key,
            "cached":         False,
            "search_query":   filters.query,
            "fallback_used":  False,
            "message":        "No jobs found even with broader search. Try a different role or location.",
            "results":        []
        }

    # Normalise raw API response
    normalised = [normalize_job(job) for job in raw_jobs]

    # ── Step 2: Filter ────────────────────────────────────────────────────────
    filtered = apply_filters(normalised, filters)

    # Save pre-filter jobs for fallback — in case filter removes everything
    pre_filter_jobs_json = json.dumps({"jobs": normalised})

    # ── FALLBACK B: If filter removed everything, note it — agent handles rest ─
    used_fallback = len(filtered) == 0
    jobs_for_ranking = filtered if filtered else normalised

    # ── Step 3: Embed + Rank ──────────────────────────────────────────────────
    ranked_raw = await embed_and_rank_tool.ainvoke({
        "resume_text":         resume_text[:8000],
        "jobs_json":           json.dumps({"jobs": jobs_for_ranking}),
        "resume_skills":       ", ".join(resume_skills),
        "pre_filter_jobs_json": pre_filter_jobs_json
    })
    ranked_data = json.loads(ranked_raw)
    ranked_jobs = ranked_data.get("jobs", [])

    # ── Step 4: Explain top 5 ────────────────────────────────────────────────
    explained_raw = await explain_matches_tool.ainvoke({
        "resume_json":   json.dumps(resume),
        "top_jobs_json": json.dumps({"jobs": ranked_jobs[:5]})
    })
    explained_data = json.loads(explained_raw)
    top_5_explained = explained_data.get("jobs", [])

    # Merge explanations back into full ranked list
    explained_ids = {j["job_id"]: j for j in top_5_explained}
    final_jobs = [
        explained_ids.get(j["job_id"], j)
        for j in ranked_jobs
    ]

    response = {
        "total_found":   len(final_jobs),
        "cache_id":      cache_key,
        "cached":        False,
        "search_query":  filters.query,

        # ← these two fields tell frontend what happened
        "fallback_used": used_fallback,
        "fallback_reason": (
            "No jobs matched your exact filters. "
            "Showing relevant jobs outside your filters, ranked by resume match."
            if used_fallback else None
        ),

        "results": final_jobs
    }

    if final_jobs:
        await cache_results(cache_key, response)

    return response


def _simplify_query(query: str) -> str:
    """
    Strips the query down to the core role for broader retry.
    "Senior Backend Engineer Python FastAPI" → "Backend Engineer"
    """
    # Remove seniority levels and tech keywords, keep role words
    noise = ["senior", "junior", "lead", "principal", "staff",
             "python", "fastapi", "node", "react", "aws", "remote"]
    words = [w for w in query.lower().split()
             if w not in noise]
    return " ".join(words[:3]) if words else query  # max 3 words


async def match_single_job(resume: dict, job: dict, explain: bool = True) -> dict:
    """
    Score and explain a single job against a resume.
    Called by POST /api/jobs/match for the "Tailor for this job" button.
    """
    resume_text   = _resume_to_text(resume)
    resume_skills = resume.get("skills", [])

    resume_vector = await embed_text(resume_text[:8000])
    jd_text       = f"{job.get('title','')} {job.get('company','')} {job.get('description','')}"
    jd_vector     = await embed_text(jd_text[:6000])

    similarity = cosine_similarity(resume_vector, jd_vector)
    score      = round(similarity * 100, 1)

    skill_analysis = extract_skills_from_jd(
        job.get("description", ""),
        resume_skills
    )

    result = {
        **job,
        "match_score":             score,
        "match_label":             match_score_to_label(score),
        "skills_matched":          skill_analysis["skills_matched"],
        "skills_missing":          skill_analysis["skills_missing"],
        "skills_missing_priority": skill_analysis["skills_missing_priority"],
        "match_explanation":       None
    }

    if explain:
        explained_raw = await explain_matches_tool.ainvoke({
            "resume_json":    json.dumps(resume),
            "top_jobs_json":  json.dumps({"jobs": [result]})
        })
        explained_data = json.loads(explained_raw)
        explained_jobs = explained_data.get("jobs", [result])
        if explained_jobs:
            result["match_explanation"] = explained_jobs[0].get("match_explanation")

    return result


def _resume_to_text(resume: dict) -> str:
    """
    Converts a ResumeData dict into a plain text string for embedding.
    Embeddings work on text — not JSON — so we flatten the structure.
    """
    lines = []

    if resume.get("summary"):
        lines.append(f"Summary: {resume['summary']}")

    if resume.get("skills"):
        lines.append(f"Skills: {', '.join(resume['skills'])}")

    for exp in resume.get("experience", []):
        lines.append(f"\n{exp.get('role','')} at {exp.get('company','')}")
        for bullet in exp.get("bullets", []):
            lines.append(f"  - {bullet}")
        if exp.get("tech_used"):
            lines.append(f"  Tech: {', '.join(exp['tech_used'])}")

    for edu in resume.get("education", []):
        lines.append(
            f"Education: {edu.get('degree','')} from {edu.get('institution','')}"
        )

    return "\n".join(lines)
