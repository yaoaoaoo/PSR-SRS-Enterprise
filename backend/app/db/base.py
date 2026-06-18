"""Re-export the SQLAlchemy declarative base.

Model imports for Alembic auto-detection are in ``app.db.base``
(``__init__.py``) — they are NOT imported here to avoid circular imports
with ``app.models`` → ``app.db.base``.
"""

from app.db import Base

__all__ = ["Base"]
