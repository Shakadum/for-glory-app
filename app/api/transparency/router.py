"""Rotas FastAPI do Portal da Transparência."""
import asyncio
import traceback
import logging
_log = logging.getLogger(__name__)
import json as _json
from typing import Optional
from fastapi import APIRouter, Query, Depends, Body, Request as FARequest, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal

from .models import PoliticianRating, MayorCache
from .data.politicians import CURATED_POLITICIANS
from .data.mayors import _norm, get_mayor_data, GOVERNORS_BY_UF, UF_NAMES, COUNTRY_FLAGS
from .data.charges import _CHARGES_DB
from .data.salaries import SALARY_BR
from .enrichment import get_photo, get_wiki_data, enrich_with_photo, _warmup_photo_cache, _PHOTO_CACHE
from .data.fallback_photos import _FALLBACK_PHOTOS
from .sources import search_wikidata_politicians, _get, _wikidata_sparql, _parse_politician_binding, get_executive_actions, get_deputado_details, get_senador_details, get_wikidata_entity
from .mayor_cache import _get_mayor_dynamic, _populate_uf_cache, search_city_politicians_wikidata, _db_mayor_get, _UF_QID, _MAYOR_MEM
from .geo import get_local_politicians as _get_local_impl, STF_MINISTERS
from .encyclopedia import (
    create_edit_suggestion, vote_on_edit, moderate_edit,
    get_edits_for_politician, get_revision_history, get_pending_edits,
    get_trust_score, EDITABLE_FIELDS, SOURCE_KINDS,
)


router = APIRouter()

def _get_charges(name: str, full_name: str = "") -> list:
    for key, charges in _CHARGES_DB.items():
        if key.lower() in name.lower() or key.lower() in (full_name or "").lower():
            return charges
    return []



@router.on_event("startup")
async def on_startup():
    """Dispara warmup do cache de fotos na inicialização."""
    asyncio.create_task(_warmup_photo_cache())


@router.get("/transparency/search")
async def search_politicians(q:str=Query(...,min_length=2), country:Optional[str]=Query("BR")):
    country = (country or "BR").upper()
    if country == "BR":
        dep_r, sen_r, wd_r = await asyncio.gather(
            search_deputados(q), search_senadores(q), search_wikidata_politicians(q))
        br_names = {r["name"].lower() for r in dep_r+sen_r}
        return {"results": dep_r + sen_r + [r for r in wd_r if r["name"].lower() not in br_names], "query":q}
    return {"results": await search_wikidata_politicians(q), "query":q}

