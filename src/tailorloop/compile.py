from __future__ import annotations

import pathlib
import subprocess
import tempfile
from datetime import datetime, timezone

from .models import NodeLogEntry, RunState


class LaTeXCompileError(Exception):
    def __init__(self, stderr: str, tex: str) -> None:
        super().__init__(f"Tectonic compilation failed:\n{stderr}")
        self.stderr = stderr
        self.tex = tex  # included so callers can inspect/save for debugging


def compile_pdf(tex: str, outdir: pathlib.Path, name: str) -> pathlib.Path:
    """Compile a LaTeX string to PDF via Tectonic. Returns the PDF path.

    Also writes <name>.tex alongside the PDF for debugging — useful when
    escaping is wrong and the compile fails.
    """
    outdir.mkdir(parents=True, exist_ok=True)

    # Always persist the .tex for debugging, even on success
    tex_path = outdir / f"{name}.tex"
    tex_path.write_text(tex, encoding="utf-8")

    with tempfile.TemporaryDirectory() as td:
        # Copy .tex to a temp dir so Tectonic's aux files don't clutter outdir
        tmp_tex = pathlib.Path(td) / f"{name}.tex"
        tmp_tex.write_text(tex, encoding="utf-8")

        proc = subprocess.run(
            [
                "tectonic",
                "--chatter", "minimal",
                "--outdir", str(outdir),
                str(tmp_tex),
            ],
            capture_output=True,
            text=True,
        )

    if proc.returncode != 0:
        raise LaTeXCompileError(proc.stderr, tex)

    return outdir / f"{name}.pdf"


# ---------------------------------------------------------------------------
# Graph node wrapper — called by graph.py after filtering to approved content
# ---------------------------------------------------------------------------

def run_node(state: RunState, outdir: pathlib.Path) -> dict:
    """Render approved selections to LaTeX and compile to PDF.

    This is NOT an LLM agent. It is deterministic; any failure here is a
    template/escaping bug, not an LLM issue — fix the template, not the model.
    """
    from . import render

    profile = state["profile"]
    jd_profile = state["jd_profile"]
    final_resume = state["final_resume_selection"]
    final_cl = state["final_cover_letter_draft"]

    resume_tex = render.render_resume(profile, final_resume)
    cl_tex = render.render_cover_letter(profile, final_cl, company=jd_profile.company)

    resume_pdf = compile_pdf(resume_tex, outdir, "resume")
    cl_pdf = compile_pdf(cl_tex, outdir, "cover_letter")

    log_entry: NodeLogEntry = {
        "node": "pdf_compile",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_summary": {
            "resume_experience_entries": len(final_resume.experience),
            "cl_paragraphs": len(final_cl.paragraphs),
        },
        "output_summary": {
            "resume_pdf": str(resume_pdf),
            "cover_letter_pdf": str(cl_pdf),
        },
    }

    return {
        "node_log": [log_entry],
        "_pdf_paths": {"resume": resume_pdf, "cover_letter": cl_pdf},
    }
