from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # --- Gemini model IDs ---
    judgment_model: str = "gemini-3.5-flash"
    extraction_model: str = "gemini-3.5-flash"

    # --- Retry cap for the verifier feedback loop ---
    max_retries: int = 2

    # --- On-disk LLM response cache (keyed on model + prompt hash) ---
    cache_dir: str = ".cache/llm"
    cache_enabled: bool = True

    # --- Google API key (from environment) ---
    google_api_key: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_API_KEY", "")
    )

    # --- Role → model mapping (override individual roles here) ---
    # Seam for future Ollama backend: swap these to "ollama/qwen3:9b" etc.
    role_overrides: dict[str, str] = field(default_factory=dict)

    def model_for_role(self, role: str) -> str:
        if role in self.role_overrides:
            return self.role_overrides[role]
        judgment_roles = {"resume_tailor", "cover_letter_writer", "verifier"}
        extraction_roles = {"jd_analyzer", "routing"}
        if role in judgment_roles:
            return self.judgment_model
        if role in extraction_roles:
            return self.extraction_model
        raise ValueError(f"Unknown role: {role!r}")


# Module-level singleton — agents import this directly
config = Config()
