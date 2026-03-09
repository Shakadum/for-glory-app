"""FastAPI app assembly — todos os routers registrados."""

from app.api.core import app  # noqa: F401

from app.api.routers.frontend      import router as frontend_router
from app.api.routers.auth          import router as auth_router
from app.api.routers.users         import router as users_router
from app.api.routers.posts         import router as posts_router
from app.api.routers.comments      import router as comments_router
from app.api.routers.friends       import router as friends_router
from app.api.routers.inbox         import router as inbox_router
from app.api.routers.groups        import router as groups_router
from app.api.routers.communities   import router as communities_router
from app.api.routers.calls         import router as calls_router
from app.api.routers.ws            import router as ws_router
from app.api.routers.news          import router as news_router
from app.api.transparency          import router as transparency_router
from app.api.routers.vip           import router as vip_router
from app.api.routers.quiz          import router as quiz_router
from app.api.routers.reactions     import router as reactions_router
from app.api.routers.diagnostics   import router as diagnostics_router
from app.api.routers.news_db       import router as news_db_router

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
app.include_router(news_router)
app.include_router(news_db_router)
app.include_router(transparency_router)
app.include_router(vip_perks_router)
app.include_router(vip_router)
app.include_router(quiz_router)
app.include_router(reactions_router)
app.include_router(diagnostics_router)
app.include_router(frontend_router)
