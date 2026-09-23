"""A trava do tamanho sem comprimento declarado — o caso que a rota não produz."""

from io import BytesIO

import pytest
from fastapi import UploadFile

from app.controllers import executions
from app.domain.errors import UploadTooLargeError
from app.domain.vocabulary import UploadSlot

TWO_MEGABYTES = 2 * 1024 * 1024


def _upload_without_declared_size(payload: bytes) -> UploadFile:
    upload = UploadFile(file=BytesIO(payload), filename="simo-closings.xlsx")
    assert upload.size is None
    return upload


def test_file_without_declared_size_is_measured_not_waved_through(monkeypatch):
    monkeypatch.setattr(executions.settings, "max_upload_mb", 1)
    upload = _upload_without_declared_size(b"x" * TWO_MEGABYTES)

    with pytest.raises(UploadTooLargeError, match=r"2\.0 MB"):
        executions._reject_oversized({UploadSlot.SIMO_CLOSINGS: upload})


def test_measuring_leaves_the_stream_at_the_start(monkeypatch):
    monkeypatch.setattr(executions.settings, "max_upload_mb", 64)
    upload = _upload_without_declared_size(b"conteudo")

    executions._reject_oversized({UploadSlot.SIMO_CLOSINGS: upload})

    assert upload.file.read() == b"conteudo"
