import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import router
from app.metrics import init_db

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="North Star")


@app.on_event("startup")
def _startup():
    # Create the SQLite metrics tables if they don't exist yet.
    init_db()


app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# MUST be registered last — this catch-all mount at "/" would otherwise swallow
# /api and /health. It serves the single-page frontend (static/index.html).
app.mount("/", StaticFiles(directory="static", html=True), name="static")
