# backend/agents/optimizer.py
"""
LangGraph Resume Optimizer Agent with Human-in-the-Loop (HITL).

Flow:
  start_optimization()
      └── analyze_node   → finds weak bullets
      └── rewrite_node   → rewrites bullets
      └── PAUSE ──────── returns diff to frontend for user review
                         frontend shows highlighted changes + new ATS score
                         user clicks Accept / Edit / Reject

  resume_optimization()
      └── applies user edits (if any)
      └── score_node     → re-scores the resume
      └── if score >= 80 or iteration >= 3 → END
      └── else → loop back to analyze_node
"""

import json
import re
from typing import TypedDict, List, Annotated, Optional
import operator

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from models.resume import ResumeData
from prompts.optimizer_prompts import (
    ANALYZE_SYSTEM_PROMPT,
    REWRITE_SYSTEM_PROMPT,
    SCORE_SYSTEM_PROMPT
)
from utils.diff_utils import compute_full_resume_diff
from api.config import get_settings

settings = get_settings()

MAX_ITERATIONS = 3
ATS_TARGET_SCORE = 80


# ── State ─────────────────────────────────────────────────────────────────────

class OptimizerState(TypedDict):
    """
    The shared memory passed between every node in the graph.
    Persisted to Redis between pause and resume steps.
    """
    original_resume: dict        # never modified — preserved for final diff
    current_resume: dict         # updated after each rewrite
    pending_resume: dict         # rewritten version waiting for user approval
    suggestions: List[str]       # all suggestions accumulated across iterations
    iteration: int               # current loop count (max = MAX_ITERATIONS)
    approved: bool               # True when user approves OR score >= target
    finished: bool               # True when full optimization is complete
    history: List[dict]          # full log of every change per iteration
    diff: Optional[dict]         # current diff shown to user (populated at pause)
    score_data: Optional[dict]   # latest score breakdown


# ── LLM helpers ───────────────────────────────────────────────────────────────

def get_llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=temperature,
        api_key=settings.openai_api_key
    )


def parse_json_response(content: str) -> dict | list:
    """Strip markdown fences and parse JSON from LLM response."""
    content = content.strip()
    content = re.sub(r"^```(?:json)?\n?", "", content)
    content = re.sub(r"\n?```$", "", content)
    return json.loads(content)


# ── Node 1: Analyze ───────────────────────────────────────────────────────────

async def analyze_node(state: OptimizerState) -> dict:
    """
    Reads current_resume and finds all weak bullets.
    Does NOT modify the resume — diagnosis only.
    Returns a list of specific, actionable suggestions.
    """
    llm = get_llm()

    # Format experience into readable text
    experience_text = ""
    for exp in state["current_resume"].get("experience", []):
        experience_text += f"\n\n{exp['role']} at {exp['company']}:\n"
        for bullet in exp.get("bullets", []):
            experience_text += f"  - {bullet}\n"

    summary = state["current_resume"].get("summary", "No summary provided.")

    messages = [
        SystemMessage(content=ANALYZE_SYSTEM_PROMPT),
        HumanMessage(content=f"Summary:\n{summary}\n\nExperience:{experience_text}")
    ]

    response = await llm.ainvoke(messages)
    suggestions_raw = parse_json_response(response.content)

    # Convert to readable strings for state storage
    suggestions = [
        f"[{s['location']}] {s['issue']} → {s['suggestion']}"
        for s in suggestions_raw
    ]

    return {
        "suggestions": suggestions,
        "history": [{
            "iteration": state["iteration"] + 1,
            "phase": "analyze",
            "findings_count": len(suggestions),
            "findings": suggestions_raw
        }]
    }


# ── Node 2: Rewrite ───────────────────────────────────────────────────────────

