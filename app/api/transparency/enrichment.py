"""
For Glory — Portal da Transparência
Módulo: Enriquecimento de dados — fotos, bio, Wikipedia
"""
import asyncio, time, urllib.parse
import httpx
from .data.fallback_photos import _FALLBACK_PHOTOS
from .data.politicians import CURATED_POLITICIANS

_HDR = {"User-Agent": "ForGloryApp/2.0 (transparency@forglory.online)"}

_PHOTO_CACHE: dict = {}
_PHOTO_CACHE_TTL = 43200  # 12 horas

_PHOTO_LOCK = asyncio.Lock()

async def _wiki_summary(title: str, lang: str = "pt") -> dict:
    """Busca resumo Wikipedia pelo título EXATO via REST API — sempre URL atual."""
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    d = await _get(url, timeout=8)
    if d and d.get("type") == "standard" and d.get("extract"):
        # originalimage = maior resolução; thumbnail = fallback
        photo = (d.get("originalimage") or d.get("thumbnail") or {}).get("source", "")
        return {
            "bio":   d["extract"][:900],
            "photo": photo,
            "link":  d.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }
    return {}

async def get_photo(wiki_title_pt: str, wiki_title_en: str = "") -> str:
    """Retorna URL de foto via Wikipedia (cache 12h) com fallback garantido."""
    if not wiki_title_pt and not wiki_title_en:
        return ""
    cache_key = wiki_title_pt or wiki_title_en
    now = time.time()
    cached = _PHOTO_CACHE.get(cache_key)
    if cached and (now - cached["ts"]) < _PHOTO_CACHE_TTL:
        return cached.get("photo", "")
    async with _PHOTO_LOCK:
        cached = _PHOTO_CACHE.get(cache_key)
        if cached and (now - cached["ts"]) < _PHOTO_CACHE_TTL:
            return cached.get("photo", "")
        result = {}
        if wiki_title_pt:
            result = await _wiki_summary(wiki_title_pt, "pt")
        if not result.get("photo") and wiki_title_en:
            result = await _wiki_summary(wiki_title_en, "en")
        # Fallback garantido: URLs verificadas do Wikimedia Commons
        if not result.get("photo"):
            fb = _FALLBACK_PHOTOS.get(wiki_title_pt) or _FALLBACK_PHOTOS.get(wiki_title_en, "")
            if fb:
                result = {**result, "photo": fb}
        _PHOTO_CACHE[cache_key] = {**result, "ts": now}
        return result.get("photo", "")

async def get_wiki_data(wiki_title_pt: str, wiki_title_en: str = "") -> dict:
    """Retorna { photo, bio, link } com cache de 12h."""
    if not wiki_title_pt and not wiki_title_en:
        return {}
    cache_key = wiki_title_pt or wiki_title_en
    now = time.time()
    cached = _PHOTO_CACHE.get(cache_key)
    if cached and (now - cached["ts"]) < _PHOTO_CACHE_TTL:
        return cached
    async with _PHOTO_LOCK:
        cached = _PHOTO_CACHE.get(cache_key)
        if cached and (now - cached["ts"]) < _PHOTO_CACHE_TTL:
            return cached
        result = {}
        if wiki_title_pt:
            result = await _wiki_summary(wiki_title_pt, "pt")
        if not result.get("photo") and wiki_title_en:
            result = await _wiki_summary(wiki_title_en, "en")
    # Fallback garantido — URLs verificadas do Wikimedia Commons
    if not result.get("photo"):
        fb = _FALLBACK_PHOTOS.get(wiki_title_pt) or _FALLBACK_PHOTOS.get(wiki_title_en, "")
        if fb:
            result = {**result, "photo": fb}
    entry = {**result, "ts": now}
    _PHOTO_CACHE[cache_key] = entry
    return entry

# _warmup_photo_cache é definida APÓS CURATED_POLITICIANS (ver abaixo)

# ── DADOS CURADOS — POLÍTICOS PRINCIPAIS ─────────────────────
# Fonte: dados oficiais verificados manualmente


