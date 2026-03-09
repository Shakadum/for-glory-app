"""Geolocalização e representantes locais por IP/cidade."""
import asyncio
import httpx
from .data.mayors import _norm, get_mayor_data, MAYORS_BY_CITY, GOVERNORS_BY_UF, UF_NAMES, COUNTRY_FLAGS
from .data.charges import _CHARGES_DB
from .data.politicians import CURATED_POLITICIANS
from .enrichment import enrich_with_photo
from .mayor_cache import _get_mayor_dynamic, search_city_politicians_wikidata
from .sources import _get, get_deputados_by_uf, get_senadores_by_uf


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


_geo_cache: dict = {}


async def _resolve_geo(ip: str) -> dict:
    if ip in _geo_cache: return _geo_cache[ip]
    if ip in ("127.0.0.1","::1") or ip.startswith(("192.168.","10.","172.")):
        return {"city":"Rio de Janeiro","regionName":"Rio de Janeiro","regionCode":"RJ","country":"Brasil","countryCode":"BR"}
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"http://ip-api.com/json/{ip}?fields=status,city,regionName,regionCode,countryCode,country", headers=_HDR)
            d = r.json()
            if d.get("status") == "success":
                _geo_cache[ip] = d; return d
    except: pass
    return {"city":"","regionName":"","regionCode":"RJ","country":"Brasil","countryCode":"BR"}

async def get_deputados_by_uf(uf: str) -> list:
    data = await _get(f"{CAMARA_BASE}/deputados", {"siglaUf":uf,"itens":30,"ordem":"ASC","ordenarPor":"nome"})
    if not data or "dados" not in data: return []
    return [{"id":f"dep-{d.get('id','')}","api_id":d.get("id"),"name":d.get("nome",""),
             "party":d.get("siglaPartido",""),"state":d.get("siglaUf",""),
             "role":"Deputado Federal","country":"Brasil",
             "photo":d.get("urlFoto",""),"email":d.get("email",""),"source":"camara"} for d in data["dados"]]

async def get_senadores_by_uf(uf: str) -> list:
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





async def get_local_politicians(request, uf_override=None, city_override=None):
    ip = request.headers.get("X-Forwarded-For", request.client.host or "127.0.0.1")
    ip = ip.split(",")[0].strip()
    geo = await _resolve_geo(ip)

    if uf_override and len(uf_override) == 2:
        uf    = uf_override.upper()
        state = UF_NAMES.get(uf, uf)
        city  = city_override or ""
    else:
        uf    = geo.get("regionCode", "RJ").upper()
        city  = city_override or geo.get("city", "")
        state = geo.get("regionName", "")

    country      = geo.get("countryCode", "BR").upper()
    country_flag = COUNTRY_FLAGS.get(country, "🌍")
    state_full   = UF_NAMES.get(uf, state)

    # Busca dados em paralelo
    dep_task = get_deputados_by_uf(uf)
    sen_task = get_senadores_by_uf(uf)
    city_wd_task = search_city_politicians_wikidata(city, uf) if city else asyncio.sleep(0)

    deputados, senadores, city_politicians_raw = await asyncio.gather(dep_task, sen_task, city_wd_task)
    if not isinstance(city_politicians_raw, list):
        city_politicians_raw = []

    # Enriquece fotos dos deputados via Wikipedia se necessário (em paralelo, max 10)
    dep_enrich = await asyncio.gather(*[enrich_with_photo(d) for d in deputados[:10]])
    deputados = list(dep_enrich) + deputados[10:]

    # Senadores — enriquece fotos
    sen_enrich = await asyncio.gather(*[enrich_with_photo(s) for s in senadores])
    senadores = list(sen_enrich)

    # Executivo: Lula e Alckmin com foto dinâmica
    exec_raw = [
        {**CURATED_POLITICIANS["wd-Q28227"], "highlight": True},
        {**CURATED_POLITICIANS["wd-Q41551"], "highlight": False},
    ]
    exec_enrich = await asyncio.gather(*[enrich_with_photo(e) for e in exec_raw])
    executivo = list(exec_enrich)

    # Governador com foto
    gov_raw = GOVERNORS_BY_UF.get(uf)
    if gov_raw:
        gov_dict = {**gov_raw, "state": uf, "country": "Brasil", "source": "wikidata", "email": ""}
        gov_dict = await enrich_with_photo(gov_dict)
        governador = [gov_dict]
    else:
        governador = []

    # ── Prefeito — cobertura total dos 5.571 municípios ──────────────────────
    # Camada 1: dict curado (87 cidades, 100% confiável)
    mayor_data = get_mayor_data(city)
    if mayor_data:
        mayor_dict = {**mayor_data, "country": "Brasil", "source": "wikidata", "email": ""}
        mayor_dict = await enrich_with_photo(mayor_dict)
        prefeito = [mayor_dict]
    elif city:
        # Camadas 2-5: TSE 2024 + Wikidata (cache DB → estado completo → individual)
        mayor_dyn = await _get_mayor_dynamic(city, uf)
        if mayor_dyn:
            mayor_dyn = await enrich_with_photo({**mayor_dyn, "email": ""})
            prefeito = [mayor_dyn]
        else:
            # Último recurso: filtrar da busca de vereadores
            pref_from_search = [p for p in city_politicians_raw
                                 if "prefeito" in p.get("role","").lower()
                                 or "prefeita" in p.get("role","").lower()]
            prefeito = [await enrich_with_photo(pref_from_search[0])] if pref_from_search else []
    else:
        prefeito = []

    # Vereadores / outros políticos locais do Wikidata (exceto já listado como prefeito)
    prefeito_ids = {p["id"] for p in prefeito}
    vereadores = [p for p in city_politicians_raw if p["id"] not in prefeito_ids]
    # Enriquece fotos dos vereadores do Wikidata em paralelo
    if vereadores:
        vereadores = list(await asyncio.gather(*[enrich_with_photo(v) for v in vereadores[:10]]))

    # STF: enriquece fotos em paralelo
    stf_enriched = list(await asyncio.gather(*[enrich_with_photo(dict(m)) for m in STF_MINISTERS]))

    sections = [
        {"id":"executivo","title":f"{country_flag} Poder Executivo Federal","subtitle":"Presidente e Vice-Presidente da República","color":"#ffd93d","politicians":executivo},
        {"id":"governador","title":"🏛️ Governo do Estado","subtitle":f"Governador(a) de {state_full}","color":"#66fcf1","politicians":governador},
    ]
    if city:
        sections.append({"id":"prefeito","title":f"🏙️ Prefeitura de {city}","subtitle":f"Prefeito(a) Municipal","color":"#f97316","politicians":prefeito})
        if vereadores:
            sections.append({"id":"vereadores","title":f"🗳️ Vereadores de {city}","subtitle":f"Representantes na Câmara Municipal","color":"#a78bfa","politicians":vereadores})
    sections += [
        {"id":"senadores","title":f"🗣️ Senadores de {uf}","subtitle":f"Senadores de {state_full} no Senado Federal","color":"#c678dd","politicians":senadores},
        {"id":"deputados","title":f"📋 Deputados Federais de {uf}","subtitle":f"Deputados eleitos por {state_full}","color":"#45b7d1","politicians":deputados},
        {"id":"stf","title":"⚖️ Supremo Tribunal Federal","subtitle":"11 Ministros — guardiões da Constituição Federal","color":"#ff6b6b","politicians":stf_enriched},
    ]

    return {
        "location": {
            "ip": ip, "city": city, "state": state, "uf": uf,
            "country": country, "country_flag": country_flag,
            "state_full": state_full,
        },
        "sections": sections,
    }

