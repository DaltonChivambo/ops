"""Engine, sessionmaker e o `search_path` do schema deste serviço."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from notification.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"options": f"-csearch_path={settings.db_schema}"},
)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Sessão por request: abre, entrega, commit no fim; rollback se algo rebentar.

    É isto que dispensa Unit of Work — dois repositórios partilham a mesma sessão.
    """
    async with SessionLocal() as sessao:
        try:
            yield sessao
            await sessao.commit()
        except Exception:
            await sessao.rollback()
            raise


async def verificar_ligacao() -> bool:
    """Usado pelo /ready."""
    try:
        async with engine.connect() as ligacao:
            await ligacao.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
