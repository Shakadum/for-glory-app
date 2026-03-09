"""
For Glory — Portal da Transparência
Módulo: Fontes externas — Câmara, Senado, Wikidata, TSE
"""
import asyncio
import httpx
from .data.salaries import SALARY_BR
from .data.politicians import CURATED_POLITICIANS
from .enrichment import get_wiki_data, enrich_with_photo

CAMARA_BASE = "https://dadosabertos.camara.leg.br/api/v2"
SENADO_BASE = "https://legis.senado.leg.br/dadosabertos"
_HDR = {"User-Agent": "ForGloryApp/2.0 (transparency@forglory.online)"}


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
        dv = snak.get("datavalue", {}); t = dv.get("type",""); v = dv.get("value",{})
        if t == "string": return str(v)
        if t == "time": return str(v.get("time",""))[1:11]
        if t == "wikibase-entityid": return str(v.get("id",""))
        if t == "monolingualtext": return str(v.get("text",""))
        return str(v) if v else ""
    except: return ""

def _wd_values_all(claims, prop):
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
    data = await _get("https://www.wikidata.org/w/api.php", {
        "action":"wbgetentities","ids":"|".join(list(set(qids))[:30]),
        "props":"labels","languages":"pt|en","format":"json"})
    if not data: return {}
    out = {}
    for qid, ent in data.get("entities",{}).items():
        lab = ent.get("labels",{})
        out[qid] = (lab.get("pt") or lab.get("en") or {}).get("value","")
    return out

async def get_wikidata_entity(qid: str) -> dict:
    """Para políticos não curados (internacionais). Usa sitelink exato."""
    data = await _get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    if not data: return {}
    ent = data.get("entities",{}).get(qid,{})
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
    image_file = _wd_value(claims,"P18")
    website    = _wd_value(claims,"P856")

    all_qids = list(set(party_qs + [country_q, bplace_q] + edu_qs + pos_qs + occ_qs))
    lmap = await _resolve_labels([q for q in all_qids if q])

    # Bio via sitelink EXATO — nunca busca por texto livre
    title_pt = sitelinks.get("ptwiki",{}).get("title","")
    title_en = sitelinks.get("enwiki",{}).get("title","")
    wiki = {}
    if title_pt:
        wiki = await _wiki_summary(title_pt, "pt")
    if not wiki.get("bio") and title_en:
        wiki = await _wiki_summary(title_en, "en")

    photo = _wd_image(image_file) if image_file else wiki.get("photo","")

    return {
        "full_name": name, "description": desc,
        "bio": wiki.get("bio",""), "wiki_link": wiki.get("link",""),
        "birth_date": birth_date, "birth_place": lmap.get(bplace_q,""),
        "party": (lmap.get(party_qs[0],"") if party_qs else ""),
        "all_parties": [lmap.get(q,"") for q in party_qs if lmap.get(q)],
        "country": lmap.get(country_q,""),
        "education": (lmap.get(edu_qs[0],"") if edu_qs else ""),
        "all_education": [lmap.get(q,"") for q in edu_qs if lmap.get(q)],
        "role": (lmap.get(pos_qs[0],"") if pos_qs else ""),
        "all_roles": [lmap.get(q,"") for q in pos_qs if lmap.get(q)],
        "occupation": (lmap.get(occ_qs[0],"") if occ_qs else ""),
        "photo": photo, "website": website,
        "votes":[], "expenses":[], "charges":[], "salary_info": None,
    }

# ── CÂMARA ────────────────────────────────────────────────────


