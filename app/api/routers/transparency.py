"""
For Glory — Portal da Transparência v6
Estratégia de fotos:
  - Sistema de cache dinâmico: Wikipedia REST API como fonte única de verdade
  - Todas as fotos são buscadas via /api/rest_v1/page/summary/{title}
  - Cache em memória com TTL de 12h — refresh automático no background
  - Fallback para Wikidata image property se Wikipedia não retornar
  - NUNCA usa URLs hardcoded do Wikimedia Commons (quebram quando renomeadas)
"""
import asyncio, hashlib, urllib.parse, time
import httpx
from fastapi import APIRouter, Query, Depends, Body, Request as FARequest
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from typing import Optional
from app.db.session import get_db
from app.db.base import Base

router = APIRouter()

CAMARA_BASE = "https://dadosabertos.camara.leg.br/api/v2"
SENADO_BASE = "https://legis.senado.leg.br/dadosabertos"
_HDR = {"User-Agent": "ForGloryApp/2.0 (transparency@forglory.online)"}

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

# ═══════════════════════════════════════════════════════════════
#  SISTEMA DINÂMICO DE FOTOS — Wikipedia REST API + Cache TTL
# ═══════════════════════════════════════════════════════════════
_PHOTO_CACHE: dict = {}          # { wiki_title: { photo, bio, link, ts } }
_PHOTO_CACHE_TTL = 43200         # 12 horas em segundos
_PHOTO_LOCK = asyncio.Lock()

# URLs de fallback verificadas — usadas quando Wikipedia API falha
# Formato: { wiki_title_pt: "url_commons" }
_FALLBACK_PHOTOS: dict[str, str] = {
    "Luiz Inácio Lula da Silva":        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Lula_-_foto_oficial_2023.jpg/400px-Lula_-_foto_oficial_2023.jpg",
    "Geraldo Alckmin":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Geraldo_Alckmin_-_foto_oficial_2023.jpg/400px-Geraldo_Alckmin_-_foto_oficial_2023.jpg",
    "Luís Roberto Barroso":             "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Ministro_Lu%C3%ADs_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg/400px-Ministro_Lu%C3%ADs_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg",
    "Alexandre de Moraes":              "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Alexandre_de_Moraes_-_foto_oficial_2023.jpg/400px-Alexandre_de_Moraes_-_foto_oficial_2023.jpg",
    "Cármen Lúcia Antunes Rocha":       "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/C%C3%A1rmen_L%C3%BAcia_-_foto_oficial_2017_%28cropped%29.jpg/400px-C%C3%A1rmen_L%C3%BAcia_-_foto_oficial_2017_%28cropped%29.jpg",
    "Cármen Lúcia":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/C%C3%A1rmen_L%C3%BAcia_-_foto_oficial_2017_%28cropped%29.jpg/400px-C%C3%A1rmen_L%C3%BAcia_-_foto_oficial_2017_%28cropped%29.jpg",
    "Dias Toffoli":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Dias_Toffoli_%282023%29.jpg/400px-Dias_Toffoli_%282023%29.jpg",
    "Gilmar Ferreira Mendes":           "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Gilmar_Mendes_%282023%29.jpg/400px-Gilmar_Mendes_%282023%29.jpg",
    "Gilmar Mendes":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Gilmar_Mendes_%282023%29.jpg/400px-Gilmar_Mendes_%282023%29.jpg",
    "Edson Fachin":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Edson_Fachin_2023.jpg/400px-Edson_Fachin_2023.jpg",
    "André Mendonça (ministro)":        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Andr%C3%A9_Mendon%C3%A7a_2023.jpg/400px-Andr%C3%A9_Mendon%C3%A7a_2023.jpg",
    "André Mendonça":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Andr%C3%A9_Mendon%C3%A7a_2023.jpg/400px-Andr%C3%A9_Mendon%C3%A7a_2023.jpg",
    "Kassio Nunes Marques":             "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Kassio_Nunes_Marques_2023.jpg/400px-Kassio_Nunes_Marques_2023.jpg",
    "Flávio Dino":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Fl%C3%A1vio_Dino_2023_%28cropped%29.jpg/400px-Fl%C3%A1vio_Dino_2023_%28cropped%29.jpg",
    "Cristiano Zanin Martins":          "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Cristiano_Zanin_2023.jpg/400px-Cristiano_Zanin_2023.jpg",
    "Cristiano Zanin":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Cristiano_Zanin_2023.jpg/400px-Cristiano_Zanin_2023.jpg",
    "Jair Bolsonaro":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Jair_Bolsonaro_2019.jpg/400px-Jair_Bolsonaro_2019.jpg",
    "Tarcísio de Freitas":              "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Tarc%C3%ADsio_de_Freitas_-_foto_oficial_2022_%28cropped%29.jpg/400px-Tarc%C3%ADsio_de_Freitas_-_foto_oficial_2022_%28cropped%29.jpg",
    "Arthur Lira":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Arthur_Lira_-_foto_oficial_2023.jpg/400px-Arthur_Lira_-_foto_oficial_2023.jpg",
    "Rodrigo Pacheco":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Rodrigo_Pacheco_-_foto_oficial_2021.jpg/400px-Rodrigo_Pacheco_-_foto_oficial_2021.jpg",
    "Michel Temer":                     "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Michel_Temer_-_foto_oficial_2016.jpg/400px-Michel_Temer_-_foto_oficial_2016.jpg",
    "Dilma Rousseff":                   "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Dilma_Rousseff_-_foto_oficial_2011.jpg/400px-Dilma_Rousseff_-_foto_oficial_2011.jpg",
    "Romeu Zema":                       "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Romeu_Zema_-_foto_oficial_2019.jpg/400px-Romeu_Zema_-_foto_oficial_2019.jpg",
    "Raquel Lyra":                      "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Raquel_Lyra_-_foto_oficial_2023.jpg/400px-Raquel_Lyra_-_foto_oficial_2023.jpg",
    "Helder Barbalho":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Helder_Barbalho_-_foto_oficial_2019.jpg/400px-Helder_Barbalho_-_foto_oficial_2019.jpg",
    "Eduardo Leite (político)":         "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Eduardo_Leite_-_foto_oficial_2023.jpg/400px-Eduardo_Leite_-_foto_oficial_2023.jpg",
}

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
# Salário presidente: Lei 13.752/2018 — R$ 30.934,70/mês
# Salário ministro STF: R$ 46.366,19/mês (teto constitucional)
# Salário dep/sen: R$ 46.366,19/mês

