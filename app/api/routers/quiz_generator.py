"""
ForGlory — Gerador Automático de Quizzes Diários
Gera 30 quizzes/dia via Claude API baseados em:
  - Política do país do usuário
  - Notícias locais/nacionais (via GNews)
  - Geopolítica global, história, geografia
"""
import os, json, asyncio, logging
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.features import Quiz, QuizQuestion

logger = logging.getLogger("ForGlory.QuizGen")

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GNEWS_KEY     = os.environ.get("GNEWS_API_KEY", "")
GNEWS_BASE    = "https://gnews.io/api/v4"

# Distribuição dos 30 quizzes diários por categoria
DAILY_DISTRIBUTION = [
    {"category": "política_local",   "count": 7, "label": "Política Local",      "icon": "🏛️"},
    {"category": "noticias_locais",  "count": 5, "label": "Notícias do Dia",     "icon": "📰"},
    {"category": "geopolitica",      "count": 5, "label": "Geopolítica",         "icon": "🌍"},
    {"category": "noticias_globais", "count": 4, "label": "Mundo",               "icon": "🌐"},
    {"category": "historia",         "count": 5, "label": "História",            "icon": "📜"},
    {"category": "geografia",        "count": 4, "label": "Geografia",           "icon": "🗺️"},
]

COUNTRY_CONFIGS = {
    "BR": {"lang": "pt", "country": "br", "politics_context": "política brasileira, Congresso Nacional, STF, governo Lula, estados e municípios brasileiros"},
    "US": {"lang": "en", "country": "us", "politics_context": "US politics, Congress, White House, Supreme Court, state governments"},
    "AR": {"lang": "es", "country": "ar", "politics_context": "política argentina, Casa Rosada, Congreso, gobierno Milei"},
    "PT": {"lang": "pt", "country": "pt", "politics_context": "política portuguesa, Assembleia da República, governo português"},
    "MX": {"lang": "es", "country": "mx", "politics_context": "política mexicana, Senado, gobierno Sheinbaum"},
}
DEFAULT_CONFIG = {"lang": "pt", "country": "br", "politics_context": "política internacional e brasileira"}


async def _fetch_news_headlines(country_code: str, category: str = "general", max_items: int = 5) -> list[str]:
    """Busca manchetes recentes do GNews para contextualizar os quizzes."""
    if not GNEWS_KEY:
        return []
    cfg = COUNTRY_CONFIGS.get(country_code, DEFAULT_CONFIG)
    query_map = {
        "política_local":   f"política {cfg['country']}",
        "noticias_locais":  "governo brasil noticias",
        "geopolitica":      "geopolitica relacoes internacionais",
        "noticias_globais": "mundo internacional",
        "historia":         "história brasil mundo",
        "geografia":        "brasil regioes estados",
    }
    q = query_map.get(category, "politica")
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{GNEWS_BASE}/search", params={
                "q": q, "lang": cfg["lang"], "country": cfg["country"],
                "max": max_items, "token": GNEWS_KEY,
            })
            if r.status_code == 200:
                articles = r.json().get("articles", [])
                return [a["title"] for a in articles if a.get("title")]
    except Exception as e:
        logger.warning(f"GNews fetch failed: {e}")
    return []


