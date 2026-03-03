"""
For Glory — Portal da Transparência
-------------------------------------
BRASIL:
  - API Câmara dos Deputados: https://dadosabertos.camara.leg.br/api/v2
  - API Senado Federal:       https://legis.senado.leg.br/dadosabertos
INTERNACIONAL:
  - Wikidata Entity API + MediaWiki Action API + Wikipedia REST API
"""

import os, asyncio, hashlib
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
WIKI_SEARCH = "https://pt.wikipedia.org/w/api.php"
WIKI_PT     = "https://pt.wikipedia.org/api/rest_v1/page/summary/{}"
WIKI_EN     = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
_HDR        = {"User-Agent": "ForGloryApp/1.0"}

# ── DB ──────────────────────────────────────────────────────
class PoliticianRating(Base):
    __tablename__ = "politician_ratings"
    id            = Column(Integer, primary_key=True, index=True)
    politician_id = Column(String(100), index=True)
    user_id       = Column(Integer, index=True)
    score         = Column(Integer)
    comment       = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# ── HELPERS ─────────────────────────────────────────────────
async def _get(url, params=None, timeout=10):
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
            r = await c.get(url, params=params, headers=_HDR)
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None

def _wd_value(claims, prop):
    try:
        snak = claims.get(prop, [{}])[0].get("mainsnak", {})
        dv = snak.get("datavalue", {})
        t = dv.get("type", ""); v = dv.get("value", {})
        if t == "string": return str(v)
        if t == "time": return str(v.get("time",""))[1:11]
        if t == "wikibase-entityid": return str(v.get("id",""))
        if t == "monolingualtext": return str(v.get("text",""))
        return str(v) if v else ""
    except: return ""

def _wd_image(filename):
    if not filename: return ""
    if filename.startswith("http"): return filename
    name = filename.replace(" ","_")
    h = hashlib.md5(name.encode()).hexdigest()
    return f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[0:2]}/{name}"

async def _resolve_labels(qids):
    if not qids: return {}
    data = await _get("https://www.wikidata.org/w/api.php", {
        "action":"wbgetentities","ids":"|".join(qids[:30]),
        "props":"labels","languages":"pt|en","format":"json"})
    if not data: return {}
    out = {}
    for qid, ent in data.get("entities",{}).items():
        lab = ent.get("labels",{})
        out[qid] = (lab.get("pt") or lab.get("en") or {}).get("value","")
    return out

async def _wiki_bio(title_pt=None, title_en=None):
    """Busca bio + thumbnail no Wikipedia, tenta PT depois EN."""
    for url_tpl, title in [(WIKI_PT, title_pt),(WIKI_EN, title_en)]:
        if not title: continue
        d = await _get(url_tpl.format(title.replace(" ","_")))
        if d and d.get("type") == "standard":
            return {
                "bio":   d.get("extract","")[:800],
                "photo": (d.get("thumbnail") or {}).get("source",""),
                "link":  d.get("content_urls",{}).get("desktop",{}).get("page",""),
            }
    return {}

# ── WIKIDATA ENTITY (núcleo de tudo) ────────────────────────
async def get_wikidata_entity(qid):
    data = await _get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    if not data: return {}
    ent   = data.get("entities",{}).get(qid,{})
    if not ent: return {}

    claims    = ent.get("claims",{})
    labels    = ent.get("labels",{})
    descs     = ent.get("descriptions",{})
    sitelinks = ent.get("sitelinks",{})

    name = (labels.get("pt") or labels.get("en") or {}).get("value","")
    desc = (descs.get("pt") or descs.get("en") or {}).get("value","")

    party_q    = _wd_value(claims,"P102")
    country_q  = _wd_value(claims,"P27")
    edu_q      = _wd_value(claims,"P69")
    pos_q      = _wd_value(claims,"P39")
    occ_q      = _wd_value(claims,"P106")
    bplace_q   = _wd_value(claims,"P19")
    birth_date = _wd_value(claims,"P569")
    image_file = _wd_value(claims,"P18")
    website    = _wd_value(claims,"P856")

    lmap = await _resolve_labels([q for q in [party_q,country_q,edu_q,pos_q,occ_q,bplace_q] if q])

    title_pt = sitelinks.get("ptwiki",{}).get("title","")
    title_en = sitelinks.get("enwiki",{}).get("title","")
    wiki     = await _wiki_bio(title_pt, title_en)

    photo = _wd_image(image_file) if image_file else wiki.get("photo","")

    return {
        "full_name":   name,
        "description": desc,
        "bio":         wiki.get("bio",""),
        "wiki_link":   wiki.get("link",""),
        "birth_date":  birth_date,
        "birth_place": lmap.get(bplace_q,""),
        "party":       lmap.get(party_q,""),
        "country":     lmap.get(country_q,""),
        "education":   lmap.get(edu_q,""),
        "role":        lmap.get(pos_q,""),
        "occupation":  lmap.get(occ_q,""),
        "photo":       photo,
        "website":     website,
        "votes":       [],
        "expenses":    [],
    }

