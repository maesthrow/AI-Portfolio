from logging.config import fileConfig
import os, sys
from sqlalchemy import engine_from_config, pool
from alembic import context

# чтобы импортировать app.*
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database.models import Base
from settings import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return settings.database_url


def run_migrations_online():
    connectable = engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,  # важно для DEFAULT NOW()
            render_as_batch=True,  # если вдруг нужна совместимость
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
