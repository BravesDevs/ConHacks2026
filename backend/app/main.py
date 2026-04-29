from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.services.events import event_bus


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ConHacks FastAPI Backend", version="0.1.0")

    if settings.cors_origins:
        origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router)

    @app.websocket("/ws")
    async def ws(ws: WebSocket) -> None:
        await ws.accept()
        repo = ws.query_params.get("repo", "")
        run_id = ws.query_params.get("run_id", "")
        topics = {
            "terraform.updated",
            "run.queued",
            "run.running",
            "run.suggestion_ready",
            "run.pr_opened",
            "run.failed",
        }
        if repo:
            topics = {
                t for t in topics if t.startswith("run.") or t == "terraform.updated"
            }
        try:

            async def forward(topic: str) -> None:
                async for msg in event_bus.subscribe(topic):
                    await ws.send_text(msg)

            # For now, subscribe to all topics; filtering should be done client-side.
            tasks = [__import__("asyncio").create_task(forward(t)) for t in topics]
            await ws.receive_text()
        except WebSocketDisconnect:
            return
        finally:
            for t in list(locals().get("tasks", [])):
                t.cancel()

    return app


app = create_app()