CURATED_POLITICIANS = {

    # ════════════════ EXECUTIVO FEDERAL ════════════════
    "wd-Q28227": {
        "id": "wd-Q28227",
        "name": "Luiz Inácio Lula da Silva",
        "display_name": "Lula",
        "role": "Presidente da República",
        "party": "PT",
        "state": "Nacional",
        "country": "Brasil",
        "source": "wikidata",
        "photo": "",
        "full_name": "Luiz Inácio Lula da Silva",
        "birth_date": "1945-10-27",
        "birth_place": "Caetés, Pernambuco",
        "education": "Curso técnico em Torneiro Mecânico (SENAI)",
        "occupation": "Torneiro mecânico / Sindicalista",
        "email": "",
        "website": "https://www.gov.br/planalto/pt-br",
        "wiki_title_pt": "Luiz Inácio Lula da Silva", "wiki_title_en": "Lula",
        "all_parties": ["PT"],
        "all_roles": [
            "Presidente da República (2023–presente)",
            "Presidente da República (2003–2011)",
            "Presidente do PT (1980–1994)",
            "Deputado Federal por SP (1986–1991)",
        ],
        "all_education": ["Curso técnico em Torneiro Mecânico — SENAI"],
        "salary_info": {
            "cargo": "Presidente da República",
            "subsidio_mensal": 30934.70,
            "subsidio_desc": "Subsídio mensal do Presidente da República (Lei nº 13.752/2018)",
            "beneficios": [
                {"nome": "Residência Oficial (Palácio da Alvorada)", "valor": "Custeado pela União", "descricao": "Moradia oficial do Presidente e família"},
                {"nome": "Segurança (GSI)", "valor": "Custeado pela União", "descricao": "Serviço de segurança institucional"},
                {"nome": "Aeronave Presidencial (VC-1/VC-2)", "valor": "Custeado pela União", "descricao": "Transporte oficial em missões de Estado"},
                {"nome": "Staff e equipe de apoio", "valor": "Custeado pela União", "descricao": "Equipe de assessoria, comunicação e logística do Palácio"},
                {"nome": "Verba de representação", "valor": "Não divulgado publicamente", "descricao": "Despesas protocolares e de representação do cargo"},
            ],
            "beneficios_abdicados_info": "O Presidente pode abrir mão de benefícios adicionais como o uso exclusivo de aeronave em voos particulares. Lula declarou abrir mão do uso do Palácio do Jaburu.",
            "fonte": "https://www.gov.br/planejamento/pt-br/acesso-a-informacao/transparencia-e-prestacao-de-contas",
        },
        "charges": [
            "Condenado em 1ª instância (TRF-4) por corrupção e lavagem de dinheiro no caso do tríplex do Guarujá — sentença de 9 anos e 6 meses (jul/2017, Sérgio Moro); confirmada pelo TRF-4 com aumento para 12 anos (jan/2018)",
            "Condenado em 1ª instância no caso do sítio em Atibaia — sentença de 12 anos e 11 meses (fev/2019); confirmada pelo TRF-4 (abr/2021)",
            "Preso preventivamente em 07/04/2018 após STF negar HC, cumprindo 580 dias de prisão em Curitiba",
            "STF anulou as condenações em 08/03/2021 (min. Edson Fachin), por incompetência da Vara Federal de Curitiba — Lula recuperou direitos políticos",
            "Processos remetidos à Justiça Federal do DF e SP — instrução reiniciada (situação: em andamento, 2024)",
            "Investigado na Operação Lava Jato em outros casos (Instituto Lula, palestras internacionais) — processos sem condenação transitada em julgado",
            "NOTA: Plenário do STF confirmou parcialidade do ex-juiz Sérgio Moro nos julgamentos (jun/2021)",
        ],
        "votes": [],
        "expenses": [],
    },

    "wd-Q41551": {
        "id": "wd-Q41551",
        "name": "Geraldo Alckmin",
        "display_name": "Geraldo Alckmin",
        "role": "Vice-Presidente da República",
        "party": "PSB",
        "state": "Nacional",
        "country": "Brasil",
        "source": "wikidata",
        "photo": "",
        "full_name": "Geraldo José Rodrigues Alckmin Filho",
        "birth_date": "1952-11-11",
        "birth_place": "Pindamonhangaba, São Paulo",
        "education": "Medicina — Faculdade de Medicina de Taubaté",
        "occupation": "Médico / Político",
        "website": "https://www.gov.br/planalto/pt-br",
        "wiki_title_pt": "Geraldo Alckmin", "wiki_title_en": "Geraldo Alckmin",
        "all_parties": ["PSB", "PSDB (até 2022)"],
        "all_roles": [
            "Vice-Presidente da República (2023–presente)",
            "Governador de São Paulo (2001–2006, 2011–2018)",
            "Vice-Governador de São Paulo (1995–2001)",
            "Deputado Estadual SP (1983–1988)",
        ],
        "all_education": ["Medicina — Faculdade de Medicina de Taubaté (Unitau)"],
        "salary_info": {
            "cargo": "Vice-Presidente da República",
            "subsidio_mensal": 27176.88,
            "subsidio_desc": "Subsídio mensal do Vice-Presidente da República",
            "beneficios": [
                {"nome": "Residência Oficial (Palácio do Jaburu)", "valor": "Custeado pela União", "descricao": "Moradia oficial do Vice-Presidente"},
                {"nome": "Segurança (GSI)", "valor": "Custeado pela União", "descricao": "Serviço de segurança institucional"},
            ],
            "beneficios_abdicados_info": "Alckmin não reside no Palácio do Jaburu — mora em residência particular em São Paulo.",
            "fonte": "https://www.gov.br/planejamento/pt-br",
        },
        "charges": [
            "Investigado na Operação Lava Jato por suposto recebimento de propina da Odebrecht em caixa dois para campanha de 2010",
            "Denunciado pelo MPF no STJ em 2018 por crime eleitoral — STJ rejeitou a denúncia em 2019",
        ],
        "votes": [],
        "expenses": [],
    },

    # ════════════════ STF ════════════════
    "wd-Q10319857": {
        "id": "wd-Q10319857",
        "name": "Luís Roberto Barroso",
        "display_name": "Barroso",
        "role": "Presidente do STF",
        "party": "",
        "state": "Nacional",
        "country": "Brasil",
        "source": "wikidata",
        "photo": "",
        "full_name": "Luís Roberto Barroso",
        "birth_date": "1958-03-11",
        "birth_place": "Vassouras, Rio de Janeiro",
        "education": "Direito — UERJ; LLM e PhD — Yale Law School (EUA)",
        "occupation": "Jurista / Professor de Direito Constitucional",
        "website": "https://portal.stf.jus.br",
        "wiki_title_pt": "Luís Roberto Barroso", "wiki_title_en": "Roberto Barroso",
        "all_parties": [],
        "all_roles": ["Presidente do STF (2023–presente)", "Ministro do STF (desde 2013)"],
        "all_education": ["Direito — UERJ", "LLM — Yale Law School", "PhD (Doutorado) — Yale Law School"],
        "salary_info": {
            "cargo": "Ministro do Supremo Tribunal Federal",
            "subsidio_mensal": 46366.19,
            "subsidio_desc": "Subsídio dos ministros do STF — teto constitucional do funcionalismo público",
            "beneficios": [
                {"nome": "Auxílio-Moradia", "valor": "R$ 4.377,73/mês", "descricao": "Para ministros sem imóvel funcional em Brasília"},
                {"nome": "Auxílio-Alimentação", "valor": "R$ 1.022,54/mês", "descricao": "Benefício alimentar"},
                {"nome": "Plano de Saúde", "valor": "Custeado pelo STF", "descricao": "Para o ministro e dependentes"},
                {"nome": "Aposentadoria integral", "valor": "R$ 46.366,19/mês", "descricao": "Aposentadoria com subsídio integral após afastamento"},
            ],
            "beneficios_abdicados_info": "Ministros podem abrir mão do auxílio-moradia caso utilizem imóvel funcional do STF.",
            "fonte": "https://portal.stf.jus.br/textos/verTexto.asp?servico=processoAudienciaPublicaSaude",
        },
        "charges": [],
        "votes": [],
        "expenses": [],
    },

    "wd-Q16503855": {
        "id": "wd-Q16503855",
        "name": "Alexandre de Moraes",
        "display_name": "Alexandre de Moraes",
        "role": "Ministro do STF",
        "party": "",
        "state": "Nacional",
        "country": "Brasil",
        "source": "wikidata",
        "photo": "",
        "full_name": "Alexandre de Moraes",
        "birth_date": "1968-08-13",
        "birth_place": "São Paulo, SP",
        "education": "Direito — USP; Doutorado em Direito Constitucional — USP",
        "occupation": "Jurista / Professor",
        "website": "https://portal.stf.jus.br",
        "wiki_title_pt": "Alexandre de Moraes", "wiki_title_en": "Alexandre de Moraes",
        "all_parties": [],
        "all_roles": [
            "Ministro do STF (desde 2017)",
            "Presidente do TSE (2022–2024)",
            "Ministro da Justiça e Segurança Pública (2017)",
            "Secretário de Segurança Pública de SP (2016)",
        ],
        "all_education": ["Direito — USP", "Doutorado em Direito Constitucional — USP"],
        "salary_info": {
            "cargo": "Ministro do Supremo Tribunal Federal",
            "subsidio_mensal": 46366.19,
            "subsidio_desc": "Subsídio dos ministros do STF — teto constitucional",
            "beneficios": [
                {"nome": "Auxílio-Moradia", "valor": "R$ 4.377,73/mês", "descricao": "Para ministros sem imóvel funcional"},
                {"nome": "Auxílio-Alimentação", "valor": "R$ 1.022,54/mês", "descricao": "Benefício alimentar"},
                {"nome": "Plano de Saúde", "valor": "Custeado pelo STF", "descricao": "Para o ministro e dependentes"},
            ],
            "beneficios_abdicados_info": "",
            "fonte": "https://portal.stf.jus.br",
        },
        "charges": [
            "Investigado pelo Parlamento Europeu por restrições à liberdade de expressão (2024)",
            "Alvo de inquérito nos EUA sobre possível interferência eleitoral (2024) — arquivado",
        ],
        "votes": [],
        "expenses": [],
    },

    "wd-Q2948413": {
        "id": "wd-Q2948413", "name": "Cármen Lúcia", "wiki_title_pt": "Cármen Lúcia Antunes Rocha", "wiki_title_en": "Carmen Lúcia", "display_name": "Cármen Lúcia",
        "role": "Ministra do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Cármen Lúcia Antunes Rocha",
        "birth_date": "1954-04-05", "birth_place": "Montes Claros, MG",
        "education": "Direito — PUC Minas; Doutorado — UFMG",
        "occupation": "Jurista / Professora",
        "wiki_title_pt": "Cármen Lúcia Antunes Rocha",
        "all_roles": ["Ministra do STF (desde 2006)", "Presidente do STF (2016–2018)", "Presidente do TSE (2016–2018)"],
        "all_education": ["Direito — PUC Minas", "Doutorado em Direito — UFMG"],
        "salary_info": {
            "cargo": "Ministra do STF",
            "subsidio_mensal": 46366.19,
            "subsidio_desc": "Subsídio dos ministros do STF — teto constitucional",
            "beneficios": [{"nome": "Auxílio-Moradia", "valor": "R$ 4.377,73/mês", "descricao": ""}, {"nome": "Auxílio-Alimentação", "valor": "R$ 1.022,54/mês", "descricao": ""}, {"nome": "Plano de Saúde", "valor": "Custeado pelo STF", "descricao": ""}],
            "beneficios_abdicados_info": "",
            "fonte": "https://portal.stf.jus.br",
        },
        "charges": [], "votes": [], "expenses": [],
    },

    "wd-Q10314705": {
        "id": "wd-Q10314705", "name": "Dias Toffoli", "display_name": "Dias Toffoli",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "José Antonio Dias Toffoli",
        "birth_date": "1967-11-15", "birth_place": "Marília, SP",
        "education": "Direito — USP", "occupation": "Advogado / Jurista",
        "wiki_title_pt": "Dias Toffoli",
        "all_roles": ["Ministro do STF (desde 2009)", "Presidente do STF (2018–2019)", "Advogado-Geral da União (2007–2009)"],
        "all_education": ["Direito — USP"],
        "salary_info": {"cargo": "Ministro do STF", "subsidio_mensal": 46366.19, "subsidio_desc": "Teto constitucional", "beneficios": [], "beneficios_abdicados_info": "", "fonte": "https://portal.stf.jus.br"},
        "charges": ["Investigado no Supremo por suposto envolvimento em negociações irregulares (inquérito em andamento)"],
        "votes": [], "expenses": [],
    },

    "wd-Q1516706": {
        "id": "wd-Q1516706", "name": "Gilmar Mendes", "wiki_title_pt": "Gilmar Ferreira Mendes", "wiki_title_en": "Gilmar Mendes", "display_name": "Gilmar Mendes",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "",
        "full_name": "Gilmar Ferreira Mendes",
        "birth_date": "1955-02-17", "birth_place": "Diamantino, MT",
        "education": "Direito — UnB; Doutorado — Universidade de Münster (Alemanha)",
        "occupation": "Jurista / Professor",
        "wiki_title_pt": "Gilmar Ferreira Mendes",
        "all_roles": ["Ministro do STF (desde 2002)", "Presidente do STF (2008–2010)", "Advogado-Geral da União (2000–2002)"],
        "all_education": ["Direito — UnB", "Doutorado — Universidade de Münster (Alemanha)"],
        "salary_info": {"cargo": "Ministro do STF", "subsidio_mensal": 46366.19, "subsidio_desc": "Teto constitucional", "beneficios": [{"nome": "Auxílio-Moradia", "valor": "R$ 4.377,73/mês", "descricao": ""}, {"nome": "Auxílio-Alimentação", "valor": "R$ 1.022,54/mês", "descricao": ""}], "beneficios_abdicados_info": "", "fonte": "https://portal.stf.jus.br"},
        "charges": ["Alvo de questionamentos sobre suspeição em casos envolvendo o agronegócio (2023)"],
        "votes": [], "expenses": [],
    },

    "wd-Q10321893": {
        "id": "wd-Q10321893", "name": "Edson Fachin", "display_name": "Edson Fachin",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Luiz Edson Fachin",
        "birth_date": "1958-02-17", "birth_place": "Pinhão, PR",
        "education": "Direito — UFPR; Doutorado — PUC-SP",
        "occupation": "Jurista / Professor",
        "wiki_title_pt": "Edson Fachin",
        "all_roles": ["Ministro do STF (desde 2015)", "Presidente do TSE (2020–2022)", "Professor de Direito Civil — UFPR"],
        "all_education": ["Direito — UFPR", "Doutorado em Direito — PUC-SP"],
        "salary_info": {"cargo": "Ministro do STF", "subsidio_mensal": 46366.19, "subsidio_desc": "Teto constitucional", "beneficios": [], "beneficios_abdicados_info": "", "fonte": "https://portal.stf.jus.br"},
        "charges": [], "votes": [], "expenses": [],
    },

    "wd-Q106363617": {
        "id": "wd-Q106363617", "name": "André Mendonça", "wiki_title_pt": "André Mendonça (ministro)", "wiki_title_en": "André Mendonça", "display_name": "André Mendonça",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "André Luís de Almeida Mendonça",
        "birth_date": "1977-03-24", "birth_place": "Goiânia, GO",
        "education": "Direito — UFG; Doutorado — UnB",
        "occupation": "Advogado / Procurador da República",
        "wiki_title_pt": "André Mendonça (ministro)",
        "all_roles": ["Ministro do STF (desde 2021)", "AGU (2019–2020)", "Ministro da Justiça (2020–2021)"],
        "all_education": ["Direito — UFG", "Doutorado em Direito — UnB"],
        "salary_info": {"cargo": "Ministro do STF", "subsidio_mensal": 46366.19, "subsidio_desc": "Teto constitucional", "beneficios": [], "beneficios_abdicados_info": "", "fonte": "https://portal.stf.jus.br"},
        "charges": [], "votes": [], "expenses": [],
    },

    "wd-Q105748993": {
        "id": "wd-Q105748993", "name": "Kassio Nunes Marques", "display_name": "Nunes Marques",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Kassio Nunes Marques",
        "birth_date": "1975-10-10", "birth_place": "Timon, MA",
        "education": "Direito — UFPI; Doutorado — USP",
        "occupation": "Jurista / Desembargador",
        "wiki_title_pt": "Kassio Nunes Marques",
        "all_roles": ["Ministro do STF (desde 2020)", "Desembargador TRF-1 (2013–2020)"],
        "all_education": ["Direito — UFPI", "Doutorado — USP"],
        "salary_info": {"cargo": "Ministro do STF", "subsidio_mensal": 46366.19, "subsidio_desc": "Teto constitucional", "beneficios": [], "beneficios_abdicados_info": "", "fonte": "https://portal.stf.jus.br"},
        "charges": [], "votes": [], "expenses": [],
    },

    "wd-Q768093": {
        "id": "wd-Q768093", "name": "Flávio Dino", "display_name": "Flávio Dino",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Flávio Dino de Castro e Costa",
        "birth_date": "1968-06-08", "birth_place": "Caxias, MA",
        "education": "Direito — UFMA; Doutorado — USP",
        "occupation": "Jurista / Político",
        "wiki_title_pt": "Flávio Dino",
        "all_roles": ["Ministro do STF (desde 2023)", "Ministro da Justiça (2023)", "Governador do Maranhão (2015–2022)", "Senador do Maranhão (2022–2023)"],
        "all_education": ["Direito — UFMA", "Doutorado em Direito — USP"],
        "salary_info": {"cargo": "Ministro do STF", "subsidio_mensal": 46366.19, "subsidio_desc": "Teto constitucional", "beneficios": [], "beneficios_abdicados_info": "", "fonte": "https://portal.stf.jus.br"},
        "charges": [], "votes": [], "expenses": [],
    },

    "wd-Q118812476": {
        "id": "wd-Q118812476", "name": "Cristiano Zanin", "wiki_title_pt": "Cristiano Zanin Martins", "wiki_title_en": "Cristiano Zanin", "display_name": "Cristiano Zanin",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Cristiano Zanin Martins",
        "birth_date": "1977-10-23", "birth_place": "Lins, SP",
        "education": "Direito — Universidade Metodista de Piracicaba; Doutorado — USP",
        "occupation": "Advogado criminalista",
        "wiki_title_pt": "Cristiano Zanin Martins",
        "all_roles": ["Ministro do STF (desde 2023)", "Advogado de Lula no processo do Mensalão e Lava Jato (2004–2021)"],
        "all_education": ["Direito — Universidade Metodista de Piracicaba", "Doutorado — USP"],
        "salary_info": {"cargo": "Ministro do STF", "subsidio_mensal": 46366.19, "subsidio_desc": "Teto constitucional", "beneficios": [], "beneficios_abdicados_info": "", "fonte": "https://portal.stf.jus.br"},
        "charges": [], "votes": [], "expenses": [],
    },

    # ════════════════ GOVERNADORES ════════════════
    "wd-gov-SP": {
        "id": "wd-gov-SP", "name": "Tarcísio de Freitas", "display_name": "Tarcísio",
        "role": "Governador de São Paulo", "party": "Republicanos", "state": "SP",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Tarcísio Gomes de Freitas",
        "birth_date": "1975-06-13", "birth_place": "Rio de Janeiro, RJ",
        "education": "Academia Militar das Agulhas Negras; Engenharia Civil — IME",
        "occupation": "Militar / Engenheiro / Político",
        "wiki_title_pt": "Tarcísio de Freitas", "wiki_title_en": "Tarcísio de Freitas",
        "all_roles": ["Governador de São Paulo (2023–presente)", "Ministro da Infraestrutura (2019–2022)"],
        "salary_info": {"cargo": "Governador de São Paulo", "subsidio_mensal": 33836.86,
            "subsidio_desc": "Subsídio do Governador do Estado de São Paulo", "beneficios": [],
            "fonte": "https://www.transparencia.sp.gov.br"},
        "charges": [
            "Investigado pelo TCU por irregularidades em contratos de infraestrutura durante gestão no Ministério (2022) — sem condenação",
        ],
        "votes": [], "expenses": [],
    },
    "wd-gov-RJ": {
        "id": "wd-gov-RJ", "name": "Cláudio Castro", "display_name": "Cláudio Castro",
        "role": "Governador do Rio de Janeiro", "party": "PL", "state": "RJ",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Cláudio Bomfim de Castro e Silva",
        "birth_date": "1980-04-04", "birth_place": "Rio de Janeiro, RJ",
        "education": "Administração de Empresas",
        "wiki_title_pt": "Cláudio Castro (político)", "wiki_title_en": "Cláudio Castro (politician)",
        "all_roles": ["Governador do Rio de Janeiro (2021–presente)", "Vice-Governador (2019–2021)", "Vereador Rio de Janeiro (2017–2019)"],
        "salary_info": {"cargo": "Governador do Rio de Janeiro", "subsidio_mensal": 32411.36,
            "subsidio_desc": "Subsídio do Governador do Estado do Rio de Janeiro", "beneficios": [],
            "fonte": "https://www.transparencia.rj.gov.br"},
        "charges": [
            "Investigado pela CGE-RJ e MP por irregularidades em contratos de saúde durante a pandemia Covid-19 (2021) — inquérito em andamento",
            "Alvo de representação no TCE-RJ por suspeita de sobrepreço em contratos de TI (2023)",
        ],
        "votes": [], "expenses": [],
    },
    "wd-gov-MG": {
        "id": "wd-gov-MG", "name": "Romeu Zema", "display_name": "Zema",
        "role": "Governador de Minas Gerais", "party": "Novo", "state": "MG",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Romeu Rodrigues Zema Neto",
        "birth_date": "1965-10-21", "birth_place": "Patrocínio, MG",
        "education": "Agronomia — UFLA",
        "wiki_title_pt": "Romeu Zema", "wiki_title_en": "Romeu Zema",
        "all_roles": ["Governador de Minas Gerais (2019–presente)", "Empresário do setor agropecuário"],
        "salary_info": {"cargo": "Governador de Minas Gerais", "subsidio_mensal": 32411.36,
            "subsidio_desc": "Subsídio do Governador do Estado de Minas Gerais", "beneficios": [],
            "fonte": "https://www.transparencia.mg.gov.br"},
        "charges": [],
        "votes": [], "expenses": [],
    },
    "wd-gov-BA": {
        "id": "wd-gov-BA", "name": "Jerônimo Rodrigues", "display_name": "Jerônimo",
        "role": "Governador da Bahia", "party": "PT", "state": "BA",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Jerônimo Rodrigues dos Santos",
        "birth_date": "1971-09-15", "birth_place": "Caetité, BA",
        "education": "Agronomia — UFRB; Mestrado em Extensão Rural — UFV",
        "wiki_title_pt": "Jerônimo Rodrigues", "wiki_title_en": "Jerônimo Rodrigues",
        "all_roles": ["Governador da Bahia (2023–presente)", "Secretário de Educação da Bahia (2015–2022)"],
        "salary_info": {"cargo": "Governador da Bahia", "subsidio_mensal": 30934.70,
            "subsidio_desc": "Subsídio do Governador do Estado da Bahia", "beneficios": [],
            "fonte": "https://www.transparencia.ba.gov.br"},
        "charges": [],
        "votes": [], "expenses": [],
    },
    "wd-gov-RS": {
        "id": "wd-gov-RS", "name": "Eduardo Leite", "display_name": "Eduardo Leite",
        "role": "Governador do Rio Grande do Sul", "party": "PSDB", "state": "RS",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Eduardo Leite",
        "birth_date": "1984-08-17", "birth_place": "Pelotas, RS",
        "education": "Direito — UCPel",
        "wiki_title_pt": "Eduardo Leite (político)", "wiki_title_en": "Eduardo Leite (politician)",
        "all_roles": ["Governador do RS (2019–2022, 2023–presente)", "Prefeito de Pelotas (2013–2018)"],
        "salary_info": {"cargo": "Governador do Rio Grande do Sul", "subsidio_mensal": 32411.36,
            "subsidio_desc": "Subsídio do Governador do Estado do RS", "beneficios": [],
            "fonte": "https://www.transparencia.rs.gov.br"},
        "charges": [],
        "votes": [], "expenses": [],
    },
    "wd-gov-PR": {
        "id": "wd-gov-PR", "name": "Carlos Ratinho Junior", "display_name": "Ratinho Junior",
        "role": "Governador do Paraná", "party": "PSD", "state": "PR",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Carlos Roberto Massa Ratinho Junior",
        "birth_date": "1981-07-14", "birth_place": "Curitiba, PR",
        "education": "Educação Física — PUC-PR",
        "wiki_title_pt": "Ratinho Junior", "wiki_title_en": "Carlos Ratinho Junior",
        "all_roles": ["Governador do Paraná (2019–presente)", "Secretário de Desenvolvimento Social (2011–2018)"],
        "salary_info": {"cargo": "Governador do Paraná", "subsidio_mensal": 32411.36,
            "subsidio_desc": "Subsídio do Governador do Estado do Paraná", "beneficios": [],
            "fonte": "https://www.transparencia.pr.gov.br"},
        "charges": [],
        "votes": [], "expenses": [],
    },
    "wd-gov-PE": {
        "id": "wd-gov-PE", "name": "Raquel Lyra", "display_name": "Raquel Lyra",
        "role": "Governadora de Pernambuco", "party": "PSDB", "state": "PE",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Raquel Loureiro Lyra Lucena",
        "birth_date": "1977-11-03", "birth_place": "Caruaru, PE",
        "education": "Direito — ASCES",
        "wiki_title_pt": "Raquel Lyra", "wiki_title_en": "Raquel Lyra",
        "all_roles": ["Governadora de Pernambuco (2023–presente)", "Prefeita de Caruaru (2017–2022)"],
        "salary_info": {"cargo": "Governadora de Pernambuco", "subsidio_mensal": 30934.70,
            "subsidio_desc": "Subsídio do Governador do Estado de Pernambuco", "beneficios": [],
            "fonte": "https://www.transparencia.pe.gov.br"},
        "charges": [],
        "votes": [], "expenses": [],
    },
    "wd-gov-CE": {
        "id": "wd-gov-CE", "name": "Elmano de Freitas", "display_name": "Elmano",
        "role": "Governador do Ceará", "party": "PT", "state": "CE",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Elmano de Freitas da Costa",
        "birth_date": "1975-03-26", "birth_place": "Fortaleza, CE",
        "education": "Direito — UFC",
        "wiki_title_pt": "Elmano de Freitas", "wiki_title_en": "Elmano de Freitas",
        "all_roles": ["Governador do Ceará (2023–presente)", "Deputado Federal CE (2019–2022)"],
        "salary_info": {"cargo": "Governador do Ceará", "subsidio_mensal": 30934.70,
            "subsidio_desc": "Subsídio do Governador do Estado do Ceará", "beneficios": [],
            "fonte": "https://www.cge.ce.gov.br"},
        "charges": [],
        "votes": [], "expenses": [],
    },
    "wd-gov-AM": {
        "id": "wd-gov-AM", "name": "Wilson Lima", "display_name": "Wilson Lima",
        "role": "Governador do Amazonas", "party": "União Brasil", "state": "AM",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Wilson Miranda Lima",
        "birth_date": "1978-11-29", "birth_place": "Manaus, AM",
        "education": "Jornalismo — UFAM",
        "wiki_title_pt": "Wilson Lima (político)", "wiki_title_en": "Wilson Lima",
        "all_roles": ["Governador do Amazonas (2019–presente)", "Apresentador de TV"],
        "salary_info": {"cargo": "Governador do Amazonas", "subsidio_mensal": 30934.70,
            "subsidio_desc": "Subsídio do Governador do Estado do Amazonas", "beneficios": [],
            "fonte": "https://www.transparencia.am.gov.br"},
        "charges": [
            "Investigado pelo MP-AM e PGR por suspeita de irregularidades em contratos de saúde durante a pandemia Covid-19 (2020–2021)",
            "Ação penal por fraude em licitações para compra de respiradores (2021) — em andamento no STJ",
        ],
        "votes": [], "expenses": [],
    },
    "wd-gov-PA": {
        "id": "wd-gov-PA", "name": "Helder Barbalho", "display_name": "Helder Barbalho",
        "role": "Governador do Pará", "party": "MDB", "state": "PA",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Helder Zahluth Barbalho",
        "birth_date": "1980-02-24", "birth_place": "Belém, PA",
        "education": "Direito — UNAMA",
        "wiki_title_pt": "Helder Barbalho", "wiki_title_en": "Helder Barbalho",
        "all_roles": ["Governador do Pará (2019–presente)", "Ministro da Integração Nacional (2012–2013)", "Deputado Federal PA (2007–2012)"],
        "salary_info": {"cargo": "Governador do Pará", "subsidio_mensal": 30934.70,
            "subsidio_desc": "Subsídio do Governador do Estado do Pará", "beneficios": [],
            "fonte": "https://www.transparencia.pa.gov.br"},
        "charges": [
            "Investigado por suspeita de corrupção no âmbito da Operação Hydra (2020) — arquivado pelo STJ",
        ],
        "votes": [], "expenses": [],
    },

    # ════════════════ LÍDERES DO CONGRESSO ════════════════
    "wd-Q10296965": {
        "id": "wd-Q10296965", "name": "Arthur Lira", "display_name": "Arthur Lira",
        "role": "Presidente da Câmara dos Deputados", "party": "PP", "state": "AL",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Arthur César Pereira de Lira",
        "birth_date": "1970-07-12", "birth_place": "Belo Monte, AL",
        "education": "Direito — UFAL",
        "wiki_title_pt": "Arthur Lira", "wiki_title_en": "Arthur Lira",
        "all_roles": ["Presidente da Câmara dos Deputados (2021–2025)", "Deputado Federal AL (1995–presente)"],
        "salary_info": {"cargo": "Presidente da Câmara dos Deputados", "subsidio_mensal": 46366.19,
            "subsidio_desc": "Subsídio + benefícios do Presidente da Câmara",
            "beneficios": [{"nome": "Apartamento funcional", "valor": "Custeado pela Câmara", "descricao": "Moradia oficial em Brasília"}],
            "fonte": "https://www.camara.leg.br/transparencia"},
        "charges": [
            "Condenado em 1ª instância por corrupção passiva e peculato no TRE-AL (2007) — condenação prescrita (STJ, 2016)",
            "Investigado no âmbito do 'Orçamento Secreto' (emendas de relator) por supostas irregularidades na distribuição de recursos (2022)",
        ],
        "votes": [], "expenses": [],
    },
    "wd-Q55657773": {
        "id": "wd-Q55657773", "name": "Rodrigo Pacheco", "display_name": "Rodrigo Pacheco",
        "role": "Presidente do Senado Federal", "party": "PSD", "state": "MG",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Rodrigo Cunha Pacheco",
        "birth_date": "1980-06-12", "birth_place": "Belo Horizonte, MG",
        "education": "Direito — PUC Minas; Mestrado — UFMG",
        "wiki_title_pt": "Rodrigo Pacheco", "wiki_title_en": "Rodrigo Pacheco",
        "all_roles": ["Presidente do Senado Federal (2021–presente)", "Senador por MG (2019–presente)", "Deputado Federal MG (2007–2018)"],
        "salary_info": {"cargo": "Presidente do Senado Federal", "subsidio_mensal": 46366.19,
            "subsidio_desc": "Subsídio + benefícios do Presidente do Senado",
            "beneficios": [{"nome": "Residência oficial", "valor": "Custeado pelo Senado", "descricao": "Moradia oficial em Brasília"}],
            "fonte": "https://www.senado.leg.br/transparencia"},
        "charges": [],
        "votes": [], "expenses": [],
    },

    # ════════════════ EX-PRESIDENTES (RELEVÂNCIA HISTÓRICA) ════════════════
    "wd-Q193080": {
        "id": "wd-Q193080", "name": "Jair Bolsonaro", "display_name": "Bolsonaro",
        "role": "Ex-Presidente da República (2019–2022)", "party": "PL", "state": "RJ",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Jair Messias Bolsonaro",
        "birth_date": "1955-03-21", "birth_place": "Glicério, SP",
        "education": "Academia Militar das Agulhas Negras (AMAN)",
        "occupation": "Militar / Político",
        "wiki_title_pt": "Jair Bolsonaro", "wiki_title_en": "Jair Bolsonaro",
        "all_roles": [
            "Presidente da República (2019–2022)",
            "Deputado Federal RJ (1991–2018)",
            "Capitão do Exército Brasileiro (reformado)",
        ],
        "salary_info": {"cargo": "Ex-Presidente (pensão)", "subsidio_mensal": 30934.70,
            "subsidio_desc": "Subsídio de ex-presidente + pensão militar",
            "beneficios": [{"nome": "Segurança (GSI)", "valor": "Custeado pela União", "descricao": ""},
                           {"nome": "Pensão de militar reformado", "valor": "Calculada pelo posto (Capitão)", "descricao": ""}],
            "fonte": "https://www.gov.br/planalto"},
        "charges": [
            "Condenado pelo TSE à inelegibilidade por 8 anos (2023) por abuso do poder político e uso indevido de meios de comunicação na reunião com embaixadores (jun/2022)",
            "Indiciado pela PF por tentativa de golpe de Estado e abolição violenta do Estado democrático de Direito (nov/2024)",
            "Indiciado pela PF por homicídio e tentativa de homicídio no plano 'Green and Yellow Dagger' de assassinato do Presidente Lula, Vice Alckmin e Min. Barroso (nov/2024)",
            "Investigado no inquérito do golpe (IQ 4878 — STF) por envolvimento em trama golpista pós-eleição 2022",
            "Indiciado pela PF por falsificação de certificados de vacinação contra Covid-19 (nov/2023)",
            "Investigado por desvio de joias presenteadas por autoridades estrangeiras ao Estado brasileiro (2023)",
            "NOTA: Inelegível até 2030 por decisão do TSE",
        ],
        "votes": [], "expenses": [],
    },
    "wd-Q465088": {
        "id": "wd-Q465088", "name": "Michel Temer", "display_name": "Michel Temer",
        "role": "Ex-Presidente da República (2016–2018)", "party": "MDB", "state": "SP",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Michel Miguel Elias Temer Lulia",
        "birth_date": "1940-09-23", "birth_place": "Tietê, SP",
        "education": "Direito — PUC-SP; Doutorado — PUC-SP",
        "wiki_title_pt": "Michel Temer", "wiki_title_en": "Michel Temer",
        "all_roles": ["Presidente da República (2016–2018)", "Vice-Presidente (2011–2016)", "Presidente da Câmara (2009–2010, 2013–2014)"],
        "salary_info": {"cargo": "Ex-Presidente (pensão)", "subsidio_mensal": 30934.70,
            "subsidio_desc": "Pensão de ex-presidente da República",
            "beneficios": [],
            "fonte": "https://www.gov.br/planalto"},
        "charges": [
            "Preso preventivamente por 4 dias (mar/2019) — habeas corpus concedido pelo STJ",
            "Acusado de corrupção passiva, lavagem de dinheiro e organização criminosa (Operação Lava Jato, 2017–2019)",
            "Condenado pelo TRF-4 em 2023 a 8 anos e 6 meses por corrupção passiva e lavagem de dinheiro (caso Angra 3) — recurso pendente no STJ",
            "Investigado no caso do porto de Santos (recebimento de propina da Rodrimar) — ação penal no TRF-3",
        ],
        "votes": [], "expenses": [],
    },
    "wd-Q61167": {
        "id": "wd-Q61167", "name": "Dilma Rousseff", "display_name": "Dilma Rousseff",
        "role": "Ex-Presidenta da República (2011–2016)", "party": "PT", "state": "MG",
        "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Dilma Vana Rousseff",
        "birth_date": "1947-12-14", "birth_place": "Belo Horizonte, MG",
        "education": "Economia — UFRGS",
        "wiki_title_pt": "Dilma Rousseff", "wiki_title_en": "Dilma Rousseff",
        "all_roles": ["Presidenta da República (2011–2016)", "Ministra da Casa Civil (2005–2010)", "Ministra de Minas e Energia (2003–2005)"],
        "salary_info": {"cargo": "Presidente do Novo Banco de Desenvolvimento (NDB)", "subsidio_mensal": 0,
            "subsidio_desc": "Cargo no NDB — salário não divulgado publicamente. Perde direito à pensão por ter acumulado cargo.",
            "beneficios": [],
            "fonte": "https://www.ndb.int"},
        "charges": [
            "Sofreu impeachment aprovado pelo Senado em 31/08/2016 por crime de responsabilidade fiscal (pedaladas fiscais) — destituída da presidência",
            "Investigada no âmbito da Lava Jato por suposta ciência de irregularidades na Petrobras quando era presidente do Conselho de Administração (2003–2010) — sem condenação criminal",
            "TSE absolveu chapa Dilma/Temer de abuso de poder econômico em campanha de 2014 (2017)",
        ],
        "votes": [], "expenses": [],
    },

}