@router.get("/transparency/politician/{politician_id}")
async def get_politician(politician_id:str, db:Session=Depends(get_db)):
    # 1. Verifica banco de dados curado primeiro
    if politician_id in CURATED_POLITICIANS:
        details = dict(CURATED_POLITICIANS[politician_id])
        wiki_title_pt = details.pop("wiki_title_pt", "") or ""
        wiki_title_en = details.pop("wiki_title_en", "") or ""

        # Busca bio + foto via cache dinâmico (sempre URL atual)
        async def _empty(): return {}
        is_exec = politician_id in ("wd-Q28227", "wd-Q41551")

        wiki_task = get_wiki_data(wiki_title_pt, wiki_title_en)
        act_task  = get_executive_actions() if is_exec else _empty()
        wiki_res, act_res = await asyncio.gather(wiki_task, act_task)

        # Foto: Wikipedia → fallback Wikimedia Commons
        photo = wiki_res.get("photo", "")
        if not photo:
            photo = _FALLBACK_PHOTOS.get(wiki_title_pt) or _FALLBACK_PHOTOS.get(wiki_title_en, "")
        details["photo"] = photo or details.get("photo", "")
        if wiki_res.get("bio"):
            details["bio"]       = wiki_res["bio"]
            details["wiki_link"] = wiki_res.get("link", "")
        if is_exec and act_res:
            details["executive_actions"] = act_res.get("actions", [])
            details["actions_source"]    = act_res.get("source", "")
        # Complementa charges do banco de dados (não sobrescreve dados curados)
        if not details.get("charges"):
            details["charges"] = _get_charges(
                details.get("name",""), details.get("full_name","")
            )
    else:
        parts = politician_id.split("-", 1)
        source = parts[0]
        api_id = parts[1] if len(parts) > 1 else ""

        if source == "dep":
            details = await get_deputado_details(api_id)
        elif source == "sen":
            details = await get_senador_details(api_id)
        elif source == "wd":
            details = await get_wikidata_entity(api_id)
        elif source == "tse":
            # Prefeito do sistema TSE — busca no cache do banco pelo ID
            try:
                db2 = SessionLocal()
                row = db2.query(MayorCache).filter(
                    MayorCache.data.contains(f'"id": "{politician_id}"')
                ).first()
                db2.close()
                if row:
                    details = _json.loads(row.data)
                else:
                    return {"error": "Prefeito não encontrado no cache"}
            except Exception:
                return {"error": "Erro ao buscar prefeito"}
            # Enriquece com Wikipedia
            wiki_pt = details.pop("wiki_title_pt", details.get("name", ""))
            wiki_en = details.pop("wiki_title_en", details.get("name", ""))
            wiki_res = await get_wiki_data(wiki_pt, wiki_en)
            details["photo"]     = wiki_res.get("photo") or details.get("photo", "")
            details["bio"]       = wiki_res.get("bio", "")
            details["wiki_link"] = wiki_res.get("link", "")
        else:
            # IDs "mayor-*" — curated ou não encontrado
            match = next((v for v in CURATED_POLITICIANS.values() if v.get("id") == politician_id), None)
            if match:
                details = dict(match)
                wiki_title_pt = details.pop("wiki_title_pt", "") or ""
                wiki_title_en = details.pop("wiki_title_en", "") or ""
                wiki_res = await get_wiki_data(wiki_title_pt, wiki_title_en)
                photo = wiki_res.get("photo", "")
                if not photo:
                    photo = _FALLBACK_PHOTOS.get(wiki_title_pt) or _FALLBACK_PHOTOS.get(wiki_title_en, "")
                details["photo"] = photo or details.get("photo", "")
                if wiki_res.get("bio"):
                    details["bio"] = wiki_res["bio"]
                    details["wiki_link"] = wiki_res.get("link", "")
            else:
                return {"error": "Político não encontrado"}

    ratings = db.query(PoliticianRating).filter_by(politician_id=politician_id).all()
    avg = (sum(r.score for r in ratings)/len(ratings)) if ratings else None
    details["community_rating"] = {
        "average": round(avg,1) if avg else None, "count": len(ratings),
        "comments":[{"score":r.score,"comment":r.comment or "",
            "date":r.created_at.strftime("%d/%m/%Y") if r.created_at else ""}
            for r in sorted(ratings, key=lambda x: x.created_at or datetime.min, reverse=True)[:10]]}
    return details

@router.post("/transparency/rate")
async def rate_politician(data:dict=Body(...), db:Session=Depends(get_db)):
    pid=str(data.get("politician_id","")).strip(); uid=int(data.get("user_id",0))
    score=int(data.get("score",3)); comment=str(data.get("comment",""))[:400]
    if not pid or not uid or not(1<=score<=5): return {"error":"Dados inválidos"}
    ex = db.query(PoliticianRating).filter_by(politician_id=pid,user_id=uid).first()
    if ex: ex.score=score; ex.comment=comment; ex.created_at=datetime.now(timezone.utc)
    else: db.add(PoliticianRating(politician_id=pid,user_id=uid,score=score,comment=comment))
    db.commit()
    ratings = db.query(PoliticianRating).filter_by(politician_id=pid).all()
    avg = round(sum(r.score for r in ratings)/len(ratings),1)
    return {"status":"ok","new_average":avg,"count":len(ratings)}

@router.get("/transparency/compare")
async def compare_politicians(ids:str=Query(...)):
    id_list = [i.strip() for i in ids.split(",") if i.strip()][:4]
    async def _fetch(pid):
        # 1. Dict curado pelo ID exato
        if pid in CURATED_POLITICIANS:
            d = dict(CURATED_POLITICIANS[pid]); d.pop("wiki_title_pt",None); d.pop("wiki_title_en",None); return d
        # 2. IDs curados alternativos (mayor-*, etc.)
        match = next((v for v in CURATED_POLITICIANS.values() if v.get("id") == pid), None)
        if match:
            d = dict(match); d.pop("wiki_title_pt",None); d.pop("wiki_title_en",None); return d
        parts=pid.split("-",1); src=parts[0]; aid=parts[1] if len(parts)>1 else ""
        if src=="dep": return await get_deputado_details(aid)
        if src=="sen": return await get_senador_details(aid)
        if src=="wd":  return await get_wikidata_entity(aid)
        if src=="tse":
            try:
                db2 = SessionLocal()
                needle = '"id": "' + pid + '"'
                row = db2.query(MayorCache).filter(MayorCache.data.contains(needle)).first()
                db2.close()
                return _json.loads(row.data) if row else {}
            except: return {}
        return {}
    results = await asyncio.gather(*[_fetch(pid) for pid in id_list])
    return {"politicians":[{"id":pid,**d} for pid,d in zip(id_list,results)]}

