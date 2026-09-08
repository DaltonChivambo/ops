"""Constrói, uma vez, as peças de autenticação a partir da configuração.

É I/O — o verificador vai buscar o JWKS por HTTP — e por isso vive aqui e não
nos controladores, que só o recebem já feito.
"""

from app.settings import settings
from mozaops_libs.auth import Auth, TokenVerifier, parse_set

verifier = TokenVerifier(
    jwks_url=settings.auth_jwks_url,
    issuer=settings.auth_issuer,
    allowed_azp=parse_set(settings.auth_allowed_azp),
)

auth = Auth(verifier, settings.area_mapping())
