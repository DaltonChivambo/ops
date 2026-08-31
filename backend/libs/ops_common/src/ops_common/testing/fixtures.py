"""Fixtures partilhadas pelos testes de todos os serviços."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from ops_common.auth.models import CurrentUser
from ops_common.messaging.envelope import EventEnvelope


def utilizador_falso(
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
    **extra: Any,
) -> CurrentUser:
    return CurrentUser(
        sub=extra.pop("sub", str(uuid.uuid4())),
        username=extra.pop("username", "teste"),
        email=extra.pop("email", "teste@exemplo.local"),
        roles=roles or ["utilizador"],
        permissions=permissions or [],
        **extra,
    )


def claims_falsas(minutos_validade: int = 30, **extra: Any) -> dict[str, Any]:
    agora = datetime.now(timezone.utc)
    claims = {
        "sub": str(uuid.uuid4()),
        "username": "teste",
        "roles": ["utilizador"],
        "iss": "ops-auth",
        "aud": "ops-platform",
        "iat": int(agora.timestamp()),
        "exp": int((agora + timedelta(minutes=minutos_validade)).timestamp()),
    }
    claims.update(extra)
    return claims


def evento_falso(event_name: str = "teste.ocorrido", **data: Any) -> EventEnvelope:
    return EventEnvelope(event_name=event_name, producer="teste", data=data)


class PublisherFalso:
    """Substitui o EventPublisher nos testes: guarda em vez de publicar."""

    def __init__(self) -> None:
        self.publicados: list[EventEnvelope] = []

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def publish(self, event_name: str, data: dict, event_version: int = 1) -> EventEnvelope:
        envelope = EventEnvelope(
            event_name=event_name, event_version=event_version, producer="teste", data=data
        )
        self.publicados.append(envelope)
        return envelope

    def nomes(self) -> list[str]:
        return [e.event_name for e in self.publicados]


@pytest.fixture
def publisher_falso() -> PublisherFalso:
    return PublisherFalso()


@pytest.fixture
def utilizador() -> CurrentUser:
    return utilizador_falso()


@pytest.fixture
def administrador() -> CurrentUser:
    return utilizador_falso(roles=["admin"], permissions=["*"])
