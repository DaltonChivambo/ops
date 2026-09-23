"""Constrói, uma vez, as peças de autenticação a partir da configuração."""

from app.settings import settings
from mozaops_libs.auth import AreaMapping, Auth, TokenVerifier, parse_set

area_mapping: AreaMapping = settings.area_mapping()

verifier = TokenVerifier(
    jwks_url=settings.auth_jwks_url,
    issuer=settings.auth_issuer,
    allowed_azp=parse_set(settings.auth_allowed_azp),
)

auth = Auth(verifier, area_mapping, settings.auth_client_id)
