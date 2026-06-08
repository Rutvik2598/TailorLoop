from __future__ import annotations

import logging
from datetime import datetime, timezone

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .agents import cover_letter_writer, jd_analyzer, resume_tailor, verifier
from .config import config
from .models import RunState, Verdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def _dispatch_to_writers(state: RunState) -> list[Send]:
    """Fan out to both writers in parallel after jd_analyzer."""
    return [
        Send("resume_tailor", state),
        Send("cover_letter_writer", state),
    ]


def _route_after_verification(state: RunState) -> list[Send] | str:
    """After the verifier, either compile or retry the writer(s) that failed."""
    result = state.get("verification_result")
    if result is None:
        raise RuntimeError("Verifier node produced no VerificationResult")

    if result.all_approved:
        logger.info("verification_passed — routing to compile")
        return "compile"

    max_retries = config.max_retries
    resume_needs_retry = (
        any(v.verdict != Verdict.APPROVE for v in result.resume_verdicts)
        and state.get("resume_retry_count", 0) < max_retries
    )
    cl_needs_retry = (
        (
            any(v.verdict != Verdict.APPROVE for v in result.cover_letter_verdicts)
            or not result.specificity_ok
        )
        and state.get("cover_letter_retry_count", 0) < max_retries
    )

    sends = []
    if resume_needs_retry:
        logger.info("routing resume_tailor for retry %d", state.get("resume_retry_count", 0) + 1)
        sends.append(Send("resume_tailor", state))
    if cl_needs_retry:
        logger.info("routing cover_letter_writer for retry %d", state.get("cover_letter_retry_count", 0) + 1)
        sends.append(Send("cover_letter_writer", state))

    if sends:
        return sends

    # Both writers exhausted their retry budgets — compile whatever passed
    logger.warning(
        "retry_budget_exhausted — compiling with partial approvals; "
        "resume_rejections=%d cl_rejections=%d",
        len(state.get("resume_rejection_reasons") or []),
        len(state.get("cover_letter_rejection_reasons") or []),
    )
    return "compile"


# ---------------------------------------------------------------------------
# Compile node (deterministic — not an LLM agent)
# ---------------------------------------------------------------------------

def _compile_node(state: RunState) -> dict:
    """Filter approved-only content and store in state for the CLI to render+compile."""
    from .models import NodeLogEntry

    result = state["verification_result"]
    resume_selection = state["resume_selection"]
    cover_letter_draft = state["cover_letter_draft"]

    # Build sets of approved bullet IDs
    approved_resume_bullets: set[tuple[str, str]] = {
        (v.entry_id, v.bullet_id)
        for v in result.resume_verdicts
        if v.verdict == Verdict.APPROVE
    }
    approved_cl_paragraphs: set[int] = {
        v.paragraph_index
        for v in result.cover_letter_verdicts
        if v.verdict == Verdict.APPROVE
    }

    # Track what was dropped
    dropped_bullets: list[str] = []
    dropped_paragraphs: list[int] = []

    # Filter resume selection to approved bullets only
    from .models import ResumeSelection, SelectedExperience, SelectedProject, CoverLetterDraft, CoverLetterParagraph

    filtered_experience = []
    for exp in resume_selection.experience:
        approved = [
            b for b in exp.bullets
            if (exp.entry_id, b.bullet_id) in approved_resume_bullets
        ]
        dropped_bullets.extend(
            f"{exp.entry_id}/{b.bullet_id}"
            for b in exp.bullets
            if (exp.entry_id, b.bullet_id) not in approved_resume_bullets
        )
        if approved:
            filtered_experience.append(
                SelectedExperience(entry_id=exp.entry_id, bullets=approved)
            )

    filtered_projects = []
    for proj in resume_selection.projects:
        approved = [
            b for b in proj.bullets
            if (proj.entry_id, b.bullet_id) in approved_resume_bullets
        ]
        dropped_bullets.extend(
            f"{proj.entry_id}/{b.bullet_id}"
            for b in proj.bullets
            if (proj.entry_id, b.bullet_id) not in approved_resume_bullets
        )
        if approved:
            filtered_projects.append(
                SelectedProject(entry_id=proj.entry_id, bullets=approved)
            )

    # Only include approved skills (check against content bank)
    content_skills = set(state["profile"].content_bank.skills)
    approved_skills = [s for s in resume_selection.skills if s in content_skills]

    final_resume = ResumeSelection(
        experience=filtered_experience,
        projects=filtered_projects,
        skills=approved_skills,
        summary=resume_selection.summary,
    )

    # Filter cover letter to approved paragraphs
    filtered_paragraphs = []
    for i, para in enumerate(cover_letter_draft.paragraphs):
        if i in approved_cl_paragraphs:
            filtered_paragraphs.append(para)
        else:
            dropped_paragraphs.append(i)

    final_cl = CoverLetterDraft(
        paragraphs=filtered_paragraphs,
        jd_specifics_used=cover_letter_draft.jd_specifics_used,
    )

    if dropped_bullets:
        logger.warning("dropped_resume_bullets: %s", dropped_bullets)
    if dropped_paragraphs:
        logger.warning("dropped_cover_letter_paragraphs: %s", dropped_paragraphs)

    log_entry: NodeLogEntry = {
        "node": "compile",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "resume_bullets_before": sum(len(e.bullets) for e in resume_selection.experience)
            + sum(len(p.bullets) for p in resume_selection.projects),
            "cl_paragraphs_before": len(cover_letter_draft.paragraphs),
        },
        "output_summary": {
            "dropped_bullets": dropped_bullets,
            "dropped_paragraphs": dropped_paragraphs,
        },
    }

    return {
        "final_resume_selection": final_resume,
        "final_cover_letter_draft": final_cl,
        "dropped_resume_bullets": dropped_bullets,
        "dropped_cover_letter_paragraphs": dropped_paragraphs,
        "node_log": [log_entry],
    }


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph():
    g = StateGraph(RunState)

    g.add_node("jd_analyzer", jd_analyzer.run)
    g.add_node("resume_tailor", resume_tailor.run)
    g.add_node("cover_letter_writer", cover_letter_writer.run)
    g.add_node("verifier", verifier.run)
    g.add_node("compile", _compile_node)

    g.add_edge(START, "jd_analyzer")

    # Parallel fan-out: jd_analyzer → both writers simultaneously
    g.add_conditional_edges(
        "jd_analyzer",
        _dispatch_to_writers,
        ["resume_tailor", "cover_letter_writer"],
    )

    # Fan-in: both writers → verifier (LangGraph waits for both before proceeding)
    g.add_edge("resume_tailor", "verifier")
    g.add_edge("cover_letter_writer", "verifier")

    # Verifier → compile or retry writers
    g.add_conditional_edges(
        "verifier",
        _route_after_verification,
        ["resume_tailor", "cover_letter_writer", "compile"],
    )

    g.add_edge("compile", END)

    return g.compile()


pipeline = build_graph()
