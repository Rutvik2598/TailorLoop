from __future__ import annotations

from datetime import datetime, timezone

from ..llm import call_structured
from ..models import JDProfile, NodeLogEntry, RunState
from ..prompts import jd_analyzer as prompt_module


def run(state: RunState) -> dict:
    jd_text = state["jd_text"]
    prompt = prompt_module.build_prompt(jd_text)

    jd_profile = call_structured("jd_analyzer", prompt, JDProfile)

    log_entry: NodeLogEntry = {
        "node": "jd_analyzer",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_summary": {"jd_length": len(jd_text)},
        "output_summary": {
            "role_title": jd_profile.role_title,
            "company": jd_profile.company,
            "seniority": jd_profile.seniority,
            "must_have_count": len(jd_profile.must_have_skills),
            "nice_to_have_count": len(jd_profile.nice_to_have_skills),
        },
    }

    return {
        "jd_profile": jd_profile,
        "node_log": [log_entry],
    }
