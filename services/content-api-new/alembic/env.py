import os, sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# чтобы импортировать app.*
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.db import Base  # noqa: F401
from app import models  # noqa: F401

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None and config.file_config.has_section("formatters"):
    fileConfig(config.config_file_name)
else:
    # Fallback to a simple logging setup if alembic.ini does not define formatters/handlers.
    import logging

    logging.basicConfig(level=logging.INFO)

target_metadata = Base.metadata


def run_migrations_offline():
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.database_url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
