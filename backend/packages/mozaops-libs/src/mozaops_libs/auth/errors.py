"""O que pode correr mal na autenticação, sem saber o que é HTTP."""


class AuthError(Exception):
    """Raiz do que a autenticação levanta de propósito."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UnauthenticatedError(AuthError):
    """Não veio token, ou o que veio não é de confiança."""

    def __init__(self, message: str = "Sessão inválida ou expirada. Entre de novo."):
        super().__init__(message)


class IdentityUnavailableError(AuthError):
    """Não se conseguiu falar com o GEEA para obter as chaves de assinatura."""

    def __init__(
        self,
        message: str = (
            "Não foi possível confirmar a sessão junto do GEEA. Tente novamente dentro de momentos."
        ),
    ):
        super().__init__(message)


class ForbiddenError(AuthError):
    """A pessoa é quem diz ser, mas não é da área a que isto pertence."""

    def __init__(
        self,
        message: str = (
            "Esta automação é de outra área. Fale com a coordenação do DOP se precisar de acesso."
        ),
    ):
        super().__init__(message)
