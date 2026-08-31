from fastapi import FastAPI
from fastapi.testclient import TestClient

from ops_common.logging.correlation import (
    HEADER,
    CorrelationIdMiddleware,
    get_correlation_id,
)


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/eco")
    def eco():
        return {"correlation_id": get_correlation_id()}

    return app


def test_propaga_o_header_do_osb():
    cliente = TestClient(_app())
    resposta = cliente.get("/eco", headers={HEADER: "id-do-osb"})

    assert resposta.json()["correlation_id"] == "id-do-osb"
    assert resposta.headers[HEADER] == "id-do-osb"


def test_gera_um_id_quando_o_pedido_nao_traz_nenhum():
    cliente = TestClient(_app())
    resposta = cliente.get("/eco")

    gerado = resposta.json()["correlation_id"]
    assert gerado not in ("", "-")
    assert resposta.headers[HEADER] == gerado
