from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.config import STATIC_DIR
from app.errors import register_error_handlers
from app.routers import bookings, health, ships, time


def create_app(static_dir: Path = STATIC_DIR) -> FastAPI:
    app = FastAPI(
        title="Spaceport Charter System", docs_url="/api/docs", openapi_url="/api/openapi.json"
    )
    register_error_handlers(app)
    for router in (health.router, time.router, ships.router, bookings.router):
        app.include_router(router, prefix="/api")

    # In the Docker image the built frontend sits next to the app. In development
    # the directory doesn't exist and Vite serves the frontend instead.
    if static_dir.is_dir():
        mount_frontend(app, static_dir.resolve())
    return app


def mount_frontend(app: FastAPI, static_dir: Path) -> None:
    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not Found")  # never answer an API typo with HTML
        file = (static_dir / path).resolve()
        if file.is_file() and file.is_relative_to(static_dir):
            return FileResponse(file)
        # Any other path is a client-side route (e.g. /fleet): let React Router handle it.
        return FileResponse(static_dir / "index.html", headers={"Cache-Control": "no-cache"})


app = create_app()
