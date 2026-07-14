from datetime import datetime, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func

from src.core.db import SessionLocal, init_db
from src.models import Competitor, Keyword, Note, PublishQueue

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
    db = SessionLocal()
    try:
        total_notes = db.query(func.count(Note.id)).scalar() or 0
        total_likes = db.query(func.coalesce(func.sum(Note.like_count), 0)).scalar() or 0
        total_followers = (
            db.query(func.coalesce(func.sum(Competitor.followers), 0))
            .filter(Competitor.is_active)
            .scalar()
            or 0
        )
        total_published = (
            db.query(func.count(PublishQueue.id))
            .filter(PublishQueue.status == "published")
            .scalar()
            or 0
        )

        cutoff = datetime.now() - timedelta(days=30)
        rows = (
            db.query(
                func.date(Note.published_at).label("date"),
                func.coalesce(func.sum(Note.like_count), 0).label("likes"),
                func.count(Note.id).label("notes"),
            )
            .filter(Note.published_at >= cutoff)
            .group_by(func.date(Note.published_at))
            .order_by("date")
            .all()
        )
        daily_stats = [{"date": r.date, "likes": r.likes, "notes": r.notes} for r in rows]

        return {
            "total_notes": total_notes,
            "total_likes": total_likes,
            "total_followers": total_followers,
            "total_published": total_published,
            "daily_stats": daily_stats,
        }
    finally:
        db.close()


@app.get("/api/competitors")
async def list_competitors() -> list:
    db = SessionLocal()
    try:
        rows = db.query(Competitor).filter(Competitor.is_active).all()
        return [
            {
                "id": c.id,
                "competitor_name": c.competitor_name,
                "followers": c.followers,
                "notes_count": c.notes_count,
                "avg_likes": c.avg_likes,
                "category": c.category or "",
            }
            for c in rows
        ]
    finally:
        db.close()


@app.get("/api/queue")
async def queue_list(status: str = Query("pending")) -> list:
    db = SessionLocal()
    try:
        rows = (
            db.query(PublishQueue)
            .filter(PublishQueue.status == status)
            .order_by(PublishQueue.scheduled_at.asc())
            .all()
        )
        return [
            {
                "id": q.id,
                "title": q.title or "",
                "status": q.status,
                "scheduled_for": q.scheduled_at.isoformat() if q.scheduled_at else None,
            }
            for q in rows
        ]
    finally:
        db.close()


@app.get("/api/notes")
async def list_notes(limit: int = Query(50), offset: int = Query(0)) -> list:
    db = SessionLocal()
    try:
        rows = db.query(Note).order_by(Note.published_at.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": n.id,
                "title": n.title or "",
                "like_count": n.like_count,
                "collect_count": n.collect_count,
                "comment_count": n.comment_count,
                "share_count": n.share_count,
                "published_at": n.published_at.isoformat() if n.published_at else None,
            }
            for n in rows
        ]
    finally:
        db.close()


@app.get("/api/keywords")
async def list_keywords(top: int = Query(50)) -> list:
    db = SessionLocal()
    try:
        rows = (
            db.query(Keyword)
            .filter(Keyword.is_active)
            .order_by(Keyword.search_volume.desc())
            .limit(top)
            .all()
        )
        return [
            {
                "keyword": k.keyword,
                "search_volume": k.search_volume,
                "competition": k.competition,
                "category": k.category or "",
            }
            for k in rows
        ]
    finally:
        db.close()


# Mount static frontend AFTER API routes so "/" does not shadow /api/*.
_frontend = Path("frontend/dist")
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")


def main() -> None:
    init_db()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
