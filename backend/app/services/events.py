from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator


class EventBus:
    def __init__(self) -> None:
        self._topics: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, payload: dict) -> None:
        message = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        async with self._lock:
            queues = list(self._topics.get(topic, set()))
        for q in queues:
            q.put_nowait(message)

    async def subscribe(self, topic: str) -> AsyncIterator[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._topics[topic].add(q)
        try:
            while True:
                yield await q.get()
        finally:
            async with self._lock:
                self._topics[topic].discard(q)


event_bus = EventBus()
