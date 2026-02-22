import json

from fastapi.testclient import TestClient

from tests.utils import register_and_login


def test_ws_ping_pong(client: TestClient):
    token = register_and_login(client, username='wsu', email='wsu@e.com')
    with client.websocket_connect(f"/ws/Geral/1?token={token}") as ws:
        ws.send_text('ping')
        data = json.loads(ws.receive_text())
        assert data['type'] == 'pong'
