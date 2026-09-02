"""As seis rotas, vistas de fora — estado, corpo e cabeçalhos.

Estes testes não sabem que camadas existem por baixo, e é essa a intenção: o
que aqui está afirmado é o contrato que o SPA consome (`data/models.ts`), e é
suposto sobreviver a qualquer arrumação interna. Se uma reorganização os partir,
partiu o frontend.

O andaime — serviço falso, cliente, ficheiros — está todo no `conftest.py`.
"""

from tests.conftest import CASE_ID, EXECUTION_ID, KEY, FakeService

BASE = "/pos/validacao-credito-fecho"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ─── Executar uma validação ──────────────────────────────────────────────────


def test_executar_devolve_201_com_a_execucao_e_os_casos(client, ficheiros, service):
    resposta = client.post(f"{BASE}/execucoes", files=ficheiros)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["executionId"] == EXECUTION_ID
    assert corpo["reportName"] == "FECHO_POS_DOP 21 a 28 de Junho-2026"
    assert corpo["files"] == {
        "posList": "pos-list.xlsx",
        "simoClosings": "simo-closings.xlsx",
        "bankaCredits": "banka-credits.xlsx",
    }
    assert corpo["summary"]["processed"] == 18138
    assert len(corpo["cases"]) == 1
    # Os três ficheiros chegaram ao serviço com o nome com que foram carregados.
    assert service.chamadas["run_validation"] == {
        "posList": "pos-list.xlsx",
        "simoClosings": "simo-closings.xlsx",
        "bankaCredits": "banka-credits.xlsx",
    }


def test_executar_sem_um_ficheiro_e_erro_de_negocio_que_nomeia_o_campo(client, ficheiros):
    del ficheiros["bankaCredits"]

    resposta = client.post(f"{BASE}/execucoes", files=ficheiros)

    assert resposta.status_code == 422
    erro = resposta.json()["error"]
    assert erro["code"] == "business_rule"
    # A mensagem vai direita para o ecrã do operador: tem de dizer qual falta.
    assert "Créditos Banka" in erro["message"]


# ─── A última execução ───────────────────────────────────────────────────────


def test_ultima_execucao_devolve_o_resultado(client):
    resposta = client.get(f"{BASE}/execucoes/ultima")

    assert resposta.status_code == 200
    assert resposta.json()["executionId"] == EXECUTION_ID


def test_ultima_execucao_sem_nenhuma_devolve_204_sem_corpo(client, service: FakeService):
    service.execution = None

    resposta = client.get(f"{BASE}/execucoes/ultima")

    # 204 e não 200 com `null`: é o que o `getLatestResult()` do SPA espera para
    # distinguir «ainda não correu nada» de «correu e deu vazio».
    assert resposta.status_code == 204
    assert not resposta.content


# ─── A tabela de detalhes ────────────────────────────────────────────────────


def test_detalhes_devolve_pagina_com_contagens(client):
    resposta = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/detalhes")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 1
    assert corpo["page"] == 1
    assert corpo["perPage"] == 50
    assert corpo["counts"] == {
        "all": 1,
        "match": 0,
        "mismatch": 1,
        "missing": 0,
        "zero": 0,
        "duplicated": 0,
    }

    linha = corpo["items"][0]
    assert linha["key"] == KEY
    assert linha["validation"] == "mismatch"
    assert linha["difference"] == 6641.0
    # O enum da base é `D_PLUS_1`; o que sai para o frontend é `D+1`.
    assert linha["closingType"] == "D+1"


def test_detalhes_encaminha_pagina_filtro_e_pesquisa(client, service: FakeService):
    client.get(
        f"{BASE}/execucoes/{EXECUTION_ID}/detalhes",
        params={"page": 3, "perPage": 25, "validation": "missing,mismatch", "q": "259342"},
    )

    assert service.chamadas["list_details"] == {
        "page": 3,
        "perPage": 25,
        "validation": "missing,mismatch",
        "search": "259342",
    }


def test_detalhes_limita_o_perpage_ao_maximo(client, service: FakeService):
    client.get(f"{BASE}/execucoes/{EXECUTION_ID}/detalhes", params={"perPage": 5000})

    assert service.chamadas["list_details"]["perPage"] == 200


def test_detalhes_de_execucao_inexistente_da_404(client):
    resposta = client.get(f"{BASE}/execucoes/nao-existe/detalhes")

    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "not_found"


# ─── Os dois lados de uma chave ──────────────────────────────────────────────


def test_chave_devolve_fechos_movimentos_e_caso(client):
    resposta = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/chaves/{KEY}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["key"] == KEY
    assert len(corpo["closings"]) == 1
    assert len(corpo["movements"]) == 1
    assert corpo["movements"][0]["amount"] == 7641.0
    assert corpo["case"]["id"] == CASE_ID


def test_chave_sem_fechos_da_404(client):
    resposta = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/chaves/000000000")

    assert resposta.status_code == 404


# ─── Actualizar um caso ──────────────────────────────────────────────────────


def test_actualizar_caso_devolve_o_caso_e_o_summary_recalculado(client):
    resposta = client.patch(
        f"{BASE}/casos/{CASE_ID}", json={"status": "in-review", "eTicket": "INC-4210"}
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    # `in_review` na base, `in-review` no contrato — a tradução é da apresentação.
    assert corpo["case"]["status"] == "in-review"
    assert corpo["case"]["eTicket"] == "INC-4210"
    assert corpo["summary"]["processed"] == 18138


def test_actualizar_caso_inexistente_da_404(client):
    resposta = client.patch(f"{BASE}/casos/nao-existe", json={"status": "resolved"})

    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "not_found"


def test_actualizar_caso_com_estado_invalido(client):
    resposta = client.patch(f"{BASE}/casos/{CASE_ID}", json={"status": "inventado"})

    # DEFEITO conhecido: hoje devolve 404. Um estado inválido é um pedido mal
    # formado, não um recurso que não existe — passa a 422 no commit dos códigos
    # de erro, e esta asserção muda com ele.
    assert resposta.status_code == 404


def test_actualizar_caso_sem_nada_para_mudar(client):
    resposta = client.patch(f"{BASE}/casos/{CASE_ID}", json={})

    # DEFEITO conhecido: hoje devolve 404, quando devia ser 400.
    assert resposta.status_code == 404


# ─── O relatório ─────────────────────────────────────────────────────────────


def test_relatorio_devolve_xlsx_com_o_nome_do_periodo(client):
    resposta = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/relatorio")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == XLSX
    assert (
        resposta.headers["content-disposition"]
        == 'attachment; filename="FECHO_POS_DOP 21 a 28 de Junho-2026.xlsx"'
    )
    assert resposta.content.startswith(b"PK")


# ─── O envelope de erro ──────────────────────────────────────────────────────


def test_todos_os_erros_usam_o_mesmo_envelope(client):
    resposta = client.get(f"{BASE}/execucoes/nao-existe/detalhes")

    # O `error.interceptor.ts` do SPA depende desta forma exacta para transformar
    # a resposta num `ApiError` com mensagem para mostrar ao operador.
    corpo = resposta.json()
    assert set(corpo) == {"error"}
    assert set(corpo["error"]) == {"code", "message"}
    assert isinstance(corpo["error"]["message"], str)