@router.get("/transparency/cities/{uf}")
async def get_cities_by_uf(uf: str):
    """Retorna todos os municípios de um estado via API do IBGE."""
    data = await _get(
        f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf.upper()}/municipios",
        timeout=10
    )
    if not data:
        return {"cities": [], "uf": uf.upper()}
    cities = sorted([m.get("nome","") for m in data if m.get("nome")])
    return {"cities": cities, "uf": uf.upper(), "total": len(cities)}


# ═══════════════════════════════════════════════════════════════════════
#  WIKIDATA SPARQL — base de todas as buscas de políticos
# ═══════════════════════════════════════════════════════════════════════





@router.get("/transparency/local")
async def get_local_politicians(
    request: FARequest,
    uf_override: Optional[str] = Query(None),
    city_override: Optional[str] = Query(None),
):
    try:
        return await _get_local_impl(request, uf_override, city_override)
    except Exception as exc:
        _log.error(f"[/transparency/local] ERRO: {exc}\n{traceback.format_exc()}")
        raise



@router.get("/transparency/prefetch-mayors/{uf}")
async def prefetch_mayors(uf: str):
    """Popula o cache de prefeitos para um estado inteiro (TSE + Wikidata).
    Chamar via cron: GET /transparency/prefetch-mayors/SP, /RJ, etc.
    Retorna resumo do que foi encontrado."""
    uf = uf.upper()
    if uf not in _UF_QID and uf != "DF":
        return {"error": "UF inválida"}
    state_map = await _populate_uf_cache(uf)
    tse_count = sum(1 for p in state_map.values() if p.get("source") in ("tse",))
    wd_count  = sum(1 for p in state_map.values() if p.get("source") == "wikidata")
    return {
        "status":   "ok",
        "uf":       uf,
        "total":    len(state_map),
        "tse":      tse_count,
        "wikidata": wd_count,
        "sample":   [{"city": p.get("city_name","?"), "name": p.get("name","?"), "party": p.get("party","")}
                     for p in list(state_map.values())[:10]],
    }

@router.get("/transparency/prefetch-all-mayors")
async def prefetch_all_mayors():
    """Popula o cache de todos os estados. Usar apenas no deploy inicial.
    Execução assíncrona — retorna imediatamente, processa em background."""
    all_ufs = list(_UF_QID.keys())
    results = {}
    for uf in all_ufs:
        try:
            state_map = await _populate_uf_cache(uf)
            results[uf] = len(state_map)
            await asyncio.sleep(2)  # respeita rate limit do Wikidata e TSE
        except Exception as e:
            results[uf] = f"erro: {e}"
    return {"status": "ok", "total_cached": sum(v for v in results.values() if isinstance(v, int)), "by_uf": results}

@router.get("/transparency/mayor-cache-stats")
async def mayor_cache_stats():
    """Estatísticas do cache de prefeitos no banco."""
    try:
        db = SessionLocal()
        total = db.query(MayorCache).count()
        by_uf = {}
        for uf in _UF_QID:
            by_uf[uf] = db.query(MayorCache).filter_by(uf=uf).count()
        db.close()
        return {"total": total, "by_uf": by_uf, "mem_loaded": list(_MAYOR_MEM.keys())}
    except Exception as e:
        return {"error": str(e)}

@router.get("/transparency/refresh-photos")
async def refresh_photo_cache():
    """Força refresh do cache de fotos para todos os políticos curados.
    Chamado automaticamente pelo cron do Render a cada 12h."""
    _PHOTO_CACHE.clear()
    refreshed = []
    for pid, p in CURATED_POLITICIANS.items():
        wiki_pt = p.get("wiki_title_pt", "")
        wiki_en = p.get("wiki_title_en", "")
        if wiki_pt or wiki_en:
            photo = await get_photo(wiki_pt, wiki_en)
            refreshed.append({"id": pid, "name": p.get("name"), "has_photo": bool(photo)})
            await asyncio.sleep(0.5)
    return {"status": "ok", "refreshed": len(refreshed), "results": refreshed}


@router.get("/transparency/photo")
async def get_politician_photo(title: str = Query(...)):
    """Retorna URL de foto atual para um título Wikipedia."""
    photo = await get_photo(title)
    return {"photo": photo, "title": title}


