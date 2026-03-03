"""
For Glory — Portal da Transparência v3
Fontes: Câmara, Senado, Wikidata Entity API, Wikipedia REST
"""
import asyncio, hashlib
import httpx
from fastapi import APIRouter, Query, Depends, Body
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from typing import Optional
from app.db.session import get_db
from app.db.base import Base

router = APIRouter()

CAMARA_BASE = "https://dadosabertos.camara.leg.br/api/v2"
SENADO_BASE = "https://legis.senado.leg.br/dadosabertos"
WD_ENTITY   = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
WD_API      = "https://www.wikidata.org/w/api.php"
WIKI_PT_SUM = "https://pt.wikipedia.org/api/rest_v1/page/summary/{}"
WIKI_EN_SUM = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WIKI_PT_API = "https://pt.wikipedia.org/w/api.php"
_HDR = {"User-Agent": "ForGloryApp/1.0 (transparency@forglory.online)"}

# Ocupações Wikidata que indicam político de fato
POLITICAL_OCCUPATIONS = {
    "Q82955",   # politician
    "Q372436",  # statesperson
    "Q1028181", # member of parliament
    "Q4964182", # politician (broader)
    "Q30461",   # president
    "Q16707842",# head of government
    "Q16707845",# head of state
    "Q17540564",# government minister
    "Q189290",  # military officer (inclui presidentes militares)
    "Q2285706", # senator
    "Q1055894", # city council member
    "Q15978655",# member of the National Congress of Brazil
}

# Salários e benefícios fixos (2024) — fonte: Portal da Transparência / Câmara / Senado
SALARY_BR = {
    "camara": {
        "cargo": "Deputado Federal",
        "subsidio_mensal": 46366.19,
        "subsidio_desc": "Subsídio parlamentar mensal (bruto)",
        "beneficios": [
            {"nome": "Cota Parlamentar (CEAP)", "valor": "até R$ 50.112/mês", "descricao": "Verba para custeio de atividades parlamentares (gasolina, passagens, alimentação etc.)"},
            {"nome": "Auxílio-Moradia", "valor": "R$ 4.253,00/mês", "descricao": "Para deputados sem imóvel em Brasília"},
            {"nome": "Passagens Aéreas", "valor": "Até 84 bilhetes/mês", "descricao": "Viagens entre o domicílio e Brasília"},
            {"nome": "Plano de Saúde (PAMS)", "valor": "Custeado pela Câmara", "descricao": "Para o parlamentar e dependentes"},
            {"nome": "Seguro de Vida", "valor": "Custeado pela Câmara", "descricao": "Apólice individual"},
        ],
        "beneficios_abdicados_info": "Parlamentares podem abrir mão do auxílio-moradia declarando imóvel funcional em Brasília ou imóvel próprio. A Cota Parlamentar pode ser reduzida voluntariamente.",
        "fonte": "https://www2.camara.leg.br/transparencia",
    },
    "senado": {
        "cargo": "Senador Federal",
        "subsidio_mensal": 46366.19,
        "subsidio_desc": "Subsídio parlamentar mensal (bruto) — igual ao dos Deputados por determinação constitucional",
        "beneficios": [
            {"nome": "Verba de Gabinete", "valor": "até R$ 155.520/mês", "descricao": "Para custeio de pessoal e atividades do gabinete"},
            {"nome": "Auxílio-Moradia", "valor": "R$ 4.253,00/mês", "descricao": "Para senadores sem imóvel em Brasília"},
            {"nome": "Passagens Aéreas", "valor": "Sem limite fixo", "descricao": "Viagens a serviço do mandato"},
            {"nome": "Plano de Saúde (PAMS)", "valor": "Custeado pelo Senado", "descricao": "Para o parlamentar e dependentes"},
            {"nome": "Verba de Representação", "valor": "R$ 9.273,24/mês", "descricao": "Para Mesa Diretora e líderes de bloco"},
        ],
        "beneficios_abdicados_info": "Senadores podem abrir mão do auxílio-moradia. A verba de representação é exclusiva de cargos de liderança.",
        "fonte": "https://www12.senado.leg.br/transparencia",
    }
}

