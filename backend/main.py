import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routers.jobs import router as jobs_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
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


@app.get("/health")
def health():
    return {"status": "success", "data": {"service": "scRNA Explorer Backend", "health": "ok"}, "error": None}


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
