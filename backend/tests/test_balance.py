from app.services.balance import balance_paise, paise_to_inr


def test_deposit_balance():
    assert balance_paise("SAVINGS_CURRENT", {"ledger": 10050, "hold": 50, "float": 0}) == 10000
    assert paise_to_inr(10000) == 100.0


def test_loan_balance():
    assert balance_paise("LOAN", {"principal": 100000, "interest": 250}) == 100250
    assert round(paise_to_inr(100250), 2) == 1002.50


def test_missing_bins_zero():
    assert balance_paise("CARD", {"principal": 1}) == 0
    assert balance_paise("TERM_DEPOSIT", None) == 0
