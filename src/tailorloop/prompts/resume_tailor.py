from __future__ import annotations

import json


def build_prompt(
    jd_profile_json: str,
    content_bank_json: str,
    rejection_reasons: list[str] | None = None,
) -> str:
    base = f"""\
You are a resume tailoring assistant. Select the best content from the candidate's \
profile to match this job description.

━━━ ABSOLUTE RULES — violating any of these is a critical bug ━━━
1. You may ONLY reference entries that exist in the content bank, using their exact IDs.
2. Each SelectedBullet must reference a real entry_id AND a real bullet_id from that entry.
3. You may reword a bullet (reworded_text), but only to rephrase the SAME achievement — \
never add skills, metrics, scope, tools, or facts not present in the original bullet text.
4. Skills must only be included if they appear verbatim in the content bank's skills list.
5. Summary (if included) must be a rephrasing of the candidate's existing summary, \
not new claims.
6. When in doubt, OMIT a bullet rather than stretch the truth.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Job Description Analysis:
{jd_profile_json}

Candidate Content Bank (the ONLY source of truth):
{content_bank_json}
"""

    if rejection_reasons:
        formatted = "\n".join(f"  - {r}" for r in rejection_reasons)
        base += f"""
━━━ FEEDBACK FROM PREVIOUS ATTEMPT ━━━
The following issues were found in your last selection. Fix them before returning.
{formatted}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    base += """
Return JSON matching the ResumeSelection schema. Include only entries and bullets that \
genuinely highlight relevant experience. Order experience entries most-recent first.
"""
    return base