# ── BUSCA WIKIDATA (via Wikipedia Search + QID lookup) ──────
async def search_wikidata_politicians(query):
    data = await _get(WIKI_SEARCH, {
        "action":"query","list":"search","srsearch": query,
        "srnamespace":"0","srlimit":"8","format":"json","srsort":"relevance"})
    if not data: return []

    results = []
    for item in data.get("query",{}).get("search",[]):
        title = item.get("title","")
        # Pega QID via pageprops
        qdata = await _get(WIKI_SEARCH, {
            "action":"query","titles":title,"prop":"pageprops",
            "ppprop":"wikibase_item","format":"json"})
        qid = ""
        if qdata:
            for _, pg in qdata.get("query",{}).get("pages",{}).items():
                qid = pg.get("pageprops",{}).get("wikibase_item",""); break
        if not qid: continue
        results.append({
            "id":"wd-"+qid,"api_id":qid,"name":title,
            "party":"","state":"","role":"","country":"","photo":"","email":"","source":"wikidata"})

    # Enriquece primeiros 4 com dados básicos
    for i,r in enumerate(results[:4]):
        ent = await get_wikidata_entity(r["api_id"])
        if ent:
            results[i].update({
                "photo":   ent.get("photo",""),
                "party":   ent.get("party",""),
                "country": ent.get("country",""),
                "role":    ent.get("role","") or ent.get("description","")[:80],
            })
    return results[:8]

# ── CÂMARA ───────────────────────────────────────────────────
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
        _get(f"{base}/despesas",{"itens":5,"ordenarPor":"ano","ordem":"DESC"}),
        _get(f"{base}/votacoes",{"itens":8,"ordenarPor":"dataHoraVoto","ordem":"DESC"}))
    details = {}
    if data and "dados" in data:
        d = data["dados"]; ult = d.get("ultimoStatus",{})
        details.update({
            "full_name": d.get("nomeCivil",""),
            "birth_date":d.get("dataNascimento",""),
            "education": d.get("escolaridade",""),
            "occupation":(d.get("profissoes") or [{}])[0].get("titulo",""),
            "party":ult.get("siglaPartido",""),"state":ult.get("siglaUf",""),
        })
        # Bio via Wikipedia
        nome = d.get("nomeCivil","") or ult.get("nome","")
        if nome:
            sr = await _get(WIKI_SEARCH,{"action":"query","list":"search",
                "srsearch":nome+" político","srlimit":"1","format":"json"})
            if sr:
                hits = sr.get("query",{}).get("search",[])
                if hits:
                    w = await _wiki_bio(hits[0].get("title",""))
                    if w.get("bio"):
                        details["bio"]   = w["bio"]
                        if not details.get("photo"): details["photo"] = w.get("photo","")

    details["expenses"] = []
    if desp and "dados" in desp:
        details["expenses"] = [{"description":e.get("tipoDespesa",""),
            "value":e.get("valorLiquido",0),
            "date":f"{e.get('mes','')}/{e.get('ano','')}",
            "provider":e.get("nomeFornecedor","")} for e in desp["dados"][:5]]

    details["votes"] = []
    if vot and "dados" in vot:
        details["votes"] = [{"description":v.get("descricao",""),
            "date":(v.get("dataHoraVoto") or "")[:10]} for v in vot["dados"][:5]]
    return details