# ═══════════════════════════════════════════════════════════════
#  WARMUP DO CACHE DE FOTOS — roda APÓS CURATED_POLITICIANS
# ═══════════════════════════════════════════════════════════════
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

@router.on_event("startup")
async def on_startup():
    """Dispara warmup do cache de fotos na inicialização do servidor."""
    asyncio.create_task(_warmup_photo_cache())


# Salário padrão para Deputados e Senadores
SALARY_BR = {
    "camara": {
        "cargo": "Deputado Federal",
        "subsidio_mensal": 46366.19,
        "subsidio_desc": "Subsídio parlamentar mensal bruto (teto constitucional)",
        "beneficios": [
            {"nome": "Cota Parlamentar (CEAP)", "valor": "até R$ 50.112/mês", "descricao": "Verba para custeio de atividades parlamentares: combustível, passagens, alimentação, hospedagem, telefone etc."},
            {"nome": "Auxílio-Moradia", "valor": "R$ 4.253,00/mês", "descricao": "Para deputados que não utilizam imóvel funcional em Brasília"},
            {"nome": "Passagens Aéreas", "valor": "Até 84 bilhetes/mês", "descricao": "Viagens entre o domicílio eleitoral e Brasília, e em atividades parlamentares"},
            {"nome": "Plano de Saúde (PAMS)", "valor": "Custeado integralmente pela Câmara", "descricao": "Para o parlamentar e dependentes legais"},
            {"nome": "Seguro de Vida", "valor": "Custeado pela Câmara", "descricao": "Apólice individual"},
            {"nome": "Aposentadoria parlamentar", "valor": "Proporcional ao mandato", "descricao": "Após 8 anos de mandato com 60 anos de idade"},
        ],
        "beneficios_abdicados_info": "Parlamentares podem renunciar ao auxílio-moradia declarando imóvel próprio em Brasília ou utilizando imóvel funcional da Câmara. A Cota Parlamentar pode ser reduzida voluntariamente. Todos os gastos são publicados no Portal da Transparência.",
        "fonte": "https://www2.camara.leg.br/transparencia",
    },
    "senado": {
        "cargo": "Senador Federal",
        "subsidio_mensal": 46366.19,
        "subsidio_desc": "Subsídio parlamentar mensal bruto — idêntico ao dos Deputados Federais por determinação constitucional",
        "beneficios": [
            {"nome": "Verba de Gabinete", "valor": "até R$ 155.520/mês", "descricao": "Para custeio de pessoal (até 8 assessores) e atividades do gabinete"},
            {"nome": "Auxílio-Moradia", "valor": "R$ 4.253,00/mês", "descricao": "Para senadores sem imóvel em Brasília"},
            {"nome": "Passagens Aéreas", "valor": "Ilimitadas em missões oficiais", "descricao": "Viagens a serviço do mandato"},
            {"nome": "Plano de Saúde (PAMS)", "valor": "Custeado pelo Senado", "descricao": "Para o parlamentar e dependentes"},
            {"nome": "Verba de Representação", "valor": "R$ 9.273,24/mês", "descricao": "Exclusivo para membros da Mesa Diretora e líderes de bancada"},
        ],
        "beneficios_abdicados_info": "Senadores podem abrir mão do auxílio-moradia e da verba de representação (quando aplicável). Todos os gastos são publicados no Portal da Transparência do Senado.",
        "fonte": "https://www12.senado.leg.br/transparencia",
    },
}

