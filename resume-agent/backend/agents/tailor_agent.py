# backend/agents/tailor_agent.py
"""
Phase 4 — LangGraph Resume Tailor Agent.

Graph structure (fixed sequence, no loops):

  START
    │
    ▼
  analyze_jd_node          ← reads JD, extracts structured intelligence
    │
    ▼
  mirror_keywords_node     ← injects JD keywords into summary + reorders skills
    │
    ▼
  rewrite_bullets_node     ← rewrites top 3 bullets per role to match JD
    │
    ▼
  score_against_jd_node    ← scores tailored resume vs JD specifically
    │
    ▼
  ⏸ PAUSE (human review)  ← shows diff, waits for approve/reject
    │
    ▼ (on approve)
  cover_letter_node        ← generates cover letter IF options.generate_cover_letter=True
    │                         SKIPPED if option is False
    ▼
  END

Unlike Phase 2's loop (which iterates until score >= 80),
Phase 4 runs exactly ONCE. One tailoring pass is enough because
we're targeting a specific job, not doing generic improvement.

The human pause happens AFTER all tailoring — you see the full diff
and decide to approve the whole thing, not step-by-step.
"""

import json
import uuid
from typing import TypedDict, Optional, List, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.checkpoint.memory import MemorySaver

from models.tailor import TailorState, TailorOptions, JDAnalysis, BulletRewrite
from tools.tailor_tools import (
    analyse_jd,
    mirror_keywords,
    rewrite_bullets,
    score_against_jd,
    generate_cover_letter,
    _resume_to_plain_text
)
from utils.diff_utils import build_resume_diff
from api.config import get_settings

settings = get_settings()


# ── State Type for LangGraph ──────────────────────────────────────────────────
# LangGraph needs a TypedDict (not Pydantic) for its internal state management.
# We keep TailorState as Pydantic for validation, and convert here.

class GraphState(TypedDict):
    original_resume:  dict
    job:              dict
    options:          dict              # TailorOptions as dict
    jd_analysis:      Optional[dict]   # JDAnalysis as dict
    tailored_resume:  Optional[dict]
    bullet_rewrites:  List[dict]        # List[BulletRewrite] as dicts
    keywords_added:   List[str]
    keywords_missed:  List[str]
    jd_ats_score:     Optional[float]
    jd_ats_breakdown: Optional[dict]
    cover_letter:     Optional[str]
    diff:             Optional[dict]
    approved:         bool
    finished:         bool


# ── Node 1: analyze_jd_node ───────────────────────────────────────────────────

async def analyze_jd_node(state: GraphState) -> GraphState:
    """
    NODE 1 — Read the job description deeply.

    Reads from state:  job (the full JobListing dict)
    Writes to state:   jd_analysis (structured JD intelligence)

    This node runs FIRST and its output is used by ALL other nodes.
    The JD analysis is the "briefing document" for the entire tailoring session.

    What GPT-4o does here:
    - Identifies required vs preferred skills
    - Counts keyword frequency (how often each term appears)
    - Determines seniority level from language cues
    - Identifies domain focus (what this role ACTUALLY does day-to-day)
    - Reads the company tone (startup energy vs corporate formality)
    """
    print("[Tailor] Node 1: Analysing job description...")

    try:
        jd_analysis = await analyse_jd(state["job"])
        print(f"[Tailor] Node 1 complete: {jd_analysis}")
        return {
            **state,
            "jd_analysis": jd_analysis.model_dump()
        }
    except Exception as e:
        import traceback
        print(f"[Tailor] Node 1 FAILED:")
        traceback.print_exc()
        raise


# ── Node 2: mirror_keywords_node ─────────────────────────────────────────────