# ── SENADO ───────────────────────────────────────────────────
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
                "role":"Senador","country":"Brasil","photo":id_s.get("UrlFotoParlamentar",""),
                "email":id_s.get("EmailParlamentar",""),"source":"senado"})
            if len(results) >= 5: break
        except: continue
    return results

async def get_senador_details(api_id):
    data = await _get(f"{SENADO_BASE}/senador/{api_id}.json")
    details = {"votes":[],"expenses":[]}
    if data:
        try:
            p = data["DetalheParlamentar"]["Parlamentar"]
            ident = p.get("IdentificacaoParlamentar",{}); dados = p.get("DadosBasicosParlamentar",{})
            details.update({"full_name":ident.get("NomeCompletoParlamentar",""),
                "birth_date":dados.get("DataNascimento",""),"education":dados.get("FormacaoAcademica",""),
                "occupation":dados.get("Profissao",""),"website":ident.get("UrlPaginaParlamentar","")})
        except: pass
    vd = await _get(f"{SENADO_BASE}/senador/{api_id}/votacoes.json",{"v":6})
    if vd:
        try:
            vlist = vd["VotacoesParlamentar"]["Parlamentar"]["Votacoes"]["Votacao"]
            if isinstance(vlist,dict): vlist=[vlist]
            details["votes"] = [{"description":v.get("DescricaoVotacao",""),
                "date":v.get("DataSessao",""),"vote":v.get("Voto","")} for v in (vlist or [])[:5]]
        except: pass
    return details

# ── ENDPOINTS ────────────────────────────────────────────────
@router.get("/transparency/search")
async def search_politicians(q:str=Query(...,min_length=2), country:Optional[str]=Query("BR")):
    country = (country or "BR").upper()
    if country == "BR":
        dep_r, sen_r, wd_r = await asyncio.gather(
            search_deputados(q), search_senadores(q), search_wikidata_politicians(q))
        br_names = {r["name"].lower() for r in dep_r+sen_r}
        return {"results": dep_r + sen_r + [r for r in wd_r if r["name"].lower() not in br_names], "query":q, "country":country}
    else:
        return {"results": await search_wikidata_politicians(q), "query":q, "country":country}

@router.get("/transparency/politician/{politician_id}")
async def get_politician(politician_id:str, db:Session=Depends(get_db)):
    parts  = politician_id.split("-",1)
    source = parts[0]; api_id = parts[1] if len(parts)>1 else ""
    if source=="dep":   details = await get_deputado_details(api_id)
    elif source=="sen": details = await get_senador_details(api_id)
    elif source=="wd":  details = await get_wikidata_entity(api_id)
    else: return {"error":"Fonte desconhecida"}

    ratings = db.query(PoliticianRating).filter_by(politician_id=politician_id).all()
    avg = (sum(r.score for r in ratings)/len(ratings)) if ratings else None
    details["community_rating"] = {
        "average": round(avg,1) if avg else None, "count": len(ratings),
        "comments":[{"score":r.score,"comment":r.comment,
            "date":r.created_at.strftime("%d/%m/%Y") if r.created_at else ""} for r in ratings[-5:]]}
    return details

