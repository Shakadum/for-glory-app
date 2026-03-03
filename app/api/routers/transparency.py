"""
For Glory — Portal da Transparência
-------------------------------------
Fontes de dados (todas públicas e gratuitas):

BRASIL:
  - API Câmara dos Deputados: https://dadosabertos.camara.leg.br/api/v2
  - API Senado Federal:       https://legis.senado.leg.br/dadosabertos
  - Portal da Transparência:  https://api.portaldatransparencia.gov.br (requer chave gratuita)
  
INTERNACIONAL:
  - Wikidata SPARQL:          https://query.wikidata.org
  - Wikipedia REST API:       https://en.wikipedia.org/api/rest_v1
  
AVALIAÇÕES:
  - Salvas no banco local (tabela politician_ratings)
  
Variáveis de ambiente opcionais:
  TRANSPARENCIA_API_KEY  → chave da API Portal da Transparência (gratuita em portaldatransparencia.gov.br)
"""

import os
import httpx
import asyncio
from fastapi import APIRouter, Query, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from typing import Optional
from app.db.session import get_db
from app.db.base import Base

router = APIRouter()

CAMARA_BASE  = "https://dadosabertos.camara.leg.br/api/v2"
SENADO_BASE  = "https://legis.senado.leg.br/dadosabertos"
TRANSP_KEY   = os.environ.get("TRANSPARENCIA_API_KEY", "")
TRANSP_BASE  = "https://api.portaldatransparencia.gov.br/api-de-dados"
WIKIDATA_URL = "https://query.wikidata.org/sparql"
WIKI_REST    = "https://en.wikipedia.org/api/rest_v1"

# ─────────────────────────────────────────────────────────────
#  MODELOS DE BANCO (ratings de usuários)
# ─────────────────────────────────────────────────────────────

class PoliticianRating(Base):
    __tablename__ = "politician_ratings"
    id           = Column(Integer, primary_key=True, index=True)
    politician_id= Column(String(100), index=True)   # ex: "dep-12345" ou "sen-678"
    user_id      = Column(Integer, index=True)
    score        = Column(Integer)                   # 1-5
    comment      = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─────────────────────────────────────────────────────────────
#  HELPERS HTTP
# ─────────────────────────────────────────────────────────────

async def _get(url: str, params: dict = None, headers: dict = None, timeout: int = 8) -> dict | list | None:
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.get(url, params=params, headers=headers or {})
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────
#  BUSCA DE POLÍTICOS BRASILEIROS
# ─────────────────────────────────────────────────────────────

async def search_deputados(query: str, uf: str = None) -> list:
    params = {"nome": query, "itens": 10, "ordem": "ASC", "ordenarPor": "nome"}
    if uf:
        params["siglaUf"] = uf.upper()
    data = await _get(f"{CAMARA_BASE}/deputados", params=params)
    if not data or "dados" not in data:
        return []
    results = []
    for d in data["dados"]:
        results.append({
            "id":       f"dep-{d.get('id','')}",
            "api_id":   d.get("id"),
            "name":     d.get("nome", ""),
            "party":    d.get("siglaPartido", ""),
            "state":    d.get("siglaUf", ""),
            "role":     "Deputado Federal",
            "country":  "Brasil",
            "photo":    d.get("urlFoto", ""),
            "email":    d.get("email", ""),
            "source":   "camara",
        })
    return results


