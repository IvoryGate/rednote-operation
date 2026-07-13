from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.db import init_db

app = FastAPI(title="RedNote Operation", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/dashboard/stats")
async def dashboard_stats() -> dict:
    return {
        "total_notes": 0,
        "total_likes": 0,
        "total_followers": 0,
        "total_published": 0,
        "daily_stats": [],
    }


@app.get("/api/competitors")
async def list_competitors() -> list:
    return []


@app.get("/api/queue")
async def queue_list(status: str = "pending") -> list:
    return []


def main() -> None:
    init_db()
    frontend = Path("frontend/dist")
    if frontend.exists():
        app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