@router.post("/transparency/rate")
async def rate_politician(data:dict=Body(...), db:Session=Depends(get_db)):
    pid=str(data.get("politician_id","")).strip(); uid=int(data.get("user_id",0))
    score=int(data.get("score",3)); comment=str(data.get("comment",""))[:300]
    if not pid or not uid or not(1<=score<=5): return {"error":"Dados inválidos"}
    ex = db.query(PoliticianRating).filter_by(politician_id=pid,user_id=uid).first()
    if ex: ex.score=score; ex.comment=comment
    else: db.add(PoliticianRating(politician_id=pid,user_id=uid,score=score,comment=comment))
    db.commit(); return {"status":"ok"}

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
    featured = [
        {"id":"wd-Q28227","name":"Lula","role":"Presidente do Brasil","country":"Brasil","party":"PT","source":"wikidata",
         "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Lula_-_foto_oficial_2023.jpg/800px-Lula_-_foto_oficial_2023.jpg"},
        {"id":"wd-Q41551","name":"Geraldo Alckmin","role":"Vice-Presidente do Brasil","country":"Brasil","party":"PSB","source":"wikidata","photo":""},
        {"id":"wd-Q22686","name":"Donald Trump","role":"Presidente dos EUA","country":"EUA","party":"Republicano","source":"wikidata",
         "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Donald_Trump_official_portrait.jpg/800px-Donald_Trump_official_portrait.jpg"},
        {"id":"wd-Q47468","name":"Emmanuel Macron","role":"Presidente da França","country":"França","party":"Renaissance","source":"wikidata",
         "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Emmanuel_Macron_in_2019.jpg/800px-Emmanuel_Macron_in_2019.jpg"},
        {"id":"wd-Q183522","name":"Xi Jinping","role":"Presidente da China","country":"China","party":"PCCh","source":"wikidata","photo":""},
        {"id":"wd-Q167756","name":"Vladimir Putin","role":"Presidente da Rússia","country":"Rússia","party":"Rússia Unida","source":"wikidata","photo":""},
    ]
    return {"featured":featured}


# ── IP GEOLOCATION (reused from news.py) ─────────────────────
_geo_cache_trans: dict = {}
IPAPI_URL_T = "http://ip-api.com/json/{ip}?fields=status,city,regionName,regionCode,countryCode,country"

async def _resolve_geo_trans(ip: str) -> dict:
    if ip in _geo_cache_trans: return _geo_cache_trans[ip]
    if ip in ("127.0.0.1","::1") or ip.startswith("192.168.") or ip.startswith("10."):
        r = {"city":"Rio de Janeiro","regionName":"Rio de Janeiro","regionCode":"RJ","country":"Brasil","countryCode":"BR"}
        _geo_cache_trans[ip] = r; return r
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(IPAPI_URL_T.format(ip=ip), headers=_HDR)
            data = r.json()
            if data.get("status") == "success":
                _geo_cache_trans[ip] = data; return data
    except: pass
    return {"city":"Brasil","regionName":"","regionCode":"","country":"Brasil","countryCode":"BR"}

# STF — ministros atuais (lista oficial 2024-2025)
STF_MINISTERS = [
    {"id":"wd-Q10319857","name":"Luís Roberto Barroso","role":"Presidente do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Ministro_Luís_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg/800px-Ministro_Luís_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg"},
    {"id":"wd-Q2948413","name":"Cármen Lúcia","role":"Ministra do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","photo":""},
    {"id":"wd-Q10314705","name":"Dias Toffoli","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","photo":""},
    {"id":"wd-Q1516706","name":"Gilmar Mendes","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","photo":""},
    {"id":"wd-Q10321893","name":"Edson Fachin","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","photo":""},
    {"id":"wd-Q16503855","name":"Alexandre de Moraes","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Alexandre_de_Moraes_-_foto_oficial_2023.jpg/800px-Alexandre_de_Moraes_-_foto_oficial_2023.jpg"},
    {"id":"wd-Q106363617","name":"André Mendonça","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","photo":""},
    {"id":"wd-Q105748993","name":"Nunes Marques","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","photo":""},
    {"id":"wd-Q768093","name":"Flávio Dino","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","photo":""},
    {"id":"wd-Q118812476","name":"Cristiano Zanin","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","photo":""},
    {"id":"wd-Q3491617","name":"Paulo Gonet","role":"Procurador-Geral da República","party":"","state":"Nacional","country":"Brasil","source":"wikidata","photo":""},
]

