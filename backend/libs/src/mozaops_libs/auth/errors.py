"""O que pode correr mal na autenticação, sem saber o que é HTTP.

Mesmo princípio do `domain/errors.py` de cada serviço: quem levanta o erro
não decide com que estado ele sai. A tradução para resposta vive em
`fastapi.py`, e é lá — num sítio só — que se garante o envelope
`{"error": {"code", "message"}}` que o SPA sabe ler.

A `message` chega ao operador, por isso é português e não traz diagnóstico
técnico: dizer «assinatura inválida» ou «o `kid` não está no JWKS» a quem
está a tentar entrar não ajuda ninguém, e conta a quem tenta forçar a
entrada exactamente o que falhou.
"""


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
    """Não se conseguiu falar com o GEEA para obter as chaves de assinatura.

    Distinto do `UnauthenticatedError` de propósito: o token pode estar
    perfeito e o problema ser nosso. Dizer «sessão inválida» a quem acabou de
    entrar manda a pessoa repetir o login para nada, e esconde de quem opera
    que o que está em baixo é a ligação ao GEEA.
    """

    def __init__(
        self,
        message: str = (
            "Não foi possível confirmar a sessão junto do GEEA. Tente novamente dentro de momentos."
        ),
    ):
        super().__init__(message)


class ForbiddenError(AuthError):
    """A pessoa é quem diz ser, mas não tem papel para isto."""

    def __init__(
        self,
        message: str = (
            "Não tem permissão para esta operação. "
            "Fale com a coordenação do DOP se precisar de acesso."
        ),
    ):
        super().__init__(message)
