from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

from app.config import STATIC_DIR
from app.errors import register_error_handlers
from app.routers import bookings, health, ships, time


def create_app(static_dir: Path = STATIC_DIR) -> FastAPI:
    app = FastAPI(
        title="Spaceport Charter System", docs_url="/api/docs", openapi_url="/api/openapi.json"
    )
    register_error_handlers(app)
    # Nothing in front of the app compresses for it, and the JavaScript bundle is a
    # third of its size gzipped. Small JSON answers are left alone.
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    for router in (health.router, time.router, ships.router, bookings.router):
        app.include_router(router, prefix="/api")

    # In the Docker image the built frontend sits next to the app. In development
    # the directory doesn't exist and Vite serves the frontend instead.
    if static_dir.is_dir():
        mount_frontend(app, static_dir.resolve())
    return app


IMMUTABLE = "public, max-age=31536000, immutable"


def mount_frontend(app: FastAPI, static_dir: Path) -> None:
    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not Found")  # never answer an API typo with HTML
        file = (static_dir / path).resolve()
        if file.is_file() and file.is_relative_to(static_dir):
            # Vite puts a content hash in every name under assets/, so a file there never
            # changes: the browser can keep it for good and skip the revalidation request.
            hashed = file.is_relative_to(static_dir / "assets")
            return FileResponse(file, headers={"Cache-Control": IMMUTABLE} if hashed else None)
        # Any other path is a client-side route (e.g. /fleet): let React Router handle it.
        return FileResponse(static_dir / "index.html", headers={"Cache-Control": "no-cache"})


app = create_app()