# Governadores por UF (Wikidata QIDs — eleitos 2022)
GOVERNORS_BY_UF = {
    "AC": {"id":"wd-Q10282903","name":"Gladson Cameli","role":"Governador do Acre","party":"PP"},
    "AL": {"id":"wd-Q10285716","name":"Paulo Dantas","role":"Governador de Alagoas","party":"MDB"},
    "AP": {"id":"wd-Q107421","name":"Clécio Luís","role":"Governador do Amapá","party":"SD"},
    "AM": {"id":"wd-Q3730703","name":"Wilson Lima","role":"Governador do Amazonas","party":"União Brasil"},
    "BA": {"id":"wd-Q3891283","name":"Jerônimo Rodrigues","role":"Governador da Bahia","party":"PT"},
    "CE": {"id":"wd-Q10293629","name":"Elmano de Freitas","role":"Governador do Ceará","party":"PT"},
    "DF": {"id":"wd-Q10303893","name":"Ibaneis Rocha","role":"Governador do DF","party":"MDB"},
    "ES": {"id":"wd-Q3730577","name":"Renato Casagrande","role":"Governador do Espírito Santo","party":"PSB"},
    "GO": {"id":"wd-Q10306753","name":"Ronaldo Caiado","role":"Governador de Goiás","party":"União Brasil"},
    "MA": {"id":"wd-Q10306938","name":"Carlos Brandão","role":"Governador do Maranhão","party":"PSB"},
    "MT": {"id":"wd-Q10308490","name":"Mauro Mendes","role":"Governador do Mato Grosso","party":"União Brasil"},
    "MS": {"id":"wd-Q10308503","name":"Eduardo Riedel","role":"Governador do MS","party":"PSDB"},
    "MG": {"id":"wd-Q3564887","name":"Romeu Zema","role":"Governador de MG","party":"Novo"},
    "PA": {"id":"wd-Q10309820","name":"Helder Barbalho","role":"Governador do Pará","party":"MDB"},
    "PB": {"id":"wd-Q10309964","name":"João Azevêdo","role":"Governador da Paraíba","party":"PSB"},
    "PR": {"id":"wd-Q10310060","name":"Ratinho Junior","role":"Governador do Paraná","party":"PSD"},
    "PE": {"id":"wd-Q10310080","name":"Raquel Lyra","role":"Governadora de Pernambuco","party":"PSDB"},
    "PI": {"id":"wd-Q10310123","name":"Rafael Fonteles","role":"Governador do Piauí","party":"PT"},
    "RJ": {"id":"wd-Q1779090","name":"Cláudio Castro","role":"Governador do RJ","party":"PL"},
    "RN": {"id":"wd-Q10312022","name":"Fátima Bezerra","role":"Governadora do RN","party":"PT"},
    "RS": {"id":"wd-Q10312060","name":"Eduardo Leite","role":"Governador do RS","party":"PSDB"},
    "RO": {"id":"wd-Q10311952","name":"Marcos Rocha","role":"Governador de Rondônia","party":"União Brasil"},
    "RR": {"id":"wd-Q10312027","name":"Antonio Denarium","role":"Governador de Roraima","party":"PP"},
    "SC": {"id":"wd-Q10312568","name":"Jorginho Mello","role":"Governador de SC","party":"PL"},
    "SE": {"id":"wd-Q10314272","name":"Fábio Mitidieri","role":"Governador de Sergipe","party":"PSD"},
    "SP": {"id":"wd-Q1050742","name":"Tarcísio de Freitas","role":"Governador de SP","party":"Republicanos"},
    "TO": {"id":"wd-Q10314456","name":"Wanderlei Barbosa","role":"Governador do Tocantins","party":"Republicanos"},
}

async def get_deputados_by_uf(uf: str) -> list:
    """Busca deputados federais de um estado específico."""
    data = await _get(f"{CAMARA_BASE}/deputados", {"siglaUf": uf, "itens": 20, "ordem": "ASC", "ordenarPor": "nome"})
    if not data or "dados" not in data: return []
    return [{"id":f"dep-{d.get('id','')}","api_id":d.get("id"),"name":d.get("nome",""),
             "party":d.get("siglaPartido",""),"state":d.get("siglaUf",""),
             "role":"Deputado Federal","country":"Brasil",
             "photo":d.get("urlFoto",""),"email":d.get("email",""),"source":"camara"}
            for d in data["dados"]]

