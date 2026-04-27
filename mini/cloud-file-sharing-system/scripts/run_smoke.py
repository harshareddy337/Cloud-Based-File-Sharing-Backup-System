import os
import sys
import time
from io import BytesIO

# Ensure project root is on sys.path so `app` can be imported when running
# this script from the `scripts/` folder.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app, db, User

with app.app_context():
    db.create_all()
    email = 'smoke_test@example.com'
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name='Smoke Test', email=email)
        user.set_password('secret')
        db.session.add(user)
        db.session.commit()

    client = app.test_client()

    # Simulate OTP already set in session and verify
    with client.session_transaction() as sess:
        sess['otp'] = '123456'
        sess['otp_expires'] = time.time() + 300
        sess['otp_user_id'] = user.id

    resp = client.post('/verify', data={'otp': '123456'}, follow_redirects=True)
    print('POST /verify status:', resp.status_code)

    # Access dashboard (should be logged in)
    resp = client.get('/dashboard')
    print('GET /dashboard status:', resp.status_code)

    # Upload a small file
    data = {'file': (BytesIO(b'hello world'), 'hello.txt')}
    resp = client.post('/dashboard', data=data, content_type='multipart/form-data', follow_redirects=True)
    print('POST /dashboard (upload) status:', resp.status_code)

    # List dashboard again and print snippet
    resp = client.get('/dashboard')
    print('GET /dashboard after upload status:', resp.status_code)
    text = resp.get_data(as_text=True)
    print('Dashboard HTML snippet:', text[:800])
