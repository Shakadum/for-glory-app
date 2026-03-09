"""
For Glory — Portal da Transparência
Pacote modular — exporta o router principal.

Importar em app/api/routes.py:
    from app.api.transparency import router as transparency_router
"""
from .router import router

__all__ = ["router"]
