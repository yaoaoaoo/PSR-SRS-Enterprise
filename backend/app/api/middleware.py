"""Request ID middleware — injects/generates X-Request-ID."""

from __future__ import annotations

import logging
import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

_REQUEST_ID_HEADER = "X-Request-ID"
_VALID_CHARS = re.compile(r"^[a-zA-Z0-9\-_]{1,128}$")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(_REQUEST_ID_HEADER, "")
        if not rid or not _VALID_CHARS.match(rid):
            rid = uuid.uuid4().hex[:16]
        request.state.request_id = rid
        response = await call_next(request)
        response.headers[_REQUEST_ID_HEADER] = rid
        return response
