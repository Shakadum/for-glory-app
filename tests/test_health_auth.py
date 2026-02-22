from fastapi.testclient import TestClient

from tests.utils import register_and_login


def test_health(client: TestClient):
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_register_login_me(client: TestClient):
    token = register_and_login(client)
    r = client.get('/users/me', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    data = r.json()
    assert data['username'] == 'u1'
