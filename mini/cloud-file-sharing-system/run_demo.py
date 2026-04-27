import io
import os

from app import app, db, User, File


def short(s, n=400):
    return (s[:n] + '...') if len(s) > n else s


with app.app_context():
    db.create_all()

with app.test_client() as c:
    print('GET /register')
    r = c.get('/register')
    print(r.status_code)
    print(short(r.data.decode('utf-8')))

    print('\nPOST /register')
    r = c.post('/register', data={'name': 'Test User', 'email': 'test@example.com', 'password': 'secret'}, follow_redirects=True)
    print(r.status_code)
    print(short(r.data.decode('utf-8')))

    print('\nGET /login')
    r = c.get('/login')
    print(r.status_code)
    print(short(r.data.decode('utf-8')))

    print('\nPOST /login')
    r = c.post('/login', data={'email': 'test@example.com', 'password': 'secret'}, follow_redirects=True)
    print(r.status_code)
    out = r.data.decode('utf-8')
    print(short(out))

    # If OTP verification required, fetch OTP from session and post to /verify
    if 'Enter the OTP' in out or '/verify' in r.request.path:
        with c.session_transaction() as sess:
            otp = sess.get('otp')
        print('Detected OTP flow, using OTP from session:', otp)
        r2 = c.post('/verify', data={'otp': otp}, follow_redirects=True)
        print('POST /verify ->', r2.status_code)
        print(short(r2.data.decode('utf-8')))

    print('\nGET /dashboard (after login)')
    r = c.get('/dashboard')
    print(r.status_code)
    print(short(r.data.decode('utf-8')))

    print('\nPOST /dashboard (upload file)')
    data = {'file': (io.BytesIO(b'Hello world demo'), 'hello.txt')}
    r = c.post('/dashboard', data=data, content_type='multipart/form-data', follow_redirects=True)
    print(r.status_code)
    print(short(r.data.decode('utf-8')))

    print('\nGET /dashboard (after upload)')
    r = c.get('/dashboard')
    print(r.status_code)
    page = r.data.decode('utf-8')
    print(short(page, 800))

    # find the uploaded file id
    with app.app_context():
        f = File.query.filter_by(original_name='hello.txt').first()
        if f:
            fid = f.id
            print('\nFound file in DB:', fid, f.original_name)
        else:
            print('\nUploaded file not found in DB')
            fid = None

    if fid:
        print('\nGET /download/<id>')
        r = c.get(f'/download/{fid}')
        print(r.status_code)
        print('Downloaded bytes:', r.data[:60])

        print('\nGET /delete/<id>/<name>')
        r = c.get(f'/delete/{fid}/hello.txt', follow_redirects=True)
        print(r.status_code)
        print(short(r.data.decode('utf-8')))

        print('\nFinal /dashboard')
        r = c.get('/dashboard')
        print(r.status_code)
        print(short(r.data.decode('utf-8')))

print('\nDemo finished')
