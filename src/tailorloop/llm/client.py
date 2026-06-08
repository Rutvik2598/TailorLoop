from __future__ import annotations

import logging
from typing import TypeVar, Type

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from ..config import config
from .cache import LLMCache

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_cache = LLMCache(config.cache_dir, enabled=config.cache_enabled)


def get_model_id(role: str) -> str:
    return config.model_for_role(role)


def call_structured(
    role: str,
    prompt: str,
    response_type: Type[T],
    *,
    max_parse_retries: int = 2,
) -> T:
    """Call Gemini with structured output and return a validated Pydantic model.

    Retries up to max_parse_retries times if the model returns malformed JSON,
    feeding the validation error back so the model can self-correct.
    """
    model_id = get_model_id(role)
    schema_name = response_type.__name__

    # Check cache first
    cached = _cache.get(model_id, prompt, schema_name)
    if cached is not None:
        logger.debug("cache_hit", extra={"model": model_id, "schema": schema_name})
        try:
            return response_type.model_validate_json(cached)
        except ValidationError:
            # Cache entry is stale/corrupt; fall through to live call
            logger.warning("corrupt_cache_entry", extra={"model": model_id, "schema": schema_name})

    client = genai.Client(api_key=config.google_api_key)
    current_prompt = prompt

    for attempt in range(max_parse_retries + 1):
        logger.debug(
            "llm_call",
            extra={"model": model_id, "schema": schema_name, "attempt": attempt},
        )
        response = client.models.generate_content(
            model=model_id,
            contents=current_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_type,
            ),
        )
        raw = response.text

        try:
            result = response_type.model_validate_json(raw)
            # Only cache a response that validates successfully
            _cache.put(model_id, prompt, schema_name, raw)
            return result
        except ValidationError as exc:
            if attempt == max_parse_retries:
                raise
            logger.warning(
                "parse_retry",
                extra={"attempt": attempt, "error": str(exc)},
            )
            # Feed the validation error back so the model can fix it
            current_prompt = (
                f"{prompt}\n\n"
                f"Your previous response failed JSON validation with this error:\n"
                f"{exc}\n\n"
                f"Return corrected JSON that passes validation."
            )

    raise RuntimeError("unreachable")  # loop always raises or returns
