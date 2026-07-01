from fastapi import FastAPI

app = FastAPI(title="North Star")

@app.get("/health")
def health():
    return {"status": "ok"}
