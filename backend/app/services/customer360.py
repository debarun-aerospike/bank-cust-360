from __future__ import annotations

from collections import defaultdict

from app.repositories import aerospike_repo as repo
from app.repositories.writes import overwrite_booking_bucket, touch_customer
from app.schemas.models import (
    AccountRow,
    Customer360Response,
    CustomerBlock,
    ProductLine,
)
from app.services.balance import balance_paise, paise_to_inr


def assemble_customer_360(
    customer_id: str,
    *,
    status_filter: str | None = "Active",
    require_active_customer: bool = False,
) -> Customer360Response:
    cust = repo.get_customer(customer_id)
    customer_status = cust.get("status") or ""
    if require_active_customer and customer_status != "Active":
        raise IneligibleCustomerError(
            f"Customer {customer_id} is {customer_status or 'unknown'} and cannot use netbanking"
        )

    acct_ids = repo.get_cust_accts(customer_id)
    accounts = repo.get_accounts(acct_ids)
    bookings = repo.get_bookings(acct_ids)

    rows: list[AccountRow] = []
    for aid in acct_ids:
        acct = accounts.get(aid)
        if not acct:
            continue
        desc = (acct.get("productDesc") or "").strip()
        if not desc:
            continue
        status = acct.get("acctStatus") or ""
        if status_filter and status != status_filter:
            continue
        pl = acct.get("productLine") or ""
        try:
            product_line = ProductLine(pl)
        except ValueError:
            continue
        bal = paise_to_inr(balance_paise(pl, bookings.get(aid)))
        ownership = acct.get("ownership") or "PRIMARY"
        if ownership not in ("PRIMARY", "JOINT"):
            ownership = "PRIMARY"
        rows.append(
            AccountRow(
                accountId=aid,
                productLine=product_line,
                currency=acct.get("currency") or "INR",
                accountStatus=status,
                productDescription=desc,
                balance=round(bal, 2),
                ownership=ownership,  # type: ignore[arg-type]
            )
        )

    rows.sort(key=lambda r: (0 if r.ownership == "PRIMARY" else 1, r.accountId))

    by_line: dict[str, list[AccountRow]] = defaultdict(list)
    for r in rows:
        by_line[r.productLine.value].append(r)

    return Customer360Response(
        customer=CustomerBlock(
            customerId=customer_id,
            customerNo=customer_id,
            salutation=cust.get("salutation") or "",
            name=cust.get("name") or "",
            status=customer_status,
        ),
        accounts=rows,
        accountsByProductLine=dict(by_line),
    )


class IneligibleCustomerError(Exception):
    """Customer exists but is not eligible for netbanking (e.g. Dormant)."""


__all__ = [
    "assemble_customer_360",
    "touch_customer",
    "overwrite_booking_bucket",
    "NotFoundError",
    "IneligibleCustomerError",
]

NotFoundError = repo.NotFoundError
