# backend/utils/diff_utils.py
"""
Computes human-readable diffs between original and rewritten resume bullets.
Used to show the user exactly what the agent changed — highlighted in the UI.
"""

import difflib
from typing import List, Dict

def compute_bullet_diff(original: str, rewritten: str) -> dict:
    """
    Compares two bullet strings word by word.
    Returns a structured diff the frontend can use to highlight changes.

    Returns:
    {
      "original": "original bullet text",
      "rewritten": "rewritten bullet text",
      "changed": True/False,
      "diff_tokens": [
        {"text": "word", "type": "equal|removed|added"}
      ]
    }
    """
    original_words = original.split()     
    rewritten_words = rewritten.split()

    matcher = difflib.SequenceMatcher(None, original_words, rewritten_words)
    tokens = []

    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == "equal":
            for word in original_words[i1:i2]:
                tokens.append({"text": word, "type": "equal"})
        elif opcode == "replace":
            for word in original_words[i1:i2]:
                tokens.append({"text": word, "type": "removed"})
            for word in rewritten_words[j1:j2]:
                tokens.append({"text": word, "type": "added"})
        elif opcode == "delete":
            for word in original_words[i1:i2]:
                tokens.append({"text": word, "type": "removed"})
        elif opcode == "insert":
            for word in rewritten_words[j1:j2]:
                tokens.append({"text": word, "type": "added"})

    changed = original.strip() != rewritten.strip()

    return {
        "original": original,
        "rewritten": rewritten,
        "changed": changed,
        "diff_tokens": tokens
    }


def compute_experience_diff(
    original_experience: List[dict],
    rewritten_experience: List[dict]
) -> List[dict]:
    """
    Produces a full diff for the entire experience section.
    Matches roles by role+company key.

    Returns list of experience diffs:
    [
      {
        "role": "Backend Developer",
        "company": "TechCorp",
        "bullet_diffs": [ ...compute_bullet_diff results... ],
        "bullets_changed": 3,
        "bullets_total": 4
      }
    ]
    """
    # Build lookup for rewritten experience: "role|company" -> bullets
    rewrite_map = {
        f"{e['role']}|{e['company']}": e.get("bullets", e.get("rewritten_bullets", []))
        for e in rewritten_experience
    }

    diffs = []
    for orig_exp in original_experience:
        key = f"{orig_exp['role']}|{orig_exp['company']}"
        original_bullets = orig_exp.get("bullets", [])
        rewritten_bullets = rewrite_map.get(key, original_bullets)

        # Pair bullets by index — if counts differ, fill with empty strings
        max_len = max(len(original_bullets), len(rewritten_bullets))
        bullet_diffs = []

        for i in range(max_len):
            orig = original_bullets[i] if i < len(original_bullets) else ""
            rewr = rewritten_bullets[i] if i < len(rewritten_bullets) else ""
            bullet_diffs.append(compute_bullet_diff(orig, rewr))

        bullets_changed = sum(1 for d in bullet_diffs if d["changed"])

        diffs.append({
            "role": orig_exp["role"],
            "company": orig_exp["company"],
            "bullet_diffs": bullet_diffs,
            "bullets_changed": bullets_changed,
            "bullets_total": len(bullet_diffs)
        })

    return diffs


def compute_summary_diff(original_summary: str, rewritten_summary: str) -> dict:
    """Diff for the summary section."""
    return compute_bullet_diff(
        original_summary or "",
        rewritten_summary or ""
    )


def compute_full_resume_diff(original: dict, rewritten: dict) -> dict:
    """
    Top-level diff between two full resume dicts.
    Returns everything the frontend needs to render the review screen.
    """
    experience_diffs = compute_experience_diff(
        original.get("experience", []),
        rewritten.get("experience", [])
    )

    summary_diff = compute_summary_diff(
        original.get("summary", ""),
        rewritten.get("summary", "")
    )

    total_changed = sum(e["bullets_changed"] for e in experience_diffs)
    total_bullets = sum(e["bullets_total"] for e in experience_diffs)

    return {
        "summary_diff": summary_diff,
        "experience_diffs": experience_diffs,
        "total_bullets_changed": total_changed,
        "total_bullets": total_bullets,
        "summary_changed": summary_diff["changed"]
    }
    
    """
Word-level diff between original and tailored resume.
Used by both Phase 2 (optimizer diff) and Phase 4 (tailor diff).

The diff output drives the frontend review screen — showing exactly
what changed in red (removed) and green (added).
"""