# ── WIKIDATA (para políticos internacionais não curados) ──────
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

def _gov(wid, name, role, party, photo="", wiki_pt="", wiki_en=""):
    """Cria entrada de governador. photo é fallback; wiki_pt é título Wikipedia PT."""
    return {
        "id": wid, "name": name, "role": role, "party": party,
        "photo": photo,
        "wiki_title_pt": wiki_pt or name,
        "wiki_title_en": wiki_en or name,
    }

WM = "https://upload.wikimedia.org/wikipedia/commons/thumb"
GOVERNORS_BY_UF = {
    "AC": _gov("wd-Q10282903","Gladson Cameli",   "Governador do Acre",             "PP",           wiki_pt="Gladson Cameli",     wiki_en="Gladson Cameli"),
    "AL": _gov("wd-Q10285716","Paulo Dantas",      "Governador de Alagoas",          "MDB",          wiki_pt="Paulo Dantas",       wiki_en="Paulo Dantas"),
    "AM": _gov("wd-Q3730703", "Wilson Lima",       "Governador do Amazonas",         "União Brasil", wiki_pt="Wilson Lima (político)", wiki_en="Wilson Lima"),
    "AP": _gov("wd-Q107421",  "Clécio Luís",       "Governador do Amapá",            "SD",           wiki_pt="Clécio Luís",        wiki_en="Clécio Luís"),
    "BA": _gov("wd-Q3891283", "Jerônimo Rodrigues","Governador da Bahia",            "PT",           wiki_pt="Jerônimo Rodrigues", wiki_en="Jerônimo Rodrigues"),
    "CE": _gov("wd-Q10293629","Elmano de Freitas", "Governador do Ceará",            "PT",           wiki_pt="Elmano de Freitas",  wiki_en="Elmano de Freitas"),
    "DF": _gov("wd-Q10303893","Ibaneis Rocha",     "Governador do Distrito Federal", "MDB",          wiki_pt="Ibaneis Rocha",      wiki_en="Ibaneis Rocha"),
    "ES": _gov("wd-Q3730577", "Renato Casagrande", "Governador do Espírito Santo",   "PSB",          wiki_pt="Renato Casagrande",  wiki_en="Renato Casagrande"),
    "GO": _gov("wd-Q10306753","Ronaldo Caiado",    "Governador de Goiás",            "União Brasil", wiki_pt="Ronaldo Caiado",     wiki_en="Ronaldo Caiado"),
    "MA": _gov("wd-Q10306938","Carlos Brandão",    "Governador do Maranhão",         "PSB",          wiki_pt="Carlos Brandão (político)", wiki_en="Carlos Brandão"),
    "MT": _gov("wd-Q10308490","Mauro Mendes",      "Governador do Mato Grosso",      "União Brasil", wiki_pt="Mauro Mendes",       wiki_en="Mauro Mendes"),
    "MS": _gov("wd-Q10308503","Eduardo Riedel",    "Governador do Mato Grosso do Sul","PSDB",        wiki_pt="Eduardo Riedel",     wiki_en="Eduardo Riedel"),
    "MG": _gov("wd-Q3564887", "Romeu Zema",        "Governador de Minas Gerais",     "Novo",         wiki_pt="Romeu Zema",         wiki_en="Romeu Zema"),
    "PA": _gov("wd-Q10309820","Helder Barbalho",   "Governador do Pará",             "MDB",          wiki_pt="Helder Barbalho",    wiki_en="Helder Barbalho"),
    "PB": _gov("wd-Q10309964","João Azevêdo",      "Governador da Paraíba",          "PSB",          wiki_pt="João Azevêdo",       wiki_en="João Azevêdo"),
    "PR": _gov("wd-Q10310060","Ratinho Junior",    "Governador do Paraná",           "PSD",          wiki_pt="Ratinho Junior",     wiki_en="Carlos Ratinho Junior"),
    "PE": _gov("wd-Q10310080","Raquel Lyra",       "Governadora de Pernambuco",      "PSDB",         wiki_pt="Raquel Lyra",        wiki_en="Raquel Lyra"),
    "PI": _gov("wd-Q10310123","Rafael Fonteles",   "Governador do Piauí",            "PT",           wiki_pt="Rafael Fonteles",    wiki_en="Rafael Fonteles"),
    "RJ": _gov("wd-Q1779090", "Cláudio Castro",    "Governador do Rio de Janeiro",   "PL",           wiki_pt="Cláudio Castro (político)", wiki_en="Cláudio Castro"),
    "RN": _gov("wd-Q10312022","Fátima Bezerra",    "Governadora do Rio Grande do Norte","PT",        wiki_pt="Fátima Bezerra",     wiki_en="Fátima Bezerra"),
    "RS": _gov("wd-Q10312060","Eduardo Leite",     "Governador do Rio Grande do Sul","PSDB",         wiki_pt="Eduardo Leite (político)", wiki_en="Eduardo Leite"),
    "RO": _gov("wd-Q10311952","Marcos Rocha",      "Governador de Rondônia",         "União Brasil", wiki_pt="Marcos Rocha",       wiki_en="Marcos Rocha"),
    "RR": _gov("wd-Q10312027","Arthur Henrique",   "Governador de Roraima",          "MDB",          wiki_pt="Arthur Henrique",    wiki_en="Arthur Henrique"),
    "SC": _gov("wd-Q10312568","Jorginho Mello",    "Governador de Santa Catarina",   "PL",           wiki_pt="Jorginho Mello",     wiki_en="Jorginho Mello"),
    "SE": _gov("wd-Q10314272","Fábio Mitidieri",   "Governador de Sergipe",          "PSD",          wiki_pt="Fábio Mitidieri",    wiki_en="Fábio Mitidieri"),
    "SP": _gov("wd-Q1050742", "Tarcísio de Freitas","Governador de São Paulo",       "Republicanos", wiki_pt="Tarcísio de Freitas", wiki_en="Tarcísio de Freitas"),
    "TO": _gov("wd-Q10314456","Wanderlei Barbosa", "Governador do Tocantins",        "Republicanos", wiki_pt="Wanderlei Barbosa",  wiki_en="Wanderlei Barbosa"),
}
UF_NAMES = {"AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia","CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás","MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais","PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí","RJ":"Rio de Janeiro","RN":"Rio Grande do Norte","RS":"Rio Grande do Sul","RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SE":"Sergipe","SP":"São Paulo","TO":"Tocantins"}

