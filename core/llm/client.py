"""LLM abstraction layer — supports OpenAI and mock mode.

Provides a unified interface for LLM calls with:
- Cost tracking
- Response caching
- Mock mode for demo/testing
- Structured JSON output

INVARIANT: LLM output is EVIDENCE, never AUTHORITY.
Use sparingly — report cost before calling.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

# In-memory cache
_llm_cache: dict[str, dict] = {}
_cost_tracker = {"total_tokens_in": 0, "total_tokens_out": 0, "total_cost_usd": 0.0, "calls": 0}

# Cost per 1M tokens (approximate)
COST_TABLE = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}


def get_cost_summary() -> dict:
    """Get current cost tracking summary."""
    return {**_cost_tracker}


def _cache_key(messages: list[dict], model: str) -> str:
    """Generate a cache key for LLM request."""
    content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


class LLMClient:
    """Unified LLM client with caching and cost tracking."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4o-mini",
        mock_mode: bool = False,
        cache_enabled: bool = True,
    ):
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        resolved_base = base_url or os.environ.get("OPENAI_BASE_URL")
        self.model = model or os.environ.get("OPENAI_MODEL_PRIMARY", "gpt-4o-mini")
        self.mock_mode = mock_mode or not resolved_key
        self.cache_enabled = cache_enabled
        self._client = None

        if not self.mock_mode:
            try:
                from openai import OpenAI
                client_kwargs = {"api_key": resolved_key}
                if resolved_base:
                    client_kwargs["base_url"] = resolved_base
                self._client = OpenAI(**client_kwargs)
                logger.info(f"LLM client initialized with model={self.model}, base_url={resolved_base}")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Using mock mode.")
                self.mock_mode = True

        if self.mock_mode:
            logger.info("LLM client running in MOCK mode (no API calls)")

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        response_format_json: bool = False,
    ) -> dict[str, Any]:
        """Send a chat completion request.

        Returns:
            Dict with 'content', 'tokens_in', 'tokens_out', 'cost_usd'.
        """
        model = model or self.model

        # Check cache
        if self.cache_enabled:
            key = _cache_key(messages, model)
            if key in _llm_cache:
                logger.info("LLM cache hit")
                return {**_llm_cache[key], "cache_hit": True}

        if self.mock_mode:
            return self._mock_response(messages)

        return self._real_call(messages, model, temperature, max_tokens, response_format_json)

    def _real_call(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format_json: bool,
    ) -> dict[str, Any]:
        """Make a real API call to OpenAI."""
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format_json:
                kwargs["response_format"] = {"type": "json_object"}

            response = self._client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content or ""
            tokens_in = response.usage.prompt_tokens if response.usage else 0
            tokens_out = response.usage.completion_tokens if response.usage else 0

            # Calculate cost
            costs = COST_TABLE.get(model, COST_TABLE["gpt-4o-mini"])
            cost = (tokens_in * costs["input"] + tokens_out * costs["output"]) / 1_000_000

            # Track
            _cost_tracker["total_tokens_in"] += tokens_in
            _cost_tracker["total_tokens_out"] += tokens_out
            _cost_tracker["total_cost_usd"] += cost
            _cost_tracker["calls"] += 1

            result = {
                "content": content,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost,
                "cache_hit": False,
                "model": model,
            }

            # Cache
            if self.cache_enabled:
                key = _cache_key(messages, model)
                _llm_cache[key] = result

            logger.info(f"LLM call: {model} | {tokens_in}+{tokens_out} tokens | ${cost:.4f}")
            return result

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._mock_response(messages)

    def _mock_response(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Generate a mock response for demo/testing."""
        user_msg = messages[-1].get("content", "") if messages else ""

        # Generate context-aware mock response
        if "error" in user_msg.lower() or "anomal" in user_msg.lower():
            mock_json = {
                "label": "error",
                "confidence": 0.75,
                "explanation": "Mock: Potential data quality issue detected based on pattern analysis.",
                "suspicious_fields": [],
            }
        else:
            mock_json = {
                "label": "clean",
                "confidence": 0.85,
                "explanation": "Mock: Data appears consistent with expected patterns.",
                "suspicious_fields": [],
            }

        return {
            "content": json.dumps(mock_json),
            "tokens_in": len(user_msg) // 4,
            "tokens_out": 50,
            "cost_usd": 0.0,
            "cache_hit": False,
            "model": "mock",
            "mock": True,
        }


# Singleton — initialized lazily
_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the default LLM client."""
    global _default_client
    if _default_client is None:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        model = os.environ.get("OPENAI_MODEL_PRIMARY", "gpt-4o-mini")
        mock = not api_key or api_key.startswith("sk-your")
        _default_client = LLMClient(api_key=api_key, model=model, mock_mode=mock)
    return _default_client