async def rewrite_node(state: OptimizerState) -> dict:
    """
    Rewrites bullets based on suggestions from analyze_node.
    Stores result in pending_resume — NOT current_resume yet.
    The user must approve before pending becomes current.
    """
    llm = get_llm(temperature=0.3)  # slight creativity for better rewrites

    # Use only the latest batch of suggestions to stay focused
    recent_suggestions = state["suggestions"][-10:]

    messages = [
        SystemMessage(content=REWRITE_SYSTEM_PROMPT),
        HumanMessage(content=f"""Apply these suggestions:

SUGGESTIONS:
{json.dumps(recent_suggestions, indent=2)}

CURRENT EXPERIENCE:
{json.dumps(state["current_resume"].get("experience", []), indent=2)}

CURRENT SUMMARY:
{state["current_resume"].get("summary", "")}""")
    ]

    response = await llm.ainvoke(messages)
    rewrite_data = parse_json_response(response.content)

    # Build the pending resume with rewritten bullets
    pending_resume = dict(state["current_resume"])

    # Map rewrites: "role|company" → new bullets
    rewrite_map = {
        f"{e['role']}|{e['company']}": e["rewritten_bullets"]
        for e in rewrite_data.get("updated_experience", [])
    }

    updated_experience = []
    for exp in pending_resume.get("experience", []):
        key = f"{exp['role']}|{exp['company']}"
        updated_exp = dict(exp)
        if key in rewrite_map:
            updated_exp["bullets"] = rewrite_map[key]
        updated_experience.append(updated_exp)

    pending_resume["experience"] = updated_experience

    if rewrite_data.get("updated_summary"):
        pending_resume["summary"] = rewrite_data["updated_summary"]

    # Compute diff between current (approved) and pending (awaiting approval)
    diff = compute_full_resume_diff(state["current_resume"], pending_resume)

    return {
        "pending_resume": pending_resume,
        "diff": diff,
        "history": [{
            "iteration": state["iteration"] + 1,
            "phase": "rewrite",
            "bullets_rewritten": sum(
                e["bullets_changed"] for e in diff["experience_diffs"]
            )
        }]
    }


# ── Node 3: Score ─────────────────────────────────────────────────────────────

async def score_node(state: OptimizerState) -> dict:
    """
    Scores the current_resume (which has been approved by the user).
    Decides whether to loop or finish.
    """
    llm = get_llm()

    messages = [
        SystemMessage(content=SCORE_SYSTEM_PROMPT),
        HumanMessage(content=json.dumps(state["current_resume"], indent=2))
    ]

    response = await llm.ainvoke(messages)
    score_data = parse_json_response(response.content)

    new_score = score_data.get("ats_score", 0)
    max_reached = state["iteration"] >= MAX_ITERATIONS
    score_reached = new_score >= ATS_TARGET_SCORE

    # Update current_resume with new score + gaps + strengths
    updated_resume = dict(state["current_resume"])
    updated_resume["ats_score"] = new_score
    updated_resume["gaps"] = score_data.get("gaps", [])
    updated_resume["strengths"] = score_data.get("strengths", [])

    finished = score_reached or max_reached

    return {
        "current_resume": updated_resume,
        "finished": finished,
        "score_data": score_data,
        "history": [{
            "iteration": state["iteration"],
            "phase": "score",
            "ats_score": new_score,
            "finished": finished,
            "stop_reason": "score >= 80" if score_reached
                           else "max iterations reached" if max_reached
                           else "continuing",
            "score_breakdown": score_data.get("score_breakdown", {})
        }]
    }


# ── Public API ─────────────────────────────────────────────────────────────────

async def start_optimization(resume: ResumeData) -> dict:
    """
    STEP 1 — Called by POST /api/resume/optimize/start

    Runs analyze + rewrite, then PAUSES.
    Returns the diff for the user to review in the frontend.

    Returns:
    {
      "session_id": "uuid",
      "iteration": 1,
      "diff": { summary_diff, experience_diffs, ... },
      "original_ats_score": 58,
      "pending_resume": { ...rewritten resume... },
      "suggestions": [ ...list of issues found... ],
      "status": "awaiting_review"
    }
    """
    resume_dict = resume.model_dump()

    state: OptimizerState = {
        "original_resume": resume_dict,
        "current_resume": resume_dict,
        "pending_resume": {},
        "suggestions": [],
        "iteration": 0,
        "approved": False,
        "finished": False,
        "history": [],
        "diff": None,
        "score_data": None
    }

    # Run analyze → rewrite (pauses here — does NOT run score yet)
    state.update(await analyze_node(state))
    state.update(await rewrite_node(state))

    # Save full state to Redis — returns session_id
    from utils.session_store import save_session
    session_id = await save_session(state)

    return {
        "session_id": session_id,
        "iteration": state["iteration"] + 1,
        "diff": state["diff"],
        "original_ats_score": resume_dict.get("ats_score", 0),
        "pending_resume": state["pending_resume"],
        "suggestions": state["suggestions"],
        "status": "awaiting_review"
    }


