from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Content bank — ground truth; the verifier re-reads this independently
# ---------------------------------------------------------------------------

class BulletVariant(BaseModel):
    id: str
    text: str


class ExperienceEntry(BaseModel):
    id: str
    company: str
    title: str
    start_date: str       # "YYYY-MM"
    end_date: str | None  # None = currently employed
    location: str | None
    bullets: list[BulletVariant]


class ProjectEntry(BaseModel):
    id: str
    name: str
    description: str
    tech_stack: list[str]
    bullets: list[BulletVariant]
    url: str | None


class EducationEntry(BaseModel):
    id: str
    institution: str
    degree: str
    field: str
    graduation_year: str
    gpa: str | None


class ContentBank(BaseModel):
    experience: list[ExperienceEntry]
    projects: list[ProjectEntry]
    education: list[EducationEntry]
    skills: list[str]  # verified flat list; tailor may only pick from here


class Profile(BaseModel):
    name: str
    email: str
    phone: str | None
    location: str | None
    linkedin: str | None
    github: str | None
    summary: str | None
    content_bank: ContentBank


# ---------------------------------------------------------------------------
# JD analysis output
# ---------------------------------------------------------------------------

class JDProfile(BaseModel):
    role_title: str
    company: str | None
    seniority: str  # "junior" | "mid" | "senior" | "lead" | "staff"
    must_have_skills: list[str]
    nice_to_have_skills: list[str]
    ats_keywords: list[str]
    core_responsibilities: list[str]
    raw_jd: str  # preserved verbatim for the verifier's specificity check


# ---------------------------------------------------------------------------
# Resume selection — references into the content bank only; no free claims
# ---------------------------------------------------------------------------

class SelectedBullet(BaseModel):
    entry_id: str        # must match an ExperienceEntry.id or ProjectEntry.id
    bullet_id: str       # must match a BulletVariant.id within that entry
    reworded_text: str | None  # None = use original; any rephrasing must be equivalent


class SelectedExperience(BaseModel):
    entry_id: str
    bullets: list[SelectedBullet]


class SelectedProject(BaseModel):
    entry_id: str
    bullets: list[SelectedBullet]


class ResumeSelection(BaseModel):
    experience: list[SelectedExperience]
    projects: list[SelectedProject]
    skills: list[str]       # strict subset of ContentBank.skills
    summary: str | None     # paraphrase of profile.summary; must not add facts


# ---------------------------------------------------------------------------
# Cover letter — prose with source references so the verifier can check
# ---------------------------------------------------------------------------

class CoverLetterParagraph(BaseModel):
    text: str
    source_entry_ids: list[str]  # IDs from content bank this paragraph draws on


class CoverLetterDraft(BaseModel):
    paragraphs: list[CoverLetterParagraph]
    jd_specifics_used: list[str]  # concrete JD details cited (verifier checks)


# ---------------------------------------------------------------------------
# Verifier output — per-claim verdicts
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"


class BulletVerdict(BaseModel):
    entry_id: str
    bullet_id: str
    verdict: Verdict
    reason: str | None


class ParagraphVerdict(BaseModel):
    paragraph_index: int
    verdict: Verdict
    reason: str | None
    unverified_claims: list[str]  # specific claims that couldn't be verified


class VerificationResult(BaseModel):
    resume_verdicts: list[BulletVerdict]
    cover_letter_verdicts: list[ParagraphVerdict]
    specificity_ok: bool           # cover letter references concrete JD details?
    specificity_notes: str | None
    all_approved: bool             # True only when every verdict is APPROVE


# ---------------------------------------------------------------------------
# LangGraph state — also serves as the full audit log
# ---------------------------------------------------------------------------

class NodeLogEntry(TypedDict):
    node: str
    timestamp: str
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]


class RunState(TypedDict):
    # --- Inputs ---
    jd_text: str
    profile: Profile

    # --- Pipeline outputs (updated each iteration) ---
    jd_profile: JDProfile | None
    resume_selection: ResumeSelection | None
    cover_letter_draft: CoverLetterDraft | None
    verification_result: VerificationResult | None

    # --- Retry management ---
    resume_retry_count: int
    cover_letter_retry_count: int
    resume_rejection_reasons: list[str]      # reasons from last verifier run
    cover_letter_rejection_reasons: list[str]

    # --- Final approved outputs (produced by the compile node) ---
    final_resume_selection: ResumeSelection | None
    final_cover_letter_draft: CoverLetterDraft | None
    dropped_resume_bullets: list[str]         # bullet IDs dropped at compile time
    dropped_cover_letter_paragraphs: list[int]

    # --- Audit log — accumulated across all nodes via operator.add ---
    node_log: Annotated[list[NodeLogEntry], operator.add]
