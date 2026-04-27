from app import app


def test_index_redirects_to_login():
    client = app.test_client()
    res = client.get('/', follow_redirects=False)
    assert res.status_code in (301, 302)
    assert '/login' in res.headers.get('Location', '')


def test_login_get():
    client = app.test_client()
    res = client.get('/login')
    assert res.status_code == 200


def test_register_get():
    client = app.test_client()
    res = client.get('/register')
    assert res.status_code == 200


def test_dashboard_requires_login():
    client = app.test_client()
    res = client.get('/dashboard', follow_redirects=False)
    # Should redirect to login when not authenticated
    assert res.status_code in (301, 302)
    assert '/login' in res.headers.get('Location', '')
