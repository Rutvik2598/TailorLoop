from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any

# In-memory job store — fine for local single-user use
_jobs: dict[str, dict[str, Any]] = {}

# ── Stage definitions (what the frontend shows) ──────────────────────────────
STAGES = [
    ("analyze", "Analyzing job description",
     "Extracting must-have skills, ATS keywords, and responsibilities"),
    ("write",   "Tailoring resume & cover letter",
     "Selecting the best experience and crafting a grounded cover letter"),
    ("verify",  "Verifying claims",
     "Ensuring every statement traces back to your real experience"),
    ("compile", "Compiling PDFs",
     "Rendering LaTeX templates and building final documents"),
]
_STAGE_ORDER = [s[0] for s in STAGES]

# LangGraph node → display stage
_NODE_STAGE: dict[str, str] = {
    "jd_analyzer":         "analyze",
    "resume_tailor":       "write",
    "cover_letter_writer": "write",
    "verifier":            "verify",
    "compile":             "compile",
}


def _advance(job: dict[str, Any], stage: str) -> None:
    """Mark all stages before `stage` as done and set current."""
    idx = _STAGE_ORDER.index(stage)
    for s in _STAGE_ORDER[:idx]:
        if s not in job["stages_done"]:
            job["stages_done"].append(s)
    job["current_stage"] = stage


def _run_pipeline(job_id: str, jd_text: str, db_path: str) -> None:
    job = _jobs[job_id]
    try:
        from ..loaders import load_profile_from_db
        from ..graph import pipeline
        from .. import compile as compiler
        from ..models import RunState

        job["current_stage"] = "analyze"

        profile = load_profile_from_db(db_path)
        out_dir = Path(job["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)

        initial_state: RunState = {
            "jd_text": jd_text,
            "profile": profile,
            "jd_profile": None,
            "resume_selection": None,
            "cover_letter_draft": None,
            "verification_result": None,
            "resume_retry_count": 0,
            "cover_letter_retry_count": 0,
            "resume_rejection_reasons": [],
            "cover_letter_rejection_reasons": [],
            "final_resume_selection": None,
            "final_cover_letter_draft": None,
            "dropped_resume_bullets": [],
            "dropped_cover_letter_paragraphs": [],
            "node_log": [],
        }

        accumulated: dict[str, Any] = dict(initial_state)
        writers_done: set[str] = set()

        for chunk in pipeline.stream(initial_state, stream_mode="updates"):
            for node_name, updates in chunk.items():
                # Accumulate state (node_log is additive, all others replace)
                for key, val in updates.items():
                    if key == "node_log":
                        accumulated["node_log"] = accumulated.get("node_log", []) + val
                    else:
                        accumulated[key] = val

                # Advance progress
                if node_name == "jd_analyzer":
                    _advance(job, "write")
                elif node_name in ("resume_tailor", "cover_letter_writer"):
                    writers_done.add(node_name)
                    if len(writers_done) >= 2:
                        _advance(job, "verify")
                elif node_name == "verifier":
                    job["current_stage"] = "verify"
                elif node_name == "compile":
                    _advance(job, "compile")

        # Compile PDFs using accumulated final state
        compiler.run_node(accumulated, out_dir)

        if "compile" not in job["stages_done"]:
            job["stages_done"].append("compile")
        job["current_stage"] = None
        job["status"] = "complete"
        job["files"] = {
            "resume":        str(out_dir / "resume.pdf"),
            "cover_letter":  str(out_dir / "cover_letter.pdf"),
        }

    except Exception as exc:
        import traceback
        traceback.print_exc()
        job["status"] = "error"
        job["error"] = str(exc)


def start_job(jd_text: str, db_path: str, out_base: str = "out") -> str:
    job_id = uuid.uuid4().hex[:12]
    job: dict[str, Any] = {
        "status":        "running",
        "current_stage": "analyze",
        "stages_done":   [],
        "error":         None,
        "output_dir":    str(Path(out_base) / job_id),
        "files":         None,
    }
    _jobs[job_id] = job
    threading.Thread(
        target=_run_pipeline,
        args=(job_id, jd_text, db_path),
        daemon=True,
    ).start()
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    return _jobs.get(job_id)
