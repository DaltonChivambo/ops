"""O que pode correr mal a fazer login, dito no vocabulário do domínio."""


class DomainError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidCredentialsError(DomainError):
    """Utilizador ou password que o GEEA não aceitou."""

    def __init__(self) -> None:
        super().__init__("Credenciais inválidas. Verifique o utilizador e a password.")


class TooManyAttemptsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Demasiadas tentativas seguidas. Aguarde um momento e tente de novo.")


class GeeaUnavailableError(DomainError):
    """O GEEA não respondeu, ou respondeu o que não se esperava."""

    def __init__(self) -> None:
        super().__init__(
            "Não foi possível contactar o GEEA para validar as credenciais. "
            "Tente novamente dentro de momentos."
        )


class NoSessionError(DomainError):
    """Pediram renovação sem cookie de sessão — ou com um que já não serve."""

    def __init__(self) -> None:
        super().__init__("A sessão terminou. Entre de novo.")
