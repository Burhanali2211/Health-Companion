import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "watan.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    age_mode    TEXT NOT NULL DEFAULT 'jawaan',
    district    TEXT NOT NULL DEFAULT 'srinagar',
    started_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT,
    query_text      TEXT,
    response_text   TEXT,
    source          TEXT,
    season          TEXT,
    age_mode        TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_checkins (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_profile    TEXT DEFAULT 'default',
    feeling         TEXT,
    age_mode        TEXT,
    season          TEXT,
    checked_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_version (
    id          INTEGER PRIMARY KEY,
    version     TEXT,
    last_synced DATETIME
);
"""

def init() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"Database initialised at {DB_PATH}")

if __name__ == "__main__":
    init()