async def search_deputados(query, uf=None):
    params = {"nome":query,"itens":10,"ordem":"ASC","ordenarPor":"nome"}
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

    details = {"salary_info": SALARY_BR["camara"], "expenses":[], "votes":[], "charges":[],
               "all_roles":["Deputado Federal"], "all_education":[], "all_parties":[]}

    if data and "dados" in data:
        d = data["dados"]; ult = d.get("ultimoStatus",{})
        nome_civil = d.get("nomeCivil","")
        party = ult.get("siglaPartido","")
        details.update({
            "full_name": nome_civil,
            "birth_date": d.get("dataNascimento",""),
            "education":  d.get("escolaridade",""),
            "occupation": (d.get("profissoes") or [{}])[0].get("titulo",""),
            "party": party, "state": ult.get("siglaUf",""),
            "photo": ult.get("urlFoto","") or d.get("urlFoto",""),
            "email": ult.get("email","") or d.get("email",""),
            "website": ult.get("urlRedeSocial",""),
            "role": "Deputado Federal",
            "all_parties": [party] if party else [],
        })
        # Bio por título exato no Wikipedia
        if nome_civil:
            wiki = await _wiki_summary(nome_civil, "pt")
            if wiki.get("bio"):
                details["bio"] = wiki["bio"]
                details["wiki_link"] = wiki.get("link","")
                # Só usa foto do Wikipedia se não tiver foto da Câmara
                if not details.get("photo"): details["photo"] = wiki.get("photo","")

    if desp and "dados" in desp:
        details["expenses"] = [{"description":e.get("tipoDespesa",""),
            "value":e.get("valorLiquido",0),
            "date":f"{e.get('mes','')}/{e.get('ano','')}",
            "provider":e.get("nomeFornecedor","")} for e in desp["dados"][:10]]

    if vot and "dados" in vot:
        vote_items = []
        for v in vot["dados"][:12]:
            prop = v.get("proposicao_") or {}
            ementa = prop.get("ementa","") or v.get("descricao","") or v.get("titulo","")
            sigla  = prop.get("siglaTipo","")
            numero = prop.get("numero","")
            ano    = prop.get("ano","")
            label  = f"{sigla} {numero}/{ano} — {ementa}" if sigla and ementa else ementa or v.get("descricao","")
            vote_items.append({
                "description": label[:180],
                "date": (v.get("dataHoraVoto") or v.get("data",""))[:10],
                "vote": v.get("voto","") or "",
            })
        details["votes"] = [vi for vi in vote_items if vi["description"]]
    # Enriquece com processos do banco de dados de charges
    if not details.get("charges"):
        details["charges"] = _get_charges(
            details.get("name","") or details.get("full_name",""),
            details.get("full_name","")
        )
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
    details = {"salary_info": SALARY_BR["senado"], "votes":[], "expenses":[], "charges":[],
               "all_roles":["Senador Federal"], "all_education":[], "all_parties":[]}
    if data:
        try:
            p = data["DetalheParlamentar"]["Parlamentar"]
            ident = p.get("IdentificacaoParlamentar",{}); dados = p.get("DadosBasicosParlamentar",{})
            nome_completo = ident.get("NomeCompletoParlamentar","")
            party = ident.get("SiglaPartidoParlamentar","")
            details.update({
                "full_name": nome_completo,
                "birth_date": dados.get("DataNascimento",""),
                "education":  dados.get("FormacaoAcademica",""),
                "occupation": dados.get("Profissao",""),
                "website":    ident.get("UrlPaginaParlamentar",""),
                "email":      ident.get("EmailParlamentar",""),
                "party": party, "all_parties": [party] if party else [],
                "role": "Senador Federal",
            })
            if nome_completo:
                wiki = await _wiki_summary(nome_completo, "pt")
                if not wiki.get("bio"):
                    wiki = await _wiki_summary(ident.get("NomeParlamentar",""), "pt")
                if wiki.get("bio"):
                    details["bio"] = wiki["bio"]
                    details["wiki_link"] = wiki.get("link","")
                    if not details.get("photo"): details["photo"] = wiki.get("photo","")
        except: pass
    if vd:
        try:
            vlist = vd["VotacoesParlamentar"]["Parlamentar"]["Votacoes"]["Votacao"]
            if isinstance(vlist,dict): vlist=[vlist]
            details["votes"] = [
                {"description": v.get("DescricaoVotacao","") or v.get("Titulo",""),
                 "date": v.get("DataSessao",""),
                 "vote": v.get("Voto","") or v.get("DescricaoVoto","")}
                for v in (vlist or [])[:12] if v.get("DescricaoVotacao") or v.get("Titulo")
            ]
        except: pass
    # Enriquece com processos do banco de dados de charges
    if not details.get("charges"):
        details["charges"] = _get_charges(
            details.get("name","") or details.get("full_name",""),
            details.get("full_name","")
        )
    return details

