from __future__ import annotations

from datetime import datetime, timezone

from ..llm import call_structured
from ..models import CoverLetterDraft, NodeLogEntry, RunState
from ..prompts import cover_letter_writer as prompt_module


def run(state: RunState) -> dict:
    jd_profile = state["jd_profile"]
    profile = state["profile"]
    rejection_reasons = state.get("cover_letter_rejection_reasons") or []
    retry_count = state.get("cover_letter_retry_count", 0)

    # Passthrough: if we already have an approved draft and no rejection reasons, skip.
    if state.get("cover_letter_draft") is not None and not rejection_reasons:
        return {}

    # Provide profile without the content bank (writer gets profile metadata + bank separately)
    profile_meta = profile.model_dump(exclude={"content_bank"})

    prompt = prompt_module.build_prompt(
        jd_profile_json=jd_profile.model_dump_json(indent=2),
        profile_json=str(profile_meta),
        content_bank_json=profile.content_bank.model_dump_json(indent=2),
        rejection_reasons=rejection_reasons if rejection_reasons else None,
    )

    cover_letter_draft = call_structured(
        "cover_letter_writer", prompt, CoverLetterDraft
    )
    new_retry_count = retry_count + 1 if rejection_reasons else retry_count

    log_entry: NodeLogEntry = {
        "node": "cover_letter_writer",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "retry_count": retry_count,
            "rejection_reasons": rejection_reasons,
        },
        "output_summary": {
            "paragraph_count": len(cover_letter_draft.paragraphs),
            "jd_specifics_count": len(cover_letter_draft.jd_specifics_used),
        },
    }

    return {
        "cover_letter_draft": cover_letter_draft,
        "cover_letter_retry_count": new_retry_count,
        "cover_letter_rejection_reasons": [],
        "node_log": [log_entry],
    }
