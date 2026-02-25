from fastapi import APIRouter
from app.api.core import *

router = APIRouter()

@router.get('/health')
def health():
    return {'status': 'ok'}



@router.get("/", response_class=HTMLResponse)
def get(request: Request):
    # Mantemos server-side template pronto (mesmo que hoje não injete variáveis)
    # Isso facilita futuras configs por ambiente, feature flags, etc.
    return templates.TemplateResponse("index.html", {"request": request})


