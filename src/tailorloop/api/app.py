from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..db.database import DEFAULT_DB_PATH, get_conn, init_db
from ..db import crud
from ..models import BulletVariant, EducationEntry, ExperienceEntry, Profile, ProjectEntry


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class MetaUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    summary: str | None = None


class ExperienceCreate(BaseModel):
    company: str
    title: str
    start_date: str
    end_date: str | None = None
    location: str | None = None


class ExperienceUpdate(BaseModel):
    company: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None


class BulletCreate(BaseModel):
    text: str


class ProjectCreate(BaseModel):
    name: str
    description: str
    tech_stack: list[str] = []
    url: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tech_stack: list[str] | None = None
    url: str | None = None


class EducationCreate(BaseModel):
    institution: str
    degree: str
    field: str
    graduation_year: str
    gpa: str | None = None


class EducationUpdate(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    graduation_year: str | None = None
    gpa: str | None = None


class SkillCreate(BaseModel):
    skill: str


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(db_path: str = DEFAULT_DB_PATH) -> FastAPI:
    app = FastAPI(title="TailorLoop Profile API", version="1.0.0")
    app.state.db_path = db_path

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup() -> None:
        init_db(app.state.db_path)

    def get_db(request: Request):
        with get_conn(request.app.state.db_path) as conn:
            yield conn

    # --- Full profile (what agents consume) ---

    @app.get("/api/profile", response_model=Profile)
    def get_profile(conn=Depends(get_db)) -> Any:
        profile = crud.get_full_profile(conn)
        if not profile:
            raise HTTPException(404, "No profile found. Run `tailorloop seed` first.")
        return profile

    # --- Meta ---

    @app.get("/api/profile/meta")
    def get_meta(conn=Depends(get_db)) -> Any:
        meta = crud.get_meta(conn)
        if not meta:
            raise HTTPException(404, "No profile meta found.")
        return meta

    @app.put("/api/profile/meta")
    def update_meta(body: MetaUpdate, conn=Depends(get_db)) -> Any:
        if not crud.get_meta(conn):
            raise HTTPException(404, "No profile found. Run `tailorloop seed` first.")
        return crud.patch_meta(conn, body.model_dump(exclude_unset=True))

    # --- Experience ---

    @app.get("/api/profile/experience", response_model=list[ExperienceEntry])
    def list_experience(conn=Depends(get_db)) -> Any:
        return crud.list_experience(conn)

    @app.post("/api/profile/experience", response_model=ExperienceEntry, status_code=201)
    def create_experience(body: ExperienceCreate, conn=Depends(get_db)) -> Any:
        return crud.create_experience(conn, **body.model_dump())

    @app.put("/api/profile/experience/{exp_id}", response_model=ExperienceEntry)
    def update_experience(exp_id: str, body: ExperienceUpdate, conn=Depends(get_db)) -> Any:
        entry = crud.update_experience(conn, exp_id, body.model_dump(exclude_unset=True))
        if not entry:
            raise HTTPException(404, f"Experience {exp_id!r} not found.")
        return entry

    @app.delete("/api/profile/experience/{exp_id}", status_code=204)
    def delete_experience(exp_id: str, conn=Depends(get_db)) -> None:
        if not crud.delete_experience(conn, exp_id):
            raise HTTPException(404, f"Experience {exp_id!r} not found.")

    @app.post("/api/profile/experience/{exp_id}/bullets", response_model=BulletVariant, status_code=201)
    def add_experience_bullet(exp_id: str, body: BulletCreate, conn=Depends(get_db)) -> Any:
        if not crud.get_experience(conn, exp_id):
            raise HTTPException(404, f"Experience {exp_id!r} not found.")
        return crud.create_experience_bullet(conn, exp_id, body.text)

    @app.put("/api/profile/experience/{exp_id}/bullets/{bullet_id}", response_model=BulletVariant)
    def update_experience_bullet(exp_id: str, bullet_id: str, body: BulletCreate, conn=Depends(get_db)) -> Any:
        bullet = crud.update_experience_bullet(conn, bullet_id, body.text)
        if not bullet:
            raise HTTPException(404, f"Bullet {bullet_id!r} not found.")
        return bullet

    @app.delete("/api/profile/experience/{exp_id}/bullets/{bullet_id}", status_code=204)
    def delete_experience_bullet(exp_id: str, bullet_id: str, conn=Depends(get_db)) -> None:
        if not crud.delete_experience_bullet(conn, bullet_id):
            raise HTTPException(404, f"Bullet {bullet_id!r} not found.")

    # --- Projects ---

    @app.get("/api/profile/projects", response_model=list[ProjectEntry])
    def list_projects(conn=Depends(get_db)) -> Any:
        return crud.list_projects(conn)

    @app.post("/api/profile/projects", response_model=ProjectEntry, status_code=201)
    def create_project(body: ProjectCreate, conn=Depends(get_db)) -> Any:
        return crud.create_project(conn, **body.model_dump())

    @app.put("/api/profile/projects/{project_id}", response_model=ProjectEntry)
    def update_project(project_id: str, body: ProjectUpdate, conn=Depends(get_db)) -> Any:
        entry = crud.update_project(conn, project_id, body.model_dump(exclude_unset=True))
        if not entry:
            raise HTTPException(404, f"Project {project_id!r} not found.")
        return entry

    @app.delete("/api/profile/projects/{project_id}", status_code=204)
    def delete_project(project_id: str, conn=Depends(get_db)) -> None:
        if not crud.delete_project(conn, project_id):
            raise HTTPException(404, f"Project {project_id!r} not found.")

    @app.post("/api/profile/projects/{project_id}/bullets", response_model=BulletVariant, status_code=201)
    def add_project_bullet(project_id: str, body: BulletCreate, conn=Depends(get_db)) -> Any:
        if not crud.get_project(conn, project_id):
            raise HTTPException(404, f"Project {project_id!r} not found.")
        return crud.create_project_bullet(conn, project_id, body.text)

    @app.put("/api/profile/projects/{project_id}/bullets/{bullet_id}", response_model=BulletVariant)
    def update_project_bullet(project_id: str, bullet_id: str, body: BulletCreate, conn=Depends(get_db)) -> Any:
        bullet = crud.update_project_bullet(conn, bullet_id, body.text)
        if not bullet:
            raise HTTPException(404, f"Bullet {bullet_id!r} not found.")
        return bullet

    @app.delete("/api/profile/projects/{project_id}/bullets/{bullet_id}", status_code=204)
    def delete_project_bullet(project_id: str, bullet_id: str, conn=Depends(get_db)) -> None:
        if not crud.delete_project_bullet(conn, bullet_id):
            raise HTTPException(404, f"Bullet {bullet_id!r} not found.")

    # --- Education ---

    @app.get("/api/profile/education", response_model=list[EducationEntry])
    def list_education(conn=Depends(get_db)) -> Any:
        return crud.list_education(conn)

    @app.post("/api/profile/education", response_model=EducationEntry, status_code=201)
    def create_education(body: EducationCreate, conn=Depends(get_db)) -> Any:
        return crud.create_education(conn, **body.model_dump())

    @app.put("/api/profile/education/{edu_id}", response_model=EducationEntry)
    def update_education(edu_id: str, body: EducationUpdate, conn=Depends(get_db)) -> Any:
        entry = crud.update_education(conn, edu_id, body.model_dump(exclude_unset=True))
        if not entry:
            raise HTTPException(404, f"Education {edu_id!r} not found.")
        return entry

    @app.delete("/api/profile/education/{edu_id}", status_code=204)
    def delete_education(edu_id: str, conn=Depends(get_db)) -> None:
        if not crud.delete_education(conn, edu_id):
            raise HTTPException(404, f"Education {edu_id!r} not found.")

    # --- Skills ---

    @app.get("/api/profile/skills", response_model=list[str])
    def list_skills(conn=Depends(get_db)) -> Any:
        return crud.list_skills(conn)

    @app.post("/api/profile/skills", status_code=201)
    def add_skill(body: SkillCreate, conn=Depends(get_db)) -> Any:
        if not crud.add_skill(conn, body.skill):
            raise HTTPException(409, f"Skill {body.skill!r} already exists.")
        return {"skill": body.skill}

    @app.delete("/api/profile/skills/{skill}", status_code=204)
    def delete_skill(skill: str, conn=Depends(get_db)) -> None:
        if not crud.delete_skill(conn, skill):
            raise HTTPException(404, f"Skill {skill!r} not found.")

    return app
