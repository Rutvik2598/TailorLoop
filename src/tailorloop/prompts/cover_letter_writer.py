from __future__ import annotations


def build_prompt(
    jd_profile_json: str,
    profile_json: str,
    content_bank_json: str,
    rejection_reasons: list[str] | None = None,
) -> str:
    base = f"""\
You are writing a cover letter for a job application. \
Every factual claim must be grounded in the candidate's real experience.

━━━ ABSOLUTE RULES ━━━
1. Every claim about skills, achievements, employers, tools, or metrics must trace \
to an entry in the content bank. Supply the source_entry_ids for each paragraph.
2. Never invent, exaggerate, or embellish — stay faithful to what the content bank says.
3. Reference concrete details from the job description: the company name (if given), \
specific responsibilities, specific technologies, or stated values. Generic letters fail.
4. The cover letter should be 3–4 paragraphs: opening (why this role), relevant \
experience (strongest 1–2 achievements), fit (skills + culture), closing call to action.
━━━━━━━━━━━━━━━━━━━━━

Job Description Analysis:
{jd_profile_json}

Candidate Profile (for personal details):
{profile_json}

Content Bank (the ONLY source of factual claims):
{content_bank_json}
"""

    if rejection_reasons:
        formatted = "\n".join(f"  - {r}" for r in rejection_reasons)
        base += f"""
━━━ FEEDBACK FROM PREVIOUS ATTEMPT ━━━
The following issues were found in your last draft. Fix them before returning.
{formatted}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    base += """
Return JSON matching the CoverLetterDraft schema. \
In jd_specifics_used, list the concrete JD details you referenced (e.g. \
"Kafka-based event pipeline", "FinCore Technologies", "100k events/second target").
"""
    return base
