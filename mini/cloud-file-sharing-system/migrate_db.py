#!/usr/bin/env python3
"""
Database Migration Script
Adds new columns to existing database for large media file support
"""

import sqlite3
from pathlib import Path
import sys

DB_NAME = "cloud.db"

def migrate_database():
    """Add new columns to files table for media optimization"""
    db_path = Path(DB_NAME)
    
    if not db_path.exists():
        print("❌ Database not found. Creating new database...")
        from create_db import init_database
        init_database()
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Check if columns already exist
    try:
        cur.execute("PRAGMA table_info(files)")
        columns = [row[1] for row in cur.fetchall()]
        
        if 'file_size' in columns and 'mime_type' in columns and 'duration' in columns and 'storage_backend' in columns:
            print("✅ Database is already up to date!")
            conn.close()
            return
        
        print("🔄 Adding new columns to files table...")
        
        # Add file_size column
        if 'file_size' not in columns:
            print("  - Adding file_size column...")
            try:
                cur.execute("ALTER TABLE files ADD COLUMN file_size INTEGER DEFAULT 0")
            except sqlite3.OperationalError as e:
                print(f"  - file_size already exists or error: {e}")
        
        # Add mime_type column
        if 'mime_type' not in columns:
            print("  - Adding mime_type column...")
            try:
                cur.execute("ALTER TABLE files ADD COLUMN mime_type TEXT DEFAULT 'application/octet-stream'")
            except sqlite3.OperationalError as e:
                print(f"  - mime_type already exists or error: {e}")
        
        # Add duration column
        if 'duration' not in columns:
            print("  - Adding duration column...")
            try:
                cur.execute("ALTER TABLE files ADD COLUMN duration REAL")
            except sqlite3.OperationalError as e:
                print(f"  - duration already exists or error: {e}")

        # Add storage_backend column (NEW - tracks which cloud holds the file)
        if 'storage_backend' not in columns:
            print("  - Adding storage_backend column...")
            try:
                cur.execute("ALTER TABLE files ADD COLUMN storage_backend TEXT DEFAULT 'local'")
            except sqlite3.OperationalError as e:
                print(f"  - storage_backend already exists or error: {e}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Database migration completed successfully!")
        print("📋 New columns added:")
        print("   - file_size (INTEGER): File size in bytes")
        print("   - mime_type (TEXT): MIME type (e.g., 'video/mp4')")
        print("   - duration (REAL): Duration in seconds for audio/video")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.close()
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Cloud File Sharing System - Database Migration")
    print("=" * 50)
    migrate_database()
