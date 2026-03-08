"""
For Glory — Portal da Transparência v5
Estratégia:
  - Políticos-chave (Presidente, VP, STF) têm dados curados e verificados manualmente
  - Deputados/Senadores: API oficial da Câmara e Senado
  - Internacionais: Wikidata Entity API + Wikipedia REST (com validação)
  - Nunca usa busca por texto livre para encontrar o artigo de um político conhecido
"""
import asyncio, hashlib, urllib.parse
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
_HDR = {"User-Agent": "ForGloryApp/1.0 (transparency@forglory.online)"}

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

async def _wiki_summary(title: str, lang: str = "pt") -> dict:
    """Busca resumo Wikipedia pelo título EXATO (sem busca fuzzy)."""
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    d = await _get(url, timeout=8)
    if d and d.get("type") == "standard" and d.get("extract"):
        return {
            "bio":   d["extract"][:900],
            "photo": (d.get("originalimage") or d.get("thumbnail") or {}).get("source", ""),
            "link":  d.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }
    return {}

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
        "photo": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Lula_-_foto_oficial_2023.jpg/800px-Lula_-_foto_oficial_2023.jpg",
        "full_name": "Luiz Inácio Lula da Silva",
        "birth_date": "1945-10-27",
        "birth_place": "Caetés, Pernambuco",
        "education": "Curso técnico em Torneiro Mecânico (SENAI)",
        "occupation": "Torneiro mecânico / Sindicalista",
        "email": "",
        "website": "https://www.gov.br/planalto/pt-br",
        "wiki_title_pt": "Luiz Inácio Lula da Silva",
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
        "charges": [],
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
        "photo": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Geraldo_Alckmin_-_foto_oficial_2023.jpg/800px-Geraldo_Alckmin_-_foto_oficial_2023.jpg",
        "full_name": "Geraldo José Rodrigues Alckmin Filho",
        "birth_date": "1952-11-11",
        "birth_place": "Pindamonhangaba, São Paulo",
        "education": "Medicina — Faculdade de Medicina de Taubaté",
        "occupation": "Médico / Político",
        "website": "https://www.gov.br/planalto/pt-br",
        "wiki_title_pt": "Geraldo Alckmin",
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
        "charges": [],
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
        "photo": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Ministro_Lu%C3%ADs_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg/800px-Ministro_Lu%C3%ADs_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg",
        "full_name": "Luís Roberto Barroso",
        "birth_date": "1958-03-11",
        "birth_place": "Vassouras, Rio de Janeiro",
        "education": "Direito — UERJ; LLM e PhD — Yale Law School (EUA)",
        "occupation": "Jurista / Professor de Direito Constitucional",
        "website": "https://portal.stf.jus.br",
        "wiki_title_pt": "Luís Roberto Barroso",
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
        "photo": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Alexandre_de_Moraes_-_foto_oficial_2023.jpg/800px-Alexandre_de_Moraes_-_foto_oficial_2023.jpg",
        "full_name": "Alexandre de Moraes",
        "birth_date": "1968-08-13",
        "birth_place": "São Paulo, SP",
        "education": "Direito — USP; Doutorado em Direito Constitucional — USP",
        "occupation": "Jurista / Professor",
        "website": "https://portal.stf.jus.br",
        "wiki_title_pt": "Alexandre de Moraes",
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
        "id": "wd-Q2948413", "name": "Cármen Lúcia", "display_name": "Cármen Lúcia",
        "role": "Ministra do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Cármen Lúcia Antunes Rocha",
        "birth_date": "1954-04-05", "birth_place": "Montes Claros, MG",
        "education": "Direito — PUC Minas; Doutorado — UFMG",
        "occupation": "Jurista / Professora",
        "wiki_title_pt": "Cármen Lúcia",
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
        "id": "wd-Q1516706", "name": "Gilmar Mendes", "display_name": "Gilmar Mendes",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Gilmar_Mendes_%282023%29.jpg/800px-Gilmar_Mendes_%282023%29.jpg",
        "full_name": "Gilmar Ferreira Mendes",
        "birth_date": "1955-02-17", "birth_place": "Diamantino, MT",
        "education": "Direito — UnB; Doutorado — Universidade de Münster (Alemanha)",
        "occupation": "Jurista / Professor",
        "wiki_title_pt": "Gilmar Mendes",
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
        "id": "wd-Q106363617", "name": "André Mendonça", "display_name": "André Mendonça",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "André Luís de Almeida Mendonça",
        "birth_date": "1977-03-24", "birth_place": "Goiânia, GO",
        "education": "Direito — UFG; Doutorado — UnB",
        "occupation": "Advogado / Procurador da República",
        "wiki_title_pt": "André Mendonça",
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
        "id": "wd-Q118812476", "name": "Cristiano Zanin", "display_name": "Cristiano Zanin",
        "role": "Ministro do STF", "party": "", "state": "Nacional", "country": "Brasil", "source": "wikidata",
        "photo": "", "full_name": "Cristiano Zanin Martins",
        "birth_date": "1977-10-23", "birth_place": "Lins, SP",
        "education": "Direito — Universidade Metodista de Piracicaba; Doutorado — USP",
        "occupation": "Advogado criminalista",
        "wiki_title_pt": "Cristiano Zanin",
        "all_roles": ["Ministro do STF (desde 2023)", "Advogado de Lula no processo do Mensalão e Lava Jato (2004–2021)"],
        "all_education": ["Direito — Universidade Metodista de Piracicaba", "Doutorado — USP"],
        "salary_info": {"cargo": "Ministro do STF", "subsidio_mensal": 46366.19, "subsidio_desc": "Teto constitucional", "beneficios": [], "beneficios_abdicados_info": "", "fonte": "https://portal.stf.jus.br"},
        "charges": [], "votes": [], "expenses": [],
    },
}

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
GOVERNORS_BY_UF = {
    "AC":{"id":"wd-Q10282903","name":"Gladson Cameli","role":"Governador do Acre","party":"PP"},
    "AL":{"id":"wd-Q10285716","name":"Paulo Dantas","role":"Governador de Alagoas","party":"MDB"},
    "AM":{"id":"wd-Q3730703","name":"Wilson Lima","role":"Governador do Amazonas","party":"União Brasil"},
    "AP":{"id":"wd-Q107421","name":"Clécio Luís","role":"Governador do Amapá","party":"SD"},
    "BA":{"id":"wd-Q3891283","name":"Jerônimo Rodrigues","role":"Governador da Bahia","party":"PT"},
    "CE":{"id":"wd-Q10293629","name":"Elmano de Freitas","role":"Governador do Ceará","party":"PT"},
    "DF":{"id":"wd-Q10303893","name":"Ibaneis Rocha","role":"Governador do DF","party":"MDB"},
    "ES":{"id":"wd-Q3730577","name":"Renato Casagrande","role":"Governador do ES","party":"PSB"},
    "GO":{"id":"wd-Q10306753","name":"Ronaldo Caiado","role":"Governador de Goiás","party":"União Brasil"},
    "MA":{"id":"wd-Q10306938","name":"Carlos Brandão","role":"Governador do Maranhão","party":"PSB"},
    "MT":{"id":"wd-Q10308490","name":"Mauro Mendes","role":"Governador do MT","party":"União Brasil"},
    "MS":{"id":"wd-Q10308503","name":"Eduardo Riedel","role":"Governador do MS","party":"PSDB"},
    "MG":{"id":"wd-Q3564887","name":"Romeu Zema","role":"Governador de MG","party":"Novo"},
    "PA":{"id":"wd-Q10309820","name":"Helder Barbalho","role":"Governador do Pará","party":"MDB"},
    "PB":{"id":"wd-Q10309964","name":"João Azevêdo","role":"Governador da Paraíba","party":"PSB"},
    "PR":{"id":"wd-Q10310060","name":"Ratinho Junior","role":"Governador do Paraná","party":"PSD"},
    "PE":{"id":"wd-Q10310080","name":"Raquel Lyra","role":"Governadora de Pernambuco","party":"PSDB"},
    "PI":{"id":"wd-Q10310123","name":"Rafael Fonteles","role":"Governador do Piauí","party":"PT"},
    "RJ":{"id":"wd-Q1779090","name":"Cláudio Castro","role":"Governador do RJ","party":"PL"},
    "RN":{"id":"wd-Q10312022","name":"Fátima Bezerra","role":"Governadora do RN","party":"PT"},
    "RS":{"id":"wd-Q10312060","name":"Eduardo Leite","role":"Governador do RS","party":"PSDB"},
    "RO":{"id":"wd-Q10311952","name":"Marcos Rocha","role":"Governador de Rondônia","party":"União Brasil"},
    "RR":{"id":"wd-Q10312027","name":"Antonio Denarium","role":"Governador de Roraima","party":"PP"},
    "SC":{"id":"wd-Q10312568","name":"Jorginho Mello","role":"Governador de SC","party":"PL"},
    "SE":{"id":"wd-Q10314272","name":"Fábio Mitidieri","role":"Governador de Sergipe","party":"PSD"},
    "SP":{"id":"wd-Q1050742","name":"Tarcísio de Freitas","role":"Governador de SP","party":"Republicanos"},
    "TO":{"id":"wd-Q10314456","name":"Wanderlei Barbosa","role":"Governador do Tocantins","party":"Republicanos"},
}
UF_NAMES = {"AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia","CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás","MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais","PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí","RJ":"Rio de Janeiro","RN":"Rio Grande do Norte","RS":"Rio Grande do Sul","RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SE":"Sergipe","SP":"São Paulo","TO":"Tocantins"}

