"""Retrieval module — BM25, LSA, hybrid fusion.

Consumers should import from the individual sub-modules::

    from app.retrieval.tokenization import tokenize, build_item_text
    from app.retrieval.bm25 import BM25Config, BM25Index
    from app.retrieval.types import SearchResult
"""

from app.retrieval.bm25 import BM25Config, BM25Index
from app.retrieval.tokenization import build_item_text, tokenize
from app.retrieval.types import FusedSearchResult, SearchResult

__all__ = [
    "SearchResult",
    "FusedSearchResult",
    "tokenize",
    "build_item_text",
    "BM25Config",
    "BM25Index",
]