def word_diff(original: str, modified: str) -> List[dict]:
    """
    Computes word-level diff between two strings.
    Returns a list of tokens, each tagged as "equal", "added", or "removed".

    Example:
    original: "Worked on backend APIs"
    modified: "Architected 12 REST APIs handling 500K daily requests"

    Returns:
    [
      { text: "Worked",       type: "removed" },
      { text: "Architected",  type: "added"   },
      { text: "12",           type: "added"   },
      { text: "REST",         type: "added"   },
      { text: "APIs",         type: "equal"   },
      { text: "handling",     type: "added"   },
      { text: "500K",         type: "added"   },
      { text: "daily",        type: "added"   },
      { text: "requests",     type: "added"   },
      { text: "on",           type: "removed" },
      { text: "backend",      type: "removed" },
    ]
    """
    original_words = original.split()
    modified_words = modified.split()

    matcher = difflib.SequenceMatcher(None, original_words, modified_words)
    tokens  = []

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for word in original_words[i1:i2]:
                tokens.append({"text": word, "type": "equal"})

        elif op == "replace":
            for word in original_words[i1:i2]:
                tokens.append({"text": word, "type": "removed"})
            for word in modified_words[j1:j2]:
                tokens.append({"text": word, "type": "added"})

        elif op == "delete":
            for word in original_words[i1:i2]:
                tokens.append({"text": word, "type": "removed"})

        elif op == "insert":
            for word in modified_words[j1:j2]:
                tokens.append({"text": word, "type": "added"})

    return tokens


def build_resume_diff(original: dict, tailored: dict) -> dict:
    """
    Builds a complete diff of all text fields between original and tailored resume.

    Returns a structured dict that the frontend can render directly:
    {
      summary_diff: [tokens...],
      skills_diff: {
        added:   ["Python", "FastAPI"],   ← new skills (reordering counts)
        removed: [],
        reordered: true
      },
      experience_diffs: [
        {
          role: "Backend Developer",
          company: "TechCorp",
          bullet_diffs: [
            {
              index: 0,
              original: "Worked on APIs",
              tailored: "Architected 12 REST APIs...",
              tokens: [...]
              changed: true
            },
            {
              index: 1,
              original: "Helped with deployment",
              tailored: "Helped with deployment",  ← unchanged
              tokens: [...all equal...],
              changed: false
            }
          ]
        }
      ],
      has_changes: true,
      total_changes: 7   ← total number of bullets/fields changed
    }
    """
    diff = {
        "summary_diff":      [],
        "skills_diff":       {},
        "experience_diffs":  [],
        "has_changes":       False,
        "total_changes":     0
    }

    total_changes = 0

    # ── Summary diff ──────────────────────────────────────────────────────────
    orig_summary     = original.get("summary", "") or ""
    tailored_summary = tailored.get("summary", "") or ""

    if orig_summary != tailored_summary:
        diff["summary_diff"] = word_diff(orig_summary, tailored_summary)
        total_changes += 1
    else:
        # No change — return all-equal tokens for consistent frontend handling
        diff["summary_diff"] = [
            {"text": w, "type": "equal"}
            for w in orig_summary.split()
        ]

    # ── Skills diff ───────────────────────────────────────────────────────────
    orig_skills     = original.get("skills", [])
    tailored_skills = tailored.get("skills",  [])
    orig_set        = set(s.lower() for s in orig_skills)
    tailored_set    = set(s.lower() for s in tailored_skills)

    skills_added    = [s for s in tailored_skills if s.lower() not in orig_set]
    skills_removed  = [s for s in orig_skills     if s.lower() not in tailored_set]
    skills_reordered = (
        orig_skills != tailored_skills and
        len(skills_added) == 0 and
        len(skills_removed) == 0
    )

    diff["skills_diff"] = {
        "original":   orig_skills,
        "tailored":   tailored_skills,
        "added":      skills_added,
        "removed":    skills_removed,
        "reordered":  skills_reordered
    }
    if skills_added or skills_removed or skills_reordered:
        total_changes += 1

    # ── Experience diffs ──────────────────────────────────────────────────────
    orig_exp     = original.get("experience", [])
    tailored_exp = tailored.get("experience",  [])

    for i, (orig_role, tail_role) in enumerate(zip(orig_exp, tailored_exp)):
        orig_bullets     = orig_role.get("bullets", [])
        tailored_bullets = tail_role.get("bullets", [])

        bullet_diffs = []
        for j, (ob, tb) in enumerate(zip(orig_bullets, tailored_bullets)):
            changed = ob != tb
            if changed:
                total_changes += 1

            bullet_diffs.append({
                "index":    j,
                "original": ob,
                "tailored": tb,
                "tokens":   word_diff(ob, tb),
                "changed":  changed
            })

        diff["experience_diffs"].append({
            "role":         orig_role.get("role", ""),
            "company":      orig_role.get("company", ""),
            "bullet_diffs": bullet_diffs
        })

    diff["has_changes"]   = total_changes > 0
    diff["total_changes"] = total_changes

    return diff

