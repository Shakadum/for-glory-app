"""Cache dinâmico de prefeitos — TSE + Wikidata + PostgreSQL."""
import asyncio, json as _json, time
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from .models import MayorCache
from .data.mayors import _norm, MAYORS_BY_CITY
from .enrichment import enrich_with_photo, get_wiki_data
from .sources import _get


_UF_QID = {
    "AC":"Q40780","AL":"Q40806","AP":"Q40786","AM":"Q40800",
    "BA":"Q40820","CE":"Q40818","DF":"Q119509","ES":"Q43506",
    "GO":"Q43505","MA":"Q43504","MT":"Q44203","MS":"Q43508",
    "MG":"Q3227", "PA":"Q43507","PB":"Q40776","PR":"Q151966",
    "PE":"Q40783","PI":"Q40779","RJ":"Q171",  "RN":"Q40775",
    "RS":"Q40787","RO":"Q43513","RR":"Q40778","SC":"Q40801",
    "SE":"Q43510","SP":"Q174",  "TO":"Q40782",
}

# Cache em memória por UF (evita hit no DB a cada request, TTL 1h)
_MAYOR_MEM:     dict[str, dict] = {}   # { "SP": { city_norm: {...} } }
_MAYOR_MEM_TS:  dict[str, float] = {}  # { "SP": timestamp }
_MAYOR_MEM_TTL = 3600  # 1 hora


def _db_mayor_get(city_norm: str, uf: str) -> dict | None:
    """Busca prefeito no cache persistente. None se não existe ou expirado."""
    try:
        db = SessionLocal()
        row = db.query(MayorCache).filter_by(uf=uf.upper(), city_norm=city_norm).first()
        db.close()
        if not row: return None
        fetched = row.fetched_at
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - fetched > timedelta(days=90):
            return None
        d = _json.loads(row.data)
        return None if d.get("_miss") else d
    except Exception:
        return None

def _db_mayor_save(city_norm: str, city_name: str, uf: str, data: dict) -> None:
    """Salva/atualiza prefeito no cache persistente."""
    try:
        db = SessionLocal()
        row = db.query(MayorCache).filter_by(uf=uf.upper(), city_norm=city_norm).first()
        payload = _json.dumps(data, ensure_ascii=False)
        now = datetime.now(timezone.utc)
        if row:
            row.data = payload; row.city_name = city_name; row.fetched_at = now
        else:
            db.add(MayorCache(uf=uf.upper(), city_norm=city_norm,
                              city_name=city_name, data=payload, fetched_at=now))
        db.commit(); db.close()
    except Exception:
        try: db.rollback(); db.close()
        except: pass

# ── Camada 3: TSE 2024 ─────────────────────────────────────────────────

async def _fetch_tse_mayors(uf: str) -> dict:
    """Busca todos os prefeitos eleitos em 2024 via TSE Divulga.
    Retorna { city_norm: { name, party, city_name, uf } }.
    Cobre todos os ~853 municípios de SP, ~184 do RJ, etc."""
    uf = uf.upper()
    url = (f"https://resultados.tse.jus.br/oficial/ele2024/619/"
           f"dados-simplificados/{uf.lower()}/{uf.lower()}-p000011-cs.json")
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.get(url, headers=_HDR)
            if r.status_code != 200:
                return {}
            raw = r.json()
    except Exception:
        return {}

    result: dict[str, dict] = {}
    # Formato TSE: { "cand": [ { "nm": "FULANO", "sg": "PT", "mu": "SAO PAULO", ... } ] }
    # ou por município: { "abr": [ { "mu": ..., "cand": [...] } ] }
    try:
        entries = raw.get("abr", [])
        for entry in entries:
            city_raw = entry.get("mu", "")
            cands = entry.get("cand", [])
            # Pega o primeiro candidato com votos (eleito)
            for c in cands:
                if c.get("st") in ("E", "D"):  # Eleito / Deferido
                    name_raw  = c.get("nm", "").strip().title()
                    party_raw = c.get("sg", "").strip()
                    city_title = city_raw.strip().title()
                    norm = _norm(city_title)
                    if name_raw and norm:
                        result[norm] = {
                            "id":       f"tse-{_norm(city_title).replace(' ','-')}",
                            "name":     name_raw,
                            "display_name": name_raw,
                            "role":     f"Prefeito(a) de {city_title}",
                            "party":    party_raw,
                            "state":    uf,
                            "country":  "Brasil",
                            "source":   "tse",
                            "photo":    "",
                            "city_name": city_title,
                            "wiki_title_pt": name_raw,
                            "wiki_title_en": name_raw,
                        }
                    break
    except Exception:
        pass
    return result

