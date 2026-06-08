const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// ---------------------------------------------------------------------------
// Types (mirror Pydantic models)
// ---------------------------------------------------------------------------

export interface BulletVariant {
  id: string;
  text: string;
}

export interface ExperienceEntry {
  id: string;
  company: string;
  title: string;
  start_date: string;
  end_date: string | null;
  location: string | null;
  bullets: BulletVariant[];
}

export interface ProjectEntry {
  id: string;
  name: string;
  description: string;
  tech_stack: string[];
  bullets: BulletVariant[];
  url: string | null;
}

export interface EducationEntry {
  id: string;
  institution: string;
  degree: string;
  field: string;
  graduation_year: string;
  gpa: string | null;
}

export interface ProfileMeta {
  name: string;
  email: string;
  phone: string | null;
  location: string | null;
  linkedin: string | null;
  github: string | null;
  summary: string | null;
}

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText);
    throw new Error(body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

export const getMeta = () => request<ProfileMeta>("/api/profile/meta");
export const updateMeta = (data: Partial<ProfileMeta>) =>
  request<ProfileMeta>("/api/profile/meta", { method: "PUT", body: JSON.stringify(data) });

// ---------------------------------------------------------------------------
// Experience
// ---------------------------------------------------------------------------

export const getExperience = () => request<ExperienceEntry[]>("/api/profile/experience");

export const createExperience = (data: Omit<ExperienceEntry, "id" | "bullets">) =>
  request<ExperienceEntry>("/api/profile/experience", { method: "POST", body: JSON.stringify(data) });

export const updateExperience = (id: string, data: Partial<Omit<ExperienceEntry, "id" | "bullets">>) =>
  request<ExperienceEntry>(`/api/profile/experience/${id}`, { method: "PUT", body: JSON.stringify(data) });

export const deleteExperience = (id: string) =>
  request<void>(`/api/profile/experience/${id}`, { method: "DELETE" });

export const addExperienceBullet = (expId: string, text: string) =>
  request<BulletVariant>(`/api/profile/experience/${expId}/bullets`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });

export const updateExperienceBullet = (expId: string, bulletId: string, text: string) =>
  request<BulletVariant>(`/api/profile/experience/${expId}/bullets/${bulletId}`, {
    method: "PUT",
    body: JSON.stringify({ text }),
  });

export const deleteExperienceBullet = (expId: string, bulletId: string) =>
  request<void>(`/api/profile/experience/${expId}/bullets/${bulletId}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export const getProjects = () => request<ProjectEntry[]>("/api/profile/projects");

export const createProject = (data: Omit<ProjectEntry, "id" | "bullets">) =>
  request<ProjectEntry>("/api/profile/projects", { method: "POST", body: JSON.stringify(data) });

export const updateProject = (id: string, data: Partial<Omit<ProjectEntry, "id" | "bullets">>) =>
  request<ProjectEntry>(`/api/profile/projects/${id}`, { method: "PUT", body: JSON.stringify(data) });

export const deleteProject = (id: string) =>
  request<void>(`/api/profile/projects/${id}`, { method: "DELETE" });

export const addProjectBullet = (projId: string, text: string) =>
  request<BulletVariant>(`/api/profile/projects/${projId}/bullets`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });

export const updateProjectBullet = (projId: string, bulletId: string, text: string) =>
  request<BulletVariant>(`/api/profile/projects/${projId}/bullets/${bulletId}`, {
    method: "PUT",
    body: JSON.stringify({ text }),
  });

export const deleteProjectBullet = (projId: string, bulletId: string) =>
  request<void>(`/api/profile/projects/${projId}/bullets/${bulletId}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Education
// ---------------------------------------------------------------------------

export const getEducation = () => request<EducationEntry[]>("/api/profile/education");

export const createEducation = (data: Omit<EducationEntry, "id">) =>
  request<EducationEntry>("/api/profile/education", { method: "POST", body: JSON.stringify(data) });

export const updateEducation = (id: string, data: Partial<Omit<EducationEntry, "id">>) =>
  request<EducationEntry>(`/api/profile/education/${id}`, { method: "PUT", body: JSON.stringify(data) });

export const deleteEducation = (id: string) =>
  request<void>(`/api/profile/education/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Skills
// ---------------------------------------------------------------------------

export const getSkills = () => request<string[]>("/api/profile/skills");

export const addSkill = (skill: string) =>
  request<{ skill: string }>("/api/profile/skills", {
    method: "POST",
    body: JSON.stringify({ skill }),
  });

export const deleteSkill = (skill: string) =>
  request<void>(`/api/profile/skills/${encodeURIComponent(skill)}`, { method: "DELETE" });
