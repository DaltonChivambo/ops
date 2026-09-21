"""As seis rotas, vistas de fora — estado, corpo e cabeçalhos.

Estes testes não sabem que camadas existem por baixo, e é essa a intenção: o
que aqui está afirmado é o contrato que o SPA consome (`data/models.ts`), e é
suposto sobreviver a qualquer arrumação interna. Se uma reorganização os partir,
partiu o frontend.

O andaime — serviço falso, cliente, ficheiros — está todo no `conftest.py`.
"""

from datetime import date
from decimal import Decimal

from tests.conftest import CASE_ID, EXECUTION_ID, KEY, FakeService, make_detail, make_movement

BASE = "/pos/validacao-credito-fecho"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ─── Executar uma validação ──────────────────────────────────────────────────


def test_run_returns_201_with_execution_and_cases(client, files, service):
    response = client.post(f"{BASE}/execucoes", files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["executionId"] == EXECUTION_ID
    assert body["reportName"] == "FECHO_POS_DOP 21 a 28 de Junho-2026"
    assert body["files"] == {
        "posList": "pos-list.xlsx",
        "simoClosings": "simo-closings.xlsx",
        "bankaCredits": "banka-credits.xlsx",
    }
    assert body["summary"]["processed"] == 18138
    assert len(body["cases"]) == 1
    # Os três ficheiros chegaram ao serviço com o nome com que foram carregados.
    assert service.calls["run_validation"] == {
        "posList": "pos-list.xlsx",
        "simoClosings": "simo-closings.xlsx",
        "bankaCredits": "banka-credits.xlsx",
    }


def test_run_without_a_file_is_business_error_naming_the_field(client, files):
    del files["bankaCredits"]

    response = client.post(f"{BASE}/execucoes", files=files)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "business_rule"
    # A mensagem vai direita para o ecrã do operador: tem de dizer qual falta.
    assert "Créditos Banka" in error["message"]


# ─── A última execução ───────────────────────────────────────────────────────


def test_latest_execution_returns_result(client):
    response = client.get(f"{BASE}/execucoes/ultima")

    assert response.status_code == 200
    assert response.json()["executionId"] == EXECUTION_ID


def test_latest_execution_when_none_returns_204_without_body(client, service: FakeService):
    service.execution = None

    response = client.get(f"{BASE}/execucoes/ultima")

    # 204 e não 200 com `null`: é o que o `getLatestResult()` do SPA espera para
    # distinguir «ainda não correu nada» de «correu e deu vazio».
    assert response.status_code == 204
    assert not response.content


# ─── A tabela de detalhes ────────────────────────────────────────────────────


def test_details_return_page_with_counts(client):
    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/detalhes")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["perPage"] == 50
    assert body["counts"] == {
        "all": 1,
        "match": 0,
        "mismatch": 1,
        "missing": 0,
        "zero": 0,
        "duplicated": 0,
        "simoDuplicates": 0,
    }

    row = body["items"][0]
    assert row["key"] == KEY
    assert row["validation"] == "mismatch"
    assert row["difference"] == 6641.0
    # O enum da base é `D_PLUS_1`; o que sai para o frontend é `D+1`.
    assert row["closingType"] == "D+1"
    # Fora de uma chave duplicada, as contagens são 1/1 — não há ambiguidade
    # nenhuma a desfazer.
    assert row["simoClosingsCount"] == 1
    assert row["bankaMovementsCount"] == 1


def test_detail_duplicated_in_simo_carries_per_side_counts(client, service: FakeService):
    """Distingue, no contrato HTTP, uma chave duplicada no lado SIMO de uma
    duplicada no lado Banka — a ambiguidade que o operador via como
    «Incorrecto» sem explicação nenhuma (ver a nota em `domain/reconciliation.py`)."""
    service.details[0].validation = "duplicated"
    service.key_counts = {KEY: (2, 1)}

    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/detalhes")

    row = response.json()["items"][0]
    assert row["validation"] == "duplicated"
    assert row["simoClosingsCount"] == 2
    assert row["bankaMovementsCount"] == 1


def test_detail_duplicated_in_banka_carries_per_side_counts(client, service: FakeService):
    service.details[0].validation = "duplicated"
    service.key_counts = {KEY: (1, 2)}

    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/detalhes")

    row = response.json()["items"][0]
    assert row["simoClosingsCount"] == 1
    assert row["bankaMovementsCount"] == 2


def test_details_forward_page_filter_and_search(client, service: FakeService):
    client.get(
        f"{BASE}/execucoes/{EXECUTION_ID}/detalhes",
        params={"page": 3, "perPage": 25, "validation": "missing,mismatch", "q": "259342"},
    )

    assert service.calls["list_details"] == {
        "page": 3,
        "perPage": 25,
        "validation": "missing,mismatch",
        "search": "259342",
        "repeated": "all",
    }


def test_details_forward_the_repeated_closings_filter(client, service: FakeService):
    client.get(f"{BASE}/execucoes/{EXECUTION_ID}/detalhes", params={"repeated": "only"})

    assert service.calls["list_details"]["repeated"] == "only"


def test_details_reject_an_unknown_repeated_closings_filter(client):
    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/detalhes", params={"repeated": "xpto"})

    assert response.status_code == 422


# ─── Contar, ou não, os fechos repetidos da SIMO ─────────────────────────────


def test_simo_duplicates_decision_reaches_the_service(client, service: FakeService):
    response = client.put(
        f"{BASE}/execucoes/{EXECUTION_ID}/duplicados-simo", json={"counted": True}
    )

    assert response.status_code == 200
    assert service.calls["set_count_simo_duplicates"] == {"counted": True}


def test_simo_duplicates_decision_returns_the_whole_execution(client):
    """Muda os indicadores, os casos e o estado de cada fecho: o ecrã recarrega tudo."""
    response = client.put(
        f"{BASE}/execucoes/{EXECUTION_ID}/duplicados-simo", json={"counted": True}
    )

    body = response.json()
    assert body["executionId"] == EXECUTION_ID
    assert "summary" in body
    assert "cases" in body


def test_simo_duplicates_decision_leaves_the_states_alone(client):
    """A decisão é só do apuramento: um fecho repetido não é um fecho novo."""
    before = client.get(f"{BASE}/execucoes/ultima").json()["summary"]

    client.put(f"{BASE}/execucoes/{EXECUTION_ID}/duplicados-simo", json={"counted": True})
    after = client.get(f"{BASE}/execucoes/ultima").json()["summary"]

    assert after["countSimoDuplicates"] is True
    # Tudo o resto fica onde estava — estados, casos e taxa incluídos.
    assert {k: v for k, v in after.items() if k != "countSimoDuplicates"} == {
        k: v for k, v in before.items() if k != "countSimoDuplicates"
    }


def test_simo_duplicates_decision_on_an_unknown_execution_is_404(client):
    response = client.put(f"{BASE}/execucoes/nao-existe/duplicados-simo", json={"counted": True})

    assert response.status_code == 404


def test_details_cap_per_page_at_maximum(client, service: FakeService):
    client.get(f"{BASE}/execucoes/{EXECUTION_ID}/detalhes", params={"perPage": 5000})

    assert service.calls["list_details"]["perPage"] == 200


def test_details_of_unknown_execution_return_404(client):
    response = client.get(f"{BASE}/execucoes/nao-existe/detalhes")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# ─── Os dois lados de uma chave ──────────────────────────────────────────────


def test_key_returns_closings_movements_and_case(client):
    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/chaves/{KEY}")

    assert response.status_code == 200
    body = response.json()
    assert body["key"] == KEY
    assert len(body["closings"]) == 1
    assert len(body["movements"]) == 1
    assert body["movements"][0]["amount"] == 7641.0
    assert body["case"]["id"] == CASE_ID


def test_key_returns_saved_and_suggested_matches(client, service: FakeService):
    _duplicated_key(service)

    body = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/chaves/{KEY}").json()

    assert body["matches"] == []
    assert body["suggestedMatches"] == [
        {"closingId": "d1", "movementId": "m1"},
        {"closingId": "d2", "movementId": "m2"},
    ]


def test_key_without_closings_returns_404(client):
    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/chaves/000000000")

    assert response.status_code == 404


# ─── Actualizar um caso ──────────────────────────────────────────────────────


def test_update_case_returns_case_and_recomputed_summary(client):
    response = client.patch(
        f"{BASE}/casos/{CASE_ID}", json={"status": "in-review-simo", "eTicket": "INC-4210"}
    )

    assert response.status_code == 200
    body = response.json()
    # `in_review_simo` na base, `in-review-simo` no contrato — a tradução é da
    # apresentação. E o relógio do estado recomeçou hoje.
    assert body["case"]["status"] == "in-review-simo"
    assert body["case"]["statusSince"] == "2026-09-10"
    assert body["case"]["eTicket"] == "INC-4210"
    assert body["summary"]["processed"] == 18138


def test_update_duplicated_case_keeps_per_side_counts(client, service: FakeService):
    """Regressão: editar o estado/e-Ticket de um caso duplicado não pode repor
    o badge de lado para o omisso 1/1 — o PATCH é um caminho de escrita à
    parte do `/detalhes`, com a sua própria contagem a buscar."""
    service.cases[0].type = "duplicated"
    service.key_counts = {KEY: (1, 2)}

    response = client.patch(f"{BASE}/casos/{CASE_ID}", json={"status": "resolved"})

    case = response.json()["case"]
    assert case["simoClosingsCount"] == 1
    assert case["bankaMovementsCount"] == 2


def test_update_unknown_case_returns_404(client):
    response = client.patch(f"{BASE}/casos/nao-existe", json={"status": "resolved"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_update_case_with_invalid_status_is_business_rule(client):
    response = client.patch(f"{BASE}/casos/{CASE_ID}", json={"status": "inventado"})

    # Um estado que não existe é um pedido que viola a regra, não um recurso
    # ausente. Devolvia 404 até o commit dos códigos de erro.
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "business_rule"
    # A mensagem diz ao operador quais são os estados possíveis.
    assert "in-review-simo" in error["message"]


def test_update_case_with_nothing_to_change_is_bad_request(client):
    response = client.patch(f"{BASE}/casos/{CASE_ID}", json={})

    # Nem «não encontrei» nem regra violada: o pedido não diz o que fazer.
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


# ─── Conciliar um caso de períodos repetidos, fecho a fecho ─────────────────


def _duplicated_key(service: FakeService) -> None:
    """Dois fechos de 100,00 na SIMO e dois créditos de 100,00 no Banka."""
    service.cases[0].type = "duplicated"
    first = service.details[0]
    first.simo_closing_total = Decimal("100.00")
    second = make_detail()
    second.id = "d2"
    second.simo_closing_date = date(2026, 6, 24)
    second.simo_closing_total = Decimal("100.00")
    service.details = [first, second]

    credit = service.movements[0]
    credit.amount = Decimal("100.00")
    other = make_movement()
    other.id = "m2"
    other.movement_date = date(2026, 6, 25)
    other.amount = Decimal("100.00")
    service.movements = [credit, other]


def test_reconcile_all_closings_resolves_the_case(client, service: FakeService):
    _duplicated_key(service)
    pairs = [{"closingId": "d1", "movementId": "m1"}, {"closingId": "d2", "movementId": "m2"}]

    response = client.put(f"{BASE}/casos/{CASE_ID}/conciliacao", json={"matches": pairs})

    assert response.status_code == 200
    body = response.json()
    assert body["matches"] == pairs
    assert body["case"]["status"] == "resolved"
    assert body["case"]["simoClosingsCount"] == 2
    assert body["case"]["bankaMovementsCount"] == 2
    assert body["summary"]["processed"] == 18138
    # Fica registado quem emparelhou.
    assert service.calls["reconcile"]["matched_by"] == "m001926"


def test_reconcile_with_leftover_credit_still_settles_the_case(client, service: FakeService):
    """Valida-se a SIMO contra o Banka: um crédito a sobrar não segura o caso."""
    _duplicated_key(service)
    leftover = make_movement()
    leftover.id = "m3"
    leftover.amount = Decimal("780.00")
    service.movements.append(leftover)
    pairs = [{"closingId": "d1", "movementId": "m1"}, {"closingId": "d2", "movementId": "m2"}]

    response = client.put(f"{BASE}/casos/{CASE_ID}/conciliacao", json={"matches": pairs})

    assert response.status_code == 200
    assert response.json()["case"]["status"] == "resolved"


def test_reconcile_some_closings_keeps_the_status(client, service: FakeService):
    _duplicated_key(service)
    pairs = [{"closingId": "d1", "movementId": "m1"}]

    response = client.put(f"{BASE}/casos/{CASE_ID}/conciliacao", json={"matches": pairs})

    assert response.status_code == 200
    assert response.json()["case"]["status"] == "pending"


def test_reconcile_with_different_amount_is_business_rule(client, service: FakeService):
    _duplicated_key(service)
    service.movements[1].amount = Decimal("90.00")
    pairs = [{"closingId": "d2", "movementId": "m2"}]

    response = client.put(f"{BASE}/casos/{CASE_ID}/conciliacao", json={"matches": pairs})

    assert response.status_code == 422
    assert "valor exactamente igual" in response.json()["error"]["message"]


def test_reconcile_non_duplicated_case_is_business_rule(client):
    response = client.put(f"{BASE}/casos/{CASE_ID}/conciliacao", json={"matches": []})

    assert response.status_code == 422
    assert "períodos repetidos" in response.json()["error"]["message"]


def test_reconcile_unknown_case_returns_404(client):
    response = client.put(f"{BASE}/casos/nao-existe/conciliacao", json={"matches": []})

    assert response.status_code == 404


# ─── Conciliar vários casos de uma vez ───────────────────────────────────────


def test_candidates_list_open_duplicated_cases_with_suggestions(client, service: FakeService):
    _duplicated_key(service)

    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/conciliacoes")

    assert response.status_code == 200
    (candidate,) = response.json()
    assert candidate["key"] == KEY
    assert candidate["case"]["id"] == CASE_ID
    assert len(candidate["closings"]) == 2
    assert len(candidate["movements"]) == 2
    assert candidate["suggestedMatches"] == [
        {"closingId": "d1", "movementId": "m1"},
        {"closingId": "d2", "movementId": "m2"},
    ]


def test_candidates_leave_out_cases_that_are_not_duplicated(client):
    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/conciliacoes")

    assert response.status_code == 200
    assert response.json() == []


def test_candidates_leave_out_keys_without_an_equal_credit_for_every_closing(
    client, service: FakeService
):
    """Só se concilia com crédito igual: um fecho sem par tira a chave da lista."""
    _duplicated_key(service)
    service.movements[1].amount = Decimal("90.00")

    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/conciliacoes")

    assert response.status_code == 200
    assert response.json() == []


def test_candidates_of_unknown_execution_return_404(client):
    response = client.get(f"{BASE}/execucoes/nao-existe/conciliacoes")

    assert response.status_code == 404


def test_batch_reconcile_returns_cases_and_summary(client, service: FakeService):
    _duplicated_key(service)
    items = [
        {
            "caseId": CASE_ID,
            "matches": [
                {"closingId": "d1", "movementId": "m1"},
                {"closingId": "d2", "movementId": "m2"},
            ],
        }
    ]

    response = client.put(f"{BASE}/execucoes/{EXECUTION_ID}/conciliacoes", json={"items": items})

    assert response.status_code == 200
    body = response.json()
    assert [case["status"] for case in body["cases"]] == ["resolved"]
    assert body["summary"]["processed"] == 18138
    assert service.calls["reconcile_many"] == {"case_ids": [CASE_ID], "matched_by": "m001926"}


def test_batch_reconcile_with_nothing_is_bad_request(client):
    response = client.put(f"{BASE}/execucoes/{EXECUTION_ID}/conciliacoes", json={"items": []})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_batch_reconcile_with_impossible_pair_is_business_rule(client, service: FakeService):
    _duplicated_key(service)
    service.movements[1].amount = Decimal("90.00")
    items = [{"caseId": CASE_ID, "matches": [{"closingId": "d2", "movementId": "m2"}]}]

    response = client.put(f"{BASE}/execucoes/{EXECUTION_ID}/conciliacoes", json={"items": items})

    assert response.status_code == 422


def test_oversized_file_is_rejected_before_being_read(client, files, monkeypatch):
    """O `max_upload_mb` estava declarado e nunca era lido: não havia limite."""
    from app.controllers import executions

    monkeypatch.setattr(executions.settings, "max_upload_mb", 1)
    files["simoClosings"] = (
        "simo-closings.xlsx",
        b"x" * (2 * 1024 * 1024),
        files["simoClosings"][2],
    )

    response = client.post(f"{BASE}/execucoes", files=files)

    assert response.status_code == 413
    error = response.json()["error"]
    assert error["code"] == "payload_too_large"
    assert "Fechos SIMO" in error["message"]
    assert "2.0 MB" in error["message"]


def test_invalid_query_parameter_uses_same_envelope(client):
    """Sem handler próprio, o FastAPI devolvia o seu `{"detail": [...]}`."""
    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/detalhes", params={"page": "abc"})

    assert response.status_code == 422
    assert set(response.json()) == {"error"}


# ─── O relatório ─────────────────────────────────────────────────────────────


def test_report_returns_xlsx_named_after_period(client):
    response = client.get(f"{BASE}/execucoes/{EXECUTION_ID}/relatorio")

    assert response.status_code == 200
    assert response.headers["content-type"] == XLSX
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="FECHO_POS_DOP 21 a 28 de Junho-2026.xlsx"'
    )
    assert response.content.startswith(b"PK")


# ─── Definições: o prazo de tratamento ───────────────────────────────────────


def test_settings_return_current_sla(client):
    response = client.get(f"{BASE}/definicoes")

    assert response.status_code == 200
    assert response.json() == {
        "caseSlaDays": 7,
        "caseWarningDays": 3,
        "updatedAt": None,
        "updatedBy": None,
    }


def test_save_settings_returns_new_sla_and_who_set_it(client):
    response = client.put(f"{BASE}/definicoes", json={"caseSlaDays": 15, "caseWarningDays": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["caseSlaDays"] == 15
    assert body["caseWarningDays"] == 5
    # Mudar o prazo mexe com o que toda a gente vê: fica assinado.
    assert body["updatedBy"] == "m001926"
    # E o que se lê a seguir é o que se gravou.
    assert client.get(f"{BASE}/definicoes").json()["caseSlaDays"] == 15


def test_warning_at_or_after_sla_is_rejected_with_business_message(client):
    response = client.put(f"{BASE}/definicoes", json={"caseSlaDays": 7, "caseWarningDays": 7})

    assert response.status_code == 422
    assert "menor" in response.json()["error"]["message"]


def test_zero_sla_is_rejected(client):
    response = client.put(f"{BASE}/definicoes", json={"caseSlaDays": 0, "caseWarningDays": 0})

    assert response.status_code == 422


# ─── O envelope de erro ──────────────────────────────────────────────────────


def test_all_errors_use_same_envelope(client):
    response = client.get(f"{BASE}/execucoes/nao-existe/detalhes")

    # O `error.interceptor.ts` do SPA depende desta forma exacta para transformar
    # a resposta num `ApiError` com mensagem para mostrar ao operador.
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert isinstance(body["error"]["message"], str)