async def _generate_quiz_via_claude(
    category: str,
    label: str,
    country_code: str,
    headlines: list[str],
    quiz_date: str,
) -> dict | None:
    """Chama Claude API para gerar 1 quiz com 5 perguntas."""
    if not ANTHROPIC_KEY:
        logger.error("ANTHROPIC_API_KEY não configurada")
        return None

    cfg = COUNTRY_CONFIGS.get(country_code, DEFAULT_CONFIG)
    ctx_politics = cfg["politics_context"]
    headlines_txt = "\n".join(f"- {h}" for h in headlines) if headlines else "Sem manchetes recentes disponíveis."

    category_instructions = {
        "política_local": f"Foco exclusivo em {ctx_politics}. Perguntas sobre leis recentes, votações, cargos, partidos, escândalos noticiados e estrutura do governo.",
        "noticias_locais": f"Baseie TODAS as perguntas nas manchetes fornecidas abaixo. Cada pergunta deve ser sobre um evento real dessas notícias.",
        "geopolitica": "Foco em relações internacionais, conflitos, acordos, organizações como ONU/OTAN/G20, diplomacia, guerras em curso e disputas territoriais.",
        "noticias_globais": "Baseie nas manchetes fornecidas. Foco em eventos internacionais: eleições, crises, líderes mundiais, economia global.",
        "historia": "Perguntas sobre eventos históricos marcantes: datas, personagens, revoluções, guerras, descobertas, movimentos sociais. Misture história do Brasil e mundial.",
        "geografia": "Perguntas sobre países, capitais, rios, montanhas, regiões, fronteiras, biomas, populações, bandeiras e fusos horários.",
    }

    instr = category_instructions.get(category, "Perguntas gerais sobre política e atualidades.")

    prompt = f"""Você é um especialista em quiz educativo sobre política e atualidades. 
Data de hoje: {quiz_date}
Categoria: {label}
País do usuário: {country_code}

Instruções: {instr}

Manchetes recentes para contexto:
{headlines_txt}

Gere EXATAMENTE 1 quiz com EXATAMENTE 5 perguntas de múltipla escolha.
Cada pergunta deve ter 4 opções (A, B, C, D) com apenas 1 correta.
As perguntas devem ser precisas factualmente — não invente fatos.

Responda APENAS com JSON válido neste formato exato (sem markdown, sem explicação):
{{
  "title": "Título do quiz (máx 60 chars)",
  "difficulty": "easy|medium|hard",
  "questions": [
    {{
      "question": "Texto da pergunta",
      "options": ["Opção A", "Opção B", "Opção C", "Opção D"],
      "correct_index": 0,
      "explanation": "Explicação breve da resposta correta (máx 150 chars)",
      "points": 10
    }}
  ]
}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_KEY,
                         "anthropic-version": "2023-06-01"},
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1500,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )
            if r.status_code != 200:
                logger.error(f"Claude API erro {r.status_code}: {r.text[:200]}")
                return None
            data = r.json()
            text = data["content"][0]["text"].strip()
            # Limpar markdown se vier
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
    except Exception as e:
        logger.error(f"Claude quiz generation failed: {e}")
        return None


def _save_quiz_to_db(db: Session, quiz_data: dict, category: str, country_code: str, expires_at) -> Quiz | None:
    """Salva um quiz gerado no banco de dados."""
    try:
        quiz = Quiz(
            title=quiz_data["title"][:300],
            category=category,
            difficulty=quiz_data.get("difficulty", "medium"),
            source_type=f"ai_daily_{country_code}",
            source_id=f"daily_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{country_code}",
            is_active=1,
            expires_at=expires_at,
        )
        db.add(quiz)
        db.flush()
        for q in quiz_data.get("questions", []):
            qq = QuizQuestion(
                quiz_id=quiz.id,
                question=q["question"][:500],
                correct_index=q["correct_index"],
                explanation=q.get("explanation", "")[:300],
                source_url=None,
                points=q.get("points", 10),
            )
            qq.options = q["options"]
            db.add(qq)
        db.commit()
        return quiz
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao salvar quiz: {e}")
        return None


async def generate_daily_quizzes(country_code: str = "BR") -> dict:
    """
    Gera os 30 quizzes do dia para um país.
    Chamado pelo endpoint /quizzes/generate-daily (admin) ou pelo cron.
    """
    db = SessionLocal()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    expires_at = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59) + timedelta(days=1)
    source_prefix = f"daily_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{country_code}"

    # Verificar se já foram gerados hoje
    existing = db.query(Quiz).filter(
        Quiz.source_id.like(f"{source_prefix}%"),
        Quiz.source_type == f"ai_daily_{country_code}",
    ).count()

    if existing >= 25:
        db.close()
        return {"status": "already_generated", "count": existing, "date": today}

    generated = 0
    errors = 0

    try:
        for cat_config in DAILY_DISTRIBUTION:
            cat = cat_config["category"]
            count = cat_config["count"]
            label = cat_config["label"]

            # Buscar manchetes para contexto
            headlines = await _fetch_news_headlines(country_code, cat, max_items=5)

            # Gerar os quizzes da categoria em paralelo (máx 3 simultâneos)
            tasks = [
                _generate_quiz_via_claude(cat, label, country_code, headlines, today)
                for _ in range(count)
            ]
            # Processar em lotes de 3 para não sobrecarregar a API
            results = []
            for i in range(0, len(tasks), 3):
                batch = await asyncio.gather(*tasks[i:i+3])
                results.extend(batch)
                if i + 3 < len(tasks):
                    await asyncio.sleep(1)  # respeitar rate limit

            for quiz_data in results:
                if quiz_data and quiz_data.get("questions"):
                    saved = _save_quiz_to_db(db, quiz_data, cat, country_code, expires_at)
                    if saved:
                        generated += 1
                    else:
                        errors += 1
                else:
                    errors += 1

        logger.info(f"[QuizGen] {today} {country_code}: {generated} gerados, {errors} erros")
        return {"status": "ok", "generated": generated, "errors": errors, "date": today, "country": country_code}
    finally:
        db.close()