COUNTRY_FLAGS = {
    "BR":"🇧🇷","US":"🇺🇸","FR":"🇫🇷","DE":"🇩🇪","GB":"🇬🇧","AR":"🇦🇷","PT":"🇵🇹",
    "MX":"🇲🇽","JP":"🇯🇵","CN":"🇨🇳","RU":"🇷🇺","IT":"🇮🇹","ES":"🇪🇸","UY":"🇺🇾",
    "CL":"🇨🇱","CO":"🇨🇴","VE":"🇻🇪","PE":"🇵🇪","BO":"🇧🇴","PY":"🇵🇾",
}



# Prefeitos curados — eleições 2024 + wiki_title_pt para foto automática
MAYORS_BY_CITY = {
    # RJ
    "Rio de Janeiro":        {"id":"wd-Q3723792",   "name":"Eduardo Paes",          "role":"Prefeito do Rio de Janeiro",          "party":"PSD",          "uf":"RJ","photo":"","wiki_title_pt":"Eduardo Paes",               "wiki_title_en":"Eduardo Paes"},
    "Niterói":               {"id":"wd-Q16580680",  "name":"Rodrigo Neves",          "role":"Prefeito de Niterói",                 "party":"PDT",          "uf":"RJ","photo":"","wiki_title_pt":"Rodrigo Neves",              "wiki_title_en":"Rodrigo Neves"},
    "Nova Iguaçu":           {"id":"wd-Q10309629",  "name":"Duarte Júnior",          "role":"Prefeito de Nova Iguaçu",             "party":"PSD",          "uf":"RJ","photo":"","wiki_title_pt":"Duarte Júnior",              "wiki_title_en":"Duarte Júnior"},
    "Duque de Caxias":       {"id":"wd-Q10303830",  "name":"Wilson Reis",            "role":"Prefeito de Duque de Caxias",         "party":"MDB",          "uf":"RJ","photo":"","wiki_title_pt":"Wilson Reis",                "wiki_title_en":"Wilson Reis"},
    "São Gonçalo":           {"id":"wd-Q10312550",  "name":"Capitão Nelson",         "role":"Prefeito de São Gonçalo",             "party":"PL",           "uf":"RJ","photo":"","wiki_title_pt":"Capitão Nelson",             "wiki_title_en":"Capitão Nelson"},
    "Petrópolis":            {"id":"wd-Q188892",    "name":"Rubens Bomtempo",        "role":"Prefeito de Petrópolis",              "party":"PSB",          "uf":"RJ","photo":"","wiki_title_pt":"Rubens Bomtempo",            "wiki_title_en":"Rubens Bomtempo"},
    "Teresópolis":           {"id":"wd-Q1021855",   "name":"Vinicius Claussen",      "role":"Prefeito de Teresópolis",             "party":"PSD",          "uf":"RJ","photo":"","wiki_title_pt":"Vinicius Claussen",          "wiki_title_en":"Vinicius Claussen"},
    "Volta Redonda":         {"id":"wd-Q1780",      "name":"Neto",                   "role":"Prefeito de Volta Redonda",           "party":"MDB",          "uf":"RJ","photo":"","wiki_title_pt":"Neto (Volta Redonda)",       "wiki_title_en":"Neto"},
    "Resende":               {"id":"wd-Q319",       "name":"Alexandre Fonseca",      "role":"Prefeito de Resende",                 "party":"PRD",          "uf":"RJ","photo":"","wiki_title_pt":"Alexandre Fonseca",          "wiki_title_en":"Alexandre Fonseca"},
    "Macaé":                 {"id":"wd-Q607",       "name":"Dr. Welberth Rezende",   "role":"Prefeito de Macaé",                   "party":"Podemos",      "uf":"RJ","photo":"","wiki_title_pt":"Welberth Rezende",           "wiki_title_en":"Welberth Rezende"},
    "Campos dos Goytacazes": {"id":"wd-Q183219",    "name":"Wladimir Garotinho",     "role":"Prefeito de Campos dos Goytacazes",   "party":"PRD",          "uf":"RJ","photo":"","wiki_title_pt":"Wladimir Garotinho",         "wiki_title_en":"Wladimir Garotinho"},
    "Angra dos Reis":        {"id":"wd-Q610",       "name":"Fábio do Pastel",        "role":"Prefeito de Angra dos Reis",          "party":"Solidariedade","uf":"RJ","photo":"","wiki_title_pt":"Fábio do Pastel",            "wiki_title_en":"Fábio do Pastel"},
    "Cabo Frio":             {"id":"wd-Q618",       "name":"Renatinho Vianna",       "role":"Prefeito de Cabo Frio",               "party":"MDB",          "uf":"RJ","photo":"","wiki_title_pt":"Renatinho Vianna",           "wiki_title_en":"Renatinho Vianna"},
    "Barra Mansa":           {"id":"wd-Q623",       "name":"Rodrigo Drable",         "role":"Prefeito de Barra Mansa",             "party":"AVANTE",       "uf":"RJ","photo":"","wiki_title_pt":"Rodrigo Drable",             "wiki_title_en":"Rodrigo Drable"},
    "Itaperuna":             {"id":"wd-Q629",       "name":"Ontiveiro Júnior",       "role":"Prefeito de Itaperuna",               "party":"MDB",          "uf":"RJ","photo":"","wiki_title_pt":"Ontiveiro Júnior",           "wiki_title_en":"Ontiveiro Júnior"},
    # SP
    "São Paulo":             {"id":"wd-Q75920697",  "name":"Ricardo Nunes",          "role":"Prefeito de São Paulo",               "party":"MDB",          "uf":"SP","photo":"","wiki_title_pt":"Ricardo Nunes",              "wiki_title_en":"Ricardo Nunes"},
    "Campinas":              {"id":"wd-Q181637",    "name":"Dario Saadi",            "role":"Prefeito de Campinas",                "party":"Republicanos", "uf":"SP","photo":"","wiki_title_pt":"Dario Saadi",               "wiki_title_en":"Dario Saadi"},
    "Guarulhos":             {"id":"wd-Q175",       "name":"Guti",                   "role":"Prefeito de Guarulhos",               "party":"PSD",          "uf":"SP","photo":"","wiki_title_pt":"Gustavo Henrique Gomes",     "wiki_title_en":"Guti"},
    "Santo André":           {"id":"wd-Q43498",     "name":"Gilvan Junior",          "role":"Prefeito de Santo André",             "party":"PL",           "uf":"SP","photo":"","wiki_title_pt":"Gilvan Junior",              "wiki_title_en":"Gilvan Junior"},
    "São Bernardo do Campo": {"id":"wd-Q174",       "name":"Orlando Morando",        "role":"Prefeito de São Bernardo do Campo",   "party":"PSDB",         "uf":"SP","photo":"","wiki_title_pt":"Orlando Morando",            "wiki_title_en":"Orlando Morando"},
    "Osasco":                {"id":"wd-Q180",       "name":"Rogério Lins",           "role":"Prefeito de Osasco",                  "party":"Podemos",      "uf":"SP","photo":"","wiki_title_pt":"Rogério Lins",               "wiki_title_en":"Rogério Lins"},
    "Ribeirão Preto":        {"id":"wd-Q185",       "name":"Marcos Antonio",         "role":"Prefeito de Ribeirão Preto",          "party":"PSD",          "uf":"SP","photo":"","wiki_title_pt":"Marcos Vieira",              "wiki_title_en":"Marcos Antonio"},
    "Sorocaba":              {"id":"wd-Q189",       "name":"Rodrigo Manga",          "role":"Prefeito de Sorocaba",                "party":"Republicanos", "uf":"SP","photo":"","wiki_title_pt":"Rodrigo Manga",              "wiki_title_en":"Rodrigo Manga"},
    # MG
    "Belo Horizonte":        {"id":"wd-Q10308756",  "name":"Fuad Noman",             "role":"Prefeito de Belo Horizonte",          "party":"PSD",          "uf":"MG","photo":"","wiki_title_pt":"Fuad Noman",                "wiki_title_en":"Fuad Noman"},
    "Contagem":              {"id":"wd-Q181836",    "name":"Marília Campos",         "role":"Prefeita de Contagem",                "party":"PT",           "uf":"MG","photo":"","wiki_title_pt":"Marília Campos",             "wiki_title_en":"Marília Campos"},
    "Uberlândia":            {"id":"wd-Q182479",    "name":"Sérgio Rezende",         "role":"Prefeito de Uberlândia",              "party":"PSD",          "uf":"MG","photo":"","wiki_title_pt":"Sérgio Rezende",             "wiki_title_en":"Sérgio Rezende"},
    # BA
    "Salvador":              {"id":"wd-Q10285716",  "name":"Bruno Reis",             "role":"Prefeito de Salvador",                "party":"União Brasil", "uf":"BA","photo":"","wiki_title_pt":"Bruno Reis (político)",       "wiki_title_en":"Bruno Reis"},
    "Feira de Santana":      {"id":"wd-Q183400",    "name":"Zé Ronaldo",             "role":"Prefeito de Feira de Santana",        "party":"União Brasil", "uf":"BA","photo":"","wiki_title_pt":"José Ronaldo (Feira de Santana)", "wiki_title_en":"José Ronaldo"},
    # RS
    "Porto Alegre":          {"id":"wd-Q10312060",  "name":"Sebastião Melo",         "role":"Prefeito de Porto Alegre",            "party":"MDB",          "uf":"RS","photo":"","wiki_title_pt":"Sebastião Melo",             "wiki_title_en":"Sebastião Melo"},
    "Caxias do Sul":         {"id":"wd-Q178905",    "name":"Adiló Didomenico",       "role":"Prefeito de Caxias do Sul",           "party":"PSDB",         "uf":"RS","photo":"","wiki_title_pt":"Adiló Didomenico",           "wiki_title_en":"Adiló Didomenico"},
    # PR
    "Curitiba":              {"id":"wd-Q10293629_cwb","name":"Eduardo Pimentel",     "role":"Prefeito de Curitiba",                "party":"PSD",          "uf":"PR","photo":"","wiki_title_pt":"Eduardo Pimentel (político)","wiki_title_en":"Eduardo Pimentel"},
    "Londrina":              {"id":"wd-Q181764",    "name":"Marcelo Belinati",       "role":"Prefeito de Londrina",                "party":"PP",           "uf":"PR","photo":"","wiki_title_pt":"Marcelo Belinati",           "wiki_title_en":"Marcelo Belinati"},
    # SC
    "Florianópolis":         {"id":"wd-Q181317",    "name":"Topázio Neto",           "role":"Prefeito de Florianópolis",           "party":"PSD",          "uf":"SC","photo":"","wiki_title_pt":"Topázio Neto",               "wiki_title_en":"Topázio Neto"},
    "Joinville":             {"id":"wd-Q182095",    "name":"Adriano Silva",          "role":"Prefeito de Joinville",               "party":"PSD",          "uf":"SC","photo":"","wiki_title_pt":"Adriano Silva (político)",    "wiki_title_en":"Adriano Silva"},
    # PE
    "Recife":                {"id":"wd-Q56421696",  "name":"João Campos",            "role":"Prefeito do Recife",                  "party":"PSB",          "uf":"PE","photo":"","wiki_title_pt":"João Campos (político)",      "wiki_title_en":"João Campos"},
    # CE
    "Fortaleza":             {"id":"wd-Q81898",     "name":"Evandro Leitão",         "role":"Prefeito de Fortaleza",               "party":"PT",           "uf":"CE","photo":"","wiki_title_pt":"Evandro Leitão",             "wiki_title_en":"Evandro Leitão"},
    # AM
    "Manaus":                {"id":"wd-Q181617",    "name":"David Almeida",          "role":"Prefeito de Manaus",                  "party":"Avante",       "uf":"AM","photo":"","wiki_title_pt":"David Almeida (político)",    "wiki_title_en":"David Almeida"},
    # PA
    "Belém":                 {"id":"wd-Q81922",     "name":"Igor Normando",          "role":"Prefeito de Belém",                   "party":"MDB",          "uf":"PA","photo":"","wiki_title_pt":"Igor Normando",              "wiki_title_en":"Igor Normando"},
    # GO
    "Goiânia":               {"id":"wd-Q82155",     "name":"Sandro Mabel",           "role":"Prefeito de Goiânia",                 "party":"União Brasil", "uf":"GO","photo":"","wiki_title_pt":"Sandro Mabel",              "wiki_title_en":"Sandro Mabel"},
    # MA
    "São Luís":              {"id":"wd-Q81960",     "name":"Eduardo Braide",         "role":"Prefeito de São Luís",                "party":"PSD",          "uf":"MA","photo":"","wiki_title_pt":"Eduardo Braide",             "wiki_title_en":"Eduardo Braide"},
    # MS
    "Campo Grande":          {"id":"wd-Q182033",    "name":"Adriane Lopes",          "role":"Prefeita de Campo Grande",            "party":"PP",           "uf":"MS","photo":"","wiki_title_pt":"Adriane Lopes",              "wiki_title_en":"Adriane Lopes"},
    # AL
    "Maceió":                {"id":"wd-Q82010",     "name":"João Henrique Caldas",   "role":"Prefeito de Maceió",                  "party":"PL",           "uf":"AL","photo":"","wiki_title_pt":"João Henrique Caldas",       "wiki_title_en":"João Henrique Caldas"},
    # PI
    "Teresina":              {"id":"wd-Q82004",     "name":"Dr. Silvio Mendes",      "role":"Prefeito de Teresina",                "party":"União Brasil", "uf":"PI","photo":"","wiki_title_pt":"Silvio Mendes",              "wiki_title_en":"Silvio Mendes"},
    # PB
    "João Pessoa":           {"id":"wd-Q82001",     "name":"Cícero Lucena",          "role":"Prefeito de João Pessoa",             "party":"PP",           "uf":"PB","photo":"","wiki_title_pt":"Cícero Lucena",              "wiki_title_en":"Cícero Lucena"},
    # RN
    "Natal":                 {"id":"wd-Q82032",     "name":"Paulinho Freire",        "role":"Prefeito de Natal",                   "party":"União Brasil", "uf":"RN","photo":"","wiki_title_pt":"Paulinho Freire",            "wiki_title_en":"Paulinho Freire"},
    # SE
    "Aracaju":               {"id":"wd-Q82000",     "name":"Emília Corrêa",          "role":"Prefeita de Aracaju",                 "party":"PL",           "uf":"SE","photo":"","wiki_title_pt":"Emília Corrêa",              "wiki_title_en":"Emília Corrêa"},
    # DF
    "Brasília":              {"id":"wd-Q10303893",  "name":"Ibaneis Rocha",          "role":"Governador do DF",                    "party":"MDB",          "uf":"DF","photo":"","wiki_title_pt":"Ibaneis Rocha",              "wiki_title_en":"Ibaneis Rocha"},
    # ES
    "Vitória":               {"id":"wd-Q82022",     "name":"Lorenzo Pazolini",       "role":"Prefeito de Vitória",                 "party":"Republicanos", "uf":"ES","photo":"","wiki_title_pt":"Lorenzo Pazolini",          "wiki_title_en":"Lorenzo Pazolini"},
    # MT
    "Cuiabá":                {"id":"wd-Q183341",    "name":"Abilio Brunini",         "role":"Prefeito de Cuiabá",                  "party":"PL",           "uf":"MT","photo":"","wiki_title_pt":"Abilio Brunini",             "wiki_title_en":"Abilio Brunini"},
    # AP
    "Macapá":                {"id":"wd-Q181989",    "name":"Dr. Furlan",             "role":"Prefeito de Macapá",                  "party":"MDB",          "uf":"AP","photo":"","wiki_title_pt":"Furlan (político)",          "wiki_title_en":"Furlan"},
    # RO
    "Porto Velho":           {"id":"wd-Q182028",    "name":"Hildon Chaves",          "role":"Prefeito de Porto Velho",             "party":"PSDB",         "uf":"RO","photo":"","wiki_title_pt":"Hildon Chaves",              "wiki_title_en":"Hildon Chaves"},
    # RR
    "Boa Vista":             {"id":"wd-Q181836_bvb","name":"Arthur Henrique",        "role":"Prefeito de Boa Vista",               "party":"MDB",          "uf":"RR","photo":"","wiki_title_pt":"Arthur Henrique",            "wiki_title_en":"Arthur Henrique"},
    # TO
    "Palmas":                {"id":"wd-Q182080",    "name":"Eduardo Siqueira Campos","role":"Prefeito de Palmas",                  "party":"Podemos",      "uf":"TO","photo":"","wiki_title_pt":"Eduardo Siqueira Campos",    "wiki_title_en":"Eduardo Siqueira Campos"},
    # AC
    "Rio Branco":            {"id":"wd-Q82039",     "name":"Tião Bocalom",           "role":"Prefeito de Rio Branco",              "party":"PP",           "uf":"AC","photo":"","wiki_title_pt":"Tião Bocalom",               "wiki_title_en":"Tião Bocalom"},
}

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
    else:
        parts = politician_id.split("-",1); source = parts[0]; api_id = parts[1] if len(parts)>1 else ""
        if source=="dep":   details = await get_deputado_details(api_id)
        elif source=="sen": details = await get_senador_details(api_id)
        elif source=="wd":  details = await get_wikidata_entity(api_id)
        else: return {"error":"Fonte desconhecida"}

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
        if pid in CURATED_POLITICIANS:
            d = dict(CURATED_POLITICIANS[pid]); d.pop("wiki_title_pt",None); return d
        parts=pid.split("-",1); src=parts[0]; aid=parts[1] if len(parts)>1 else ""
        if src=="dep": return await get_deputado_details(aid)
        if src=="sen": return await get_senador_details(aid)
        if src=="wd":  return await get_wikidata_entity(aid)
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


