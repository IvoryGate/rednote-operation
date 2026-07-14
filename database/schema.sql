-- RedNote Operation — Database Schema
-- SQLite
-- Source of truth for documentation; runtime creates tables via SQLAlchemy ORM
-- (src/models). Keep this file in sync with src/models/__init__.py.

CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    phone           TEXT,
    platform        TEXT NOT NULL DEFAULT 'xiaohongshu',
    cookies_path    TEXT,
    enabled         INTEGER NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id         TEXT NOT NULL UNIQUE,
    account_id      INTEGER,
    title           TEXT,
    content         TEXT,
    images          TEXT,
    video_url       TEXT,
    tags            TEXT,
    topics          TEXT,
    like_count      INTEGER NOT NULL DEFAULT 0,
    collect_count   INTEGER NOT NULL DEFAULT 0,
    comment_count   INTEGER NOT NULL DEFAULT 0,
    share_count     INTEGER NOT NULL DEFAULT 0,
    view_count      INTEGER NOT NULL DEFAULT 0,
    is_original     INTEGER NOT NULL DEFAULT 1,
    url             TEXT,
    published_at    DATETIME,
    collected_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notes_note_id ON notes(note_id);
CREATE INDEX IF NOT EXISTS idx_notes_account_id ON notes(account_id);

CREATE TABLE IF NOT EXISTS competitors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      INTEGER NOT NULL,
    competitor_name TEXT NOT NULL,
    competitor_url  TEXT,
    category        TEXT,
    followers       INTEGER NOT NULL DEFAULT 0,
    notes_count     INTEGER NOT NULL DEFAULT 0,
    avg_likes       REAL NOT NULL DEFAULT 0.0,
    avg_comments    REAL NOT NULL DEFAULT 0.0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_competitors_account_id ON competitors(account_id);
CREATE INDEX IF NOT EXISTS idx_competitors_category ON competitors(category);

CREATE TABLE IF NOT EXISTS keywords (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword         TEXT NOT NULL UNIQUE,
    category        TEXT,
    search_volume   INTEGER NOT NULL DEFAULT 0,
    competition     REAL NOT NULL DEFAULT 0.0,
    trend           TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_keywords_category ON keywords(category);

CREATE TABLE IF NOT EXISTS content_calendar (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      INTEGER NOT NULL,
    title           TEXT NOT NULL,
    content         TEXT,
    status          TEXT NOT NULL DEFAULT 'draft',
    category        TEXT,
    scheduled_at    DATETIME,
    published_at    DATETIME,
    note_id         TEXT,
    tags            TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_content_calendar_account_id ON content_calendar(account_id);
CREATE INDEX IF NOT EXISTS idx_content_calendar_status ON content_calendar(status);
CREATE INDEX IF NOT EXISTS idx_content_calendar_scheduled_at ON content_calendar(scheduled_at);

CREATE TABLE IF NOT EXISTS publish_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      INTEGER NOT NULL,
    calendar_id     INTEGER,
    title           TEXT NOT NULL,
    content         TEXT,
    images          TEXT,
    tags            TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    scheduled_at    DATETIME,
    published_at    DATETIME,
    error_message   TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 3,
    priority        INTEGER NOT NULL DEFAULT 0,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_publish_queue_account_id ON publish_queue(account_id);
CREATE INDEX IF NOT EXISTS idx_publish_queue_status ON publish_queue(status);
CREATE INDEX IF NOT EXISTS idx_publish_queue_scheduled_at ON publish_queue(scheduled_at);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    report_type     TEXT NOT NULL,
    parameters      TEXT,
    results         TEXT,
    summary         TEXT,
    file_path       TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_analysis_reports_type ON analysis_reports(report_type);

CREATE TABLE IF NOT EXISTS knowledge_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    category        TEXT NOT NULL,
    content         TEXT NOT NULL,
    tags            TEXT,
    source          TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_entries_category ON knowledge_entries(category);

CREATE TABLE IF NOT EXISTS operation_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action          TEXT NOT NULL,
    entity_type     TEXT,
    entity_id       TEXT,
    details         TEXT,
    status          TEXT NOT NULL DEFAULT 'success',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_operation_logs_action ON operation_logs(action);
