from app.services.balance import balance_paise, paise_to_inr


def test_deposit_balance():
    assert balance_paise("SAVINGS_CURRENT", {"ledger": 10050, "hold": 50, "float": 0}) == 10000
    assert paise_to_inr(10000) == 100.0


def test_savings_never_negative():
    assert balance_paise("SAVINGS_CURRENT", {"ledger": 100, "hold": 80, "float": 50}) == 0


def test_term_deposit_can_reflect_raw_available():
    # Term deposits keep the raw formula (may be negative if buckets are inconsistent).
    assert balance_paise("TERM_DEPOSIT", {"ledger": 100, "hold": 80, "float": 50}) == -30


def test_loan_balance():
    assert balance_paise("LOAN", {"principal": 100000, "interest": 250}) == 100250
    assert round(paise_to_inr(100250), 2) == 1002.50


def test_missing_bins_zero():
    assert balance_paise("CARD", {"principal": 1}) == 0
    assert balance_paise("TERM_DEPOSIT", None) == 0