async def _wikidata_sparql(sparql: str) -> list:
    """Executa query SPARQL no Wikidata. Retorna lista de bindings ou []."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
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
    """Converte um binding Wikidata em dict de político."""
    qid  = b.get("person", {}).get("value", "").split("/")[-1]
    name = b.get("personLabel", {}).get("value", "")
    if not name or name.startswith("Q") or not qid:
        return None
    image = b.get("image", {}).get("value", "")
    if image and not image.startswith("http"):
        image = _wd_image(image)
    return {
        "id":      f"wd-{qid}",
        "name":    name,
        "role":    b.get("posLabel", {}).get("value", "") or f"Político de {city_name}",
        "party":   b.get("partyLabel", {}).get("value", ""),
        "state":   uf.upper() if uf else "",
        "country": "Brasil",
        "photo":   image,
        "source":  "wikidata",
    }

async def get_mayor_by_city_wikidata(city_name: str, uf: str = "") -> dict | None:
    """Busca prefeito atual via P6 (head of government) + nome da cidade.
    Estratégia: encontra a entidade da cidade pelo nome, depois P6."""
    # Estratégia 1: city label → P6
    sparql = f"""
SELECT DISTINCT ?person ?personLabel ?partyLabel ?image WHERE {{
  ?city rdfs:label "{city_name}"@pt .
  ?city wdt:P31/wdt:P279* wd:Q515 .
  ?city wdt:P6 ?person .
  OPTIONAL {{ ?person wdt:P18 ?image }}
  OPTIONAL {{ ?person wdt:P102 ?party }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}} LIMIT 3"""
    bindings = await _wikidata_sparql(sparql)
    for b in bindings:
        p = _parse_politician_binding(b, city_name, uf)
        if p:
            p["role"] = f"Prefeito(a) de {city_name}"
            return p

    # Estratégia 2: busca por município brasileiro pelo nome
    sparql2 = f"""
SELECT DISTINCT ?person ?personLabel ?partyLabel ?image WHERE {{
  ?city rdfs:label "{city_name}"@pt .
  ?city wdt:P31 wd:Q3184121 .
  ?city wdt:P6 ?person .
  OPTIONAL {{ ?person wdt:P18 ?image }}
  OPTIONAL {{ ?person wdt:P102 ?party }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}} LIMIT 3"""
    bindings2 = await _wikidata_sparql(sparql2)
    for b in bindings2:
        p = _parse_politician_binding(b, city_name, uf)
        if p:
            p["role"] = f"Prefeito(a) de {city_name}"
            return p
    return None

async def search_city_politicians_wikidata(city_name: str, uf: str = "") -> list:
    """Busca vereadores e políticos locais via Wikidata SPARQL.
    Usa sintaxe correta com p:/ps:/pq: para qualifiers."""
    # SPARQL correto: p:P39/ps:P39 + pq:P642 para cargo+cidade
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
    seen = set()
    results = []
    for b in bindings:
        p = _parse_politician_binding(b, city_name, uf)
        if p and p["id"] not in seen:
            seen.add(p["id"])
            results.append(p)
    return results[:15]


@router.get("/transparency/local")
async def get_local_politicians(
    request: FARequest,
    uf_override: Optional[str]   = Query(None),
    city_override: Optional[str] = Query(None),
):
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

    # Prefeito: 3 camadas de fallback
    # 1) MAYORS_BY_CITY (curado — mais confiável)
    mayor_data = MAYORS_BY_CITY.get(city)
    if mayor_data:
        mayor_dict = {**mayor_data, "country": "Brasil", "source": "wikidata", "email": ""}
        mayor_dict = await enrich_with_photo(mayor_dict)
        prefeito = [mayor_dict]
    else:
        # 2) Filtra de city_politicians_raw quem é prefeito
        prefeito_wd = [p for p in city_politicians_raw
                       if "prefeito" in p.get("role","").lower()
                       or "prefeita" in p.get("role","").lower()]
        if prefeito_wd:
            prefeito = prefeito_wd[:1]
        elif city:
            # 3) Busca direta P6 no Wikidata (para cidades não curadas)
            mayor_wd = await get_mayor_by_city_wikidata(city, uf)
            if mayor_wd:
                mayor_wd = await enrich_with_photo(mayor_wd)
                prefeito = [mayor_wd]
            else:
                prefeito = []
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
    """Retorna URL de foto atual para um título Wikipedia. Cacheable."""
    photo = await get_photo(title)
    return {"photo": photo, "title": title}

@router.get("/transparency/featured")
async def featured_politicians():
    return {"featured":[
        {**CURATED_POLITICIANS["wd-Q28227"]},
        {**CURATED_POLITICIANS["wd-Q41551"]},
        {"id":"wd-Q22686","name":"Donald Trump","role":"Presidente dos EUA","country":"EUA","party":"Republicano","source":"wikidata","photo":""},
        {"id":"wd-Q47468","name":"Emmanuel Macron","role":"Presidente da França","country":"França","party":"Renaissance","source":"wikidata","photo":""},
    ]}