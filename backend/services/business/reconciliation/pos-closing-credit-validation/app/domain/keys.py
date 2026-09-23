"""Chave de reconciliação entre o Portal SIMO e o Banka."""

import re

_DESCRIPTION_KEY = re.compile(r"0{0,4}(\d+)\s*-\s*(\d+)\s*$")


def normalize_pos_id(raw: str) -> str:
    """Forma canónica do POS Id: sem zeros à esquerda."""
    return raw.lstrip("0")


def build_key(pos_id: str, period: int) -> str:
    return f"{pos_id}{period % 1000:03d}"


def key_from_description(description: str) -> str:
    """Deriva a chave do descritivo do movimento — fonte única da chave do Banka."""
    match = _DESCRIPTION_KEY.search(description)
    if not match:
        return ""
    return normalize_pos_id(match.group(1)) + match.group(2).rjust(3, "0")
