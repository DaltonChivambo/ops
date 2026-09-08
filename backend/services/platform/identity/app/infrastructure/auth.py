"""Constrói, uma vez, as peças de autenticação a partir da configuração.

É I/O (o verificador vai buscar o JWKS por HTTP), por isso vive na
infraestrutura. Os controladores recebem-nas por `Depends` e não sabem como
foram feitas.
"""

from app.settings import settings
from mozaops_libs.auth import Auth, RoleMapping, TokenVerifier, parse_set

role_mapping: RoleMapping = settings.role_mapping()

verifier = TokenVerifier(
    jwks_url=settings.auth_jwks_url,
    issuer=settings.auth_issuer,
    allowed_azp=parse_set(settings.auth_allowed_azp),
)

auth = Auth(verifier, role_mapping)
