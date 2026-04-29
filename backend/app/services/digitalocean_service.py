from __future__ import annotations

from typing import Any

import httpx


async def fetch_digitalocean_sizes(
    *, token: str, timeout_seconds: float = 20.0
) -> dict[str, Any]:
    if not token:
        raise ValueError("DigitalOcean token is required")
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=timeout_seconds, headers=headers) as client:
        url = "https://api.digitalocean.com/v2/sizes?per_page=200"
        sizes: list[dict[str, Any]] = []
        while url:
            resp = await client.get(url)
            resp.raise_for_status()
            body = resp.json()
            sizes.extend(body.get("sizes", []))
            url = body.get("links", {}).get("pages", {}).get("next")
        return {"sizes": sizes}
