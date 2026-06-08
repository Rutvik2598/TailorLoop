# TailorLoop

TailorLoop is a personal job-application copilot. Given a job description and the
user's profile, a small team of LLM agents produces a **tailored résumé and cover
letter** — both compiled to PDF — where every claim is grounded in the user's real
experience. The verification loop that enforces "nothing fabricated" is the core of
the project, not a feature bolted on.

This is a learning + portfolio project. Favor clarity and correctness over cleverness.
The interesting engineering is the orchestration and verification layer; keep it
visible and well-instrumented, not hidden behind framework magic.

---

## The one non-negotiable invariant

**No agent may invent experience, skills, metrics, employers, dates, or scope.**

Everything in a generated résumé or cover letter must trace back to an entry in the
user's profile / content bank. The tailor *selects and rephrases* real content; it
never originates new facts. The verifier's entire job is to enforce this. When in
doubt, the safe behavior is to drop a claim, not to keep an unverified one. Treat a
fabrication that slips through as the most serious possible bug.

---

## v1 scope (build this first)

- **Input:** the user pastes a job description as text. No job sourcing/scraping yet.
- **Profile:** a structured profile + content bank, loaded from local files.
- **Output:** one verified tailored résumé and one verified cover letter, each as a
  compiled PDF plus the structured selection that produced it.
- **Interface:** CLI first (a command that takes a JD file + profile and writes PDFs).
  A web UI (job cards with preview/download) comes after the core loop is solid.

Explicitly **out of scope for v1:** live job search, an "apply" button, the match-scorer
agent, batching over many jobs, auth/accounts, deployment. Do not build these yet.

---

## Architecture

A LangGraph state graph runs a per-JD pipeline. Nodes:

1. **jd_analyzer** — reads the JD, emits a structured `JDProfile` (must-have skills,
   nice-to-haves, ATS keywords, seniority, core responsibilities). Extraction only.
2. **resume_tailor** — given `JDProfile` + the content bank, chooses which real entries
   and bullet variants to feature, in what order, and emits a structured `ResumeSelection`
   (references into the bank + optional reworded text). It does NOT emit free-form LaTeX.
3. **cover_letter_writer** — given `JDProfile` + profile, emits a structured
   `CoverLetterDraft` grounded in real experience. Runs in parallel with resume_tailor.
4. **verifier** — checks every claim in the résumé selection and cover letter draft maps
   to a content-bank entry (no fabrication) and, for the cover letter, that it references
   concrete JD details (specificity). Emits per-claim verdicts: approve / reject / revise
   with reasons.
5. **compile** — deterministic, NOT an agent. Renders approved selections into the LaTeX
   template and compiles to PDF. See the `latex-resume` skill.

**Control flow / orchestration:** the graph is the orchestrator. If the verifier rejects
or flags claims, route back to the tailor / cover_letter_writer with the rejection reasons,
incrementing a retry counter. Stop after N retries (config, default 2) and surface whatever
passed plus a clear note about what was dropped. Never loop forever; never silently keep a
rejected claim.

The shared LangGraph state IS the audit log — design it so a full run can be replayed and
inspected. Log every node's input and output.

---

## Stack

- **Python 3.11+**, managed with `uv` (or venv + pip if you prefer).
- **LangGraph** for the state graph / orchestration.
- **Pydantic v2** for all structured data (profile, content bank, JDProfile, selections,
  verdicts). Structured outputs everywhere — agents return validated Pydantic models, not
  loose strings.
- **Gemini** via the `google-genai` SDK for all agents in v1.
- **Tectonic** for LaTeX → PDF compilation (self-contained, no full TeXLive install).
- **structlog** (or stdlib logging with JSON) for the audit trail.

### Models — abstract this layer

All model access goes through a single `llm/` module that exposes something like
`get_model(role: str)`. Roles map to models via config, never hardcoded at call sites:

- `judgment` roles (resume_tailor, cover_letter_writer, verifier) → Gemini Pro
  (current: `gemini-3.1-pro` — **verify the exact model ID against Google's docs**, IDs change).
- `routing`/`extraction` roles (orchestrator decisions, jd_analyzer) → Gemini Flash
  (current: `gemini-3-flash` — verify the ID).

This abstraction is load-bearing: later we add a local Ollama backend (Qwen 3.5 9B on a
16GB Mac) and a `--local` / `--fully-local` toggle that swaps roles to the local model so we
can measure the cloud-vs-local quality gap on the same test set. Build the seam now even
though v1 is all-Gemini.

### Dev hygiene

- **Cache LLM responses** keyed on (model, prompt) during development so re-running tests
  doesn't re-spend quota or time. A simple on-disk cache is fine.
- Keep prompts in their own files/module, not inline in node functions, so they're easy to
  iterate and diff.
- Make every agent's model swappable per the `llm/` abstraction above.

---

## Suggested project structure

```
tailorloop/
├── CLAUDE.md
├── pyproject.toml
├── src/tailorloop/
│   ├── models.py            # Pydantic: Profile, ContentBank, ExperienceEntry,
│   │                        #   ProjectEntry, BulletVariant, JDProfile,
│   │                        #   ResumeSelection, CoverLetterDraft, Verdict, RunState
│   ├── llm/                 # model abstraction (get_model by role), response cache
│   ├── prompts/             # one file per agent prompt
│   ├── agents/              # jd_analyzer, resume_tailor, cover_letter_writer, verifier
│   ├── graph.py             # LangGraph state graph wiring nodes + verifier loop
│   ├── render.py            # ResumeSelection/CoverLetterDraft -> LaTeX (uses skill)
│   ├── compile.py           # LaTeX -> PDF via Tectonic
│   └── cli.py               # `tailorloop run --jd path --profile path --out dir`
├── templates/               # resume.tex.j2, cover_letter.tex.j2 (Jinja2 templates)
├── profile/                 # the user's profile + content bank (sample provided)
└── tests/                   # incl. fabrication regression tests (see below)
```

---

## Conventions

- Agents return validated Pydantic models. If parsing fails, retry with the validation
  error fed back to the model; don't paper over malformed output.
- The verifier must re-read the ground truth (the content bank) itself — it must not trust
  text quoted to it by the tailor. Independence is the point.
- Content selection (LLM) and rendering (template) are strictly separated. The LLM picks
  references and supplies reworded text; `render.py` deterministically slots that into the
  LaTeX template. The LLM never writes raw LaTeX, so it can't break compilation or smuggle
  in structure.
- Write a **fabrication regression test**: a fixture profile + JD where a known-tempting
  embellishment exists (a skill adjacent to but absent from the profile). Assert the
  verifier rejects it. This test guards the core invariant — keep it green.

---

## How to run (target)

```
uv run tailorloop run --jd examples/jd_android.txt --profile profile/ --out out/
# -> out/resume.pdf, out/cover_letter.pdf, out/run.json (the audit trail)
```

When unsure about a product detail (a Gemini model ID, an SDK signature), check current
docs rather than guessing — model names and SDK surfaces change.