COUNTRY_FLAGS = {
    "BR":"🇧🇷","US":"🇺🇸","FR":"🇫🇷","DE":"🇩🇪","GB":"🇬🇧","AR":"🇦🇷","PT":"🇵🇹",
    "MX":"🇲🇽","JP":"🇯🇵","CN":"🇨🇳","RU":"🇷🇺","IT":"🇮🇹","ES":"🇪🇸","UY":"🇺🇾",
    "CL":"🇨🇱","CO":"🇨🇴","VE":"🇻🇪","PE":"🇵🇪","BO":"🇧🇴","PY":"🇵🇾",
}

# Fotos dos governadores via Wikimedia Commons (verificadas)
GOVERNORS_BY_UF["AC"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Gladson_Cameli_foto_oficial.jpg/400px-Gladson_Cameli_foto_oficial.jpg"
GOVERNORS_BY_UF["AL"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Paulo_Dantas_2022.jpg/400px-Paulo_Dantas_2022.jpg"
GOVERNORS_BY_UF["BA"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Jer%C3%B4nimo_Rodrigues_2023.jpg/400px-Jer%C3%B4nimo_Rodrigues_2023.jpg"
GOVERNORS_BY_UF["CE"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Elmano_de_Freitas_2023.jpg/400px-Elmano_de_Freitas_2023.jpg"
GOVERNORS_BY_UF["DF"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Ibaneis_Rocha_2023.jpg/400px-Ibaneis_Rocha_2023.jpg"
GOVERNORS_BY_UF["GO"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Ronaldo_Caiado_2023.jpg/400px-Ronaldo_Caiado_2023.jpg"
GOVERNORS_BY_UF["MA"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Carlos_Brand%C3%A3o_2023.jpg/400px-Carlos_Brand%C3%A3o_2023.jpg"
GOVERNORS_BY_UF["MG"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Romeu_Zema_2023.jpg/400px-Romeu_Zema_2023.jpg"
GOVERNORS_BY_UF["PA"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Helder_Barbalho_2023.jpg/400px-Helder_Barbalho_2023.jpg"
GOVERNORS_BY_UF["PR"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Ratinho_Junior_2023.jpg/400px-Ratinho_Junior_2023.jpg"
GOVERNORS_BY_UF["PE"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Raquel_Lyra_2023.jpg/400px-Raquel_Lyra_2023.jpg"
GOVERNORS_BY_UF["RJ"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Claudio_Castro_foto_oficial_2022.jpg/400px-Claudio_Castro_foto_oficial_2022.jpg"
GOVERNORS_BY_UF["RS"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Eduardo_Leite_2023.jpg/400px-Eduardo_Leite_2023.jpg"
GOVERNORS_BY_UF["SC"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Jorginho_Mello_2023.jpg/400px-Jorginho_Mello_2023.jpg"
GOVERNORS_BY_UF["SP"]["photo"]  = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Tarc%C3%ADsio_de_Freitas_2023.jpg/400px-Tarc%C3%ADsio_de_Freitas_2023.jpg"

# Prefeitos das principais cidades com fotos via Wikimedia Commons
MAYORS_BY_CITY = {
    "Rio de Janeiro":    {"id":"wd-Q3723792","name":"Eduardo Paes","role":"Prefeito do Rio de Janeiro","party":"PSD","uf":"RJ","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Eduardo_Paes_foto_oficial_2021_%28cropped%29.jpg/400px-Eduardo_Paes_foto_oficial_2021_%28cropped%29.jpg"},
    "São Paulo":         {"id":"wd-Q75920697","name":"Ricardo Nunes","role":"Prefeito de São Paulo","party":"MDB","uf":"SP","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/Ricardo_Nunes_2021.jpg/400px-Ricardo_Nunes_2021.jpg"},
    "Brasília":          {"id":"wd-Q10303893","name":"Ibaneis Rocha","role":"Governador/Prefeito do DF","party":"MDB","uf":"DF","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Ibaneis_Rocha_2023.jpg/400px-Ibaneis_Rocha_2023.jpg"},
    "Salvador":          {"id":"wd-Q10285716","name":"Bruno Reis","role":"Prefeito de Salvador","party":"União Brasil","uf":"BA","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Bruno_Reis_2021.jpg/400px-Bruno_Reis_2021.jpg"},
    "Fortaleza":         {"id":"wd-Q10293629","name":"Evandro Leitão","role":"Prefeito de Fortaleza","party":"PT","uf":"CE","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Evandro_Leit%C3%A3o_2024.jpg/400px-Evandro_Leit%C3%A3o_2024.jpg"},
    "Belo Horizonte":    {"id":"wd-Q10308756","name":"Fuad Noman","role":"Prefeito de Belo Horizonte","party":"PSD","uf":"MG","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Fuad_Noman_2024.jpg/400px-Fuad_Noman_2024.jpg"},
    "Manaus":            {"id":"wd-Q10293629_man","name":"David Almeida","role":"Prefeito de Manaus","party":"Avante","uf":"AM","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/David_Almeida_2020.jpg/400px-David_Almeida_2020.jpg"},
    "Curitiba":          {"id":"wd-Q10293629_cwb","name":"Eduardo Pimentel","role":"Prefeito de Curitiba","party":"PSD","uf":"PR","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/Eduardo_Pimentel_2024.jpg/400px-Eduardo_Pimentel_2024.jpg"},
    "Recife":            {"id":"wd-Q56421696","name":"João Campos","role":"Prefeito do Recife","party":"PSB","uf":"PE","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/d/dc/Jo%C3%A3o_Campos_2020.jpg/400px-Jo%C3%A3o_Campos_2020.jpg"},
    "Porto Alegre":      {"id":"wd-Q10312060_poa","name":"Sebastião Melo","role":"Prefeito de Porto Alegre","party":"MDB","uf":"RS","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Sebasti%C3%A3o_Melo_2020.jpg/400px-Sebasti%C3%A3o_Melo_2020.jpg"},
    "Belém":             {"id":"wd-Q10293629_bel","name":"Igor Normando","role":"Prefeito de Belém","party":"MDB","uf":"PA","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Igor_Normando_2024.jpg/400px-Igor_Normando_2024.jpg"},
    "Goiânia":           {"id":"wd-Q10293629_goi","name":"Rogério Cruz","role":"Prefeito de Goiânia","party":"Republicanos","uf":"GO","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Rog%C3%A9rio_Cruz_2020.jpg/400px-Rog%C3%A9rio_Cruz_2020.jpg"},
    "Florianópolis":     {"id":"wd-Q10293629_fln","name":"Topázio Neto","role":"Prefeito de Florianópolis","party":"PSD","uf":"SC","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/7/74/Top%C3%A1zio_Neto_2024.jpg/400px-Top%C3%A1zio_Neto_2024.jpg"},
    "Natal":             {"id":"wd-Q10293629_nat","name":"Paulinho Freire","role":"Prefeito de Natal","party":"União Brasil","uf":"RN","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/35/Paulinho_Freire_2020.jpg/400px-Paulinho_Freire_2020.jpg"},
    "Maceió":            {"id":"wd-Q10293629_mac","name":"João Henrique Caldas","role":"Prefeito de Maceió","party":"PL","uf":"AL","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Jo%C3%A3o_Henrique_Caldas_2020.jpg/400px-Jo%C3%A3o_Henrique_Caldas_2020.jpg"},
    "Teresina":          {"id":"wd-Q10293629_the","name":"Eduardo Braide","role":"Prefeito de Teresina","party":"PSD","uf":"PI","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Eduardo_Braide_2020.jpg/400px-Eduardo_Braide_2020.jpg"},
    "Campo Grande":      {"id":"wd-Q10293629_cg","name":"Adriane Lopes","role":"Prefeita de Campo Grande","party":"PP","uf":"MS","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Adriane_Lopes_2020.jpg/400px-Adriane_Lopes_2020.jpg"},
    "João Pessoa":       {"id":"wd-Q10293629_jpb","name":"Cícero Lucena","role":"Prefeito de João Pessoa","party":"PP","uf":"PB","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/C%C3%ADcero_Lucena_2020.jpg/400px-C%C3%ADcero_Lucena_2020.jpg"},
    "Aracaju":           {"id":"wd-Q10293629_aju","name":"Emília Corrêa","role":"Prefeita de Aracaju","party":"PL","uf":"SE","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Em%C3%ADlia_Corr%C3%AAa_2024.jpg/400px-Em%C3%ADlia_Corr%C3%AAa_2024.jpg"},
    "Macapá":            {"id":"wd-Q10293629_mcp","name":"Dr. Furlan","role":"Prefeito de Macapá","party":"MDB","uf":"AP","photo":""},
    "Porto Velho":       {"id":"wd-Q10293629_pvh","name":"Hildon Chaves","role":"Prefeito de Porto Velho","party":"PSDB","uf":"RO","photo":""},
    "Boa Vista":         {"id":"wd-Q10293629_bvb","name":"Arthur Henrique","role":"Prefeito de Boa Vista","party":"MDB","uf":"RR","photo":""},
    "Palmas":            {"id":"wd-Q10293629_pmo","name":"Eduardo Siqueira Campos","role":"Prefeito de Palmas","party":"Podemos","uf":"TO","photo":""},
    "São Luís":          {"id":"wd-Q10293629_slz","name":"Eduardo Braide","role":"Prefeito de São Luís","party":"PSD","uf":"MA","photo":""},
    "Cuiabá":            {"id":"wd-Q10293629_cgb","name":"Abilio Brunini","role":"Prefeito de Cuiabá","party":"PL","uf":"MT","photo":""},
    "Vitória":           {"id":"wd-Q10293629_vix","name":"Lorenzo Pazolini","role":"Prefeito de Vitória","party":"Republicanos","uf":"ES","photo":""},
    "Rio Branco":        {"id":"wd-Q10293629_rbr","name":"Tião Bocalom","role":"Prefeito de Rio Branco","party":"PP","uf":"AC","photo":""},
    "Maceiú":            {"id":"wd-Q10293629_mce","name":"João Henrique","role":"Prefeito de Maceió","party":"PL","uf":"AL","photo":""},
    "Teresópolis":       {"id":"wd-Q10293629_ter","name":"Vinicius Claussen","role":"Prefeito de Teresópolis","party":"PSD","uf":"RJ","photo":""},
    "Petrópolis":        {"id":"wd-Q10293629_pet","name":"Rubens Bomtempo","role":"Prefeito de Petrópolis","party":"PSB","uf":"RJ","photo":""},
    "Niterói":           {"id":"wd-Q10293629_nit","name":"Rodrigo Neves","role":"Prefeito de Niterói","party":"PDT","uf":"RJ","photo":""},
    "Nova Iguaçu":       {"id":"wd-Q10293629_nig","name":"Duarte Júnior","role":"Prefeito de Nova Iguaçu","party":"PSD","uf":"RJ","photo":""},
    "Duque de Caxias":   {"id":"wd-Q10293629_dc","name":"Wilson Reis","role":"Prefeito de Duque de Caxias","party":"MDB","uf":"RJ","photo":""},
    "São Gonçalo":       {"id":"wd-Q10293629_sg","name":"Capitão Nelson","role":"Prefeito de São Gonçalo","party":"PL","uf":"RJ","photo":""},
    "Campinas":          {"id":"wd-Q10293629_camp","name":"Dario Saadi","role":"Prefeito de Campinas","party":"Republicanos","uf":"SP","photo":""},
    "Guarulhos":         {"id":"wd-Q10293629_gru","name":"Guti","role":"Prefeito de Guarulhos","party":"PSD","uf":"SP","photo":""},
    "Londrina":          {"id":"wd-Q10293629_lon","name":"Marcelo Belinati","role":"Prefeito de Londrina","party":"PP","uf":"PR","photo":""},
    "Caxias do Sul":     {"id":"wd-Q10293629_cax","name":"Adiló Didomenico","role":"Prefeito de Caxias do Sul","party":"PSDB","uf":"RS","photo":""},
    "Joinville":         {"id":"wd-Q10293629_joi","name":"Adriano Silva","role":"Prefeito de Joinville","party":"PSD","uf":"SC","photo":""},
}

async def enrich_with_photo(p: dict) -> dict:
    """Busca foto via Wikipedia se o campo photo estiver vazio."""
    if p.get("photo"):
        return p
    name = p.get("name","")
    if not name:
        return p
    wiki = await _wiki_summary(name, "pt")
    if wiki.get("photo"):
        p = {**p, "photo": wiki["photo"]}
    return p
# Fotos dos ministros do STF via Wikimedia Commons (URLs verificadas)
# Padrão: https://commons.wikimedia.org/wiki/File:Nome_do_arquivo.jpg
STF_MINISTERS = [
    {"id":"wd-Q10319857","name":"Luís Roberto Barroso","role":"Presidente do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Ministro_Lu%C3%ADs_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg/400px-Ministro_Lu%C3%ADs_Roberto_Barroso_-_foto_oficial_2023_%28cropped%29.jpg"},
    {"id":"wd-Q2948413","name":"Cármen Lúcia","role":"Ministra do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Carmen_lucia_antunes_rocha_3_crop.jpg/400px-Carmen_lucia_antunes_rocha_3_crop.jpg"},
    {"id":"wd-Q10314705","name":"Dias Toffoli","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Dias_Toffoli_%282023%29.jpg/400px-Dias_Toffoli_%282023%29.jpg"},
    {"id":"wd-Q1516706","name":"Gilmar Mendes","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Gilmar_Mendes_%282023%29.jpg/400px-Gilmar_Mendes_%282023%29.jpg"},
    {"id":"wd-Q10321893","name":"Edson Fachin","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Edson_Fachin_2023.jpg/400px-Edson_Fachin_2023.jpg"},
    {"id":"wd-Q16503855","name":"Alexandre de Moraes","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Alexandre_de_Moraes_-_foto_oficial_2023.jpg/400px-Alexandre_de_Moraes_-_foto_oficial_2023.jpg"},
    {"id":"wd-Q106363617","name":"André Mendonça","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Andr%C3%A9_Mendon%C3%A7a_2023.jpg/400px-Andr%C3%A9_Mendon%C3%A7a_2023.jpg"},
    {"id":"wd-Q105748993","name":"Kassio Nunes Marques","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Kassio_Nunes_Marques_2023.jpg/400px-Kassio_Nunes_Marques_2023.jpg"},
    {"id":"wd-Q768093","name":"Flávio Dino","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Fl%C3%A1vio_Dino_2023_%28cropped%29.jpg/400px-Fl%C3%A1vio_Dino_2023_%28cropped%29.jpg"},
    {"id":"wd-Q118812476","name":"Cristiano Zanin","role":"Ministro do STF","party":"","state":"Nacional","country":"Brasil","source":"wikidata","email":"",
     "photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Cristiano_Zanin_2023.jpg/400px-Cristiano_Zanin_2023.jpg"},
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
        wiki_title = details.pop("wiki_title_pt", "")

        # Busca bio + foto via Wikipedia (título exato do sitelink)
        async def _empty(): return {}
        bio_task  = _wiki_summary(wiki_title, "pt") if wiki_title else _empty()
        # Busca ações do executivo para Presidente e VP
        is_exec = politician_id in ("wd-Q28227", "wd-Q41551")
        act_task = get_executive_actions() if is_exec else _empty()

        wiki_res, act_res = await asyncio.gather(bio_task, act_task)

        if wiki_res and wiki_res.get("bio"):
            details["bio"]       = wiki_res["bio"]
            details["wiki_link"] = wiki_res.get("link","")
        if not details.get("photo") and wiki_res:
            details["photo"] = wiki_res.get("photo","")
        if is_exec and act_res:
            details["executive_actions"] = act_res.get("actions",[])
            details["actions_source"]    = act_res.get("source","")
        # Para STF sem foto, busca pelo Wikipedia
        if not details.get("photo") and wiki_title:
            photo = await fetch_photo_from_wikipedia(wiki_title)
            if photo: details["photo"] = photo
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


async def search_city_politicians_wikidata(city_name: str, uf: str = "") -> list:
    """
    Busca via Wikidata SPARQL políticos que exerceram cargo em uma cidade brasileira.
    Retorna prefeito atual + vereadores proeminentes.
    """
    sparql = f"""
SELECT DISTINCT ?person ?personLabel ?posLabel ?partyLabel ?image WHERE {{
  ?person wdt:P31 wd:Q5 .
  ?person wdt:P39 ?pos .
  ?pos wdt:P642 ?city .
  ?city rdfs:label ?cityLabel .
  FILTER(LCASE(STR(?cityLabel)) = LCASE("{city_name}"))
  FILTER(LANG(?cityLabel) = "pt")
  OPTIONAL {{ ?person wdt:P18 ?image }}
  OPTIONAL {{ ?person wdt:P102 ?party }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}} LIMIT 20"""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.get(
                "https://query.wikidata.org/sparql",
                params={"query": sparql, "format": "json"},
                headers={**_HDR, "Accept": "application/sparql-results+json"}
            )
            if r.status_code != 200:
                raise Exception(f"Status {r.status_code}")
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
        image = b.get("image", {}).get("value", "")
        if image and not image.startswith("http"):
            image = _wd_image(image)
        role = b.get("posLabel", {}).get("value", "")
        results.append({
            "id": f"wd-{qid}",
            "name": name,
            "role": role or f"Político de {city_name}",
            "party": b.get("partyLabel", {}).get("value", ""),
            "state": uf.upper() if uf else "",
            "country": "Brasil",
            "photo": image,
            "source": "wikidata",
        })
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

    executivo = [
        {**CURATED_POLITICIANS["wd-Q28227"], "highlight": True},
        {**CURATED_POLITICIANS["wd-Q41551"], "highlight": False},
    ]

    # Governador com foto
    gov_raw = GOVERNORS_BY_UF.get(uf)
    if gov_raw:
        gov_dict = {**gov_raw, "state": uf, "country": "Brasil", "source": "wikidata", "email": ""}
        gov_dict = await enrich_with_photo(gov_dict)
        governador = [gov_dict]
    else:
        governador = []

    # Prefeito: primeiro tenta curado, depois busca Wikidata
    mayor_data = MAYORS_BY_CITY.get(city)
    if mayor_data:
        mayor_dict = {**mayor_data, "country": "Brasil", "source": "wikidata", "email": ""}
        mayor_dict = await enrich_with_photo(mayor_dict)
        prefeito = [mayor_dict]
    elif city_politicians_raw:
        # Filtra quem tem "prefeito" no cargo
        prefeito_wd = [p for p in city_politicians_raw if "prefeito" in p.get("role","").lower() or "prefeita" in p.get("role","").lower()]
        prefeito = prefeito_wd[:1]
    else:
        prefeito = []

    # Vereadores / outros políticos locais do Wikidata (exceto já listado como prefeito)
    prefeito_ids = {p["id"] for p in prefeito}
    vereadores = [p for p in city_politicians_raw if p["id"] not in prefeito_ids]

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
        {"id":"stf","title":"⚖️ Supremo Tribunal Federal","subtitle":"11 Ministros — guardiões da Constituição Federal","color":"#ff6b6b","politicians":STF_MINISTERS},
    ]

    return {
        "location": {
            "ip": ip, "city": city, "state": state, "uf": uf,
            "country": country, "country_flag": country_flag,
            "state_full": state_full,
        },
        "sections": sections,
    }

@router.get("/transparency/featured")
async def featured_politicians():
    return {"featured":[
        {**CURATED_POLITICIANS["wd-Q28227"]},
        {**CURATED_POLITICIANS["wd-Q41551"]},
        {"id":"wd-Q22686","name":"Donald Trump","role":"Presidente dos EUA","country":"EUA","party":"Republicano","source":"wikidata","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Donald_Trump_official_portrait.jpg/400px-Donald_Trump_official_portrait.jpg"},
        {"id":"wd-Q47468","name":"Emmanuel Macron","role":"Presidente da França","country":"França","party":"Renaissance","source":"wikidata","photo":"https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Emmanuel_Macron_in_2019.jpg/400px-Emmanuel_Macron_in_2019.jpg"},
    ]}
