# TailorLoop

AI-powered job application copilot. Paste a job description, get a tailored résumé and cover letter PDF — every claim verified against your real experience, nothing fabricated.

## How it works

A LangGraph pipeline runs four agents against your profile and the job description:

1. **jd_analyzer** — extracts required skills, ATS keywords, and responsibilities
2. **resume_tailor** + **cover_letter_writer** — select and rephrase real entries from your content bank (run in parallel)
3. **verifier** — checks every claim traces back to your profile; rejects anything invented
4. **compile** — renders approved content to LaTeX and compiles to PDF via Tectonic

If the verifier rejects claims, the writers retry with the rejection reasons. After 2 retries, rejected content is dropped rather than kept.

---

## Prerequisites

```bash
# uv — Python package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Tectonic — LaTeX → PDF compiler
brew install tectonic

# Node.js 18+ — for the frontend
# https://nodejs.org
```

---

## Setup

### 1. Clone and install Python dependencies

```bash
git clone https://github.com/Rutvik2598/TailorLoop.git
cd TailorLoop
uv sync
```

### 2. API key

Create a `.env` file in the project root:

```bash
echo 'GOOGLE_API_KEY=your-key-here' > .env
```

Get a key at [aistudio.google.com](https://aistudio.google.com). The `.env` file is gitignored.

### 3. Install frontend dependencies

```bash
cd web && npm install && cd ..
```

---

## Running the app

### Step 1 — Initialise the database

Run once to create `tailorloop.db` and seed it with the profile data from `profile/`:

```bash
uv run --env-file .env tailorloop seed --profile profile/ --db tailorloop.db
```

To wipe and re-seed at any point, delete `tailorloop.db` and run the command again.

### Step 2 — Start the API server

```bash
uv run --env-file .env tailorloop serve --db tailorloop.db
```

Server runs at `http://127.0.0.1:8000`. Interactive API docs at `http://127.0.0.1:8000/docs`.

### Step 3 — Start the frontend

```bash
cd web && npm run dev
```

Open `http://localhost:3000`. The Generate page is the home screen — paste a job description and hit Generate.

---

## CLI usage (without the web UI)

Run the pipeline directly against a JD file:

```bash
uv run --env-file .env tailorloop run \
  --jd examples/jd_backend_engineer.txt \
  --db tailorloop.db \
  --out out/
```

Outputs:

```
out/
├── resume.pdf
├── cover_letter.pdf
└── run.json        ← full audit trail (every agent input/output)
```

**Flags**

| Flag | Default | Description |
|------|---------|-------------|
| `--db` | `tailorloop.db` | Path to SQLite database |
| `--out` | `out/` | Output directory for PDFs and audit log |
| `--max-retries N` | `2` | Verifier retry cap |
| `--no-cache` | off | Disable on-disk LLM response cache |
| `-v` | off | Verbose structured logging |

---

## Project structure

```
TailorLoop/
├── src/tailorloop/
│   ├── agents/          # jd_analyzer, resume_tailor, cover_letter_writer, verifier
│   ├── api/             # FastAPI app + generate job runner
│   ├── db/              # SQLite schema, CRUD, seeding
│   ├── llm/             # Model abstraction (get_model by role) + response cache
│   ├── prompts/         # One file per agent prompt
│   ├── graph.py         # LangGraph state graph wiring
│   ├── render.py        # ResumeSelection/CoverLetterDraft → LaTeX
│   ├── compile.py       # LaTeX → PDF via Tectonic
│   ├── models.py        # Pydantic models (Profile, RunState, etc.)
│   ├── loaders.py       # Load profile from DB or from JSON files
│   └── cli.py           # CLI commands: run, seed, serve
├── templates/           # resume.tex.j2, cover_letter.tex.j2
├── profile/             # Seed data JSON files
├── examples/            # Sample job descriptions
├── tests/               # Fabrication regression tests
├── web/                 # Next.js frontend
│   ├── app/             # Pages: generate, about, experience, projects, education, skills
│   ├── components/      # Sidebar, shadcn/ui components
│   └── lib/             # Typed API client
├── .env                 # GOOGLE_API_KEY (gitignored)
├── tailorloop.db        # SQLite database (gitignored)
└── pyproject.toml
```

---

## Stack

**Backend:** Python 3.11 · LangGraph · Pydantic v2 · FastAPI · SQLite · Google Gemini (`google-genai`) · Tectonic · Jinja2 · `uv`

**Frontend:** Next.js · TypeScript · Tailwind CSS · shadcn/ui
