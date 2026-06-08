# TailorLoop

AI-powered job application copilot. Paste a job description, get a tailored résumé and cover letter PDF — every claim verified against your real experience, nothing fabricated.

## How it works

A LangGraph pipeline runs four agents against your profile and the job description:

1. **jd_analyzer** — extracts required skills, ATS keywords, responsibilities
2. **resume_tailor** + **cover_letter_writer** — select and rephrase real entries from your content bank (run in parallel)
3. **verifier** — checks every claim traces back to your profile; rejects anything invented
4. **compile** — renders approved content to LaTeX and compiles to PDF via Tectonic

If the verifier rejects claims, the writers retry with the rejection reasons. After 2 retries, rejected content is dropped rather than kept.

## Setup

**Prerequisites**

```bash
# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Tectonic (LaTeX → PDF compiler)
brew install tectonic
```

**API key** — add to your shell config once:

```bash
echo 'export GOOGLE_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**Install dependencies**

```bash
uv sync
```

## Usage

```bash
uv run tailorloop run \
  --jd examples/jd_backend_engineer.txt \
  --profile profile/ \
  --out out/
```

Outputs:

```
out/
├── resume.pdf
├── cover_letter.pdf
└── run.json        ← full audit trail
```

**Flags**

| Flag | Description |
|------|-------------|
| `--pro` | Use `gemini-3.1-pro-preview` for judgment agents (higher quality, higher cost) |
| `--no-cache` | Disable on-disk LLM response cache |
| `--max-retries N` | Override verifier retry cap (default: 2) |
| `-v` | Verbose logging |

## Your profile

Edit the files in `profile/` to use your own experience:

| File | Contents |
|------|----------|
| `meta.json` | Name, email, location, LinkedIn, GitHub, summary |
| `experience.json` | Work history with bullet variants |
| `projects.json` | Side projects with bullet variants |
| `education.json` | Degrees |
| `skills.json` | Flat list of verified skills |

Every bullet and skill must have a unique `id` — the verifier uses these IDs to trace claims back to the source.

## Stack

Python 3.11 · LangGraph · Pydantic v2 · Google Gemini (via `google-genai`) · Tectonic · Jinja2
