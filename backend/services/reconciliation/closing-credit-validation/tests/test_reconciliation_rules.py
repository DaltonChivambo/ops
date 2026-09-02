"""As regras da reconciliação, com dados inventados.

O `test_reconciliation.py` prova os números contra os ficheiros reais do
departamento — mas esses são dados bancários, não são versionados, e saltam-se
sozinhos em qualquer checkout que não os tenha (CI incluído). Ou seja: o
algoritmo que dá valor a esta automação podia ser mexido sem que nada
protestasse.

Estes exercitam as MESMAS regras com números pequenos e inventados, e correm
sempre. Não substituem a prova de paridade — dizem que a regra está lá, não que
os 18 138 fechos de Junho dão o que davam.

Cada teste nomeia a regra que fixa, e as regras são as documentadas em
`domain/reconciliation.py`.
"""

from datetime import date
from decimal import Decimal

from app.domain.models import BankaCredit, BankaMovement, PosInfo, SimoClosing
from app.domain.reconciliation import build_report_name, reconcile, validation_rate
from app.domain.vocabulary import CaseType, ClosingType, Validation

DIA = date(2026, 6, 23)


def pos(**alteracoes: object) -> dict[str, PosInfo]:
    base = {"merchant": "Comerciante", "accountNumber": "000123", "closingType": ClosingType.D}
    return {"200001": PosInfo(**{**base, **alteracoes})}  # type: ignore[arg-type]


def fecho(
    pos_id: str = "200001", periodo: int = 101, total: str = "100.00", ops: int = 1, dia: date = DIA
) -> SimoClosing:
    return SimoClosing(
        posId=pos_id, period=periodo, closingDate=dia, operationNumber=ops, total=Decimal(total)
    )


def credito(*montantes: str) -> BankaCredit:
    movimentos = [
        BankaMovement(date=DIA, amount=Decimal(m), description="P24-Fecho TPA 0000200001 - 101")
        for m in montantes
    ]
    return BankaCredit(
        amount=sum((m.amount for m in movimentos), Decimal(0)),
        creditDate=DIA,
        description=movimentos[0].description,
        movements=movimentos,
    )


# ─── Os cinco estados ────────────────────────────────────────────────────────


def test_confere_quando_os_totais_da_chave_sao_exactamente_iguais() -> None:
    r = reconcile(pos(), [fecho(total="100.00")], {"200001101": credito("100.00")})

    assert r.details[0].validation is Validation.MATCH
    assert r.details[0].difference == Decimal(0)
    assert r.cases == []


def test_um_centimo_de_diferenca_ja_e_incorrecto() -> None:
    """Igualdade EXACTA: não há tolerância de arredondamento."""
    r = reconcile(pos(), [fecho(total="100.00")], {"200001101": credito("100.01")})

    assert r.details[0].validation is Validation.MISMATCH
    assert r.details[0].difference == Decimal("0.01")
    assert r.cases[0].type is CaseType.MISMATCH


def test_sem_credito_nenhum_e_nao_creditado() -> None:
    r = reconcile(pos(), [fecho(total="100.00")], {})

    assert r.details[0].validation is Validation.MISSING
    assert r.details[0].difference is None
    assert r.details[0].bankaClosingTotal is None
    assert r.cases[0].type is CaseType.MISSING
    assert r.summary.simoAmountMissing == Decimal("100.00")


def test_fecho_a_zero_sem_credito_e_zerado_e_nao_divergencia() -> None:
    r = reconcile(pos(), [fecho(total="0.00")], {})

    assert r.details[0].validation is Validation.ZERO
    assert r.cases == [], "um fecho zerado não pede tratamento a ninguém"
    assert r.summary.divergent == 0


def test_dois_fechos_na_mesma_chave_ficam_para_analise_individual() -> None:
    fechos = [fecho(total="100.00", ops=1), fecho(total="200.00", ops=2)]

    r = reconcile(pos(), fechos, {"200001101": credito("300.00")})

    assert [d.validation for d in r.details] == [Validation.DUPLICATED] * 2
    assert r.cases == [], "períodos duplicados não geram caso — vão para análise manual"
    assert r.summary.duplicatedPeriods == 2
    # Os dois lados registam-se: o Banka duplica na mesma proporção da SIMO.
    assert r.summary.simoAmountDuplicated == Decimal("300.00")
    assert r.summary.bankaAmountDuplicated == Decimal("300.00")


# ─── A regra central: somar por chave antes de comparar ──────────────────────


