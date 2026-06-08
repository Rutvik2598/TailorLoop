from __future__ import annotations

import json
from datetime import datetime, timezone

from ..llm import call_structured
from ..models import NodeLogEntry, ResumeSelection, RunState
from ..prompts import resume_tailor as prompt_module


def run(state: RunState) -> dict:
    jd_profile = state["jd_profile"]
    profile = state["profile"]
    rejection_reasons = state.get("resume_rejection_reasons") or []
    retry_count = state.get("resume_retry_count", 0)

    # Passthrough: if we already have a good selection and no rejection reasons, skip.
    if state.get("resume_selection") is not None and not rejection_reasons:
        return {}

    prompt = prompt_module.build_prompt(
        jd_profile_json=jd_profile.model_dump_json(indent=2),
        content_bank_json=profile.content_bank.model_dump_json(indent=2),
        rejection_reasons=rejection_reasons if rejection_reasons else None,
    )

    resume_selection = call_structured("resume_tailor", prompt, ResumeSelection)
    new_retry_count = retry_count + 1 if rejection_reasons else retry_count

    log_entry: NodeLogEntry = {
        "node": "resume_tailor",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "retry_count": retry_count,
            "rejection_reasons": rejection_reasons,
        },
        "output_summary": {
            "experience_entries": len(resume_selection.experience),
            "project_entries": len(resume_selection.projects),
            "skills_count": len(resume_selection.skills),
        },
    }

    return {
        "resume_selection": resume_selection,
        "resume_retry_count": new_retry_count,
        "resume_rejection_reasons": [],  # clear for this pass
        "node_log": [log_entry],
    }