# ── BUSCA WIKIDATA (só para internacionais) ───────────────────
async def search_wikidata_politicians(query: str) -> list:
    sparql = f"""
SELECT DISTINCT ?person ?personLabel ?partyLabel ?countryLabel ?posLabel ?image WHERE {{
  ?person wdt:P31 wd:Q5 .
  {{ ?person wdt:P106 ?occ . VALUES ?occ {{ wd:Q82955 wd:Q372436 wd:Q1028181 wd:Q30461 wd:Q16707842 wd:Q16707845 wd:Q17540564 wd:Q2285706 }} }}
  UNION {{ ?person wdt:P39 ?anyPos . }}
  ?person rdfs:label ?label .
  FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{query}")))
  FILTER(LANG(?label) IN ("pt","en","es","fr","de","ja","zh"))
  OPTIONAL {{ ?person wdt:P18 ?image }}
  OPTIONAL {{ ?person wdt:P102 ?party }}
  OPTIONAL {{ ?person wdt:P27 ?country }}
  OPTIONAL {{ ?person wdt:P39 ?pos }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}} LIMIT 10"""
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as c:
            r = await c.get("https://query.wikidata.org/sparql",
                            params={"query": sparql, "format": "json"},
                            headers={**_HDR, "Accept": "application/sparql-results+json"})
            if r.status_code != 200: raise Exception()
            bindings = r.json().get("results",{}).get("bindings",[])
    except: return []
    seen = set(); results = []
    for b in bindings:
        qid = b.get("person",{}).get("value","").split("/")[-1]
        if qid in seen: continue
        seen.add(qid)
        name = b.get("personLabel",{}).get("value","")
        if not name or name.startswith("Q"): continue
        image = b.get("image",{}).get("value","")
        results.append({
            "id":f"wd-{qid}","api_id":qid,"name":name,
            "party":b.get("partyLabel",{}).get("value",""),
            "state":"","role":b.get("posLabel",{}).get("value",""),
            "country":b.get("countryLabel",{}).get("value",""),
            "photo":_wd_image(image) if image and not image.startswith("http") else image,
            "email":"","source":"wikidata",})
    return results[:8]

# ── GEO + DADOS LOCAIS ────────────────────────────────────────
_geo_cache: dict = {}



async def get_executive_actions(year_start: str = "2023-01-01") -> dict:
    """
    Busca ações do Executivo Federal:
    - Medidas Provisórias (MPV) editadas
    - Proposições de lei do Executivo recentemente aprovadas
    - Mensagens presidenciais (MSG) ao Congresso
    Fonte: API da Câmara dos Deputados (dados abertos)
    """
    mpv_task = _get(f"{CAMARA_BASE}/proposicoes", {
        "siglaTipo": "MPV", "dataInicio": year_start,
        "itens": 8, "ordem": "DESC", "ordenarPor": "id"})
    msg_task = _get(f"{CAMARA_BASE}/proposicoes", {
        "siglaTipo": "MSG", "dataInicio": year_start,
        "itens": 8, "ordem": "DESC", "ordenarPor": "id"})
    pl_exec_task = _get(f"{CAMARA_BASE}/proposicoes", {
        "siglaTipo": "PL", "dataInicio": year_start,
        "autor": "EXECUTIVO", "itens": 6,
        "ordem": "DESC", "ordenarPor": "id"})

    mpvs_data, msgs_data, pls_data = await asyncio.gather(mpv_task, msg_task, pl_exec_task)

    actions = []
    for source, tipo_label in [(mpvs_data, "Medida Provisória"), (msgs_data, "Mensagem ao Congresso"), (pls_data, "Projeto de Lei — Executivo")]:
        if not source or "dados" not in source: continue
        for p in source["dados"][:5]:
            ementa = p.get("ementa","") or p.get("titulo","")
            if not ementa: continue
            actions.append({
                "type":        tipo_label,
                "sigla":       p.get("siglaTipo",""),
                "numero":      f"{p.get('numero','')}/{p.get('ano','')}",
                "description": ementa[:200],
                "date":        p.get("dataApresentacao","")[:10] if p.get("dataApresentacao") else "",
            })
    # Sort by date desc
    actions.sort(key=lambda x: x["date"], reverse=True)
    return {"actions": actions[:12], "source": "API da Câmara dos Deputados (dadosabertos.camara.leg.br)"}


