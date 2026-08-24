"""
One place that knows how to talk to a model. Everything else in the agent
calls `chat()` and never touches an SDK directly — this is what makes it
trivial to swap NVIDIA NIM for OpenAI/Anthropic/a local model later.

NVIDIA NIM ships an OpenAI-compatible endpoint, so the `openai` python
package works unmodified — we just point `base_url` at NVIDIA and use an
`nvapi-...` key instead of an `sk-...` key.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from openai import OpenAI

from app.config import settings


def _client() -> OpenAI:
    if settings.LLM_PROVIDER == "nvidia_nim":
        return OpenAI(base_url=settings.NVIDIA_BASE_URL, api_key=settings.NVIDIA_API_KEY)
    if settings.LLM_PROVIDER == "openai":
        return OpenAI(api_key=settings.OPENAI_API_KEY)
    if settings.LLM_PROVIDER == "anthropic":
        # Anthropic's Messages API is close-but-not-identical to OpenAI's;
        # swap this for `anthropic.Anthropic()` + a small adapter if you
        # switch providers. Left as a clear extension point.
        raise NotImplementedError(
            "Anthropic provider selected — add an adapter in llm_client.py "
            "(the Anthropic Python SDK's tool-call schema differs slightly "
            "from OpenAI's; see docs.anthropic.com for the messages.create tools param)."
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}")


def chat(
    messages: list[dict[str, Any]],
    tools: Optional[list[dict[str, Any]]] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """
    Thin wrapper around chat.completions.create.
    Returns a plain dict: {"content": str | None, "tool_calls": [...] }
    """
    client = _client()
    resp = client.chat.completions.create(
        model=model or settings.AGENT_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto" if tools else None,
        temperature=temperature,
    )
    choice = resp.choices[0].message
    tool_calls = []
    if choice.tool_calls:
        for tc in choice.tool_calls:
            tool_calls.append(
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments or "{}"),
                }
            )
    return {"content": choice.content, "tool_calls": tool_calls}
