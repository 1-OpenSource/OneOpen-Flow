from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any
from uuid import UUID


class RunEventBroker:
    """In-memory pub/sub for live run events (SSE/WebSocket)."""

    def __init__(self) -> None:
        self._subscribers: dict[UUID, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)

    def subscribe(self, run_id: UUID) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: UUID, queue: asyncio.Queue[dict[str, Any]]) -> None:
        if run_id in self._subscribers and queue in self._subscribers[run_id]:
            self._subscribers[run_id].remove(queue)

    async def publish(self, run_id: UUID, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers.get(run_id, [])):
            await queue.put(event)

    def publish_sync(self, run_id: UUID, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers.get(run_id, [])):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass


event_broker = RunEventBroker()
