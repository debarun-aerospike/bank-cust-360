from __future__ import annotations

from typing import Any

from aerospike import exception as ae

from app import aerospike_client as as_client


class NotFoundError(Exception):
    pass


def _normalize_get_many_item(item: Any) -> tuple[Any, dict[str, Any] | None]:
    """Handle list[(key, meta, bins)] shapes across client versions."""
    if item is None:
        return None, None
    if isinstance(item, tuple) and len(item) >= 3:
        key, _meta, bins = item[0], item[1], item[2]
        return key, bins
    if isinstance(item, tuple) and len(item) == 2:
        return item[0], item[1]
    return None, None


def _get(set_name: str, user_key: str) -> dict[str, Any] | None:
    client = as_client.get_client()
    try:
        _, _, bins = client.get((as_client.ns(), set_name, user_key))
        return bins or {}
    except ae.RecordNotFound:
        return None


def get_customer(customer_id: str) -> dict[str, Any]:
    bins = _get("customers", customer_id)
    if bins is None:
        raise NotFoundError(f"customer {customer_id}")
    return bins


def get_cust_accts(customer_id: str) -> list[str]:
    bins = _get("cust_accts", customer_id)
    if not bins:
        return []
    return list(bins.get("acctIds") or [])


def _batch_get(set_name: str, ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    client = as_client.get_client()
    seen: set[str] = set()
    uniq: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    keys = [(as_client.ns(), set_name, i) for i in uniq]
    out: dict[str, dict[str, Any]] = {}
    raw = client.get_many(keys)
    # dict keyed by key tuple in some versions; list in others
    if isinstance(raw, dict):
        iterable = raw.items()
        for key_tuple, rec in iterable:
            if rec is None:
                continue
            bins = rec[-1] if isinstance(rec, tuple) else rec
            if bins is None:
                continue
            uk = key_tuple[2]
            if isinstance(uk, bytes):
                uk = uk.decode()
            out[str(uk)] = bins
        return out

    for item in raw or []:
        key_tuple, bins = _normalize_get_many_item(item)
        if key_tuple is None or bins is None:
            continue
        uk = key_tuple[2]
        if isinstance(uk, bytes):
            uk = uk.decode()
        out[str(uk)] = bins
    return out


def get_accounts(account_ids: list[str]) -> dict[str, dict[str, Any]]:
    return _batch_get("accounts", account_ids)


def get_bookings(account_ids: list[str]) -> dict[str, dict[str, Any]]:
    return _batch_get("booking", account_ids)


def get_inventory() -> dict[str, Any]:
    return _get("inventory", "totals") or {}
