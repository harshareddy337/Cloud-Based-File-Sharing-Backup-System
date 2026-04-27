import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app, db
from flask import render_template

with app.test_request_context('/', method='GET'):
    try:
        # Render with a request context so `current_user` and session helpers work
        html = render_template('verify.html', masked_email='test@example.com', cooldown_seconds=30)
        print('Rendered successfully. Length:', len(html))
        print(html[:1200])
    except Exception as e:
        print('Render error:', type(e).__name__, e)