# ── Camada 4: Wikidata bulk por estado ───────────────────────────────

async def _fetch_wikidata_mayors_bulk(uf: str) -> dict:
    """Busca TODOS os prefeitos de um estado com uma query SPARQL.
    Retorna { city_norm: politician_dict }.
    Cobertura: ~40-60% dos municípios (apenas os com P6 no Wikidata)."""
    state_qid = _UF_QID.get(uf.upper(), "")
    if not state_qid: return {}
    sparql = f"""
SELECT DISTINCT ?city ?cityLabel ?person ?personLabel ?partyLabel ?image ?sitelink WHERE {{
  ?city wdt:P31 wd:Q3184121 .
  ?city wdt:P131+ wd:{state_qid} .
  ?city wdt:P6 ?person .
  ?person wdt:P31 wd:Q5 .
  OPTIONAL {{ ?person wdt:P18 ?image }}
  OPTIONAL {{ ?person wdt:P102 ?party }}
  OPTIONAL {{ ?sitelink schema:about ?person ; schema:inLanguage "pt" ;
              schema:isPartOf <https://pt.wikipedia.org/> }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}} LIMIT 1000"""
    bindings = await _wikidata_sparql(sparql, timeout=35)
    result: dict[str, dict] = {}
    for b in bindings:
        city_label = b.get("cityLabel", {}).get("value", "")
        if not city_label: continue
        p = _parse_politician_binding(b, city_label, uf)
        if not p: continue
        p["role"] = f"Prefeito(a) de {city_label}"
        norm = _norm(city_label)
        if norm not in result:
            result[norm] = (city_label, p)
    return result  # { norm: (city_name_original, politician_dict) }

# ── Orquestrador principal ─────────────────────────────────────────────

async def _populate_uf_cache(uf: str) -> dict[str, dict]:
    """Popula o cache completo para um estado:
    TSE (todos) + Wikidata (enriquece com QID/foto).
    Retorna { city_norm: politician_dict }."""
    uf = uf.upper()

    # Executa TSE e Wikidata em paralelo
    tse_data, wd_data = await asyncio.gather(
        _fetch_tse_mayors(uf),
        _fetch_wikidata_mayors_bulk(uf),
    )

    merged: dict[str, dict] = {}

    # Base: TSE tem nome oficial de todos os prefeitos
    for norm, p in tse_data.items():
        merged[norm] = p

    # Enriquece com dados do Wikidata (QID real, foto, partido)
    for norm, (city_orig, wd_p) in wd_data.items():
        if norm in merged:
            base = merged[norm]
            # Wikidata sobrescreve: id (QID real), party se vazio, photo se disponível
            merged[norm] = {
                **base,
                "id":            wd_p["id"],       # wd-QXXXX é melhor que tse-slug
                "party":         wd_p.get("party") or base.get("party",""),
                "photo":         wd_p.get("photo") or "",
                "wiki_title_pt": wd_p.get("wiki_title_pt") or base.get("wiki_title_pt",""),
                "wiki_title_en": wd_p.get("wiki_title_en") or base.get("wiki_title_en",""),
                "source":        "wikidata",
            }
        else:
            # Cidade apenas no Wikidata (TSE não retornou — raro)
            merged[norm] = wd_p

    # Salva tudo no DB
    for norm, p in merged.items():
        _db_mayor_save(norm, p.get("city_name", norm), uf, p)

    # Atualiza cache em memória
    _MAYOR_MEM[uf] = merged
    _MAYOR_MEM_TS[uf] = time.time()
    return merged