async def resume_optimization(session_id: str, user_decision: dict) -> dict:
    """
    STEP 2 — Called by POST /api/resume/optimize/review

    Applies the user's decision and either:
    - Runs score → loops back to analyze+rewrite (returns next diff)
    - Runs score → finishes (returns final result)

    user_decision format:
    {
      "action": "approve" | "approve_with_edits" | "reject",
      "edited_resume": { ...ResumeData if action is approve_with_edits... }
    }

    Returns either:
    - { "status": "awaiting_review", "diff": ..., "session_id": ... }  (loop continues)
    - { "status": "complete", "optimized_resume": ..., "score_improvement": ... }
    """
    from utils.session_store import get_session, update_session, delete_session

    state = await get_session(session_id)
    if state is None:
        raise ValueError("Session expired or not found. Please start a new optimization.")

    action = user_decision.get("action", "approve")

    if action == "reject":
        # User rejected — keep current_resume unchanged, mark finished
        await delete_session(session_id)
        return {
            "status": "complete",
            "optimized_resume": state["current_resume"],
            "original_ats_score": state["original_resume"].get("ats_score", 0),
            "final_ats_score": state["current_resume"].get("ats_score", 0),
            "score_improvement": 0,
            "iterations_run": state["iteration"],
            "message": "Optimization rejected by user. Original resume kept.",
            "history": state["history"]
        }

    elif action == "approve_with_edits":
        # User made manual edits — use their edited version as current
        edited = user_decision.get("edited_resume", state["pending_resume"])
        state["current_resume"] = edited

    else:
        # action == "approve" — accept the pending rewritten resume as-is
        state["current_resume"] = state["pending_resume"]

    state["iteration"] += 1

    # Run score on the now-approved resume
    score_result = await score_node(state)
    state.update(score_result)

    if state["finished"]:
        # Optimization complete — clean up and return final result
        await delete_session(session_id)

        original_score = state["original_resume"].get("ats_score", 0)
        final_score = state["current_resume"].get("ats_score", 0)

        return {
            "status": "complete",
            "optimized_resume": state["current_resume"],
            "original_ats_score": original_score,
            "final_ats_score": final_score,
            "score_improvement": final_score - original_score,
            "iterations_run": state["iteration"],
            "diff_summary": compute_full_resume_diff(
                state["original_resume"],
                state["current_resume"]
            ),
            "history": state["history"]
        }

    else:
        # Score not high enough — run another analyze+rewrite cycle
        analyze_result = await analyze_node(state)
        state.update(analyze_result)

        rewrite_result = await rewrite_node(state)
        state.update(rewrite_result)

        # Save updated state back to Redis (same session_id)
        await update_session(session_id, state)

        return {
            "session_id": session_id,
            "iteration": state["iteration"] + 1,
            "diff": state["diff"],
            "current_ats_score": state["current_resume"].get("ats_score", 0),
            "pending_resume": state["pending_resume"],
            "suggestions": state["suggestions"][-5:],  # latest 5 only
            "status": "awaiting_review"
        }


async def get_session_status(session_id: str) -> dict:
    """
    Called by GET /api/resume/optimize/{session_id}
    Returns current state of an in-progress optimization session.
    """
    from utils.session_store import get_session
    state = await get_session(session_id)
    if state is None:
        raise ValueError("Session not found or expired.")

    return {
        "session_id": session_id,
        "iteration": state["iteration"],
        "status": "awaiting_review" if not state["finished"] else "complete",
        "current_ats_score": state["current_resume"].get("ats_score", 0),
        "original_ats_score": state["original_resume"].get("ats_score", 0),
        "diff": state.get("diff")
    }
