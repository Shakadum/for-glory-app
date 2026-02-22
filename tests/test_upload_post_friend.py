import io
import sys
import types

import pytest
from fastapi.testclient import TestClient

from tests.utils import register_and_login


@pytest.fixture(autouse=True)
def mock_cloudinary(monkeypatch):
    # Provide a fake cloudinary module even if dependency isn't installed in the test env
    cloudinary = types.SimpleNamespace()
    uploader = types.SimpleNamespace()

    def fake_upload(*args, **kwargs):
        return {'secure_url': 'https://example.com/fake.png'}

    uploader.upload = fake_upload
    cloudinary.uploader = uploader

    sys.modules['cloudinary'] = cloudinary
    sys.modules['cloudinary.uploader'] = uploader

    yield


def test_upload_and_post_flow(client: TestClient):
    token = register_and_login(client, username='u2', email='u2@example.com')

    files = {'file': ('x.png', io.BytesIO(b'123'), 'image/png')}
    r = client.post('/upload', files=files, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    url = r.json()['secure_url']
    assert url.startswith('https://example.com')

    r = client.post(
        '/post',
        json={'caption': 'hi', 'content_url': url, 'media_type': 'image'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert r.status_code == 200

    r = client.get('/posts?uid=1&limit=10')
    assert r.status_code == 200


def test_friend_request_accept_remove(client: TestClient):
    t1 = register_and_login(client, username='a', email='a@e.com')
    t2 = register_and_login(client, username='b', email='b@e.com')

    r = client.post('/friend/request', json={'target_id': 2}, headers={'Authorization': f'Bearer {t1}'})
    assert r.status_code == 200

    r = client.get('/friend/requests', headers={'Authorization': f'Bearer {t2}'})
    assert r.status_code == 200
    reqs = r.json().get('requests', [])
    assert len(reqs) == 1
    req_id = reqs[0]['id']

    r = client.post('/friend/handle', json={'request_id': req_id, 'action': 'accept'}, headers={'Authorization': f'Bearer {t2}'})
    assert r.status_code == 200

    r = client.post('/friend/remove', json={'friend_id': 2}, headers={'Authorization': f'Bearer {t1}'})
    assert r.status_code == 200
