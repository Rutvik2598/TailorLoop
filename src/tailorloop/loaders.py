from __future__ import annotations

import json
import pathlib

from .models import (
    BulletVariant,
    ContentBank,
    EducationEntry,
    ExperienceEntry,
    Profile,
    ProjectEntry,
)


def load_profile_from_db(db_path: str) -> Profile:
    """Load a Profile from a SQLite database populated by `tailorloop seed`."""
    from .db.database import get_conn
    from .db.crud import get_full_profile

    with get_conn(db_path) as conn:
        profile = get_full_profile(conn)

    if not profile:
        raise RuntimeError(
            f"No profile found in {db_path!r}. Run `tailorloop seed --profile <dir> --db {db_path}` first."
        )
    return profile


def load_profile(profile_dir: pathlib.Path) -> Profile:
    """Load a Profile from a directory of separate JSON files.

    Expected files:
        meta.json       — name, email, phone, location, linkedin, github, summary
        experience.json — list of ExperienceEntry objects
        projects.json   — list of ProjectEntry objects
        education.json  — list of EducationEntry objects
        skills.json     — list of skill strings
    """
    meta = json.loads((profile_dir / "meta.json").read_text(encoding="utf-8"))
    experience_raw = json.loads((profile_dir / "experience.json").read_text(encoding="utf-8"))
    projects_raw = json.loads((profile_dir / "projects.json").read_text(encoding="utf-8"))
    education_raw = json.loads((profile_dir / "education.json").read_text(encoding="utf-8"))
    skills = json.loads((profile_dir / "skills.json").read_text(encoding="utf-8"))

    content_bank = ContentBank(
        experience=[ExperienceEntry.model_validate(e) for e in experience_raw],
        projects=[ProjectEntry.model_validate(p) for p in projects_raw],
        education=[EducationEntry.model_validate(e) for e in education_raw],
        skills=skills,
    )

    return Profile(
        name=meta["name"],
        email=meta["email"],
        phone=meta.get("phone"),
        location=meta.get("location"),
        linkedin=meta.get("linkedin"),
        github=meta.get("github"),
        summary=meta.get("summary"),
        content_bank=content_bank,
    )
