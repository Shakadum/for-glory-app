"""FastAPI app assembly.

This project started as a single-file routes.py. It is now split into:
- app/api/core.py: app instance + shared deps/helpers
- app/api/routers/*: domain routers (auth, users, posts, ws, ...)

Keep app/main.py importing `app` from here.
"""

from app.api.core import app  # noqa: F401

from app.api.routers.frontend import router as frontend_router
from app.api.routers.auth import router as auth_router
from app.api.routers.users import router as users_router
from app.api.routers.posts import router as posts_router
from app.api.routers.comments import router as comments_router
from app.api.routers.friends import router as friends_router
from app.api.routers.inbox import router as inbox_router
from app.api.routers.groups import router as groups_router
from app.api.routers.communities import router as communities_router
from app.api.routers.calls import router as calls_router
from app.api.routers.ws import router as ws_router

# Order matters a bit: health/root last is fine
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(friends_router)
app.include_router(inbox_router)
app.include_router(groups_router)
app.include_router(communities_router)
app.include_router(calls_router)
app.include_router(ws_router)
app.include_router(frontend_router)
