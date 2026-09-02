"""Erros da API — envelope uniforme `{"error": {"code", "message"}}`.

A `message` é a que chega ao operador — logo, em português. Handlers
registados em `main.py` traduzem estas excepções para a resposta JSON.
"""


class ApiError(Exception):
    status = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status:
            self.status = status


class BusinessError(ApiError):
    """Exceção de negócio do PDD (dados incompletos ou em formato inválido)."""

    status = 422
    code = "business_rule"


class NotFoundError(ApiError):
    status = 404
    code = "not_found"
