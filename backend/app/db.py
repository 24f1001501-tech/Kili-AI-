import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    preferred_language TEXT NOT NULL CHECK (preferred_language IN ('ta-IN', 'hi-IN')),
    practice_goal TEXT NOT NULL DEFAULT '',
    feedback_style TEXT NOT NULL DEFAULT 'step_by_step',
    consent_settings TEXT NOT NULL DEFAULT '{"keep_audio": false}',
    is_demo INTEGER NOT NULL DEFAULT 0,
    baseline_done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    speech_target_id TEXT NOT NULL,
    current_level INTEGER NOT NULL DEFAULT 1 CHECK (current_level BETWEEN 1 AND 5),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('active', 'queued', 'mastered', 'not_needed')),
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, speech_target_id)
);

CREATE TABLE IF NOT EXISTS practice_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    learning_plan_id INTEGER REFERENCES learning_plans(id) ON DELETE SET NULL,
    kind TEXT NOT NULL CHECK (kind IN ('baseline', 'practice')),
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS practice_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    speech_target_id TEXT NOT NULL,
    level INTEGER NOT NULL,
    item_text TEXT NOT NULL,
    status TEXT NOT NULL,
    outcome TEXT,
    heard_as TEXT,
    transcript TEXT,
    phonemes TEXT,
    analysis_result TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    method TEXT NOT NULL,
    audio_quality_status TEXT NOT NULL,
    audio_path TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES practice_attempts(id) ON DELETE CASCADE,
    feedback_type TEXT NOT NULL,
    guidance_text TEXT NOT NULL,
    next_action TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    speech_target_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    note TEXT,
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attempts_user_target ON practice_attempts(user_id, speech_target_id, created_at);
CREATE INDEX IF NOT EXISTS idx_plans_user ON learning_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_user ON progress_records(user_id, speech_target_id);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def tx():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def new_key() -> str:
    return secrets.token_urlsafe(24)


def init_db() -> None:
    with tx() as conn:
        conn.executescript(SCHEMA)
        # Each profile is identified by a secret key, not its guessable row id.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        if "api_key" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN api_key TEXT")
        for (uid,) in conn.execute("SELECT id FROM users WHERE api_key IS NULL").fetchall():
            conn.execute("UPDATE users SET api_key = ? WHERE id = ?", (new_key(), uid))
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_key ON users(api_key)")


def row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for key in ("consent_settings", "analysis_result"):
        if key in d and isinstance(d[key], str):
            d[key] = json.loads(d[key])
    return d


def rows(rs) -> list[dict]:
    return [row(r) for r in rs]
