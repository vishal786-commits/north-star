import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="North Star")

app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# MUST be registered last — this catch-all mount at "/" would otherwise swallow
# /api and /health. It serves the single-page frontend (static/index.html).
app.mount("/", StaticFiles(directory="static", html=True), name="static")
