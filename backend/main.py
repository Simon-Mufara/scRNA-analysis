from fastapi import FastAPI

from backend.routers.jobs import router as jobs_router

app = FastAPI(title="scRNA Explorer Backend", version="1.0.0")
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}

