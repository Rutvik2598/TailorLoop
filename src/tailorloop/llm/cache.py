from __future__ import annotations

import hashlib
import json
from pathlib import Path


class LLMCache:
    """On-disk cache keyed on (model, prompt, schema_name) → raw JSON string."""

    def __init__(self, cache_dir: str, enabled: bool = True) -> None:
        self._dir = Path(cache_dir)
        self._enabled = enabled
        if self._enabled:
            self._dir.mkdir(parents=True, exist_ok=True)

    def _key(self, model: str, prompt: str, schema_name: str) -> str:
        raw = json.dumps(
            {"model": model, "prompt": prompt, "schema": schema_name},
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, model: str, prompt: str, schema_name: str) -> str | None:
        if not self._enabled:
            return None
        path = self._dir / self._key(model, prompt, schema_name)
        return path.read_text(encoding="utf-8") if path.exists() else None

    def put(self, model: str, prompt: str, schema_name: str, response: str) -> None:
        if not self._enabled:
            return
        path = self._dir / self._key(model, prompt, schema_name)
        path.write_text(response, encoding="utf-8")
