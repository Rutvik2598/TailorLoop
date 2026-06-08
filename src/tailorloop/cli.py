from __future__ import annotations

import json
import pathlib
import sys

import click
import structlog

from .config import config
from .graph import pipeline
from .loaders import load_profile
from .models import RunState
from . import compile as compiler

logger = structlog.get_logger()


def _configure_logging(verbose: bool) -> None:
    level = "DEBUG" if verbose else "INFO"
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            __import__("logging").getLevelName(level)
        ),
    )


@click.group()
def app() -> None:
    pass


@app.command()
@click.option("--jd", "jd_path", required=True, type=click.Path(exists=True), help="Path to job description text file")
@click.option("--profile", "profile_dir", required=True, type=click.Path(exists=True), help="Path to profile directory")
@click.option("--out", "out_dir", required=True, type=click.Path(), help="Output directory for PDFs and audit trail")
@click.option("--max-retries", default=None, type=int, help="Override max verifier retries (default: 2)")
@click.option("--no-cache", is_flag=True, default=False, help="Disable LLM response cache")
@click.option("--pro", is_flag=True, default=False, help="Use Pro model for judgment roles (higher quality, higher cost)")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Verbose logging")
def run(
    jd_path: str,
    profile_dir: str,
    out_dir: str,
    max_retries: int | None,
    no_cache: bool,
    pro: bool,
    verbose: bool,
) -> None:
    """Run the TailorLoop pipeline: JD + profile → verified resume + cover letter PDFs."""
    _configure_logging(verbose)

    # Apply CLI overrides to config
    if max_retries is not None:
        config.max_retries = max_retries
    if no_cache:
        config.cache_enabled = False
    if pro:
        config.judgment_model = "gemini-3.1-pro-preview"
        config.extraction_model = "gemini-3.1-pro-preview"

    jd_text = pathlib.Path(jd_path).read_text(encoding="utf-8")
    profile = load_profile(pathlib.Path(profile_dir))
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    logger.info("pipeline_start", jd=jd_path, profile=profile_dir, out=out_dir)

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

    final_state = pipeline.invoke(initial_state)

    # Compile PDFs
    pdf_paths = compiler.run_node(final_state, out)

    # Write audit trail
    audit = {
        "jd_path": jd_path,
        "profile_dir": profile_dir,
        "jd_profile": final_state["jd_profile"].model_dump() if final_state.get("jd_profile") else None,
        "resume_retry_count": final_state.get("resume_retry_count", 0),
        "cover_letter_retry_count": final_state.get("cover_letter_retry_count", 0),
        "dropped_resume_bullets": final_state.get("dropped_resume_bullets", []),
        "dropped_cover_letter_paragraphs": final_state.get("dropped_cover_letter_paragraphs", []),
        "verification_result": (
            final_state["verification_result"].model_dump()
            if final_state.get("verification_result")
            else None
        ),
        "node_log": final_state.get("node_log", []),
    }
    audit_path = out / "run.json"
    audit_path.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")

    logger.info("pipeline_complete", resume_pdf=str(out / "resume.pdf"), cover_letter_pdf=str(out / "cover_letter.pdf"), audit=str(audit_path))

    if final_state.get("dropped_resume_bullets") or final_state.get("dropped_cover_letter_paragraphs"):
        click.echo(
            "\nNote: some content was dropped after verification:\n"
            f"  Dropped bullets: {final_state.get('dropped_resume_bullets', [])}\n"
            f"  Dropped CL paragraphs: {final_state.get('dropped_cover_letter_paragraphs', [])}",
            err=True,
        )

    click.echo(f"resume.pdf        → {out / 'resume.pdf'}")
    click.echo(f"cover_letter.pdf  → {out / 'cover_letter.pdf'}")
    click.echo(f"run.json          → {audit_path}")
