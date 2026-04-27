import sqlite3
from pathlib import Path
from datetime import datetime

DB_NAME = "cloud.db"

def init_database():
    db_path = Path(DB_NAME)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # -------------------------------
    # USERS TABLE
    # -------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Index for faster login lookups
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email)
    """)

    # -------------------------------
    # FILES TABLE
    # -------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stored_name TEXT NOT NULL,
        original_name TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        uploaded_at TEXT NOT NULL,
        download_count INTEGER DEFAULT 0,
        file_size INTEGER DEFAULT 0,
        mime_type TEXT DEFAULT 'application/octet-stream',
        duration REAL,

        FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
    )
    """)

    # Index for fast file listing per user
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_files_user
    ON files(user_id)
    """)

    conn.commit()
    conn.close()

    print("✅ Database initialized successfully")
    print(f"📦 Database location: {db_path.resolve()}")
    print(f"🕒 Initialized at: {datetime.now().isoformat()}")

# -------------------------------
# Entry Point
# -------------------------------
if __name__ == "__main__":
    init_database()
