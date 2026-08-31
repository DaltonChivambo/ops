from ops_common.messaging.envelope import EventEnvelope


def test_envelope_sobrevive_a_ida_e_volta():
    original = EventEnvelope(
        event_name="ativo.criado",
        producer="asset",
        correlation_id="abc-123",
        data={"id": "1", "nome": "Portátil"},
    )
    recuperado = EventEnvelope.from_bytes(original.to_bytes())

    assert recuperado.event_name == "ativo.criado"
    assert recuperado.correlation_id == "abc-123"
    assert recuperado.data["nome"] == "Portátil"
    assert recuperado.event_id == original.event_id


def test_envelope_gera_id_e_data_por_defeito():
    envelope = EventEnvelope(event_name="teste.ocorrido", producer="teste")
    assert envelope.event_id
    assert envelope.occurred_at is not None
    assert envelope.event_version == 1
