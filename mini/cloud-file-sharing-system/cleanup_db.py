"""
cleanup_db.py

Merge data from duplicate singular tables (`user`, `file`) into plural tables
(`users`, `files`) and drop the singular tables if merge succeeded.

Run: python cleanup_db.py
"""
from pathlib import Path
import sqlite3
from datetime import datetime

DB = Path("cloud.db")

def table_exists(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def copy_users(cur):
    # user -> users
    if not table_exists(cur, 'user'):
        print('No singular "user" table found.')
        return
    if not table_exists(cur, 'users'):
        print('No "users" table found; creating...')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

    cur.execute('SELECT id, name, email, password_hash, created_at FROM user')
    rows = cur.fetchall()
    # Inspect target users columns to decide insert column names
    cur.execute("PRAGMA table_info(users)")
    users_cols = [r[1] for r in cur.fetchall()]

    inserted = 0
    for r in rows:
        uid, name, email, password_hash, created_at = r
        if created_at is None:
            created_at = datetime.utcnow().isoformat()
        # Check existing by email
        cur.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cur.fetchone():
            continue

        # Build dynamic insert based on existing users table columns
        insert_cols = []
        insert_vals = []
        if 'id' in users_cols:
            insert_cols.append('id')
            insert_vals.append(uid)
        if 'name' in users_cols:
            insert_cols.append('name')
            insert_vals.append(name)
        if 'email' in users_cols:
            insert_cols.append('email')
            insert_vals.append(email)
        if 'password_hash' in users_cols:
            insert_cols.append('password_hash')
            insert_vals.append(password_hash)
        elif 'password' in users_cols:
            insert_cols.append('password')
            insert_vals.append(password_hash)
        if 'created_at' in users_cols:
            insert_cols.append('created_at')
            insert_vals.append(created_at)

        if not insert_cols:
            # Unexpected: create standard columns and retry
            cur.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            cur.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
            insert_cols = ['id', 'name', 'email', 'password_hash', 'created_at']
            insert_vals = [uid, name, email, password_hash, created_at]

        # Avoid inserting conflicting id if it already exists
        if 'id' in insert_cols:
            cur.execute('SELECT 1 FROM users WHERE id = ?', (uid,))
            if cur.fetchone():
                # remove id from insert
                idx = insert_cols.index('id')
                insert_cols.pop(idx)
                insert_vals.pop(idx)

        cols_sql = ', '.join(insert_cols)
        placeholders = ', '.join(['?'] * len(insert_vals))
        cur.execute(f'INSERT INTO users ({cols_sql}) VALUES ({placeholders})', tuple(insert_vals))
        inserted += 1
    print(f'Copied {inserted} users from "user" -> "users"')

def copy_files(cur):
    # file -> files
    if not table_exists(cur, 'file'):
        print('No singular "file" table found.')
        return
    if not table_exists(cur, 'files'):
        print('No "files" table found; creating...')
        cur.execute('''
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
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

    cur.execute('SELECT id, stored_name, original_name, uploaded_at, downloads, user_id FROM file')
    rows = cur.fetchall()

    # Inspect target files columns to decide mapping
    cur.execute("PRAGMA table_info(files)")
    files_cols = [r[1] for r in cur.fetchall()]
    # determine stored_name column name in target
    stored_col = 'stored_name' if 'stored_name' in files_cols else ('filename' if 'filename' in files_cols else None)
    orig_col = 'original_name' if 'original_name' in files_cols else None
    download_col = 'download_count' if 'download_count' in files_cols else ('downloads' if 'downloads' in files_cols else None)

    inserted = 0
    for r in rows:
        fid, stored_name, original_name, uploaded_at, downloads, user_id = r
        if uploaded_at is None:
            uploaded_at = datetime.utcnow().isoformat()

        # Build dynamic insert based on existing files table columns
        insert_cols = []
        insert_vals = []
        if 'id' in files_cols:
            insert_cols.append('id')
            insert_vals.append(fid)
        if stored_col:
            insert_cols.append(stored_col)
            insert_vals.append(stored_name)
        if orig_col:
            insert_cols.append(orig_col)
            insert_vals.append(original_name if original_name is not None else stored_name)
        if 'user_id' in files_cols:
            insert_cols.append('user_id')
            insert_vals.append(user_id)
        if 'uploaded_at' in files_cols:
            insert_cols.append('uploaded_at')
            insert_vals.append(uploaded_at)
        if download_col:
            insert_cols.append(download_col)
            insert_vals.append(downloads or 0)
        if 'file_size' in files_cols:
            insert_cols.append('file_size')
            insert_vals.append(0)
        if 'mime_type' in files_cols:
            insert_cols.append('mime_type')
            insert_vals.append('application/octet-stream')
        if 'duration' in files_cols:
            insert_cols.append('duration')
            insert_vals.append(None)

        # If no recognizable columns, add basic ones then insert
        if not insert_cols:
            cur.execute("ALTER TABLE files ADD COLUMN stored_name TEXT")
            cur.execute("ALTER TABLE files ADD COLUMN original_name TEXT")
            cur.execute("ALTER TABLE files ADD COLUMN user_id INTEGER")
            cur.execute("ALTER TABLE files ADD COLUMN uploaded_at TEXT")
            insert_cols = ['id', 'stored_name', 'original_name', 'user_id', 'uploaded_at']
            insert_vals = [fid, stored_name, original_name or stored_name, user_id, uploaded_at]

        # Avoid id conflict
        if 'id' in insert_cols:
            cur.execute('SELECT 1 FROM files WHERE id = ?', (fid,))
            if cur.fetchone():
                idx = insert_cols.index('id')
                insert_cols.pop(idx)
                insert_vals.pop(idx)

        # For duplicate check use stored_col if available else filename+user
        dup_check = None
        if stored_col:
            cur.execute(f'SELECT id FROM files WHERE {stored_col} = ? AND user_id = ?', (stored_name, user_id))
            dup_check = cur.fetchone()
        else:
            cur.execute('SELECT id FROM files WHERE user_id = ? AND uploaded_at = ?', (user_id, uploaded_at))
            dup_check = cur.fetchone()
        if dup_check:
            continue

        cols_sql = ', '.join(insert_cols)
        placeholders = ', '.join(['?'] * len(insert_vals))
        cur.execute(f'INSERT INTO files ({cols_sql}) VALUES ({placeholders})', tuple(insert_vals))
        inserted += 1
    print(f'Copied {inserted} files from "file" -> "files"')


def drop_table(cur, name):
    try:
        cur.execute(f'DROP TABLE IF EXISTS {name}')
        print(f'Dropped table {name}')
    except Exception as e:
        print(f'Failed to drop {name}: {e}')


def main():
    if not DB.exists():
        print('Database not found: cloud.db')
        return
    conn = sqlite3.connect(DB)
    conn.execute('PRAGMA foreign_keys = OFF')
    cur = conn.cursor()

    copy_users(cur)
    copy_files(cur)

    conn.commit()

    # After copying, drop the singular tables to avoid future confusion
    if table_exists(cur, 'user'):
        drop_table(cur, 'user')
    if table_exists(cur, 'file'):
        drop_table(cur, 'file')

    conn.commit()
    conn.close()
    print('Cleanup completed.')

if __name__ == '__main__':
    main()
