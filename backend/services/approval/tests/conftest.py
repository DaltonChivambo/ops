"""Fixtures de approval.

`unit/` não toca em I/O; `integration/` corre contra Postgres real e está marcado com
`@pytest.mark.integration` — `pytest -m "not integration"` corre só os primeiros.
"""

from __future__ import annotations

import os

os.environ.setdefault("DB_SCHEMA", "approval")
os.environ.setdefault("SERVICE_NAME", "approval")
