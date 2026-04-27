"""run_model_query.py
Simple script to confirm SQLAlchemy model mapping works and a query like
`File.query.filter_by(user_id=3)` runs without raising column errors.
Run: python run_model_query.py
"""
from app import app, db, File

with app.app_context():
    # ensure tables exist
    db.create_all()
    # run query for user_id=3
    try:
        files = File.query.filter_by(user_id=3).all()
        print('Query succeeded. Number of files for user_id=3:', len(files))
        for f in files[:5]:
            print({'id': f.id, 'stored_name': f.stored_name, 'original_name': f.original_name, 'file_size': getattr(f, 'file_size', None)})
    except Exception as e:
        print('Query raised exception:', e)
        raise
