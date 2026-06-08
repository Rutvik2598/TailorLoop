from __future__ import annotations

import json
import pathlib
import sqlite3
from contextlib import contextmanager
from typing import Generator

DEFAULT_DB_PATH = "tailorloop.db"


@contextmanager
def get_conn(db_path: str = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create all tables if they don't exist yet."""
    with get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profile_meta (
                id      INTEGER PRIMARY KEY CHECK (id = 1),
                name    TEXT NOT NULL,
                email   TEXT NOT NULL,
                phone   TEXT,
                location TEXT,
                linkedin TEXT,
                github  TEXT,
                summary TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experience (
                id            TEXT PRIMARY KEY,
                company       TEXT NOT NULL,
                title         TEXT NOT NULL,
                start_date    TEXT NOT NULL,
                end_date      TEXT,
                location      TEXT,
                display_order INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experience_bullets (
                id            TEXT PRIMARY KEY,
                experience_id TEXT NOT NULL REFERENCES experience(id) ON DELETE CASCADE,
                text          TEXT NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id            TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                description   TEXT NOT NULL,
                tech_stack    TEXT NOT NULL DEFAULT '[]',
                url           TEXT,
                display_order INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_bullets (
                id            TEXT PRIMARY KEY,
                project_id    TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                text          TEXT NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS education (
                id              TEXT PRIMARY KEY,
                institution     TEXT NOT NULL,
                degree          TEXT NOT NULL,
                field           TEXT NOT NULL,
                graduation_year TEXT NOT NULL,
                gpa             TEXT,
                display_order   INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill         TEXT PRIMARY KEY,
                display_order INTEGER NOT NULL DEFAULT 0
            )
        """)


def seed_from_profile_dir(profile_dir: pathlib.Path, db_path: str = DEFAULT_DB_PATH) -> None:
    """Populate the DB from flat JSON profile files (idempotent — uses INSERT OR REPLACE)."""
    meta = json.loads((profile_dir / "meta.json").read_text(encoding="utf-8"))
    experience_raw = json.loads((profile_dir / "experience.json").read_text(encoding="utf-8"))
    projects_raw = json.loads((profile_dir / "projects.json").read_text(encoding="utf-8"))
    education_raw = json.loads((profile_dir / "education.json").read_text(encoding="utf-8"))
    skills = json.loads((profile_dir / "skills.json").read_text(encoding="utf-8"))

    init_db(db_path)

    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO profile_meta (id, name, email, phone, location, linkedin, github, summary)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """, (
            meta["name"], meta["email"],
            meta.get("phone"), meta.get("location"),
            meta.get("linkedin"), meta.get("github"),
            meta.get("summary"),
        ))

        for i, exp in enumerate(experience_raw):
            conn.execute("""
                INSERT OR REPLACE INTO experience (id, company, title, start_date, end_date, location, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (exp["id"], exp["company"], exp["title"], exp["start_date"],
                  exp.get("end_date"), exp.get("location"), i))
            for j, bullet in enumerate(exp.get("bullets", [])):
                conn.execute("""
                    INSERT OR REPLACE INTO experience_bullets (id, experience_id, text, display_order)
                    VALUES (?, ?, ?, ?)
                """, (bullet["id"], exp["id"], bullet["text"], j))

        for i, proj in enumerate(projects_raw):
            conn.execute("""
                INSERT OR REPLACE INTO projects (id, name, description, tech_stack, url, display_order)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (proj["id"], proj["name"], proj["description"],
                  json.dumps(proj.get("tech_stack", [])), proj.get("url"), i))
            for j, bullet in enumerate(proj.get("bullets", [])):
                conn.execute("""
                    INSERT OR REPLACE INTO project_bullets (id, project_id, text, display_order)
                    VALUES (?, ?, ?, ?)
                """, (bullet["id"], proj["id"], bullet["text"], j))

        for i, edu in enumerate(education_raw):
            conn.execute("""
                INSERT OR REPLACE INTO education (id, institution, degree, field, graduation_year, gpa, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (edu["id"], edu["institution"], edu["degree"], edu["field"],
                  edu["graduation_year"], edu.get("gpa"), i))

        for i, skill in enumerate(skills):
            conn.execute(
                "INSERT OR IGNORE INTO skills (skill, display_order) VALUES (?, ?)",
                (skill, i),
            )
