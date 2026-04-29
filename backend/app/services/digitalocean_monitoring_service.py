from __future__ import annotations

from typing import Any

import httpx


async def fetch_digitalocean_metrics(
    *,
    token: str,
    endpoint: str,
    params: dict[str, Any] | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    if not token:
        raise ValueError("DigitalOcean token is required")
    if not endpoint.startswith("/"):
        raise ValueError(
            "endpoint must start with '/' (example: /v2/monitoring/metrics/droplet/cpu)"
        )
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.digitalocean.com{endpoint}"
    async with httpx.AsyncClient(timeout=timeout_seconds, headers=headers) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
