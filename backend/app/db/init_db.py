"""Database initialisation helpers.

NOT used at import time — call explicitly from application startup or
CLI scripts.  Production schema is managed exclusively by Alembic.
"""

from __future__ import annotations

import logging

from app.db.session import check_db_connection, get_engine

logger = logging.getLogger(__name__)


def verify_db() -> dict[str, bool | str]:
    """Run a quick health-check on the database layer.

    Returns a dict suitable for the readiness endpoint.
    """
    connected = check_db_connection()
    engine = get_engine()
    return {
        "database_connected": connected,
        "database_url_type": "sqlite" if "sqlite" in str(engine.url) else "other",
    }
