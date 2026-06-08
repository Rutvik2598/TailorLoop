from __future__ import annotations

from datetime import datetime, timezone

from ..llm import call_structured
from ..models import NodeLogEntry, RunState, Verdict, VerificationResult
from ..prompts import verifier as prompt_module


def run(state: RunState) -> dict:
    profile = state["profile"]
    jd_profile = state["jd_profile"]
    resume_selection = state["resume_selection"]
    cover_letter_draft = state["cover_letter_draft"]

    # The verifier independently re-reads the content bank — it does NOT trust
    # the text that was passed to it by the tailor/writer agents.
    prompt = prompt_module.build_prompt(
        content_bank_json=profile.content_bank.model_dump_json(indent=2),
        jd_text=jd_profile.raw_jd,
        resume_selection_json=resume_selection.model_dump_json(indent=2),
        cover_letter_draft_json=cover_letter_draft.model_dump_json(indent=2),
    )

    result = call_structured("verifier", prompt, VerificationResult)

    # Collect rejection reasons per writer for the retry feedback loop
    resume_rejection_reasons = [
        f"[{v.entry_id}/{v.bullet_id}] {v.reason}"
        for v in result.resume_verdicts
        if v.verdict != Verdict.APPROVE and v.reason
    ]
    cover_letter_rejection_reasons = [
        f"[paragraph {v.paragraph_index}] {v.reason}"
        + (
            f" — unverified claims: {', '.join(v.unverified_claims)}"
            if v.unverified_claims
            else ""
        )
        for v in result.cover_letter_verdicts
        if v.verdict != Verdict.APPROVE and v.reason
    ]
    if not result.specificity_ok and result.specificity_notes:
        cover_letter_rejection_reasons.append(
            f"[specificity] {result.specificity_notes}"
        )

    log_entry: NodeLogEntry = {
        "node": "verifier",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "resume_bullets": sum(
                len(e.bullets) for e in resume_selection.experience
            )
            + sum(len(p.bullets) for p in resume_selection.projects),
            "cover_letter_paragraphs": len(cover_letter_draft.paragraphs),
        },
        "output_summary": {
            "all_approved": result.all_approved,
            "resume_rejections": len(resume_rejection_reasons),
            "cl_rejections": len(cover_letter_rejection_reasons),
            "specificity_ok": result.specificity_ok,
        },
    }

    return {
        "verification_result": result,
        "resume_rejection_reasons": resume_rejection_reasons,
        "cover_letter_rejection_reasons": cover_letter_rejection_reasons,
        "node_log": [log_entry],
    }