async def mirror_keywords_node(state: GraphState) -> GraphState:
    """
    NODE 2 — Mirror JD language into the resume summary and reorder skills.

    Reads from state:  original_resume, jd_analysis
    Writes to state:   tailored_resume (first version), keywords_added

    Two sub-steps:
    A. Rewrite the professional summary to naturally include top JD keywords
    B. Move JD-matching skills to the front of the skills list

    IMPORTANT: tailored_resume starts as a COPY of original_resume here.
    Later nodes (rewrite_bullets) receive this copy and modify it further.
    The original_resume in state is NEVER touched.

    Example:
    Before: skills = ["React", "Node.js", "Python", "FastAPI", "AWS"]
    JD wants: Python, FastAPI, AWS (in that order by frequency)
    After:  skills = ["Python", "FastAPI", "AWS", "React", "Node.js"]
    """
    print("[Tailor] Node 2: Mirroring keywords and reordering skills...")

    jd_analysis    = jd_analysis = JDAnalysis.model_validate(state["jd_analysis"])
    resume_to_use  = state.get("tailored_resume") or state["original_resume"]

    updated_resume, keywords_added = await mirror_keywords(resume_to_use, jd_analysis)

    return {
        **state,
        "tailored_resume": updated_resume,
        "keywords_added":  keywords_added
    }


# ── Node 3: rewrite_bullets_node ─────────────────────────────────────────────

async def rewrite_bullets_node(state: GraphState) -> GraphState:
    """
    NODE 3 — Rewrite experience bullets to match JD language.

    Reads from state:  tailored_resume (from node 2), jd_analysis, job
    Writes to state:   tailored_resume (updated), bullet_rewrites

    How it decides WHICH bullets to rewrite:
    - Scores every bullet for JD keyword overlap (pure Python, no LLM)
    - Takes the top 3 most-relevant bullets per role
    - Rewrites only those — leaves other bullets unchanged
    - Keeps rewrites if they improved the bullet, discards if unchanged

    Why only top 3 per role?
    - Rewriting every bullet looks unnatural and suspicious to human reviewers
    - Top 3 gives meaningful coverage without over-tailoring
    - The other bullets are still good from Phase 2 optimisation

    The bullet_rewrites list is stored for the diff display in the frontend —
    it lets you see exactly which bullets changed and why.
    """
    print("[Tailor] Node 3: Rewriting experience bullets...")

    jd_analysis    = jd_analysis = JDAnalysis.model_validate(state["jd_analysis"])
    resume_to_use  = state["tailored_resume"]

    updated_resume, rewrites = await rewrite_bullets(
        resume_to_use,
        jd_analysis,
        state["job"]
    )

    # Merge keywords from bullet rewrites into the keywords_added list
    bullet_keywords = []
    for r in rewrites:
        bullet_keywords.extend(r.keywords_added)

    all_keywords_added = list(set(
        state.get("keywords_added", []) + bullet_keywords
    ))

    return {
        **state,
        "tailored_resume":  updated_resume,
        "bullet_rewrites":  [
    {
        "role":           r.role,
        "company":        r.company,
        "original":       r.original,
        "tailored":       r.tailored,
        "keywords_added": list(r.keywords_added),  # ensure it's a plain list
        "reason":         r.reason
    }
    for r in rewrites
],
        "keywords_added":   all_keywords_added
    }


# ── Node 4: score_against_jd_node ────────────────────────────────────────────

async def score_against_jd_node(state: GraphState) -> GraphState:
    """
    NODE 4 — Score the fully tailored resume against THIS specific job.

    Reads from state:  tailored_resume, job, jd_analysis
    Writes to state:   jd_ats_score, jd_ats_breakdown, keywords_missed, diff

    Scoring is pure Python maths — no LLM needed.
    5 categories scored independently, then summed to 100.

    Also builds the DIFF at this stage — compares original_resume vs
    tailored_resume word-by-word across every text field.
    The diff is what the frontend renders in the review screen.

    After this node the graph PAUSES — session saved to Redis,
    response returned to frontend with the diff and score.
    User reviews changes and clicks Approve or Reject.
    """
    print("[Tailor] Node 4: Scoring tailored resume against JD...")

    jd_analysis      = jd_analysis = JDAnalysis.model_validate(state["jd_analysis"])
    tailored_resume  = state["tailored_resume"]
    original_resume  = state["original_resume"]

    score, breakdown, missed = await score_against_jd(
        tailored_resume,
        state["job"],
        jd_analysis
    )

    # Build word-level diff between original and tailored
    diff = build_resume_diff(original_resume, tailored_resume)

    return {
        **state,
        "jd_ats_score":    score,
        "jd_ats_breakdown": breakdown,
        "keywords_missed": missed,
        "diff":            diff,
        "finished":        False   # stays False until user approves
    }


