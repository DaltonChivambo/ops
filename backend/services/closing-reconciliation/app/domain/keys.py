"""Chave de reconciliação entre o Portal SIMO e o Banka.

Porte literal de `domain/keys.py` do MozaOps v1.

Regra descoberta nos ficheiros reais: o Banka trunca o período a 3 dígitos (o
contador cicla módulo 1000), logo a chave que aparece na coluna «POS ID vs.
Período» do MIS é `posId` seguido de `período % 1000` com pad a 3 dígitos.

Verificado: período 4540 → 237958540; período 37 → 221675037; período 1 → 263071001.
"""
import re

_DESCRIPTION_KEY = re.compile(r"0{0,4}(\d+)\s*-\s*(\d+)\s*$")


def normalize_pos_id(raw: str) -> str:
    """Forma canónica do POS Id: sem zeros à esquerda.

    A Lista de POS traz o POS Id com zeros à esquerda (`00200437`) enquanto a SIMO
    e o descritivo do Banka o trazem sem eles (`200437`). Sem esta normalização, o
    mesmo POS não casa entre ficheiros e aparece como «sem cadastro».
    """
    return raw.lstrip("0")


def build_key(pos_id: str, period: int) -> str:
    return f"{pos_id}{period % 1000:03d}"


def key_from_description(description: str) -> str:
    """Deriva a chave do descritivo do movimento — fonte única da chave do Banka.

    `P24-Fecho TPA 0000252524 - 070` → `252524070`.
    """
    match = _DESCRIPTION_KEY.search(description)
    if not match:
        return ""
    return normalize_pos_id(match.group(1)) + match.group(2).rjust(3, "0")
