"""FastAPI application entry point for the UrbanSense backend."""

from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Create the configured FastAPI application."""
    settings = get_settings()
    application = FastAPI(
        title="UrbanSense Dashboard API",
        version="0.1.0",
        description="Read-only dashboard API for fused UrbanSense pothole incidents.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)

    @application.websocket("/live-feed")
    async def root_live_feed(websocket: WebSocket):
        from app.services.live_feed import live_feed_manager
        from fastapi import WebSocketDisconnect
        await live_feed_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            live_feed_manager.disconnect(websocket)
        except Exception:
            live_feed_manager.disconnect(websocket)

    @application.get("/incidents")
    def root_incidents():
        from app.api.routes.incidents import list_incidents, IncidentQueryService
        return list_incidents(service=IncidentQueryService())

    @application.get("/health")
    def health_check():
        return {"status": "ok", "service": "urbansense-backend"}

    uploads_dir = Path("data/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    application.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    return application


app = create_app()
