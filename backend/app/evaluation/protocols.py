"""Lightweight ``Protocol`` types for evaluation-compatible results.

Evaluators accept any object that satisfies these protocols — no
dependency on concrete ``SearchResult`` or ``RankedItem`` classes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RankedItemProtocol(Protocol):
    """Any ranked result with an ``item_id`` and a ``score``.

    Both ``SearchResult`` (retrieval) and ``RankedItem`` (personalization)
    satisfy this protocol.
    """

    item_id: str
    score: float
