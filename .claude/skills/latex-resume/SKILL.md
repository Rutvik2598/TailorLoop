---
name: latex-resume
description: >-
  Render structured résumé/cover-letter data into LaTeX and compile to PDF with Tectonic.
  Use this skill WHENEVER the task involves generating, rendering, or compiling a résumé or
  cover letter to PDF, editing the LaTeX templates, escaping user content for LaTeX, handling
  Tectonic compilation or compile failures, or wiring the render/compile steps of TailorLoop.
  Trigger it even if the user just says "build the PDF step", "compile the resume", "fix the
  LaTeX", or "render the cover letter" without naming LaTeX explicitly.
---

# LaTeX résumé & cover-letter rendering

This skill encodes how TailorLoop turns **structured, verified data** into a compiled PDF.
It exists because programmatic LaTeX has sharp edges (escaping, fragile compilation, font
gaps) that are easy to get wrong and tedious to rediscover.

## Core principle: data in, PDF out — the LLM never writes LaTeX

The pipeline is strictly: `ResumeSelection`/`CoverLetterDraft` (validated Pydantic) →
Jinja2 template → `.tex` string → Tectonic → PDF. The language model supplies *content*
(which entries, reworded bullet text); this skill supplies *structure*. Never let model
output reach the `.tex` file unescaped, and never let the model emit raw LaTeX — that path
breaks compilation and is where fabricated structure sneaks in.

## Templates

Keep two Jinja2 templates in `templates/`: `resume.tex.j2` and `cover_letter.tex.j2`.

Use a Jinja environment configured so its delimiters don't collide with LaTeX's `{}`:

```python
import jinja2
env = jinja2.Environment(
    block_start_string=r"\BLOCK{", block_end_string="}",
    variable_start_string=r"\VAR{", variable_end_string="}",
    comment_start_string=r"\#{", comment_end_string="}",
    line_statement_prefix="%%", line_comment_prefix="%#",
    trim_blocks=True, autoescape=False,  # we escape manually, see below
    loader=jinja2.FileSystemLoader("templates"),
)
```

So in the template you write `\VAR{name}` and `\BLOCK{for job in experience}` instead of
`{{ }}` / `{% %}`, which would fight LaTeX braces.

Start from a clean single-column résumé class. `article` with custom spacing is the most
portable; avoid exotic CTAN classes that Tectonic would need to fetch and that may not exist.
A minimal, ATS-friendly layout (no multi-column, no images, selectable text) is the goal —
fancy two-column templates often serialize badly for ATS parsers anyway.

## Escaping (do this for every piece of model/user text)

LaTeX special characters must be escaped before insertion. Apply this to every string that
comes from the profile or the model:

```python
_LATEX_SPECIAL = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}
def latex_escape(s: str) -> str:
    # escape backslash FIRST is wrong because the replacements add backslashes;
    # build the result in one pass instead:
    out = []
    for ch in s:
        out.append(_LATEX_SPECIAL.get(ch, ch))
    return "".join(out)
```

Register `latex_escape` as a Jinja filter and apply it explicitly (`\VAR{bullet | e}` with a
custom `e`), since `autoescape` is off. Bullets, names, company names, and especially
URLs/emails (which contain `_`, `%`, `#`, `~`) all need it. A single unescaped `&` or `_` is
the most common cause of a compile failure.

## Compiling with Tectonic

Tectonic is self-contained — it downloads what it needs and caches it, so no full TeXLive.

```bash
# install (macOS): brew install tectonic
tectonic --chatter minimal --outdir <outdir> <path/to/resume.tex>
```

In Python, run it in a subprocess against a temp `.tex` file:

```python
import subprocess, tempfile, pathlib
def compile_pdf(tex: str, outdir: pathlib.Path, name: str) -> pathlib.Path:
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        texpath = pathlib.Path(td) / f"{name}.tex"
        texpath.write_text(tex, encoding="utf-8")
        proc = subprocess.run(
            ["tectonic", "--chatter", "minimal", "--outdir", str(outdir), str(texpath)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise LaTeXCompileError(proc.stderr, tex)  # include the .tex for debugging
    return outdir / f"{name}.pdf"
```

The first Tectonic run downloads packages and is slow; subsequent runs hit the cache and are
fast. Don't treat the first-run delay as a hang.

## Handling compile failures

When `returncode != 0`:
- Surface Tectonic's stderr AND save the offending `.tex` so the failure is debuggable.
- The overwhelming majority of failures are unescaped special characters — check escaping
  first before suspecting the template.
- Do NOT ask the model to "fix the LaTeX." Fix the escaping or the template deterministically.
  Routing compile errors back to an LLM reintroduces the fabrication/breakage risk this whole
  design exists to prevent.

## Output

For each document return: the PDF path, the rendered `.tex` (keep it; useful for debugging
and lets the user hand-edit), and a reference back to the structured selection that produced
it (for the audit trail).