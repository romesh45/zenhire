"""
Unified LLM router for all agents.

Builds a LiteLLM Router with every configured provider loaded under two
logical model groups:
  - "smart"  → Resume Agent + Evaluator Agent (GPT-4o class)
  - "fast"   → Interview Agent (GPT-4o-mini class)

The router tries all configured providers in order and falls back
automatically on failure (rate limit, outage, etc.).

Embeddings use sentence-transformers (all-MiniLM-L6-v2) — fully local, no API key required.
"""

from __future__ import annotations

import litellm
from litellm import Router

from app.core.config import settings

# Silence litellm's verbose success logs
litellm.suppress_debug_info = True


def build_router() -> Router:
    model_list: list[dict] = []

    # ── Smart model group ────────────────────────────────────────────────────
    if settings.OPENAI_API_KEY:
        model_list.append({
            "model_name": "smart",
            "litellm_params": {
                "model": "gpt-4o",
                "api_key": settings.OPENAI_API_KEY,
            },
        })
    if settings.ANTHROPIC_API_KEY:
        model_list.append({
            "model_name": "smart",
            "litellm_params": {
                "model": "anthropic/claude-sonnet-4-6",
                "api_key": settings.ANTHROPIC_API_KEY,
            },
        })
    if settings.GROQ_API_KEY:
        model_list.append({
            "model_name": "smart",
            "litellm_params": {
                "model": "groq/llama-3.3-70b-versatile",
                "api_key": settings.GROQ_API_KEY,
            },
        })
    if settings.OPENROUTER_API_KEY:
        model_list.append({
            "model_name": "smart",
            "litellm_params": {
                "model": "openrouter/anthropic/claude-sonnet-4-6",
                "api_key": settings.OPENROUTER_API_KEY,
                "api_base": "https://openrouter.ai/api/v1",
            },
        })

    # ── Fast model group ─────────────────────────────────────────────────────
    if settings.OPENAI_API_KEY:
        model_list.append({
            "model_name": "fast",
            "litellm_params": {
                "model": "gpt-4o-mini",
                "api_key": settings.OPENAI_API_KEY,
            },
        })
    if settings.ANTHROPIC_API_KEY:
        model_list.append({
            "model_name": "fast",
            "litellm_params": {
                "model": "anthropic/claude-haiku-4-5-20251001",
                "api_key": settings.ANTHROPIC_API_KEY,
            },
        })
    if settings.GROQ_API_KEY:
        model_list.append({
            "model_name": "fast",
            "litellm_params": {
                "model": "groq/llama-3.1-8b-instant",
                "api_key": settings.GROQ_API_KEY,
            },
        })
    if settings.OPENROUTER_API_KEY:
        model_list.append({
            "model_name": "fast",
            "litellm_params": {
                "model": "openrouter/google/gemma-3-27b-it",
                "api_key": settings.OPENROUTER_API_KEY,
                "api_base": "https://openrouter.ai/api/v1",
            },
        })

    if not model_list:
        raise ValueError(
            "No LLM provider configured. "
            "Set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, "
            "GROQ_API_KEY, OPENROUTER_API_KEY in your .env file."
        )

    return Router(
        model_list=model_list,
        num_retries=2,
        allowed_fails=3,
        cooldown_time=30,
        set_verbose=False,
    )


_router: Router | None = None


def get_router() -> Router:
    global _router
    if _router is None:
        _router = build_router()
    return _router


async def llm_smart(messages: list[dict], **kwargs: object) -> str:
    """
    High-quality completion for Resume Agent + Evaluator Agent.
    Uses the 'smart' model group with automatic cross-provider fallback.
    """
    router = get_router()
    response = await router.acompletion(model="smart", messages=messages, **kwargs)
    return response.choices[0].message.content or ""


async def llm_fast(messages: list[dict], **kwargs: object) -> str:
    """
    Fast completion for Interview Agent.
    Uses the 'fast' model group with automatic cross-provider fallback.
    """
    router = get_router()
    response = await router.acompletion(model="fast", messages=messages, **kwargs)
    return response.choices[0].message.content or ""


