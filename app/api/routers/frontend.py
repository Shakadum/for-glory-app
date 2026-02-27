from fastapi import APIRouter
from fastapi.responses import Response
from app.api.core import *

router = APIRouter()

@router.get('/health')
def health():
    return {'status': 'ok'}

@router.get('/favicon.ico', include_in_schema=False)
def favicon():
    # Retorna um SVG mínimo como ícone para parar os 404 nos logs
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#0b0c10"/><text x="16" y="22" font-size="18" text-anchor="middle" fill="#66fcf1">G</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")

@router.get("/", response_class=HTMLResponse)
def get(request: Request):
    # Cache-bust static assets to avoid stale 404s after deploys
    asset_version = (os.getenv("RENDER_GIT_COMMIT") or os.getenv("ASSET_VERSION") or "dev")[:12]
    resp = templates.TemplateResponse("index.html", {"request": request, "asset_version": asset_version})
    # Ensure HTML isn't cached aggressively on mobile/desktop
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