# ── Node 5: cover_letter_node ─────────────────────────────────────────────────

async def cover_letter_node(state: GraphState) -> GraphState:
    """
    NODE 5 — Generate cover letter (OPTIONAL).

    Reads from state:  tailored_resume, job, jd_analysis, options
    Writes to state:   cover_letter, finished=True

    Only runs if options.generate_cover_letter == True.
    If False, this node is SKIPPED via the conditional edge.

    Runs AFTER human approval — because the cover letter uses the
    approved tailored resume as its source of evidence/achievements.
    Writing it before approval would mean it might reference
    unapproved bullet rewrites.
    """
    
    # Should never reach here due to conditional edge,
        # but defensive check just in case
        
    options = state.get("options", {})
    generate_cl = options.get("generate_cover_letter") if isinstance(options, dict) else options.generate_cover_letter
    if not generate_cl:
        return {**state, "cover_letter": None, "finished": True}

    print("[Tailor] Node 5: Generating cover letter...")

    jd_analysis = JDAnalysis.model_validate(state["jd_analysis"])
    
    letter      = await generate_cover_letter(
        state["tailored_resume"],
        state["job"],
        jd_analysis
    )

    return {
        **state,
        "cover_letter": letter,
        "finished":     True
    }


# ── Conditional Edge ──────────────────────────────────────────────────────────

def should_generate_cover_letter(state: GraphState) -> str:
    """
    After score_node + human approval:
    - If options.generate_cover_letter=True  → go to cover_letter_node
    - If options.generate_cover_letter=False → go straight to END
    """
    options = state.get("options", {})
    if isinstance(options, dict):
        return "generate_cover_letter" if options.get("generate_cover_letter") else END
    return "generate_cover_letter" if options.generate_cover_letter else END


# ── Graph Builder ─────────────────────────────────────────────────────────────

def build_tailor_graph():
    """
    Assembles the LangGraph and returns a compiled graph with Redis checkpointing.

    The interrupt_before=["cover_letter_node"] is NOT used here —
    instead we pause manually by checking state after score_node
    and saving to Redis. The resume is returned to the user for review
    at that point. When they approve, the graph resumes from cover_letter_node
    (or END if no cover letter needed).

    Actually we pause AFTER score_against_jd_node.
    In this graph, the interrupt is:
      interrupt_after=["score_against_jd_node"]
    This tells LangGraph to stop after that node and wait for .resume()
    """
    graph = StateGraph(GraphState)

    # Register all nodes
    graph.add_node("analyze_jd",        analyze_jd_node)
    graph.add_node("mirror_keywords",   mirror_keywords_node)
    graph.add_node("rewrite_bullets",   rewrite_bullets_node)
    graph.add_node("score_against_jd",  score_against_jd_node)
    graph.add_node("generate_cover_letter",      cover_letter_node)

    # Fixed edges — always run in this order
    graph.set_entry_point("analyze_jd")
    graph.add_edge("analyze_jd",       "mirror_keywords")
    graph.add_edge("mirror_keywords",  "rewrite_bullets")
    graph.add_edge("rewrite_bullets",  "score_against_jd")

    # After score_against_jd → conditional: cover letter or END
    graph.add_conditional_edges(
        "score_against_jd",
        should_generate_cover_letter,
        {
            "generate_cover_letter": "generate_cover_letter",
            END:            END
        }
    )
    graph.add_edge("generate_cover_letter", END)

    # Compile with Redis checkpointer so state survives the PAUSE
    # checkpointer = AsyncRedisSaver.from_conn_string(settings.redis_url)
    checkpointer = MemorySaver()
    
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_after=["score_against_jd"]  # PAUSE here for human review
    )


