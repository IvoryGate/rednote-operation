from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    phone: Mapped[str | None]
    platform: Mapped[str] = mapped_column(default="xiaohongshu")
    cookies_path: Mapped[str | None]
    enabled: Mapped[bool] = mapped_column(default=True)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    note_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    account_id: Mapped[int | None]
    title: Mapped[str | None]
    content: Mapped[str | None]
    images: Mapped[str | None]
    video_url: Mapped[str | None]
    tags: Mapped[str | None]
    topics: Mapped[str | None]
    like_count: Mapped[int] = mapped_column(default=0)
    collect_count: Mapped[int] = mapped_column(default=0)
    comment_count: Mapped[int] = mapped_column(default=0)
    share_count: Mapped[int] = mapped_column(default=0)
    view_count: Mapped[int] = mapped_column(default=0)
    is_original: Mapped[bool] = mapped_column(default=True)
    url: Mapped[str | None]
    published_at: Mapped[datetime | None]
    collected_at: Mapped[datetime] = mapped_column(default=func.now())


class Competitor(Base, TimestampMixin):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(nullable=False)
    competitor_name: Mapped[str] = mapped_column(nullable=False)
    competitor_url: Mapped[str | None]
    category: Mapped[str | None]
    followers: Mapped[int] = mapped_column(default=0)
    notes_count: Mapped[int] = mapped_column(default=0)
    avg_likes: Mapped[float] = mapped_column(default=0.0)
    avg_comments: Mapped[float] = mapped_column(default=0.0)
    is_active: Mapped[bool] = mapped_column(default=True)


class Keyword(Base, TimestampMixin):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(nullable=False, unique=True)
    category: Mapped[str | None]
    search_volume: Mapped[int] = mapped_column(default=0)
    competition: Mapped[float] = mapped_column(default=0.0)
    trend: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)


class ContentCalendar(Base, TimestampMixin):
    __tablename__ = "content_calendar"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="draft")
    category: Mapped[str | None]
    scheduled_at: Mapped[datetime | None]
    published_at: Mapped[datetime | None]
    note_id: Mapped[str | None]
    tags: Mapped[str | None]


class PublishQueue(Base, TimestampMixin):
    __tablename__ = "publish_queue"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(nullable=False)
    content_id: Mapped[int | None]
    status: Mapped[str] = mapped_column(default="pending")
    scheduled_for: Mapped[datetime | None]
    published_at: Mapped[datetime | None]
    error_message: Mapped[str | None]
    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=3)
    priority: Mapped[int] = mapped_column(default=0)


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(nullable=False)
    report_type: Mapped[str] = mapped_column(nullable=False)
    parameters: Mapped[str | None]
    results: Mapped[str | None]
    summary: Mapped[str | None]
    file_path: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class KnowledgeEntry(Base, TimestampMixin):
    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    tags: Mapped[str | None]
    source: Mapped[str | None]
    version: Mapped[int] = mapped_column(default=1)
    is_active: Mapped[bool] = mapped_column(default=True)


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(nullable=False)
    entity_type: Mapped[str | None]
    entity_id: Mapped[str | None]
    details: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="success")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
