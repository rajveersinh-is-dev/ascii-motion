"""FastAPI application factory and static frontend mounting."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ascii_motion.api.routes import router

app = FastAPI(
    title="ascii-motion",
    description="High-performance video-to-ASCII rendering engine API",
    version="0.1.0",
)

# Enable CORS for local development (e.g. Vite dev server on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Mount frontend production build if available
WEB_DIST_DIR = (Path.cwd() / "web" / "dist").resolve()
if WEB_DIST_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = WEB_DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(WEB_DIST_DIR / "index.html")


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Run uvicorn server programmatically."""
    import uvicorn

    uvicorn.run("ascii_motion.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()