async def _warmup_photo_cache():
    """Pre-aquece o cache de fotos em background. Definida após CURATED_POLITICIANS."""
    await asyncio.sleep(8)
    batch_size = 4
    keys = list(CURATED_POLITICIANS.keys())
    for i in range(0, len(keys), batch_size):
        batch = [CURATED_POLITICIANS[k] for k in keys[i:i+batch_size]]
        await asyncio.gather(*[
            get_wiki_data(p.get("wiki_title_pt",""), p.get("wiki_title_en",""))
            for p in batch if p.get("wiki_title_pt") or p.get("wiki_title_en")
        ])
        await asyncio.sleep(0.8)



async def enrich_with_photo(p: dict) -> dict:
    """Busca foto via cache dinâmico com múltiplos fallbacks.
    Ordem: 1) wiki_title_pt → Wikipedia PT
           2) wiki_title_en → Wikipedia EN
           3) _FALLBACK_PHOTOS (Wikimedia Commons verificado)
           4) foto já presente no dict (não sobrescreve)
    """
    wiki_title = p.get("wiki_title_pt") or ""
    wiki_en    = p.get("wiki_title_en") or ""
    name       = p.get("name", "")

    # 1 & 2: Wikipedia PT/EN via cache
    if wiki_title or wiki_en:
        photo = await get_photo(wiki_title, wiki_en)
        if photo:
            return {**p, "photo": photo}

    # 3: Fallback por nome ou título
    for key in [wiki_title, wiki_en, name]:
        if key and key in _FALLBACK_PHOTOS:
            return {**p, "photo": _FALLBACK_PHOTOS[key]}

    # 4: Se já tem foto, mantém
    if p.get("photo"):
        return p

    # 5: Última tentativa — busca pelo nome sem cache
    if name and name != wiki_title:
        wiki = await _wiki_summary(name, "pt")
        if wiki.get("photo"):
            return {**p, "photo": wiki["photo"]}

    # 6: Avatar gerado — garante que NUNCA aparece sem imagem no frontend
    # DiceBear Initials — placeholder visual consistente com o nome
    if name:
        initials = "+".join(w for w in name.split() if w)
        avatar_url = f"https://ui-avatars.com/api/?name={urllib.parse.quote(initials)}&background=1a1f2e&color=66fcf1&bold=true&size=200&font-size=0.38"
        return {**p, "photo": avatar_url}

    return p
# Fotos dos ministros do STF via Wikimedia Commons (URLs verificadas)
# Padrão: https://commons.wikimedia.org/wiki/File:Nome_do_arquivo.jpg
STF_MINISTERS = [
    {"id":"wd-Q10319857","name":"Luís Roberto Barroso","role":"Presidente do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"Luís Roberto Barroso","wiki_title_en":"Roberto Barroso","photo":""},
    {"id":"wd-Q2948413","name":"Cármen Lúcia","role":"Ministra do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"Cármen Lúcia Antunes Rocha","wiki_title_en":"Carmen Lúcia","photo":""},
    {"id":"wd-Q10314705","name":"Dias Toffoli","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"Dias Toffoli","wiki_title_en":"Dias Toffoli","photo":""},
    {"id":"wd-Q1516706","name":"Gilmar Mendes","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"Gilmar Ferreira Mendes","wiki_title_en":"Gilmar Mendes","photo":""},
    {"id":"wd-Q10321893","name":"Edson Fachin","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"Edson Fachin","wiki_title_en":"Edson Fachin","photo":""},
    {"id":"wd-Q16503855","name":"Alexandre de Moraes","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"Alexandre de Moraes","wiki_title_en":"Alexandre de Moraes","photo":""},
    {"id":"wd-Q106363617","name":"André Mendonça","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"André Mendonça (ministro)","wiki_title_en":"André Mendonça","photo":""},
    {"id":"wd-Q105748993","name":"Kassio Nunes Marques","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"Kassio Nunes Marques","wiki_title_en":"Kassio Nunes Marques","photo":""},
    {"id":"wd-Q768093","name":"Flávio Dino","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"Flávio Dino","wiki_title_en":"Flávio Dino","photo":""},
    {"id":"wd-Q118812476","name":"Cristiano Zanin","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "wiki_title_pt":"Cristiano Zanin Martins","wiki_title_en":"Cristiano Zanin","photo":""},
]

