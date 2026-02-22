from fastapi.testclient import TestClient


def register_and_login(client: TestClient, username='u1', email='u1@example.com', password='pass123'):
    r = client.post('/register', json={'username': username, 'email': email, 'password': password})
    assert r.status_code in (200, 201)
    r = client.post('/token', data={'username': username, 'password': password})
    assert r.status_code == 200
    return r.json()['access_token']