# ── DB ────────────────────────────────────────────────────────
class PoliticianRating(Base):
    __tablename__ = "politician_ratings"
    id            = Column(Integer, primary_key=True, index=True)
    politician_id = Column(String(100), index=True)
    user_id       = Column(Integer, index=True)
    score         = Column(Integer)
    comment       = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# ── HTTP ──────────────────────────────────────────────────────
async def _get(url, params=None, timeout=10):
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
            r = await c.get(url, params=params, headers=_HDR)
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None

# ── WIKIDATA HELPERS ──────────────────────────────────────────
def _wd_value(claims, prop):
    try:
        snak = claims.get(prop, [{}])[0].get("mainsnak", {})
        dv = snak.get("datavalue", {}); t = dv.get("type",""); v = dv.get("value",{})
        if t == "string": return str(v)
        if t == "time": return str(v.get("time",""))[1:11]
        if t == "wikibase-entityid": return str(v.get("id",""))
        if t == "monolingualtext": return str(v.get("text",""))
        return str(v) if v else ""
    except: return ""

def _wd_values_all(claims, prop):
    """Retorna todos os valores (não só o primeiro) de uma propriedade."""
    out = []
    try:
        for stmt in claims.get(prop, []):
            snak = stmt.get("mainsnak", {}); dv = snak.get("datavalue",{})
            t = dv.get("type",""); v = dv.get("value",{})
            if t == "wikibase-entityid": out.append(v.get("id",""))
            elif t == "string": out.append(str(v))
            elif t == "time": out.append(str(v.get("time",""))[1:11])
    except: pass
    return [x for x in out if x]

def _wd_image(f):
    if not f: return ""
    if f.startswith("http"): return f
    n = f.replace(" ","_"); h = hashlib.md5(n.encode()).hexdigest()
    return f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[0:2]}/{n}"

async def _resolve_labels(qids):
    if not qids: return {}
    data = await _get(WD_API, {"action":"wbgetentities","ids":"|".join(list(set(qids))[:30]),
                                "props":"labels","languages":"pt|en","format":"json"})
    if not data: return {}
    out = {}
    for qid, ent in data.get("entities",{}).items():
        lab = ent.get("labels",{})
        out[qid] = (lab.get("pt") or lab.get("en") or {}).get("value","")
    return out

async def _wiki_summary_by_title(title_pt, title_en=None):
    """Busca resumo exato pelo título do Wikipedia — sem adivinhação."""
    for tpl, title in [(WIKI_PT_SUM, title_pt),(WIKI_EN_SUM, title_en)]:
        if not title: continue
        d = await _get(tpl.format(title.replace(" ","_")))
        if d and d.get("type") == "standard":
            return {
                "bio":   d.get("extract","")[:900],
                "photo": (d.get("originalimage") or d.get("thumbnail") or {}).get("source",""),
                "link":  d.get("content_urls",{}).get("desktop",{}).get("page",""),
            }
    return {}

def _is_politician_entity(claims):
    """Verifica se a entidade Wikidata é realmente um político."""
    occupations = _wd_values_all(claims, "P106")  # occupation
    positions   = _wd_values_all(claims, "P39")    # position held
    if not occupations and not positions: return False
    return bool(
        POLITICAL_OCCUPATIONS & set(occupations) or positions
    )

