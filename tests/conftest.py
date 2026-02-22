import os
import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope='session')
def client(tmp_path_factory):
    # Isolate DB for tests
    db_path = tmp_path_factory.mktemp('db') / 'test.db'
    os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"
    os.environ['SECRET_KEY'] = 'test-secret'

    # Reload settings-dependent modules
    import app.core.config as config
    importlib.reload(config)
    import app.db.session as session
    importlib.reload(session)
    import app.db.base as base
    importlib.reload(base)

    # Re-import routes to bind to reloaded engine
    import app.api.routes as routes
    importlib.reload(routes)

    from app.main import app

    with TestClient(app) as c:
        yield c