@router.get("/transparency/featured")
async def featured_politicians():
    return {"featured": [
        {**CURATED_POLITICIANS["wd-Q28227"]},
        {**CURATED_POLITICIANS["wd-Q41551"]},
        {"id":"wd-Q22686","name":"Donald Trump","role":"Presidente dos EUA","country":"EUA","party":"Republicano","source":"wikidata","photo":""},
        {"id":"wd-Q47468","name":"Emmanuel Macron","role":"Presidente da França","country":"França","party":"Renaissance","source":"wikidata","photo":""},
    ]}


# ═══════════════════════════════════════════════════════════════════════════════
# ENCICLOPÉDIA VIVA
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/transparency/politician/{politician_id}/trust")
async def get_politician_trust(politician_id: str, db: Session = Depends(get_db)):
    """Score de confiança do político."""
    return get_trust_score(db, politician_id)


@router.get("/transparency/politician/{politician_id}/edits")
async def list_politician_edits(
    politician_id: str,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Lista sugestões de edição de um político."""
    return {"edits": get_edits_for_politician(db, politician_id, status)}


@router.get("/transparency/politician/{politician_id}/history")
async def list_politician_history(politician_id: str, db: Session = Depends(get_db)):
    """Histórico de revisões aprovadas."""
    return {"history": get_revision_history(db, politician_id)}


@router.post("/transparency/politician/{politician_id}/suggest")
async def suggest_edit(
    politician_id: str,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Sugerir uma edição para um campo do político."""
    user_id = int(data.get("user_id", 0))
    field   = str(data.get("field", ""))
    new_val = data.get("new_value")
    old_val = data.get("old_value")
    reason  = str(data.get("reason", ""))[:500]
    sources = data.get("sources", [])

    if not user_id:
        return {"error": "Autenticação necessária"}
    if not field or new_val is None:
        return {"error": "Campo e novo valor são obrigatórios"}

    try:
        edit = create_edit_suggestion(
            db, politician_id, user_id, field, new_val, old_val, reason, sources
        )
        return {"status": "ok", "edit_id": edit.id, "message": "Sugestão enviada para moderação!"}
    except ValueError as e:
        return {"error": str(e)}


@router.post("/transparency/edit/{edit_id}/vote")
async def vote_edit(edit_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Votar numa sugestão (+1 apoia, -1 contesta)."""
    user_id = int(data.get("user_id", 0))
    value   = int(data.get("value", 1))
    if not user_id:
        return {"error": "Autenticação necessária"}
    try:
        return vote_on_edit(db, edit_id, user_id, value)
    except Exception as e:
        return {"error": str(e)}


@router.post("/transparency/edit/{edit_id}/moderate")
async def moderate_edit_route(
    edit_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Aprovar ou rejeitar uma sugestão (requer is_staff=True no usuário)."""
    mod_id  = int(data.get("moderator_id", 0))
    approve = bool(data.get("approve", False))
    note    = str(data.get("note", ""))[:400]

    if not mod_id:
        return {"error": "Autenticação necessária"}

    # Verificar se usuário é staff
    from app.db.session import SessionLocal as _SL
    from app.models import User
    db2 = _SL()
    try:
        mod = db2.query(User).filter_by(id=mod_id).first()
        if not mod or not getattr(mod, "is_staff", False):
            return {"error": "Permissão insuficiente"}
    finally:
        db2.close()

    try:
        edit = moderate_edit(db, edit_id, mod_id, approve, note)
        return {
            "status": "ok",
            "edit_status": edit.status,
            "message": "Aprovado ✅" if approve else "Rejeitado ❌",
        }
    except ValueError as e:
        return {"error": str(e)}


@router.get("/transparency/moderation/queue")
async def moderation_queue(
    moderator_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Fila de moderação — todas as sugestões pendentes."""
    from app.db.session import SessionLocal as _SL
    from app.models import User
    db2 = _SL()
    try:
        mod = db2.query(User).filter_by(id=moderator_id).first()
        if not mod or not getattr(mod, "is_staff", False):
            return {"error": "Permissão insuficiente"}
    finally:
        db2.close()
    return {"queue": get_pending_edits(db), "fields": EDITABLE_FIELDS, "source_kinds": SOURCE_KINDS}


@router.get("/transparency/fields")
async def list_editable_fields():
    """Campos editáveis pela comunidade."""
    return {"fields": EDITABLE_FIELDS, "source_kinds": SOURCE_KINDS}