# ── WIKIDATA ENTITY COMPLETO ──────────────────────────────────
async def get_wikidata_entity(qid):
    data = await _get(WD_ENTITY.format(qid))
    if not data: return {}
    ent = data.get("entities",{}).get(qid,{}); 
    if not ent: return {}

    claims = ent.get("claims",{}); labels = ent.get("labels",{})
    descs  = ent.get("descriptions",{}); sitelinks = ent.get("sitelinks",{})

    name = (labels.get("pt") or labels.get("en") or {}).get("value","")
    desc = (descs.get("pt") or descs.get("en") or {}).get("value","")

    party_qs   = _wd_values_all(claims,"P102")
    country_q  = _wd_value(claims,"P27")
    edu_qs     = _wd_values_all(claims,"P69")
    pos_qs     = _wd_values_all(claims,"P39")
    occ_qs     = _wd_values_all(claims,"P106")
    bplace_q   = _wd_value(claims,"P19")
    birth_date = _wd_value(claims,"P569")
    death_date = _wd_value(claims,"P570")
    image_file = _wd_value(claims,"P18")
    website    = _wd_value(claims,"P856")

    # Casos na justiça — Wikidata P619 (convicted of), P1344 (participant of events), P6375 (address)
    # Usamos P619 (criminal charge/conviction)
    charges_q = _wd_values_all(claims, "P619")  # criminal charge
    # também P2597 — "defendant" não existe, mas P1344 (significant event participant) pode capturar
    # Melhor: extraímos da bio Wikipedia os casos

    all_qids = list(set(party_qs + [country_q, bplace_q] + edu_qs + pos_qs + occ_qs + charges_q))
    lmap = await _resolve_labels([q for q in all_qids if q])

    title_pt = sitelinks.get("ptwiki",{}).get("title","")
    title_en = sitelinks.get("enwiki",{}).get("title","")
    wiki     = await _wiki_summary_by_title(title_pt, title_en)

    photo = _wd_image(image_file) if image_file else wiki.get("photo","")

    parties = [lmap.get(q,"") for q in party_qs if lmap.get(q)]
    roles   = [lmap.get(q,"") for q in pos_qs   if lmap.get(q)]
    occs    = [lmap.get(q,"") for q in occ_qs   if lmap.get(q)]
    edus    = [lmap.get(q,"") for q in edu_qs   if lmap.get(q)]
    charges = [lmap.get(q,"") for q in charges_q if lmap.get(q)]

    return {
        "full_name":   name,
        "description": desc,
        "bio":         wiki.get("bio",""),
        "wiki_link":   wiki.get("link",""),
        "birth_date":  birth_date,
        "death_date":  death_date,
        "birth_place": lmap.get(bplace_q,""),
        "party":       parties[0] if parties else "",
        "all_parties": parties,
        "country":     lmap.get(country_q,""),
        "education":   edus[0] if edus else "",
        "all_education": edus,
        "role":        roles[0] if roles else "",
        "all_roles":   roles,
        "occupation":  occs[0] if occs else "",
        "photo":       photo,
        "website":     website,
        "charges":     charges,   # crimes/acusações no Wikidata
        "votes":       [],
        "expenses":    [],
        "salary_info": None,
    }

# ── BUSCA WIKIDATA — apenas políticos reais ───────────────────
async def search_wikidata_politicians(query):
    """
    Busca via SPARQL para garantir que só retorne políticos.
    Filtra por P106 (occupation) = político ou por P39 (posição) existente.
    """
    sparql = f"""
SELECT DISTINCT ?person ?personLabel ?partyLabel ?countryLabel ?posLabel ?image WHERE {{
  ?person wdt:P31 wd:Q5 .
  {{?person wdt:P106 ?occ . VALUES ?occ {{ wd:Q82955 wd:Q372436 wd:Q1028181 wd:Q30461 wd:Q16707842 wd:Q16707845 wd:Q17540564 wd:Q2285706 }} }}
  UNION {{ ?person wdt:P39 ?pos . }}
  ?person rdfs:label ?label .
  FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{query}")))
  FILTER(LANG(?label) IN ("pt","en","es"))
  OPTIONAL {{ ?person wdt:P18 ?image }}
  OPTIONAL {{ ?person wdt:P102 ?party }}
  OPTIONAL {{ ?person wdt:P27 ?country }}
  OPTIONAL {{ ?person wdt:P39 ?pos }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}}
LIMIT 10
"""
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as c:
            r = await c.get("https://query.wikidata.org/sparql",
                            params={"query": sparql, "format": "json"},
                            headers={**_HDR, "Accept": "application/sparql-results+json"})
            if r.status_code != 200: raise Exception()
            bindings = r.json().get("results",{}).get("bindings",[])
    except Exception:
        return []

    seen = set(); results = []
    for b in bindings:
        qid = b.get("person",{}).get("value","").split("/")[-1]
        if qid in seen: continue
        seen.add(qid)
        name = b.get("personLabel",{}).get("value","")
        if not name or name.startswith("Q"): continue
        image = b.get("image",{}).get("value","")
        results.append({
            "id":      f"wd-{qid}", "api_id": qid, "name": name,
            "party":   b.get("partyLabel",{}).get("value",""),
            "state":   "",
            "role":    b.get("posLabel",{}).get("value",""),
            "country": b.get("countryLabel",{}).get("value",""),
            "photo":   _wd_image(image) if image and not image.startswith("http") else image,
            "email":   "", "source": "wikidata",
        })
    return results[:8]

