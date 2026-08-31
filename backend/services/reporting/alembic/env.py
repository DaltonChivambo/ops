"""Alembic de reporting.

`version_table_schema` põe a tabela `alembic_version` no schema do serviço — sem isto os
serviços partilhariam histórico de migrações.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from reporting.core.config import get_settings
from reporting.infrastructure.persistence.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
SCHEMA = settings.db_schema
target_metadata = Base.metadata


def _url() -> str:
    return os.getenv("DATABASE_URL", settings.database_url)


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    return not (type_ == "table" and obj.schema not in (SCHEMA, None))


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as ligacao:
        ligacao.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
        ligacao.commit()
        context.configure(
            connection=ligacao,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            version_table_schema=SCHEMA,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_object=include_object,
        version_table_schema=SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
