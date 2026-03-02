"""
For Glory — Navegador de Notícias Geolocalizadas
-------------------------------------------------
Requer as seguintes variáveis de ambiente:
  GNEWS_API_KEY   → chave da GNews API (https://gnews.io — 100 req/dia grátis)

IP geolocation: ip-api.com (grátis, sem chave, 45 req/min)
"""

import os
import httpx
import asyncio
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional

router = APIRouter()

GNEWS_KEY   = os.environ.get("GNEWS_API_KEY", "")
GNEWS_BASE  = "https://gnews.io/api/v4"
IPAPI_URL   = "http://ip-api.com/json/{ip}?fields=status,city,regionName,countryCode,country,lat,lon,query"

# Cache simples em memória para reduzir chamadas à IP-API (por IP)
_geo_cache: dict = {}


async def resolve_geo(ip: str) -> dict:
    """Converte IP em dados de geolocalização usando ip-api.com."""
    if ip in _geo_cache:
        return _geo_cache[ip]

    # IPs privados / localhost → retorna default Brasil
    if ip in ("127.0.0.1", "::1") or ip.startswith("192.168.") or ip.startswith("10."):
        result = {
            "city": "Rio de Janeiro", "regionName": "Rio de Janeiro",
            "country": "Brasil", "countryCode": "BR",
            "lat": -22.9, "lon": -43.1, "query": ip
        }
        _geo_cache[ip] = result
        return result

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(IPAPI_URL.format(ip=ip))
            data = r.json()
            if data.get("status") == "success":
                _geo_cache[ip] = data
                return data
    except Exception:
        pass

    return {"city": "Brasil", "regionName": "", "country": "Brasil", "countryCode": "BR", "lat": -15, "lon": -47}


async def fetch_gnews(query: str, lang: str = "pt", country: str = "br", max_items: int = 10) -> list:
    """Busca notícias na GNews API."""
    if not GNEWS_KEY:
        return []

    params = {
        "q": query,
        "lang": lang,
        "country": country,
        "max": max_items,
        "apikey": GNEWS_KEY,
        "sortby": "publishedAt",
    }

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{GNEWS_BASE}/search", params=params)
            if r.status_code == 200:
                return r.json().get("articles", [])
    except Exception:
        pass

    return []


def _time_ago(iso: str) -> str:
    """Converte timestamp ISO para '2h atrás'."""
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        mins = int(delta.total_seconds() / 60)
        if mins < 60:
            return f"{mins}min atrás"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h atrás"
        return f"{hours // 24}d atrás"
    except Exception:
        return iso


def _format_articles(articles: list, category: str) -> list:
    return [
        {
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "url": a.get("url", ""),
            "image": a.get("image", ""),
            "source": a.get("source", {}).get("name", ""),
            "published_at": _time_ago(a.get("publishedAt", "")),
            "category": category,
        }
        for a in articles
        if a.get("title") and a.get("url")
    ]


@router.get("/news/location")
async def get_location(request: Request):
    """Retorna a localização detectada pelo IP do usuário."""
    ip = request.headers.get("X-Forwarded-For", request.client.host or "127.0.0.1")
    ip = ip.split(",")[0].strip()
    geo = await resolve_geo(ip)
    return {
        "city": geo.get("city", ""),
        "state": geo.get("regionName", ""),
        "country": geo.get("country", "Brasil"),
        "country_code": geo.get("countryCode", "BR"),
        "ip": ip,
    }


@router.get("/news")
async def get_news(
    request: Request,
    level: str = Query("city", regex="^(city|state|world)$"),
    custom_city: Optional[str] = Query(None),
):
    """
    Retorna notícias segmentadas por nível geográfico.
    level = "city" | "state" | "world"
    """
    ip = request.headers.get("X-Forwarded-For", request.client.host or "127.0.0.1")
    ip = ip.split(",")[0].strip()
    geo = await resolve_geo(ip)

    city    = custom_city or geo.get("city", "Rio de Janeiro")
    state   = geo.get("regionName", "Rio de Janeiro")
    country = geo.get("country", "Brasil")
    cc      = geo.get("countryCode", "br").lower()

    articles = []

    if level == "city":
        # Notícias ultra-locais
        q = f'"{city}"'
        tasks = [
            fetch_gnews(q, lang="pt", country=cc, max_items=12),
            fetch_gnews(f'"{city}" trânsito OR clima OR evento OR vagas', lang="pt", country=cc, max_items=6),
        ]
        results = await asyncio.gather(*tasks)
        raw = results[0] + results[1]
        articles = _format_articles(raw, "cidade")

    elif level == "state":
        # Estado + nacional
        q_state   = f'"{state}"'
        q_country = f'"{country}" política OR economia OR esporte'
        tasks = [
            fetch_gnews(q_state, lang="pt", country=cc, max_items=8),
            fetch_gnews(q_country, lang="pt", country=cc, max_items=8),
        ]
        results = await asyncio.gather(*tasks)
        arts_state   = _format_articles(results[0], "estado")
        arts_country = _format_articles(results[1], "nacional")
        articles = arts_state + arts_country

    elif level == "world":
        # Geopolítica + economia global
        tasks = [
            fetch_gnews("geopolitics OR war OR conflict OR NATO OR China OR Russia", lang="en", country="us", max_items=8),
            fetch_gnews("global economy OR inflation OR stock market OR dollar OR oil", lang="en", country="us", max_items=6),
            fetch_gnews("tecnologia IA inteligência artificial inovação", lang="pt", country="br", max_items=5),
        ]
        results = await asyncio.gather(*tasks)
        articles = (
            _format_articles(results[0], "geopolítica") +
            _format_articles(results[1], "economia") +
            _format_articles(results[2], "tecnologia")
        )

    # Deduplica por URL
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    return {
        "articles": unique[:20],
        "location": {
            "city": city,
            "state": state,
            "country": country,
        },
        "level": level,
        "api_configured": bool(GNEWS_KEY),
    }