def test_a_comparacao_e_por_chave_e_nao_por_linha() -> None:
    """Vários fechos e vários créditos na mesma chave somam-se dos dois lados.

    É esta a regra que o VLOOKUP manual não tinha: ele repetia o mesmo crédito
    em cada linha e produzia divergências falsas.
    """
    fechos = [
        fecho(pos_id="200001", periodo=101, total="60.00", ops=1),
        fecho(pos_id="200001", periodo=102, total="40.00", ops=2),
    ]
    creditos = {"200001101": credito("60.00"), "200001102": credito("25.00", "15.00")}

    r = reconcile(pos(), fechos, creditos)

    assert {d.key: d.validation for d in r.details} == {
        "200001101": Validation.MATCH,
        "200001102": Validation.MATCH,
    }


def test_um_caso_por_chave_divergente_e_nao_um_por_fecho() -> None:
    fechos = [fecho(periodo=101, total="10.00"), fecho(periodo=102, total="20.00")]

    r = reconcile(pos(), fechos, {})

    assert len(r.cases) == 2
    assert {c.key for c in r.cases} == {"200001101", "200001102"}


def test_a_chave_trunca_o_periodo_a_tres_digitos() -> None:
    """O Banka cicla o contador em módulo 1000 — ver `domain/keys.py`."""
    r = reconcile(pos(), [fecho(periodo=4540, total="10.00")], {})

    assert r.details[0].key == "200001540"


# ─── Higiene dos ficheiros de entrada ────────────────────────────────────────


def test_linha_repetida_no_export_da_simo_nao_conta_duas_vezes() -> None:
    """Somada a dobrar, inflacionava a chave e criava uma divergência falsa."""
    # A identidade é a linha COMPLETA: POS, período, data, nº de operações e total.
    linha = {"total": "100.00", "ops": 3}
    r = reconcile(pos(), [fecho(**linha), fecho(**linha)], {"200001101": credito("100.00")})  # type: ignore[arg-type]

    assert r.summary.duplicatesDiscarded == 1
    assert r.summary.processed == 1
    assert r.details[0].validation is Validation.MATCH


def test_pos_sem_cadastro_fica_com_travessao_e_conta_se() -> None:
    r = reconcile({}, [fecho(total="10.00")], {})

    assert r.details[0].merchant == "—"
    assert r.details[0].accountNumber == "—"
    assert r.details[0].closingType is ClosingType.NA
    assert r.summary.unregisteredPos == 1


def test_periodos_que_colidem_no_modulo_sao_sinalizados() -> None:
    """323 e 1323 caem na mesma chave; não se corrige a soma, conta-se."""
    fechos = [fecho(periodo=323, total="10.00", ops=1), fecho(periodo=1323, total="20.00", ops=2)]

    r = reconcile(pos(), fechos, {})

    assert r.summary.keyCollisions == 1


def test_os_movimentos_do_banka_guardam_se_um_a_um() -> None:
    r = reconcile(pos(), [fecho(total="100.00")], {"200001101": credito("60.00", "40.00")})

    assert [m.amount for m in r.movements] == [Decimal("60.00"), Decimal("40.00")]
    assert all(m.key == "200001101" for m in r.movements)


# ─── Indicadores ─────────────────────────────────────────────────────────────


def test_a_taxa_nunca_arredonda_para_cem_havendo_um_fecho_por_conferir() -> None:
    assert validation_rate(999, 1000) == 99.9
    assert validation_rate(1000, 1000) == 100.0
    assert validation_rate(0, 0) == 0.0


def test_o_denominador_da_taxa_e_tudo_o_que_foi_processado() -> None:
    """Zerados e duplicados não conferem — excluí-los dava 100% com trabalho por fazer."""
    fechos = [fecho(periodo=101, total="10.00"), fecho(periodo=102, total="0.00")]

    r = reconcile(pos(), fechos, {"200001101": credito("10.00")})

    assert r.summary.processed == 2
    assert r.summary.matched == 1
    assert r.summary.zeroClosings == 1
    assert r.summary.validationRate == 50.0


def test_o_periodo_do_relatorio_vem_das_datas_dos_fechos() -> None:
    fechos = [
        fecho(periodo=101, total="10.00", dia=date(2026, 6, 21)),
        fecho(periodo=102, total="10.00", dia=date(2026, 6, 28)),
    ]

    r = reconcile(pos(), fechos, {})

    assert r.periodStart == date(2026, 6, 21)
    assert r.periodEnd == date(2026, 6, 28)
    assert r.reportName == "FECHO_POS_DOP 21 a 28 de Junho-2026"


def test_o_nome_do_relatorio_atravessa_meses() -> None:
    assert (
        build_report_name(date(2026, 5, 28), date(2026, 6, 3))
        == "FECHO_POS_DOP 28 de Maio a 3 de Junho-2026"
    )