# Compile once at module load
tailor_graph = build_tailor_graph()


# ── Public Interface ──────────────────────────────────────────────────────────

async def start_tailoring(request) -> dict:
    """
    Starts the tailoring graph. Runs nodes 1-4, then PAUSES.
    Returns session_id and the full diff + score for user review.
    Called by POST /api/tailor/resume
    """
    session_id = str(uuid.uuid4())

    initial_state: GraphState = {
        "original_resume":  request.resume,
        "job":              request.job,
        "options":          request.options.model_dump(),
        "jd_analysis":      None,
        "tailored_resume":  None,
        "bullet_rewrites":  [],
        "keywords_added":   [],
        "keywords_missed":  [],
        "jd_ats_score":     None,
        "jd_ats_breakdown": None,
        "cover_letter":     None,
        "diff":             None,
        "approved":         False,
        "finished":         False
    }

    # thread_id is how LangGraph identifies this session in Redis checkpoints
    config = {"configurable": {"thread_id": session_id}}

    # Run graph — will stop after score_against_jd due to interrupt_after
    await tailor_graph.ainvoke(initial_state, config=config)

    # Load the state as it was when the graph paused
    saved_state = (await tailor_graph.aget_state(config)).values

    return {
        "session_id":       session_id,
        "status":           "awaiting_review",
        "tailored_resume":  saved_state["tailored_resume"],
        "original_resume":  saved_state["original_resume"],
        "diff":             saved_state["diff"],
        "jd_ats_score":     saved_state["jd_ats_score"],
        "jd_ats_breakdown": saved_state["jd_ats_breakdown"],
        "generic_ats_score": request.resume.get("ats_score", 0),
        "keywords_added":   saved_state["keywords_added"],
        "keywords_missed":  saved_state["keywords_missed"],
        "bullet_rewrites":  saved_state["bullet_rewrites"],
        "cover_letter":     None  # not generated yet
    }


async def approve_tailoring(session_id: str) -> dict:
    """
    Called when user clicks APPROVE on the review screen.
    Resumes the graph from after score_against_jd.
    If cover_letter option is True → runs cover_letter_node then END.
    If cover_letter option is False → goes straight to END.
    Called by POST /api/tailor/review?action=approve
    """
    config = {"configurable": {"thread_id": session_id}}

    # Update approved flag in state
    await tailor_graph.aupdate_state(
        config,
        {"approved": True},
        as_node="score_against_jd"
    )

    # Resume from where it paused (after score_against_jd)
    await tailor_graph.ainvoke(None, config=config)

    # Load final state
    final_state = (await tailor_graph.aget_state(config)).values

    return {
        "session_id":       session_id,
        "status":           "complete",
        "tailored_resume":  final_state["tailored_resume"],
        "original_resume":  final_state["original_resume"],
        "diff":             final_state["diff"],
        "jd_ats_score":     final_state["jd_ats_score"],
        "jd_ats_breakdown": final_state["jd_ats_breakdown"],
        "generic_ats_score": final_state["original_resume"].get("ats_score", 0),
        "keywords_added":   final_state["keywords_added"],
        "keywords_missed":  final_state["keywords_missed"],
        "bullet_rewrites":  final_state["bullet_rewrites"],
        "cover_letter":     final_state.get("cover_letter")
    }


async def reject_tailoring(session_id: str) -> dict:
    """
    Called when user clicks REJECT on the review screen.
    Deletes the session from Redis and returns the original unchanged resume.
    Called by POST /api/tailor/review?action=reject
    """
    config = {"configurable": {"thread_id": session_id}}

    # Load original resume before clearing
    saved_state = (await tailor_graph.aget_state(config)).values
    original    = saved_state.get("original_resume", {})

    # Mark finished so the session is cleanable
    await tailor_graph.aupdate_state(config, {"finished": True})

    return {
        "session_id":      session_id,
        "status":          "rejected",
        "original_resume": original,
        "message":         "Tailoring rejected. Original resume unchanged."
    }
