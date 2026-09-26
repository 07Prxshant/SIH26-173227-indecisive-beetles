"""In-process WebSocket delivery for verified dashboard incidents."""

from __future__ import annotations

import asyncio
import logging
from threading import RLock
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.schemas.incidents import IncidentResponse, IncidentStatus

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage live-feed clients and safely broadcast JSON to every connection."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = RLock()

    @property
    def connection_count(self) -> int:
        """Expose the current connection count for diagnostics and tests."""
        with self._lock:
            return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register one dashboard client."""
        await websocket.accept()
        with self._lock:
            self._connections.add(websocket)
            self._event_loop = asyncio.get_running_loop()

    def disconnect(self, websocket: WebSocket) -> None:
        """Forget a disconnected client; it is safe to call repeatedly."""
        with self._lock:
            self._connections.discard(websocket)

    def publish_incident_created(self, incident: IncidentResponse) -> bool:
        """Schedule a creation event only for an incident visible on the dashboard."""
        if incident.status is not IncidentStatus.VERIFIED:
            return False
        payload = {"type": "incident_created", "incident": incident.model_dump(mode="json")}
        return self._schedule_broadcast(payload)

    def _schedule_broadcast(self, payload: dict[str, object]) -> bool:
        with self._lock:
            event_loop = self._event_loop
            has_clients = bool(self._connections)
        if event_loop is None or not has_clients or event_loop.is_closed():
            return False
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        try:
            if running_loop is event_loop:
                asyncio.create_task(self.broadcast(payload))
            else:
                asyncio.run_coroutine_threadsafe(self.broadcast(payload), event_loop)
        except RuntimeError:
            logger.exception("Unable to schedule live incident broadcast")
            return False
        return True

    async def broadcast(self, payload: dict[str, object]) -> None:
        """Send a JSON event to every client, pruning broken connections."""
        with self._lock:
            connections = tuple(self._connections)
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except WebSocketDisconnect:
                self.disconnect(websocket)
            except Exception:
                logger.exception("Removing a live-feed client after a send failure")
                self.disconnect(websocket)


live_feed_manager = ConnectionManager()
