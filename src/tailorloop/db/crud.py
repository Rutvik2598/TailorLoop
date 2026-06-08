from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from ..models import (
    BulletVariant,
    ContentBank,
    EducationEntry,
    ExperienceEntry,
    Profile,
    ProjectEntry,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

def get_meta(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM profile_meta WHERE id = 1").fetchone()
    return dict(row) if row else None


def upsert_meta(conn: sqlite3.Connection, name: str, email: str, **kwargs: Any) -> dict[str, Any]:
    conn.execute("""
        INSERT INTO profile_meta (id, name, email, phone, location, linkedin, github, summary)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, email=excluded.email, phone=excluded.phone,
            location=excluded.location, linkedin=excluded.linkedin,
            github=excluded.github, summary=excluded.summary
    """, (name, email, kwargs.get("phone"), kwargs.get("location"),
          kwargs.get("linkedin"), kwargs.get("github"), kwargs.get("summary")))
    return get_meta(conn)  # type: ignore[return-value]


def patch_meta(conn: sqlite3.Connection, updates: dict[str, Any]) -> dict[str, Any] | None:
    current = get_meta(conn)
    if not current:
        return None
    merged = dict(current)
    merged.update(updates)
    conn.execute(
        "UPDATE profile_meta SET name=?, email=?, phone=?, location=?, linkedin=?, github=?, summary=? WHERE id=1",
        (merged["name"], merged["email"], merged.get("phone"), merged.get("location"),
         merged.get("linkedin"), merged.get("github"), merged.get("summary")),
    )
    return get_meta(conn)


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

def _build_experience(conn: sqlite3.Connection, row: sqlite3.Row) -> ExperienceEntry:
    bullet_rows = conn.execute(
        "SELECT * FROM experience_bullets WHERE experience_id = ? ORDER BY display_order",
        (row["id"],),
    ).fetchall()
    return ExperienceEntry(
        id=row["id"],
        company=row["company"],
        title=row["title"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        location=row["location"],
        bullets=[BulletVariant(id=b["id"], text=b["text"]) for b in bullet_rows],
    )


def list_experience(conn: sqlite3.Connection) -> list[ExperienceEntry]:
    rows = conn.execute("SELECT * FROM experience ORDER BY display_order").fetchall()
    return [_build_experience(conn, r) for r in rows]


def get_experience(conn: sqlite3.Connection, exp_id: str) -> ExperienceEntry | None:
    row = conn.execute("SELECT * FROM experience WHERE id = ?", (exp_id,)).fetchone()
    return _build_experience(conn, row) if row else None


def create_experience(
    conn: sqlite3.Connection,
    company: str,
    title: str,
    start_date: str,
    end_date: str | None = None,
    location: str | None = None,
) -> ExperienceEntry:
    exp_id = _new_id("exp")
    order = conn.execute("SELECT COUNT(*) FROM experience").fetchone()[0]
    conn.execute(
        "INSERT INTO experience (id, company, title, start_date, end_date, location, display_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (exp_id, company, title, start_date, end_date, location, order),
    )
    return ExperienceEntry(id=exp_id, company=company, title=title,
                           start_date=start_date, end_date=end_date,
                           location=location, bullets=[])


def update_experience(
    conn: sqlite3.Connection, exp_id: str, updates: dict[str, Any]
) -> ExperienceEntry | None:
    row = conn.execute("SELECT * FROM experience WHERE id = ?", (exp_id,)).fetchone()
    if not row:
        return None
    current = dict(row)
    current.update(updates)
    conn.execute(
        "UPDATE experience SET company=?, title=?, start_date=?, end_date=?, location=? WHERE id=?",
        (current["company"], current["title"], current["start_date"],
         current["end_date"], current["location"], exp_id),
    )
    return get_experience(conn, exp_id)


def delete_experience(conn: sqlite3.Connection, exp_id: str) -> bool:
    return conn.execute("DELETE FROM experience WHERE id = ?", (exp_id,)).rowcount > 0


def create_experience_bullet(conn: sqlite3.Connection, exp_id: str, text: str) -> BulletVariant:
    bullet_id = _new_id("blt")
    order = conn.execute(
        "SELECT COUNT(*) FROM experience_bullets WHERE experience_id = ?", (exp_id,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO experience_bullets (id, experience_id, text, display_order) VALUES (?, ?, ?, ?)",
        (bullet_id, exp_id, text, order),
    )
    return BulletVariant(id=bullet_id, text=text)


def update_experience_bullet(
    conn: sqlite3.Connection, bullet_id: str, text: str
) -> BulletVariant | None:
    if conn.execute(
        "UPDATE experience_bullets SET text = ? WHERE id = ?", (text, bullet_id)
    ).rowcount == 0:
        return None
    return BulletVariant(id=bullet_id, text=text)


def delete_experience_bullet(conn: sqlite3.Connection, bullet_id: str) -> bool:
    return conn.execute(
        "DELETE FROM experience_bullets WHERE id = ?", (bullet_id,)
    ).rowcount > 0


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def _build_project(conn: sqlite3.Connection, row: sqlite3.Row) -> ProjectEntry:
    bullet_rows = conn.execute(
        "SELECT * FROM project_bullets WHERE project_id = ? ORDER BY display_order",
        (row["id"],),
    ).fetchall()
    return ProjectEntry(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        tech_stack=json.loads(row["tech_stack"]),
        bullets=[BulletVariant(id=b["id"], text=b["text"]) for b in bullet_rows],
        url=row["url"],
    )


def list_projects(conn: sqlite3.Connection) -> list[ProjectEntry]:
    rows = conn.execute("SELECT * FROM projects ORDER BY display_order").fetchall()
    return [_build_project(conn, r) for r in rows]


def get_project(conn: sqlite3.Connection, project_id: str) -> ProjectEntry | None:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _build_project(conn, row) if row else None


def create_project(
    conn: sqlite3.Connection,
    name: str,
    description: str,
    tech_stack: list[str] | None = None,
    url: str | None = None,
) -> ProjectEntry:
    proj_id = _new_id("proj")
    order = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    conn.execute(
        "INSERT INTO projects (id, name, description, tech_stack, url, display_order) VALUES (?, ?, ?, ?, ?, ?)",
        (proj_id, name, description, json.dumps(tech_stack or []), url, order),
    )
    return ProjectEntry(id=proj_id, name=name, description=description,
                        tech_stack=tech_stack or [], bullets=[], url=url)


def update_project(
    conn: sqlite3.Connection, project_id: str, updates: dict[str, Any]
) -> ProjectEntry | None:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        return None
    current = dict(row)
    for key, val in updates.items():
        if key == "tech_stack":
            current[key] = json.dumps(val)
        else:
            current[key] = val
    conn.execute(
        "UPDATE projects SET name=?, description=?, tech_stack=?, url=? WHERE id=?",
        (current["name"], current["description"], current["tech_stack"], current["url"], project_id),
    )
    return get_project(conn, project_id)


def delete_project(conn: sqlite3.Connection, project_id: str) -> bool:
    return conn.execute("DELETE FROM projects WHERE id = ?", (project_id,)).rowcount > 0


def create_project_bullet(conn: sqlite3.Connection, project_id: str, text: str) -> BulletVariant:
    bullet_id = _new_id("blt")
    order = conn.execute(
        "SELECT COUNT(*) FROM project_bullets WHERE project_id = ?", (project_id,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO project_bullets (id, project_id, text, display_order) VALUES (?, ?, ?, ?)",
        (bullet_id, project_id, text, order),
    )
    return BulletVariant(id=bullet_id, text=text)


def update_project_bullet(
    conn: sqlite3.Connection, bullet_id: str, text: str
) -> BulletVariant | None:
    if conn.execute(
        "UPDATE project_bullets SET text = ? WHERE id = ?", (text, bullet_id)
    ).rowcount == 0:
        return None
    return BulletVariant(id=bullet_id, text=text)


def delete_project_bullet(conn: sqlite3.Connection, bullet_id: str) -> bool:
    return conn.execute(
        "DELETE FROM project_bullets WHERE id = ?", (bullet_id,)
    ).rowcount > 0


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------

def _build_education(row: sqlite3.Row) -> EducationEntry:
    return EducationEntry(
        id=row["id"],
        institution=row["institution"],
        degree=row["degree"],
        field=row["field"],
        graduation_year=row["graduation_year"],
        gpa=row["gpa"],
    )


def list_education(conn: sqlite3.Connection) -> list[EducationEntry]:
    rows = conn.execute("SELECT * FROM education ORDER BY display_order").fetchall()
    return [_build_education(r) for r in rows]


def get_education(conn: sqlite3.Connection, edu_id: str) -> EducationEntry | None:
    row = conn.execute("SELECT * FROM education WHERE id = ?", (edu_id,)).fetchone()
    return _build_education(row) if row else None


def create_education(
    conn: sqlite3.Connection,
    institution: str,
    degree: str,
    field: str,
    graduation_year: str,
    gpa: str | None = None,
) -> EducationEntry:
    edu_id = _new_id("edu")
    order = conn.execute("SELECT COUNT(*) FROM education").fetchone()[0]
    conn.execute(
        "INSERT INTO education (id, institution, degree, field, graduation_year, gpa, display_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (edu_id, institution, degree, field, graduation_year, gpa, order),
    )
    return EducationEntry(id=edu_id, institution=institution, degree=degree,
                          field=field, graduation_year=graduation_year, gpa=gpa)


def update_education(
    conn: sqlite3.Connection, edu_id: str, updates: dict[str, Any]
) -> EducationEntry | None:
    row = conn.execute("SELECT * FROM education WHERE id = ?", (edu_id,)).fetchone()
    if not row:
        return None
    current = dict(row)
    current.update(updates)
    conn.execute(
        "UPDATE education SET institution=?, degree=?, field=?, graduation_year=?, gpa=? WHERE id=?",
        (current["institution"], current["degree"], current["field"],
         current["graduation_year"], current["gpa"], edu_id),
    )
    return get_education(conn, edu_id)


def delete_education(conn: sqlite3.Connection, edu_id: str) -> bool:
    return conn.execute("DELETE FROM education WHERE id = ?", (edu_id,)).rowcount > 0


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

def list_skills(conn: sqlite3.Connection) -> list[str]:
    return [r["skill"] for r in conn.execute("SELECT skill FROM skills ORDER BY display_order").fetchall()]


def add_skill(conn: sqlite3.Connection, skill: str) -> bool:
    order = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    try:
        conn.execute("INSERT INTO skills (skill, display_order) VALUES (?, ?)", (skill, order))
        return True
    except sqlite3.IntegrityError:
        return False  # already exists


def delete_skill(conn: sqlite3.Connection, skill: str) -> bool:
    return conn.execute("DELETE FROM skills WHERE skill = ?", (skill,)).rowcount > 0


# ---------------------------------------------------------------------------
# Full profile assembly (used by agents)
# ---------------------------------------------------------------------------

def get_full_profile(conn: sqlite3.Connection) -> Profile | None:
    meta = get_meta(conn)
    if not meta:
        return None
    return Profile(
        name=meta["name"],
        email=meta["email"],
        phone=meta["phone"],
        location=meta["location"],
        linkedin=meta["linkedin"],
        github=meta["github"],
        summary=meta["summary"],
        content_bank=ContentBank(
            experience=list_experience(conn),
            projects=list_projects(conn),
            education=list_education(conn),
            skills=list_skills(conn),
        ),
    )
