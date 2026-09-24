"""Loopback-only HTTP service for the optional SkillNet browser interface."""

import asyncio
import json
import threading
import webbrowser
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from skillnet_ai.web.library import absolute_directory, read_library


class LibraryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    action: Literal["read", "create-default"] = "read"
    sourcePath: str | None = Field(default=None, max_length=2048)
    indexPath: str | None = Field(default=None, max_length=2048)


def create_app(
    *,
    skills_dir: Path | None = None,
    static_dir: Path | None = None,
    dev: bool = False,
    browser_url: str | None = None,
) -> FastAPI:
    """Create the app without starting a server, creating folders or opening a browser."""
    initial_path = str(absolute_directory(str(skills_dir))) if skills_dir else None
    assets = static_dir or Path(__file__).parent / "static"
    if not dev and not (assets / "index.html").is_file():
        raise ValueError("Web assets are missing. Build web/ui with npm run build before starting.")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        timer = None
        if browser_url:
            timer = threading.Timer(0.5, webbrowser.open, args=(browser_url,))
            timer.daemon = True
            timer.start()
        yield
        if timer:
            timer.cancel()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    # Bound concurrent disk scans without blocking the event loop.
    reads = asyncio.Semaphore(2)

    @app.middleware("http")
    async def local_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        host = request.headers.get("host", "")
        try:
            local = urlsplit(f"http://{host}").hostname in {"127.0.0.1", "localhost"}
        except ValueError:
            local = False
        if not local:
            return JSONResponse({"error": "Only loopback hosts are allowed."}, status_code=403)
        if request.url.path.startswith("/api/") and request.method != "GET":
            origins = {f"http://{host}"}
            if dev:
                origins.update({"http://127.0.0.1:5173", "http://localhost:5173"})
            if request.headers.get("origin") not in origins:
                return JSONResponse(
                    {"error": "A same-origin request is required."}, status_code=403
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/config")
    def config() -> dict[str, str | None]:
        return {"sourcePath": initial_path}

    @app.post("/api/local-library")
    async def library(request: Request) -> Any:
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise HTTPException(415, "Expected application/json.")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 8192:
                raise HTTPException(413, "Request body exceeds 8 KB.")
        try:
            value = LibraryRequest.model_validate(json.loads(body))
        except ValueError:
            return JSONResponse({"error": "Invalid local library request."}, status_code=400)
        try:
            if value.action == "create-default":
                path = Path.home() / ".skillnet" / "skills"
                await run_in_threadpool(path.mkdir, parents=True, exist_ok=True)
                return {"sourcePath": str(path.resolve())}
            if not value.sourcePath:
                raise ValueError("Enter a skills folder path.")
            async with reads:
                return await run_in_threadpool(read_library, value.sourcePath, value.indexPath)
        except (OSError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    if (assets / "index.html").is_file():
        app.mount("/", StaticFiles(directory=assets, html=True), name="ui")
    return app


def serve(*, skills_dir: Path | None, port: int, open_browser: bool, dev: bool) -> None:
    url = f"http://127.0.0.1:{5173 if dev else port}"
    app = create_app(skills_dir=skills_dir, dev=dev, browser_url=url if open_browser else None)
    uvicorn.run(app, host="127.0.0.1", port=port)
