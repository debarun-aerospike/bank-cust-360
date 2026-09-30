"""
Verify Gate 3 seed: inventory totals + Customer 360 assembly path for one ID.

Usage (always via uv):
  uv run python verify_c360.py --customer 0000001 --port 13000
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import aerospike
from aerospike import exception as ae

NS = "bank"


def balance_paise(product_line: str, bins: dict[str, Any] | None) -> int:
    if not bins:
        return 0
    if product_line in ("SAVINGS_CURRENT", "TERM_DEPOSIT"):
        if any(k not in bins for k in ("ledger", "hold", "float")):
            return 0
        return int(bins["ledger"]) - int(bins["hold"]) - int(bins["float"])
    if product_line in ("LOAN", "CARD"):
        if any(k not in bins for k in ("principal", "interest")):
            return 0
        return int(bins["principal"]) + int(bins["interest"])
    return 0


def fmt_inr(paise: int) -> str:
    # round half away from zero to 2 d.p. for display
    sign = -1 if paise < 0 else 1
    a = abs(paise)
    whole, frac = divmod(a, 100)
    return f"{sign * whole}.{frac:02d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--customer", default="0000001")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    args = parser.parse_args()

    client = aerospike.client({"hosts": [(args.host, args.port)]})
    try:
        _, _, inv = client.get((NS, "inventory", "totals"))
        print("inventory/totals:", inv)

        _, _, cust = client.get((NS, "customers", args.customer))
        print("customer:", args.customer, cust)

        try:
            _, _, link = client.get((NS, "cust_accts", args.customer))
        except ae.RecordNotFound:
            print("cust_accts: (none)")
            return 0

        acct_ids = list(link.get("acctIds") or [])
        print("acctIds:", acct_ids)

        enriched = []
        for aid in acct_ids:
            try:
                _, _, acct = client.get((NS, "accounts", aid))
            except ae.RecordNotFound:
                continue
            desc = acct.get("productDesc") or ""
            if not desc:
                continue
            if acct.get("acctStatus") != "Active":
                continue
            try:
                _, _, book = client.get((NS, "booking", aid))
            except ae.RecordNotFound:
                book = None
            bal = balance_paise(acct["productLine"], book)
            enriched.append(
                (
                    0 if acct.get("ownership") == "PRIMARY" else 1,
                    {
                        "accountId": aid,
                        "productLine": acct["productLine"],
                        "currency": acct.get("currency"),
                        "accountStatus": acct.get("acctStatus"),
                        "productDescription": desc,
                        "balanceINR": fmt_inr(bal),
                    },
                )
            )

        enriched.sort(key=lambda t: t[0])
        print("C360 accounts:")
        for _, r in enriched:
            print(" ", r)
        return 0
    except ae.RecordNotFound as exc:
        print(f"Record not found: {exc}", file=sys.stderr)
        return 1
    except ae.AerospikeError as exc:
        print(f"Aerospike error: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
