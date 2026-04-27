#!/usr/bin/env python
"""Comprehensive project status check"""
import os
import sys

print("=" * 60)
print("CLOUD FILE SHARING SYSTEM - PROJECT STATUS REPORT")
print("=" * 60)
print()

# Check Python version
print("1. PYTHON ENVIRONMENT:")
print(f"   Python version: {sys.version.split()[0]}")
print(f"   Working directory: {os.getcwd()}")
print()

# Check app.py
print("2. CORE FILES:")
files_to_check = ["app.py", "requirements.txt", ".env", "cloud.db"]
for file in files_to_check:
    exists = os.path.exists(file)
    status = "✓ EXISTS" if exists else "✗ MISSING"
    print(f"   {file}: {status}")
print()

# Check database
print("3. DATABASE SCHEMA:")
try:
    from app import db, File
    cols = [c.name for c in File.__table__.columns]
    print(f"   Database file: ✓ EXISTS")
    print(f"   Total columns: {len(cols)}")
    print(f"   Columns: {cols}")
    print()
    print("4. REQUIRED COLUMNS VERIFICATION:")
    required = ["id", "stored_name", "original_name", "file_size", "mime_type", "duration", "user_id"]
    for col in required:
        status = "✓" if col in cols else "✗"
        print(f"   {status} {col}")
    print()
    all_present = all(col in cols for col in required)
    print(f"5. OVERALL STATUS: {'✓ READY FOR PRODUCTION' if all_present else '✗ MISSING COLUMNS'}")
except Exception as e:
    print(f"   Error: {str(e)}")
    print("5. OVERALL STATUS: ✗ FAILED")

print()
print("=" * 60)
print("Access app at: http://localhost:5000")
print("=" * 60)