async def search_senadores(query: str) -> list:
    # Senado não tem busca por nome diretamente — busca lista atual e filtra
    data = await _get(f"{SENADO_BASE}/senador/lista/atual.json")
    if not data:
        return []
    try:
        senadores = data["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    except (KeyError, TypeError):
        return []
    
    q = query.lower()
    results = []
    for s in senadores:
        try:
            id_sen = s["IdentificacaoParlamentar"]
            nome = id_sen.get("NomeParlamentar", "") or id_sen.get("NomeCompletoParlamentar", "")
            if q not in nome.lower():
                continue
            results.append({
                "id":       f"sen-{id_sen.get('CodigoParlamentar','')}",
                "api_id":   id_sen.get("CodigoParlamentar"),
                "name":     nome,
                "party":    id_sen.get("SiglaPartidoParlamentar", ""),
                "state":    id_sen.get("UfParlamentar", ""),
                "role":     "Senador",
                "country":  "Brasil",
                "photo":    id_sen.get("UrlFotoParlamentar", ""),
                "email":    id_sen.get("EmailParlamentar", ""),
                "source":   "senado",
            })
            if len(results) >= 5:
                break
        except Exception:
            continue
    return results


# ─────────────────────────────────────────────────────────────
#  BUSCA INTERNACIONAL (Wikidata)
# ─────────────────────────────────────────────────────────────

async def search_wikidata_politicians(query: str, country_code: str = None) -> list:
    """Busca políticos no Wikidata por nome."""
    # SPARQL query: find people that are politicians / heads of state / presidents
    sparql = f"""
SELECT DISTINCT ?person ?personLabel ?partyLabel ?countryLabel ?roleLabel ?image WHERE {{
  ?person wdt:P31 wd:Q5 .
  ?person wdt:P106 ?occupation .
  VALUES ?occupation {{ wd:Q82955 wd:Q372436 wd:Q1028181 wd:Q4964182 wd:Q30461 wd:Q16707842 }}
  ?person rdfs:label ?label .
  FILTER(CONTAINS(LCASE(?label), LCASE("{query}")))
  FILTER(LANG(?label) = "pt" || LANG(?label) = "en" || LANG(?label) = "es")
  OPTIONAL {{ ?person wdt:P18 ?image }}
  OPTIONAL {{ ?person wdt:P102 ?party }}
  OPTIONAL {{ ?person wdt:P27 ?country }}
  OPTIONAL {{ ?person wdt:P39 ?role }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en,es". }}
}}
LIMIT 8
"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(WIKIDATA_URL, params={"query": sparql, "format": "json"},
                           headers={"Accept": "application/json", "User-Agent": "ForGloryApp/1.0"})
            if r.status_code != 200:
                return []
            bindings = r.json().get("results", {}).get("bindings", [])
    except Exception:
        return []
    
    seen = set()
    results = []
    for b in bindings:
        qid = b.get("person", {}).get("value", "").split("/")[-1]
        if qid in seen:
            continue
        seen.add(qid)
        name = b.get("personLabel", {}).get("value", "")
        if not name or name.startswith("Q"):
            continue
        results.append({
            "id":      f"wd-{qid}",
            "api_id":  qid,
            "name":    name,
            "party":   b.get("partyLabel", {}).get("value", ""),
            "state":   "",
            "role":    b.get("roleLabel", {}).get("value", "Político"),
            "country": b.get("countryLabel", {}).get("value", ""),
            "photo":   b.get("image", {}).get("value", ""),
            "email":   "",
            "source":  "wikidata",
        })
    return results


# ─────────────────────────────────────────────────────────────
#  DETALHES DO POLÍTICO
# ─────────────────────────────────────────────────────────────

async def get_deputado_details(api_id: str) -> dict:
    """Busca detalhes de um deputado: despesas, presença, projetos."""
    base_url = f"{CAMARA_BASE}/deputados/{api_id}"
    
    data, despesas_data, votacoes_data = await asyncio.gather(
        _get(base_url),
        _get(f"{base_url}/despesas", params={"itens": 5, "ordenarPor": "ano", "ordem": "DESC"}),
        _get(f"{base_url}/votacoes", params={"itens": 10, "ordenarPor": "dataHoraVoto", "ordem": "DESC"}),
    )
    
    details = {}
    if data and "dados" in data:
        d = data["dados"]
        ult = d.get("ultimoStatus", {})
        details.update({
            "full_name":   d.get("nomeCivil", ""),
            "birth_date":  d.get("dataNascimento", ""),
            "education":   d.get("escolaridade", ""),
            "occupation":  d.get("profissoes", [{}])[0].get("titulo", "") if d.get("profissoes") else "",
            "website":     ult.get("urlRedeSocial", ""),
            "bio":         d.get("urlWebsite", ""),
            "party":       ult.get("siglaPartido", ""),
            "state":       ult.get("siglaUf", ""),
            "cabinet":     ult.get("gabinete", {}).get("sala", ""),
        })

    # Últimas despesas
    expenses = []
    if despesas_data and "dados" in despesas_data:
        for e in despesas_data["dados"][:5]:
            expenses.append({
                "description": e.get("tipoDespesa", ""),
                "value":       e.get("valorLiquido", 0),
                "date":        f"{e.get('mes','')}/{e.get('ano','')}",
                "provider":    e.get("nomeFornecedor", ""),
            })
    details["expenses"] = expenses

    # Votações recentes
    votes = []
    if votacoes_data and "dados" in votacoes_data:
        for v in votacoes_data["dados"][:5]:
            votes.append({
                "description": v.get("descricao", ""),
                "date":        v.get("dataHoraVoto", "")[:10] if v.get("dataHoraVoto") else "",
            })
    details["votes"] = votes

    return details


async def get_senador_details(api_id: str) -> dict:
    """Busca detalhes de um senador."""
    data = await _get(f"{SENADO_BASE}/senador/{api_id}.json")
    details = {}
    if data:
        try:
            p = data["DetalheParlamentar"]["Parlamentar"]
            ident = p.get("IdentificacaoParlamentar", {})
            dados = p.get("DadosBasicosParlamentar", {})
            details.update({
                "full_name":  ident.get("NomeCompletoParlamentar", ""),
                "birth_date": dados.get("DataNascimento", ""),
                "education":  dados.get("FormacaoAcademica", ""),
                "occupation": dados.get("Profissao", ""),
                "website":    ident.get("UrlPaginaParlamentar", ""),
            })
        except Exception:
            pass
    
    # Votações
    votes_data = await _get(f"{SENADO_BASE}/senador/{api_id}/votacoes.json", params={"v": 6})
    votes = []
    if votes_data:
        try:
            vlist = votes_data["VotacoesParlamentar"]["Parlamentar"]["Votacoes"]["Votacao"]
            if isinstance(vlist, dict):
                vlist = [vlist]
            for v in vlist[:5]:
                votes.append({
                    "description": v.get("DescricaoVotacao", ""),
                    "date":        v.get("DataSessao", ""),
                    "vote":        v.get("Voto", ""),
                })
        except Exception:
            pass
    details["votes"] = votes
    details["expenses"] = []
    return details


async def get_wikidata_details(qid: str) -> dict:
    """Busca detalhes de um político via Wikidata + Wikipedia."""
    sparql = f"""
SELECT ?birthDate ?birthPlaceLabel ?partyLabel ?countryLabel ?educationLabel ?positionLabel ?image ?article WHERE {{
  wd:{qid} wdt:P31 wd:Q5 .
  OPTIONAL {{ wd:{qid} wdt:P569 ?birthDate }}
  OPTIONAL {{ wd:{qid} wdt:P19 ?birthPlace }}
  OPTIONAL {{ wd:{qid} wdt:P102 ?party }}
  OPTIONAL {{ wd:{qid} wdt:P27 ?country }}
  OPTIONAL {{ wd:{qid} wdt:P69 ?education }}
  OPTIONAL {{ wd:{qid} wdt:P39 ?position }}
  OPTIONAL {{ wd:{qid} wdt:P18 ?image }}
  OPTIONAL {{
    ?article schema:about wd:{qid} ;
             schema:inLanguage "pt" ;
             schema:isPartOf <https://pt.wikipedia.org/> .
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}}
LIMIT 1
"""
    details = {"votes": [], "expenses": [], "education": "", "occupation": "", "full_name": ""}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(WIKIDATA_URL, params={"query": sparql, "format": "json"},
                           headers={"Accept": "application/json", "User-Agent": "ForGloryApp/1.0"})
            if r.status_code == 200:
                b = r.json().get("results", {}).get("bindings", [])
                if b:
                    row = b[0]
                    details["birth_date"]  = row.get("birthDate", {}).get("value", "")[:10]
                    details["birth_place"] = row.get("birthPlaceLabel", {}).get("value", "")
                    details["education"]   = row.get("educationLabel", {}).get("value", "")
                    details["party"]       = row.get("partyLabel", {}).get("value", "")
                    details["country"]     = row.get("countryLabel", {}).get("value", "")
                    details["role"]        = row.get("positionLabel", {}).get("value", "")
                    details["photo"]       = row.get("image", {}).get("value", "")
                    wiki_article           = row.get("article", {}).get("value", "")
                    if wiki_article:
                        title = wiki_article.split("/wiki/")[-1]
                        wiki_data = await _get(f"https://pt.wikipedia.org/api/rest_v1/page/summary/{title}")
                        if wiki_data:
                            details["bio"] = wiki_data.get("extract", "")[:600]
    except Exception:
        pass
    return details


# ─────────────────────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/transparency/search")
async def search_politicians(
    q: str = Query(..., min_length=2),
    country: Optional[str] = Query("BR"),
):
    """Busca políticos por nome. Retorna lista de candidatos."""
    country = (country or "BR").upper()
    
    if country == "BR":
        dep_task = search_deputados(q)
        sen_task = search_senadores(q)
        dep_results, sen_results = await asyncio.gather(dep_task, sen_task)
        all_results = dep_results + sen_results
    else:
        all_results = await search_wikidata_politicians(q)
    
    return {"results": all_results[:12], "query": q, "country": country}


@router.get("/transparency/politician/{politician_id}")
async def get_politician(politician_id: str, db: Session = Depends(get_db)):
    """Retorna ficha completa de um político."""
    parts = politician_id.split("-", 1)
    source = parts[0]
    api_id = parts[1] if len(parts) > 1 else ""
    
    if source == "dep":
        details = await get_deputado_details(api_id)
    elif source == "sen":
        details = await get_senador_details(api_id)
    elif source == "wd":
        details = await get_wikidata_details(api_id)
    else:
        return {"error": "Fonte desconhecida"}
    
    # Adiciona ratings da comunidade
    ratings = db.query(PoliticianRating).filter_by(politician_id=politician_id).all()
    avg_score = (sum(r.score for r in ratings) / len(ratings)) if ratings else None
    details["community_rating"] = {
        "average": round(avg_score, 1) if avg_score else None,
        "count": len(ratings),
        "comments": [
            {"score": r.score, "comment": r.comment, "date": r.created_at.strftime("%d/%m/%Y") if r.created_at else ""}
            for r in ratings[-5:]
        ]
    }
    
    return details


@router.post("/transparency/rate")
async def rate_politician(
    data: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Salva avaliação de um usuário sobre um político."""
    politician_id = str(data.get("politician_id", "")).strip()
    user_id       = int(data.get("user_id", 0))
    score         = int(data.get("score", 3))
    comment       = str(data.get("comment", ""))[:300]
    
    if not politician_id or not user_id or not (1 <= score <= 5):
        return {"error": "Dados inválidos"}
    
    # Upsert: um voto por usuário por político
    existing = db.query(PoliticianRating).filter_by(politician_id=politician_id, user_id=user_id).first()
    if existing:
        existing.score   = score
        existing.comment = comment
    else:
        db.add(PoliticianRating(politician_id=politician_id, user_id=user_id, score=score, comment=comment))
    db.commit()
    return {"status": "ok"}


@router.get("/transparency/compare")
async def compare_politicians(ids: str = Query(...)):
    """Compara dois ou mais políticos. ids = 'dep-123,sen-456'"""
    id_list = [i.strip() for i in ids.split(",") if i.strip()][:4]
    
    tasks = []
    for pid in id_list:
        parts = pid.split("-", 1)
        source = parts[0]
        api_id = parts[1] if len(parts) > 1 else ""
        if source == "dep":
            tasks.append(get_deputado_details(api_id))
        elif source == "sen":
            tasks.append(get_senador_details(api_id))
        elif source == "wd":
            tasks.append(get_wikidata_details(api_id))
        else:
            tasks.append(asyncio.coroutine(lambda: {})())
    
    results = await asyncio.gather(*tasks)
    return {"politicians": [{"id": pid, **detail} for pid, detail in zip(id_list, results)]}


@router.get("/transparency/featured")
async def featured_politicians():
    """Lista políticos em destaque (cargos mais altos do Brasil)."""
    # Presidência + líderes do Congresso como ponto de entrada
    featured = [
        {"id": "wd-Q28227", "name": "Lula", "role": "Presidente do Brasil", "country": "Brasil",
         "party": "PT", "state": "Nacional", "source": "wikidata",
         "photo": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Lula_-_foto_oficial_2023.jpg"},
        {"id": "wd-Q76", "name": "Barack Obama", "role": "Ex-Presidente EUA", "country": "EUA",
         "party": "Democrata", "state": "Nacional", "source": "wikidata",
         "photo": "https://upload.wikimedia.org/wikipedia/commons/e/e9/Official_portrait_of_Barack_Obama.jpg"},
        {"id": "wd-Q47468", "name": "Emmanuel Macron", "role": "Presidente França", "country": "França",
         "party": "Renaissance", "state": "Nacional", "source": "wikidata",
         "photo": "https://upload.wikimedia.org/wikipedia/commons/f/f4/Emmanuel_Macron_in_2019.jpg"},
    ]
    return {"featured": featured}