async def fetch_photo_from_wikipedia(wiki_title: str) -> str:
    """Busca a foto principal do artigo Wikipedia pelo título exato."""
    if not wiki_title: return ""
    wiki = await _wiki_summary(wiki_title, "pt")
    return wiki.get("photo","")


# ── ENDPOINTS ─────────────────────────────────────────────────
@router.get("/transparency/search")


async def _wikidata_sparql(sparql: str, timeout: int = 15) -> list:
    """Executa query SPARQL no Wikidata. Retorna lista de bindings ou []."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
            r = await c.get(
                "https://query.wikidata.org/sparql",
                params={"query": sparql, "format": "json"},
                headers={**_HDR, "Accept": "application/sparql-results+json"}
            )
            if r.status_code == 200:
                return r.json().get("results", {}).get("bindings", [])
    except Exception:
        pass
    return []


def _parse_politician_binding(b: dict, city_name: str, uf: str) -> dict | None:
    """Converte um binding Wikidata em dict de político normalizado."""
    qid  = b.get("person", {}).get("value", "").split("/")[-1]
    name = b.get("personLabel", {}).get("value", "")
    if not name or name.startswith("Q") or not qid:
        return None
    image = b.get("image", {}).get("value", "")
    if image and not image.startswith("http"):
        image = _wd_image(image)
    # Tenta extrair sitelink pt.wikipedia para busca de bio depois
    wiki_pt = b.get("sitelink", {}).get("value", "")
    if wiki_pt and "/wiki/" in wiki_pt:
        wiki_pt = urllib.parse.unquote(wiki_pt.split("/wiki/")[-1])
    return {
        "id":            f"wd-{qid}",
        "name":          name,
        "display_name":  name,
        "role":          b.get("posLabel", {}).get("value", "") or f"Político de {city_name}",
        "party":         b.get("partyLabel", {}).get("value", ""),
        "state":         uf.upper() if uf else "",
        "country":       "Brasil",
        "photo":         image,
        "source":        "wikidata",
        "wiki_title_pt": wiki_pt or name,
        "wiki_title_en": name,
    }

# ═══════════════════════════════════════════════════════════════════════
#  SISTEMA DE PREFEITOS — COBERTURA TOTAL DOS 5.571 MUNICÍPIOS
#
#  Camadas (executadas em ordem, parando na primeira que retorna):
#    1. Dict curado MAYORS_BY_CITY  → 87 grandes cidades, 100% confiável
#    2. MayorCache no PostgreSQL    → resultado de consultas anteriores (TTL 90d)
#    3. TSE Eleições 2024           → fonte oficial, cobre TODOS os 5.571
#    4. Wikidata bulk por UF        → enriquece com QID, foto, partido
#    5. Wikidata individual         → fallback para cidades fora do bulk
#    6. Avatar gerado               → foto garantida mesmo sem Wikipedia
# ═══════════════════════════════════════════════════════════════════════

# UF → QID do estado no Wikidata
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

# ── Helpers do banco ───────────────────────────────────────────────────