# ── CÂMARA ────────────────────────────────────────────────────
async def search_deputados(query, uf=None):
    params = {"nome":query,"itens":8,"ordem":"ASC","ordenarPor":"nome"}
    if uf: params["siglaUf"] = uf.upper()
    data = await _get(f"{CAMARA_BASE}/deputados", params)
    if not data or "dados" not in data: return []
    return [{"id":f"dep-{d.get('id','')}","api_id":d.get("id"),"name":d.get("nome",""),
             "party":d.get("siglaPartido",""),"state":d.get("siglaUf",""),
             "role":"Deputado Federal","country":"Brasil",
             "photo":d.get("urlFoto",""),"email":d.get("email",""),"source":"camara"}
            for d in data["dados"]]

async def get_deputado_details(api_id):
    base = f"{CAMARA_BASE}/deputados/{api_id}"
    data, desp, vot = await asyncio.gather(
        _get(base),
        _get(f"{base}/despesas",{"itens":10,"ordenarPor":"ano","ordem":"DESC"}),
        _get(f"{base}/votacoes",{"itens":10,"ordenarPor":"dataHoraVoto","ordem":"DESC"}))

    details = {"salary_info": SALARY_BR["camara"], "expenses":[], "votes":[], "charges":[], "all_roles":[], "all_education":[]}

    if data and "dados" in data:
        d = data["dados"]; ult = d.get("ultimoStatus",{})
        nome_civil = d.get("nomeCivil","")
        details.update({
            "full_name":  nome_civil,
            "birth_date": d.get("dataNascimento",""),
            "education":  d.get("escolaridade",""),
            "occupation": (d.get("profissoes") or [{}])[0].get("titulo",""),
            "party":      ult.get("siglaPartido",""),
            "state":      ult.get("siglaUf",""),
            "photo":      ult.get("urlFoto","") or d.get("urlFoto",""),
            "email":      ult.get("email","") or d.get("email",""),
            "website":    ult.get("urlRedeSocial",""),
            "role":       "Deputado Federal",
        })
        # Bio via Wikipedia — busca exata pelo nome civil
        if nome_civil:
            wiki = await _wiki_summary_by_title(nome_civil)
            if not wiki.get("bio"):
                # tenta com nome parlamentar
                wiki = await _wiki_summary_by_title(ult.get("nome",""))
            if wiki.get("bio"):
                details["bio"] = wiki["bio"]
                details["wiki_link"] = wiki.get("link","")
                if not details.get("photo"): details["photo"] = wiki.get("photo","")

    if desp and "dados" in desp:
        details["expenses"] = [{"description":e.get("tipoDespesa",""),
            "value":e.get("valorLiquido",0),
            "date":f"{e.get('mes','')}/{e.get('ano','')}",
            "provider":e.get("nomeFornecedor","")} for e in desp["dados"][:10]]

    if vot and "dados" in vot:
        details["votes"] = [{"description":v.get("descricao","") or v.get("proposicao_",{}).get("ementa",""),
            "date":(v.get("dataHoraVoto") or "")[:10],
            "vote": v.get("voto","") or ""} for v in vot["dados"][:10]]

    return details

