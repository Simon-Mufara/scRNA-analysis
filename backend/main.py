import logging
import os
import platform
import socket
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routers.jobs import router as jobs_router
from backend.routers.auth import router as auth_router
from utils.backend_db import DB_PATH, fetch_rows, init_db

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(message)s",
)

app = FastAPI(title="scRNA Explorer Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs_router)
app.include_router(auth_router)


@app.on_event("startup")
async def startup_log():
    port = os.getenv("PORT", "8000")
    logging.info("=== SERVER STARTED ===")
    logging.info("Running on port %s", port)
    logging.info("Working directory: %s", Path.cwd())
    logging.info("Database type: SQLite")
    logging.info("Database path: %s", DB_PATH)
    try:
        init_db()
        logging.debug("Database connected successfully")
    except Exception as exc:
        logging.error("Database connection failed: %s", exc)
        raise


@app.get("/health")
def health():
    return {"status": "ok", "message": "API is running"}


@app.get("/health/runtime")
def runtime_health():
    def _pkg(name: str):
        try:
            return {"installed": True, "version": version(name)}
        except PackageNotFoundError:
            return {"installed": False, "version": None}

    return {
        "status": "ok",
        "python_version": platform.python_version(),
        "packages": {
            "fastapi": _pkg("fastapi"),
            "scanpy": _pkg("scanpy"),
        },
    }


@app.get("/debug")
def debug():
    uploads_dir = Path("data/uploads")
    upload_files = sorted([p.name for p in uploads_dir.iterdir() if p.is_file()]) if uploads_dir.exists() else []
    return {
        "cwd": str(Path.cwd()),
        "uploads_files": upload_files,
        "python_version": platform.python_version(),
        "hostname": socket.gethostname(),
    }


@app.get("/debug/users")
def debug_users():
    # DEBUG ONLY
    rows = fetch_rows("SELECT email FROM users ORDER BY username")
    return {"debug_only": True, "users": [{"email": row.get("email")} for row in rows]}


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "data": None, "error": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logging.getLogger(__name__).exception("Unhandled backend exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "data": None, "error": "Internal server error"},
    )
