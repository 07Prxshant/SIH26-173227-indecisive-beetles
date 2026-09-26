"""WebSocket endpoint for immediate verified-incident dashboard updates."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.services.live_feed import ConnectionManager, live_feed_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["live-feed"])


def get_live_feed_manager() -> ConnectionManager:
    """Provide the process-local manager and support dependency overrides in tests."""
    return live_feed_manager


@router.websocket("/api/v1/live-feed")
async def live_feed(
    websocket: WebSocket,
    manager: Annotated[ConnectionManager, Depends(get_live_feed_manager)],
) -> None:
    """Keep a dashboard client subscribed until it disconnects or errors."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        logger.exception("Live-feed connection failed")
        manager.disconnect(websocket)
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass
