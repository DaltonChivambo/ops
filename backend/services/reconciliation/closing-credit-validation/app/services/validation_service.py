"""Caso de uso da validação: executar, consultar e gerar o relatório.

O pipeline está deliberadamente separado em `parse → reconcile → persist`: hoje
corre síncrono dentro do pedido HTTP, mas a separação já deixa a porta aberta
para o desenho assíncrono sem tocar no pipeline em si.

Esta camada não sabe o que é um pedido HTTP nem uma tabela: recebe repositórios
e devolve objectos. Quem os transforma em JSON é o controlador.
"""

from collections.abc import Mapping
from typing import IO, Any

from app.domain.errors import NotFoundError
from app.domain.models import ReconciliationResult
from app.domain.reconciliation import reconcile
from app.domain.vocabulary import UploadSlot
from app.infrastructure.excel import parsers, report
from app.infrastructure.tables import ClosingDetail, Execution, PendingCase
from app.pagination import Page
from app.repositories.case_repository import CaseRepository
from app.repositories.execution_repository import ExecutionRepository


class ValidationService:
    def __init__(self, executions: ExecutionRepository, cases: CaseRepository) -> None:
        self._executions = executions
        self._cases = cases

    async def run(self, files: Mapping[UploadSlot, tuple[IO[bytes], str]]) -> str:
        """Executa a validação e devolve o id da execução persistida.

        `files` mapeia cada campo multipart para `(stream, nome do ficheiro)`.
        """
        result = _parse_and_reconcile(files)
        names = {slot: files[slot][1] for slot in UploadSlot}
        return await self._executions.create(result, names, result.summary.to_json_dict())

    async def get_execution(self, execution_id: str) -> Execution:
        execution = await self._executions.find(execution_id)
        if execution is None:
            raise NotFoundError("A execução indicada não existe ou já foi removida.")
        return execution

    async def get_latest_execution(self) -> Execution | None:
        return await self._executions.find_latest()

    async def list_cases(self, execution_id: str) -> list[PendingCase]:
        return await self._cases.list_by_execution(execution_id)

    async def list_details(
        self,
        execution_id: str,
        page: Page,
        validation: str | None,
        search: str | None,
    ) -> tuple[list[ClosingDetail], int, dict[str, int]]:
        details, total = await self._executions.list_details(execution_id, page, validation, search)
        counts = await self._executions.count_details_by_validation(execution_id, search)
        return details, total, counts

    async def get_key_breakdown(self, execution_id: str, key: str) -> dict[str, Any]:
        """Os dois lados de uma chave: os fechos da SIMO e os movimentos do Banka.

        A unidade é a CHAVE e não o fecho, porque o crédito do Banka é da chave: um
        fecho isolado não tem crédito próprio de que se possa falar. Clicar num fecho
        abre a chave a que ele pertence.
        """
        await self.get_execution(execution_id)  # 404 se a execução não existir
        details = await self._executions.list_details_by_key(execution_id, key)
        if not details:
            raise NotFoundError("Não há nenhum fecho com esta chave nesta execução.")
        return {
            "key": key,
            "closings": details,
            "movements": await self._executions.list_movements_by_key(execution_id, key),
            "case": await self._cases.find_by_key(execution_id, key),
        }

    async def build_report(self, execution_id: str) -> tuple[bytes, str]:
        """Gera o .xlsx da execução a partir do que está persistido."""
        execution = await self.get_execution(execution_id)
        details = await self._executions.list_all_details(execution_id)
        cases = await self._cases.list_by_execution(execution_id)
        return report.build_workbook(execution, details, cases), f"{execution.report_name}.xlsx"


def _parse_and_reconcile(
    files: Mapping[UploadSlot, tuple[IO[bytes], str]],
) -> ReconciliationResult:
    pos_list = parsers.parse_pos_list(*files[UploadSlot.POS_LIST])
    closings = parsers.parse_simo_closings(*files[UploadSlot.SIMO_CLOSINGS])
    credits = parsers.parse_banka_credits(*files[UploadSlot.BANKA_CREDITS])
    # O `NoClosingsError` é uma excepção de negócio do PDD, com a mensagem já em
    # português: sobe tal como está, sem tradução pelo meio.
    return reconcile(pos_list, closings, credits)
