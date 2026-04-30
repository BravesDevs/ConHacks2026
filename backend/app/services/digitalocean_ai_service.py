from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings


DO_AI_BASE_URL = "https://inference.do-ai.run/v1/chat/completions"
DO_AI_MODEL = "nemotron-nano-12b-v2-vl"


async def chat_complete(
    settings: Settings,
    *,
    messages: list[dict[str, str]],
    max_tokens: int = 600,
) -> str:
    api_key = (settings.digitalocean_openapi_key or "").strip()
    if not api_key:
        raise ValueError("DIGITALOCEAN_OPENAPI_KEY is required for DigitalOcean AI")

    payload: dict[str, Any] = {
        "model": DO_AI_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "stop": ["<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>", "<|end_of_text|>"],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            DO_AI_BASE_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"DigitalOcean AI returned no choices: {data}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"DigitalOcean AI returned invalid content: {data}")
    # Defensive scrub: some models leak chat template tokens past stop sequences.
    for tok in (
        "<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>",
        "<|end_of_text|>", "<|begin_of_text|>",
    ):
        idx = content.find(tok)
        if idx != -1:
            content = content[:idx]
    return content.strip()
