import pytest
from app import app, db, File


def test_file_query_no_error():
    """Ensure `File.query.filter_by(user_id=3)` runs without raising DB/column errors."""
    with app.app_context():
        # Ensure tables are present for SQLAlchemy mapping
        db.create_all()
        try:
            files = File.query.filter_by(user_id=3).all()
        except Exception as e:
            pytest.fail(f"Query raised exception: {e}")
        assert isinstance(files, list)