async def _get_mayor_dynamic(city_name: str, uf: str) -> dict | None:
    """Retorna prefeito para qualquer município brasileiro.
    Ordem: memória → DB → fetch completo do estado → individual."""
    uf = uf.upper()
    norm = _norm(city_name)

    # 1. Cache em memória (1h)
    if uf in _MAYOR_MEM and (time.time() - _MAYOR_MEM_TS.get(uf, 0)) < _MAYOR_MEM_TTL:
        p = _MAYOR_MEM[uf].get(norm)
        if p: return p

    # 2. Cache no DB (90 dias)
    p = _db_mayor_get(norm, uf)
    if p: return p

    # 3. Popula cache completo do estado (TSE + Wikidata bulk)
    state_map = await _populate_uf_cache(uf)
    p = state_map.get(norm)
    if p: return p

    # 4. Fallback individual por Wikidata P6 (cidade não no TSE nem Wikidata bulk)
    for sparql in [
        f"""SELECT DISTINCT ?person ?personLabel ?partyLabel ?image ?sitelink WHERE {{
  ?city rdfs:label "{city_name}"@pt .
  ?city wdt:P31 wd:Q3184121 .
  ?city wdt:P6 ?person .
  ?person wdt:P31 wd:Q5 .
  OPTIONAL {{ ?person wdt:P18 ?image }}
  OPTIONAL {{ ?person wdt:P102 ?party }}
  OPTIONAL {{ ?sitelink schema:about ?person ; schema:inLanguage "pt" ;
              schema:isPartOf <https://pt.wikipedia.org/> }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}} LIMIT 3""",
    ]:
        bindings = await _wikidata_sparql(sparql)
        for b in bindings:
            p = _parse_politician_binding(b, city_name, uf)
            if p:
                p["role"] = f"Prefeito(a) de {city_name}"
                _db_mayor_save(norm, city_name, uf, p)
                return p

    # Não encontrado — salva miss para não repetir queries caras
    _db_mayor_save(norm, city_name, uf, {"_miss": True, "city_name": city_name})
    return None

# ── Compatibilidade com código existente ─────────────────────────────

async def get_mayor_by_city_wikidata(city_name: str, uf: str = "") -> dict | None:
    """Wrapper legado — redireciona para o novo sistema dinâmico."""
    if not city_name: return None
    return await _get_mayor_dynamic(city_name, uf)

async def search_city_politicians_wikidata(city_name: str, uf: str = "") -> list:
    """Busca vereadores e políticos locais via Wikidata SPARQL."""
    sparql = f"""
SELECT DISTINCT ?person ?personLabel ?posLabel ?partyLabel ?image WHERE {{
  ?person wdt:P31 wd:Q5 .
  ?person p:P39 ?posStmt .
  ?posStmt ps:P39 ?pos .
  ?posStmt pq:P642 ?city .
  ?city rdfs:label ?cityLabel .
  FILTER(LCASE(STR(?cityLabel)) = LCASE("{city_name}"))
  FILTER(LANG(?cityLabel) = "pt")
  OPTIONAL {{ ?person wdt:P18 ?image }}
  OPTIONAL {{ ?person wdt:P102 ?party }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}} LIMIT 25"""
    bindings = await _wikidata_sparql(sparql)
    seen, results = set(), []
    for b in bindings:
        p = _parse_politician_binding(b, city_name, uf)
        if p and p["id"] not in seen:
            seen.add(p["id"])
            results.append(p)
    return results[:15]



