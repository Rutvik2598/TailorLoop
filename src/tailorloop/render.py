from __future__ import annotations

import pathlib

import jinja2

from .models import CoverLetterDraft, Profile, ResumeSelection

# ---------------------------------------------------------------------------
# LaTeX escaping — applied to every piece of user/model text before insertion
# ---------------------------------------------------------------------------

_LATEX_SPECIAL: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(s: str) -> str:
    # Build result in one pass; backslash must be handled before other replacements
    # would re-introduce backslashes, so we put it first in _LATEX_SPECIAL above.
    out: list[str] = []
    for ch in s:
        out.append(_LATEX_SPECIAL.get(ch, ch))
    return "".join(out)


# ---------------------------------------------------------------------------
# Jinja2 environment — custom delimiters that don't collide with LaTeX {}
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = pathlib.Path(__file__).parent.parent.parent / "templates"


def _make_env(templates_dir: pathlib.Path = _TEMPLATES_DIR) -> jinja2.Environment:
    env = jinja2.Environment(
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        line_statement_prefix="%%",
        line_comment_prefix="%#",
        trim_blocks=True,
        autoescape=False,  # manual escaping via the |e filter
        loader=jinja2.FileSystemLoader(str(templates_dir)),
    )
    env.filters["e"] = latex_escape
    return env


_env = _make_env()


# ---------------------------------------------------------------------------
# Rendering helpers — resolve selection references into displayable dicts
# ---------------------------------------------------------------------------

def _resolve_resume(profile: Profile, selection: ResumeSelection) -> dict:
    """Build a template-friendly dict from a ResumeSelection + content bank."""
    bank = profile.content_bank

    exp_index = {e.id: e for e in bank.experience}
    proj_index = {p.id: p for p in bank.projects}
    bullet_index: dict[str, dict[str, str]] = {}
    for e in bank.experience:
        bullet_index[e.id] = {b.id: b.text for b in e.bullets}
    for p in bank.projects:
        bullet_index[p.id] = {b.id: b.text for b in p.bullets}

    resolved_experience = []
    for sel_exp in selection.experience:
        entry = exp_index[sel_exp.entry_id]
        bullets = []
        for sel_bullet in sel_exp.bullets:
            text = (
                sel_bullet.reworded_text
                if sel_bullet.reworded_text
                else bullet_index[sel_exp.entry_id][sel_bullet.bullet_id]
            )
            bullets.append(text)
        resolved_experience.append(
            {
                "company": entry.company,
                "title": entry.title,
                "start_date": entry.start_date,
                "end_date": entry.end_date or "Present",
                "location": entry.location or "",
                "bullets": bullets,
            }
        )

    resolved_projects = []
    for sel_proj in selection.projects:
        entry = proj_index[sel_proj.entry_id]
        bullets = []
        for sel_bullet in sel_proj.bullets:
            text = (
                sel_bullet.reworded_text
                if sel_bullet.reworded_text
                else bullet_index[sel_proj.entry_id][sel_bullet.bullet_id]
            )
            bullets.append(text)
        resolved_projects.append(
            {
                "name": entry.name,
                "description": entry.description,
                "tech_stack": entry.tech_stack,
                "url": entry.url or "",
                "bullets": bullets,
            }
        )

    resolved_education = [
        {
            "institution": e.institution,
            "degree": e.degree,
            "field": e.field,
            "graduation_year": e.graduation_year,
            "gpa": e.gpa,
        }
        for e in bank.education
    ]

    return {
        "profile": {
            "name": profile.name,
            "email": profile.email,
            "phone": profile.phone or "",
            "location": profile.location or "",
            "linkedin": profile.linkedin or "",
            "github": profile.github or "",
        },
        "summary": selection.summary,
        "experience": resolved_experience,
        "projects": resolved_projects,
        "education": resolved_education,
        "skills": selection.skills,
    }


def _resolve_cover_letter(profile: Profile, draft: CoverLetterDraft, company: str | None) -> dict:
    return {
        "profile": {
            "name": profile.name,
            "email": profile.email,
            "phone": profile.phone or "",
            "location": profile.location or "",
            "linkedin": profile.linkedin or "",
        },
        "company": company or "Hiring Team",
        "paragraphs": [p.text for p in draft.paragraphs],
    }


# ---------------------------------------------------------------------------
# Public render functions
# ---------------------------------------------------------------------------

def render_resume(
    profile: Profile,
    selection: ResumeSelection,
    templates_dir: pathlib.Path | None = None,
) -> str:
    env = _make_env(templates_dir) if templates_dir else _env
    template = env.get_template("resume.tex.j2")
    context = _resolve_resume(profile, selection)
    return template.render(**context)


def render_cover_letter(
    profile: Profile,
    draft: CoverLetterDraft,
    company: str | None = None,
    templates_dir: pathlib.Path | None = None,
) -> str:
    env = _make_env(templates_dir) if templates_dir else _env
    template = env.get_template("cover_letter.tex.j2")
    context = _resolve_cover_letter(profile, draft, company)
    return template.render(**context)
