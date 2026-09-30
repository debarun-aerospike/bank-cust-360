from __future__ import annotations

from aerospike_helpers.operations import operations as ops

from app import aerospike_client as as_client


def touch_customer(customer_id: str, ts_ms: int) -> None:
    client = as_client.get_client()
    key = (as_client.ns(), "customers", customer_id)
    client.operate(key, [ops.write("lastTouchAt", int(ts_ms))])


def overwrite_booking_bucket(account_id: str, bin_name: str, value: int) -> None:
    client = as_client.get_client()
    key = (as_client.ns(), "booking", account_id)
    client.operate(key, [ops.write(bin_name, int(value))])