async def get_senadores_by_uf(uf: str) -> list:
    """Busca senadores de um estado específico."""
    data = await _get(f"{SENADO_BASE}/senador/lista/atual.json")
    if not data: return []
    try: senadores = data["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    except: return []
    results = []
    for s in senadores:
        try:
            id_s = s["IdentificacaoParlamentar"]
            if id_s.get("UfParlamentar","").upper() != uf.upper(): continue
            results.append({"id":f"sen-{id_s.get('CodigoParlamentar','')}",
                "api_id":id_s.get("CodigoParlamentar"),
                "name":id_s.get("NomeParlamentar","") or id_s.get("NomeCompletoParlamentar",""),
                "party":id_s.get("SiglaPartidoParlamentar",""),"state":uf.upper(),
                "role":"Senador Federal","country":"Brasil",
                "photo":id_s.get("UrlFotoParlamentar",""),
                "email":id_s.get("EmailParlamentar",""),"source":"senado"})
        except: continue
    return results

# UF code -> full state name
UF_NAMES = {"AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia",
    "CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás",
    "MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais",
    "PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí",
    "RJ":"Rio de Janeiro","RN":"Rio Grande do Norte","RS":"Rio Grande do Sul",
    "RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SE":"Sergipe",
    "SP":"São Paulo","TO":"Tocantins"}

from fastapi import Request as FARequest

@router.get("/transparency/local")
async def get_local_politicians(request: FARequest):
    """
    Retorna o painel inicial do portal com seções organizadas:
    - Executivo Federal (Presidente + Vice)
    - Estadual (Governador + Deputados federais + Senadores do estado do usuário)
    - STF
    """
    ip = request.headers.get("X-Forwarded-For", request.client.host or "127.0.0.1")
    ip = ip.split(",")[0].strip()
    geo = await _resolve_geo_trans(ip)

    uf       = geo.get("regionCode", "RJ").upper()
    city     = geo.get("city", "")
    state    = geo.get("regionName", "")
    country  = geo.get("countryCode", "BR").upper()

    # Executivo federal
    executivo = [
        {"id":"wd-Q28227","name":"Lula","role":"Presidente da República","party":"PT","state":"Nacional","country":"Brasil","source":"wikidata",
         "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Lula_-_foto_oficial_2023.jpg/800px-Lula_-_foto_oficial_2023.jpg","highlight":True},
        {"id":"wd-Q41551","name":"Geraldo Alckmin","role":"Vice-Presidente da República","party":"PSB","state":"Nacional","country":"Brasil","source":"wikidata","photo":"","highlight":False},
    ]

    # Governador do estado
    governor_data = GOVERNORS_BY_UF.get(uf)
    governador = []
    if governor_data:
        governador = [{**governor_data,"state":uf,"country":"Brasil","source":"wikidata","photo":"","email":""}]

    # Deputados + Senadores do estado (em paralelo)
    dep_task = get_deputados_by_uf(uf)
    sen_task = get_senadores_by_uf(uf)
    deputados, senadores = await asyncio.gather(dep_task, sen_task)

    return {
        "location": {"ip": ip, "city": city, "state": state, "uf": uf, "country": country,
                     "state_full": UF_NAMES.get(uf, state)},
        "sections": [
            {"id":"executivo","title":"🇧🇷 Poder Executivo Federal","subtitle":"Presidente e Vice-Presidente da República",
             "color":"#ffd93d","politicians": executivo},
            {"id":"governador","title":f"🏛️ Governo do Estado","subtitle":f"Governador de {UF_NAMES.get(uf, state)}",
             "color":"#66fcf1","politicians": governador},
            {"id":"senadores","title":f"🏛️ Senadores de {uf}","subtitle":f"Senadores que representam {UF_NAMES.get(uf, state)} no Senado Federal",
             "color":"#c678dd","politicians": senadores},
            {"id":"deputados","title":f"📋 Deputados Federais de {uf}","subtitle":f"Deputados eleitos por {UF_NAMES.get(uf, state)} na Câmara Federal",
             "color":"#45b7d1","politicians": deputados},
            {"id":"stf","title":"⚖️ Supremo Tribunal Federal","subtitle":"Ministros atuais do STF — guardiões da Constituição",
             "color":"#ff6b6b","politicians": STF_MINISTERS},
        ]
    }