# ── SENADO ────────────────────────────────────────────────────
async def search_senadores(query):
    data = await _get(f"{SENADO_BASE}/senador/lista/atual.json")
    if not data: return []
    try: senadores = data["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    except: return []
    q = query.lower(); results = []
    for s in senadores:
        try:
            id_s = s["IdentificacaoParlamentar"]
            nome = id_s.get("NomeParlamentar","") or id_s.get("NomeCompletoParlamentar","")
            if q not in nome.lower(): continue
            results.append({"id":f"sen-{id_s.get('CodigoParlamentar','')}",
                "api_id":id_s.get("CodigoParlamentar"),"name":nome,
                "party":id_s.get("SiglaPartidoParlamentar",""),"state":id_s.get("UfParlamentar",""),
                "role":"Senador Federal","country":"Brasil",
                "photo":id_s.get("UrlFotoParlamentar",""),
                "email":id_s.get("EmailParlamentar",""),"source":"senado"})
            if len(results) >= 5: break
        except: continue
    return results

async def get_senador_details(api_id):
    data, vd = await asyncio.gather(
        _get(f"{SENADO_BASE}/senador/{api_id}.json"),
        _get(f"{SENADO_BASE}/senador/{api_id}/votacoes.json",{"v":6}))

    details = {"salary_info": SALARY_BR["senado"], "votes":[], "expenses":[], "charges":[], "all_roles":["Senador Federal"], "all_education":[]}

    if data:
        try:
            p    = data["DetalheParlamentar"]["Parlamentar"]
            ident= p.get("IdentificacaoParlamentar",{})
            dados= p.get("DadosBasicosParlamentar",{})
            nome_completo = ident.get("NomeCompletoParlamentar","")
            details.update({
                "full_name":  nome_completo,
                "birth_date": dados.get("DataNascimento",""),
                "education":  dados.get("FormacaoAcademica",""),
                "occupation": dados.get("Profissao",""),
                "website":    ident.get("UrlPaginaParlamentar",""),
                "email":      ident.get("EmailParlamentar",""),
                "role":       "Senador Federal",
            })
            # Bio Wikipedia
            if nome_completo:
                wiki = await _wiki_summary_by_title(nome_completo)
                if not wiki.get("bio"):
                    wiki = await _wiki_summary_by_title(ident.get("NomeParlamentar",""))
                if wiki.get("bio"):
                    details["bio"] = wiki["bio"]
                    details["wiki_link"] = wiki.get("link","")
                    if not details.get("photo"): details["photo"] = wiki.get("photo","")
        except: pass

    if vd:
        try:
            vlist = vd["VotacoesParlamentar"]["Parlamentar"]["Votacoes"]["Votacao"]
            if isinstance(vlist,dict): vlist=[vlist]
            details["votes"] = [{"description":v.get("DescricaoVotacao",""),
                "date":v.get("DataSessao",""),"vote":v.get("Voto","")} for v in (vlist or [])[:10]]
        except: pass

    return details

# ── ENDPOINTS ─────────────────────────────────────────────────
@router.get("/transparency/search")
async def search_politicians(q:str=Query(...,min_length=2), country:Optional[str]=Query("BR")):
    country = (country or "BR").upper()
    if country == "BR":
        dep_r, sen_r, wd_r = await asyncio.gather(
            search_deputados(q), search_senadores(q), search_wikidata_politicians(q))
        br_names = {r["name"].lower() for r in dep_r+sen_r}
        extra_wd = [r for r in wd_r if r["name"].lower() not in br_names]
        return {"results": dep_r + sen_r + extra_wd, "query":q, "country":country}
    return {"results": await search_wikidata_politicians(q), "query":q, "country":country}

@router.get("/transparency/politician/{politician_id}")
async def get_politician(politician_id:str, db:Session=Depends(get_db)):
    parts = politician_id.split("-",1); source = parts[0]; api_id = parts[1] if len(parts)>1 else ""
    if source=="dep":   details = await get_deputado_details(api_id)
    elif source=="sen": details = await get_senador_details(api_id)
    elif source=="wd":  details = await get_wikidata_entity(api_id)
    else: return {"error":"Fonte desconhecida"}

    ratings = db.query(PoliticianRating).filter_by(politician_id=politician_id).all()
    avg = (sum(r.score for r in ratings)/len(ratings)) if ratings else None
    details["community_rating"] = {
        "average": round(avg,1) if avg else None,
        "count":   len(ratings),
        "comments":[{"score":r.score,"comment":r.comment or "",
            "date":r.created_at.strftime("%d/%m/%Y") if r.created_at else "",
            "user_id":r.user_id} for r in sorted(ratings, key=lambda x: x.created_at or datetime.min, reverse=True)[:10]]}
    return details

@router.post("/transparency/rate")
async def rate_politician(data:dict=Body(...), db:Session=Depends(get_db)):
    pid=str(data.get("politician_id","")).strip(); uid=int(data.get("user_id",0))
    score=int(data.get("score",3)); comment=str(data.get("comment",""))[:400]
    if not pid or not uid or not(1<=score<=5): return {"error":"Dados inválidos"}
    ex = db.query(PoliticianRating).filter_by(politician_id=pid,user_id=uid).first()
    if ex: ex.score=score; ex.comment=comment; ex.created_at=datetime.now(timezone.utc)
    else:   db.add(PoliticianRating(politician_id=pid,user_id=uid,score=score,comment=comment))
    db.commit()
    # retorna nova média
    ratings = db.query(PoliticianRating).filter_by(politician_id=pid).all()
    avg = round(sum(r.score for r in ratings)/len(ratings),1)
    return {"status":"ok","new_average":avg,"count":len(ratings)}

@router.get("/transparency/compare")
async def compare_politicians(ids:str=Query(...)):
    id_list = [i.strip() for i in ids.split(",") if i.strip()][:4]
    async def _fetch(pid):
        parts=pid.split("-",1); src=parts[0]; aid=parts[1] if len(parts)>1 else ""
        if src=="dep": return await get_deputado_details(aid)
        if src=="sen": return await get_senador_details(aid)
        if src=="wd":  return await get_wikidata_entity(aid)
        return {}
    results = await asyncio.gather(*[_fetch(pid) for pid in id_list])
    return {"politicians":[{"id":pid,**d} for pid,d in zip(id_list,results)]}

@router.get("/transparency/featured")
async def featured_politicians():
    return {"featured":[
        {"id":"wd-Q28227","name":"Lula","role":"Presidente do Brasil","country":"Brasil","party":"PT","source":"wikidata",
         "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Lula_-_foto_oficial_2023.jpg/800px-Lula_-_foto_oficial_2023.jpg"},
        {"id":"wd-Q41551","name":"Geraldo Alckmin","role":"Vice-Presidente","country":"Brasil","party":"PSB","source":"wikidata","photo":""},
        {"id":"wd-Q22686","name":"Donald Trump","role":"Presidente dos EUA","country":"EUA","party":"Republicano","source":"wikidata",
         "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Donald_Trump_official_portrait.jpg/800px-Donald_Trump_official_portrait.jpg"},
        {"id":"wd-Q47468","name":"Emmanuel Macron","role":"Presidente da França","country":"França","party":"Renaissance","source":"wikidata",
         "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Emmanuel_Macron_in_2019.jpg/800px-Emmanuel_Macron_in_2019.jpg"},
        {"id":"wd-Q183522","name":"Xi Jinping","role":"Presidente da China","country":"China","party":"PCCh","source":"wikidata","photo":""},
        {"id":"wd-Q167756","name":"Vladimir Putin","role":"Presidente da Rússia","country":"Rússia","party":"Rússia Unida","source":"wikidata","photo":""},
    ]}
