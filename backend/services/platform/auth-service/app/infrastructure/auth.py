"""Constrói, uma vez, as peças de autenticação a partir da configuração.

É I/O (o verificador vai buscar o JWKS por HTTP), por isso vive na
infraestrutura. Os controladores recebem-nas por `Depends` e não sabem como
foram feitas.
"""

from app.settings import settings
from mozaops_libs.auth import AreaMapping, Auth, TokenVerifier, parse_set

area_mapping: AreaMapping = settings.area_mapping()

verifier = TokenVerifier(
    jwks_url=settings.auth_jwks_url,
    issuer=settings.auth_issuer,
    allowed_azp=parse_set(settings.auth_allowed_azp),
)

auth = Auth(verifier, area_mapping)
