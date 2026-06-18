"""Pre-import validation of CSV data.

Validates referential integrity, value ranges, and data types before
any database writes.  Strict mode: any failure aborts the import.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

_VALID_EVENT_TYPES = {"impression", "click", "favorite", "add_to_cart", "purchase"}


class ValidationError(Exception):
    """Raised when pre-import validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Validation failed with {len(errors)} error(s)")


def _parse_decimal(value: str, field: str, row_id: str) -> Decimal:
    try:
        d = Decimal(value)
        if d < 0:
            raise ValueError("negative")
        return d
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid {field} for {row_id}: {value!r}") from None


def _parse_float(value: str, field: str, row_id: str, lo: float, hi: float) -> float:
    try:
        f = float(value)
        if not (lo <= f <= hi):
            raise ValueError("out of range")
        return f
    except ValueError:
        raise ValueError(f"Invalid {field} for {row_id}: {value!r} (expected {lo}–{hi})") from None


def _parse_datetime(value: str, field: str, row_id: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Invalid {field} for {row_id}: {value!r}") from None


def _parse_json_list(value: str, field: str, row_id: str) -> list:
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            raise ValueError("not a list")
        return parsed
    except (json.JSONDecodeError, ValueError):
        raise ValueError(f"Invalid {field} JSON for {row_id}: {value!r}") from None


def _parse_bool(value: str, field: str, row_id: str) -> bool:
    v = value.strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    raise ValueError(f"Invalid {field} bool for {row_id}: {value!r}")


def _parse_int_opt(value: str, field: str, row_id: str, min_val: int | None = None) -> int | None:
    if value.strip() == "":
        return None
    try:
        v = int(value)
        if min_val is not None and v < min_val:
            raise ValueError("below minimum")
        return v
    except ValueError:
        raise ValueError(f"Invalid {field} for {row_id}: {value!r}") from None


def validate_items(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    parsed: list[dict[str, Any]] = []

    for r in rows:
        iid = r["item_id"].strip()
        if not iid:
            errors.append("item_id is empty")
            continue
        if iid in seen_ids:
            errors.append(f"Duplicate item_id: {iid!r}")
            continue
        seen_ids.add(iid)

        row_id = f"item {iid!r}"
        try:
            parsed.append(
                {
                    "item_id": iid,
                    "title": r["title"],
                    "description": r.get("description", ""),
                    "category": r["category"],
                    "subcategory": r["subcategory"],
                    "brand": r["brand"],
                    "price": _parse_decimal(r["price"], "price", row_id),
                    "quality_score": _parse_float(
                        r["quality_score"], "quality_score", row_id, 0, 1
                    ),
                    "popularity_score": _parse_float(
                        r["popularity_score"], "popularity_score", row_id, 0, 1
                    ),
                    "is_cold_start": _parse_bool(r["is_cold_start"], "is_cold_start", row_id),
                    "created_at": _parse_datetime(r["created_at"], "created_at", row_id),
                }
            )
        except ValueError as e:
            errors.append(str(e))

    if errors:
        raise ValidationError(errors)
    return parsed


def validate_users(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    parsed: list[dict[str, Any]] = []

    for r in rows:
        uid = r["user_id"].strip()
        if not uid:
            errors.append("user_id is empty")
            continue
        if uid in seen_ids:
            errors.append(f"Duplicate user_id: {uid!r}")
            continue
        seen_ids.add(uid)

        row_id = f"user {uid!r}"
        try:
            pref_cats = _parse_json_list(r["preferred_categories"], "preferred_categories", row_id)
            pref_brands = _parse_json_list(r["preferred_brands"], "preferred_brands", row_id)
            price_pref = r.get("price_preference", "").strip() or None

            parsed.append(
                {
                    "user_id": uid,
                    "preferred_categories": pref_cats,
                    "preferred_brands": pref_brands,
                    "price_preference": price_pref,
                    "activity_level": r.get("activity_level", "") or None,
                    "is_cold_start": _parse_bool(r["is_cold_start"], "is_cold_start", row_id),
                    "created_at": _parse_datetime(r["created_at"], "created_at", row_id),
                }
            )
        except (ValueError, json.JSONDecodeError) as e:
            errors.append(str(e))

    if errors:
        raise ValidationError(errors)
    return parsed


def validate_queries(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    parsed: list[dict[str, Any]] = []

    for r in rows:
        qid = r["query_id"].strip()
        if not qid:
            errors.append("query_id is empty")
            continue
        if qid in seen_ids:
            errors.append(f"Duplicate query_id: {qid!r}")
            continue
        seen_ids.add(qid)

        try:
            parsed.append(
                {
                    "query_id": qid,
                    "query_text": r["query_text"],
                    "intended_category": r.get("intended_category", "") or None,
                    "semantic_intent": r.get("semantic_intent", "") or None,
                    "created_at": _parse_datetime(r["created_at"], "created_at", qid),
                }
            )
        except ValueError as e:
            errors.append(str(e))

    if errors:
        raise ValidationError(errors)
    return parsed


def validate_qrels(
    rows: list[dict[str, str]],
    query_ids: set[str],
    item_ids: set[str],
) -> list[dict[str, Any]]:
    errors: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()
    parsed: list[dict[str, Any]] = []

    for r in rows:
        qid = r["query_id"].strip()
        iid = r["item_id"].strip()
        pair = (qid, iid)

        if pair in seen_pairs:
            errors.append(f"Duplicate qrel: query={qid!r} item={iid!r}")
            continue
        seen_pairs.add(pair)

        if qid not in query_ids:
            errors.append(f"Qrel references unknown query_id: {qid!r}")
        if iid not in item_ids:
            errors.append(f"Qrel references unknown item_id: {iid!r}")

        try:
            grade = int(r["relevance_grade"])
            if grade not in (1, 2, 3):
                raise ValueError("must be 1–3")
            parsed.append(
                {
                    "query_id": qid,
                    "item_id": iid,
                    "relevance_grade": grade,
                }
            )
        except ValueError as e:
            errors.append(f"Invalid relevance_grade for qrel {qid}/{iid}: {e}")

    if errors:
        raise ValidationError(errors)
    return parsed


def validate_events(
    rows: list[dict[str, str]],
    user_ids: set[str],
    item_ids: set[str],
    query_ids: set[str],
) -> list[dict[str, Any]]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    parsed: list[dict[str, Any]] = []

    for r in rows:
        eid = r["event_id"].strip()
        if not eid:
            errors.append("event_id is empty")
            continue
        if eid in seen_ids:
            errors.append(f"Duplicate event_id: {eid!r}")
            continue
        seen_ids.add(eid)

        row_id = f"event {eid!r}"

        etype = r["event_type"].strip()
        if etype not in _VALID_EVENT_TYPES:
            errors.append(f"Invalid event_type for {row_id}: {etype!r}")
            continue

        uid = r["user_id"].strip()
        if uid not in user_ids:
            errors.append(f"Event {eid!r} references unknown user_id: {uid!r}")

        qid_raw = r.get("query_id", "").strip()
        qid = qid_raw if qid_raw else None
        if qid is not None and qid not in query_ids:
            errors.append(f"Event {eid!r} references unknown query_id: {qid!r}")

        iid = r["item_id"].strip()
        if iid not in item_ids:
            errors.append(f"Event {eid!r} references unknown item_id: {iid!r}")

        try:
            ts = _parse_datetime(r["timestamp"], "timestamp", row_id)
            position = _parse_int_opt(r.get("position", ""), "position", row_id, min_val=1)
            click_dur = _parse_int_opt(
                r.get("click_duration_ms", ""), "click_duration_ms", row_id, min_val=0
            )
            cart_qty = _parse_int_opt(
                r.get("add_to_cart_quantity", ""), "add_to_cart_quantity", row_id, min_val=0
            )
            purchase = None
            if r.get("purchase_amount", "").strip():
                d = Decimal(r["purchase_amount"])
                if d < 0:
                    raise ValueError("negative")
                purchase = float(d)

            parsed.append(
                {
                    "event_id": eid,
                    "event_type": etype,
                    "request_id": r.get("request_id", "").strip(),
                    "session_id": r.get("session_id", "").strip(),
                    "user_id": uid,
                    "query_id": qid,
                    "query_text": r.get("query_text", "") or None,
                    "item_id": iid,
                    "position": position,
                    "timestamp": ts,
                    "click_duration_ms": click_dur,
                    "add_to_cart_quantity": cart_qty,
                    "purchase_amount": purchase,
                }
            )
        except ValueError as e:
            errors.append(str(e))

    if errors:
        raise ValidationError(errors)
    return parsed
