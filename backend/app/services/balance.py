"""Pure balance helpers — integer minor units → display major units."""

from __future__ import annotations

from typing import Any, Mapping


DEPOSIT_LINES = frozenset({"SAVINGS_CURRENT", "TERM_DEPOSIT"})
CREDIT_LINES = frozenset({"LOAN", "CARD"})


def balance_paise(product_line: str, bins: Mapping[str, Any] | None) -> int:
    if not bins:
        return 0
    if product_line in DEPOSIT_LINES:
        if any(k not in bins for k in ("ledger", "hold", "float")):
            return 0
        available = int(bins["ledger"]) - int(bins["hold"]) - int(bins["float"])
        # Savings/current (and same-formula deposits): never show a negative available balance.
        if product_line == "SAVINGS_CURRENT":
            return max(0, available)
        return available
    if product_line in CREDIT_LINES:
        if any(k not in bins for k in ("principal", "interest")):
            return 0
        return int(bins["principal"]) + int(bins["interest"])
    return 0


def paise_to_inr(paise: int) -> float:
    """Round half away from zero to 2 decimal places; return float major units."""
    sign = -1 if paise < 0 else 1
    a = abs(int(paise))
    # half away from zero at 0.005 major = 0.5 minor — already integer minor units
    whole, frac = divmod(a, 100)
    return sign * (whole + frac / 100.0)
