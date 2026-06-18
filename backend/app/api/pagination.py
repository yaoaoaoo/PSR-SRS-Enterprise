"""Pagination dependency — parses offset/limit from query params."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageParams:
    offset: int
    limit: int

    @classmethod
    def from_query(cls, offset: int = 0, limit: int = 20) -> PageParams:
        if offset < 0:
            offset = 0
        if limit < 1:
            limit = 1
        if limit > 100:
            limit = 100
        return cls(offset=offset, limit=limit)
