"""O que pode correr mal a fazer login, dito no vocabulário do domínio.

Sem HTTP: a tradução para resposta vive em `controllers/error_handlers.py`.
As mensagens chegam ao operador, por isso são português pronto a mostrar.
"""


class DomainError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidCredentialsError(DomainError):
    """Utilizador ou password que o GEEA não aceitou.

    A mensagem **não distingue** utilizador inexistente de password errada:
    dizer qual dos dois falhou é confirmar a existência de contas a quem as
    anda a adivinhar.
    """

    def __init__(self) -> None:
        super().__init__("Credenciais inválidas. Verifique o utilizador e a password.")


class TooManyAttemptsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Demasiadas tentativas seguidas. Aguarde um minuto e tente de novo.")


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
