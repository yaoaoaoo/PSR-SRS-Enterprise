"""Evaluation module — offline IR metrics.

Consumers should import from the individual sub-modules::

    from app.evaluation.metrics import evaluate_query, evaluate_all, macro_average
"""

from app.evaluation.metrics import (
    MetricResult,
    evaluate_all,
    evaluate_query,
    macro_average,
)
from app.evaluation.protocols import RankedItemProtocol

__all__ = [
    "MetricResult",
    "evaluate_query",
    "evaluate_all",
    "macro_average",
    "RankedItemProtocol",
]
