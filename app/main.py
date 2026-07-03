import logging

from fastapi import FastAPI

from app.routes import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="North Star")

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}