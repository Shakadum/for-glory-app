from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# --- garante que "app/" seja importável ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

# --- carregar .env se existir ---
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

# Alembic Config
config = context.config

# Logging do alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- IMPORTANTE: aponte para o Base do seu projeto ---
from app.db.base import Base  # Base declarative_base()
from app.models import models  # garante que os models sejam importados/registrados

target_metadata = Base.metadata

def get_url():
    # prioridade: DATABASE_URL no .env/Render
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # se estiver vindo no formato postgres://, converte pra postgresql:// (SQLAlchemy 2)
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url

    # fallback: o que estiver no alembic.ini
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,           # detecta mudança de tipo
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()