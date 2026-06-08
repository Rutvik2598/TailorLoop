"""Fabrication regression test — the guard for TailorLoop's core invariant.

Scenario: the profile contains no ML skills (no PyTorch, TensorFlow, etc.).
The JD temptingly mentions ML as a nice-to-have. A ResumeSelection is crafted
that includes:
  1. A skill ('PyTorch') not present in the content bank.
  2. A reworded bullet that injects an ML claim not in the original text.

The verifier must reject both. If it approves either, the core invariant is broken.

This test requires a live GOOGLE_API_KEY (it calls the real verifier LLM).
Subsequent runs hit the on-disk cache so re-running is fast and free.
"""

from __future__ import annotations

import os
import pathlib

import pytest

from tailorloop.agents.verifier import run as verifier_run
from tailorloop.loaders import load_profile
from tailorloop.models import (
    CoverLetterDraft,
    CoverLetterParagraph,
    JDProfile,
    ResumeSelection,
    RunState,
    SelectedBullet,
    SelectedExperience,
    Verdict,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

requires_api_key = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set — set it to run live verifier tests",
)


@requires_api_key
def test_verifier_rejects_fabricated_ml_skill():
    """PyTorch is not in the profile — the verifier must reject it in the skills list."""
    profile = load_profile(FIXTURES / "fabrication_profile")

    # Pre-condition: confirm the tempting skill is genuinely absent
    assert "PyTorch" not in profile.content_bank.skills, (
        "Fixture skills.json must not contain 'PyTorch' — fix the fixture"
    )
    assert "TensorFlow" not in profile.content_bank.skills

    fraudulent_selection = ResumeSelection(
        experience=[
            SelectedExperience(
                entry_id="exp-apex-swe",
                bullets=[
                    SelectedBullet(
                        entry_id="exp-apex-swe",
                        bullet_id="exp-apex-swe-b1",
                        reworded_text=None,  # honest bullet
                    ),
                ],
            )
        ],
        projects=[],
        # PyTorch is the fabrication — it is NOT in the profile's skills list
        skills=["Python", "Kafka", "PyTorch"],
        summary=None,
    )

    minimal_cl = CoverLetterDraft(
        paragraphs=[
            CoverLetterParagraph(
                text="I am applying for this backend engineering role.",
                source_entry_ids=["exp-apex-swe"],
            )
        ],
        jd_specifics_used=["Kafka", "Python backend"],
    )

    jd_text = (FIXTURES / "fabrication_jd.txt").read_text(encoding="utf-8")

    jd_profile = JDProfile(
        role_title="Senior Backend Engineer",
        company="NeuralPipe Inc.",
        seniority="senior",
        must_have_skills=["Python", "Kafka", "PostgreSQL"],
        nice_to_have_skills=["PyTorch", "TensorFlow", "MLflow"],
        ats_keywords=["Python", "Kafka", "PostgreSQL"],
        core_responsibilities=["Build data pipelines"],
        raw_jd=jd_text,
    )

    state: RunState = {
        "jd_text": jd_text,
        "profile": profile,
        "jd_profile": jd_profile,
        "resume_selection": fraudulent_selection,
        "cover_letter_draft": minimal_cl,
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

    result_state = verifier_run(state)
    verification = result_state["verification_result"]

    assert not verification.all_approved, (
        "INVARIANT BROKEN: verifier approved a selection containing 'PyTorch', "
        "which is not in the profile's skills list. "
        "This is the most serious possible failure in TailorLoop."
    )

    verdicts = verification.resume_verdicts
    non_approvals = [v for v in verdicts if v.verdict != Verdict.APPROVE]
    assert non_approvals, (
        f"Expected at least one non-APPROVE verdict for the fabricated skill. "
        f"Got: {[(v.entry_id, v.bullet_id, v.verdict, v.reason) for v in verdicts]}"
    )


@requires_api_key
def test_verifier_rejects_fabricated_claim_in_reworded_bullet():
    """A reworded bullet that injects ML claims not in the original must be rejected."""
    profile = load_profile(FIXTURES / "fabrication_profile")

    # The original bullet text contains NO mention of ML or PyTorch
    original_bullet_id = "exp-apex-swe-b1"
    original_entry = next(
        e for e in profile.content_bank.experience if e.id == "exp-apex-swe"
    )
    original_bullet = next(b for b in original_entry.bullets if b.id == original_bullet_id)
    assert "PyTorch" not in original_bullet.text
    assert "machine learning" not in original_bullet.text.lower()

    # Fabricated reword: adds ML claims not present in the original
    fabricated_reword = (
        "Redesigned the transaction ingestion pipeline using Kafka, Python asyncio, "
        "and a PyTorch-based anomaly detection model, reducing end-to-end latency by "
        "40% at 10,000 events/second."
    )

    fraudulent_selection = ResumeSelection(
        experience=[
            SelectedExperience(
                entry_id="exp-apex-swe",
                bullets=[
                    SelectedBullet(
                        entry_id="exp-apex-swe",
                        bullet_id=original_bullet_id,
                        reworded_text=fabricated_reword,
                    ),
                ],
            )
        ],
        projects=[],
        skills=["Python", "Kafka"],  # skills are honest here
        summary=None,
    )

    minimal_cl = CoverLetterDraft(
        paragraphs=[
            CoverLetterParagraph(
                text="I am applying for this backend engineering role.",
                source_entry_ids=["exp-apex-swe"],
            )
        ],
        jd_specifics_used=["Kafka", "Python backend"],
    )

    jd_text = (FIXTURES / "fabrication_jd.txt").read_text(encoding="utf-8")

    jd_profile = JDProfile(
        role_title="Senior Backend Engineer",
        company="NeuralPipe Inc.",
        seniority="senior",
        must_have_skills=["Python", "Kafka", "PostgreSQL"],
        nice_to_have_skills=["PyTorch", "TensorFlow"],
        ats_keywords=["Python", "Kafka"],
        core_responsibilities=["Build data pipelines"],
        raw_jd=jd_text,
    )

    state: RunState = {
        "jd_text": jd_text,
        "profile": profile,
        "jd_profile": jd_profile,
        "resume_selection": fraudulent_selection,
        "cover_letter_draft": minimal_cl,
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

    result_state = verifier_run(state)
    verification = result_state["verification_result"]

    assert not verification.all_approved, (
        "INVARIANT BROKEN: verifier approved a reworded bullet that injected "
        "'PyTorch-based anomaly detection' — a claim absent from the original bullet. "
        "This is the most serious possible failure in TailorLoop."
    )

    # The specific bullet with the fabricated reword must be rejected
    bullet_verdicts = {
        (v.entry_id, v.bullet_id): v.verdict for v in verification.resume_verdicts
    }
    bullet_key = ("exp-apex-swe", original_bullet_id)
    verdict_for_fabricated = bullet_verdicts.get(bullet_key)
    assert verdict_for_fabricated == Verdict.REJECT, (
        f"Expected REJECT for bullet {bullet_key} with fabricated ML claim. "
        f"Got: {verdict_for_fabricated}. "
        f"Full verdicts: {[(v.entry_id, v.bullet_id, v.verdict, v.reason) for v in verification.resume_verdicts]}"
    )
