from __future__ import annotations

import re
from dataclasses import replace
from decimal import Decimal
from typing import Optional

from .models import CashEvent


# Trade description examples:
# "Koop 5 @ 143,46 EUR"
# "Verkoop 10 @ 20,25 EUR"
_TRADE_RE = re.compile(
    r"^(Koop|Verkoop)\s+([0-9.,]+)\s+@\s+([0-9.,]+)\s+([A-Z]{3})\b",
    re.IGNORECASE,
)


def _parse_decimal_eu_str(s: str) -> Decimal:
    return Decimal(s.replace(".", "").replace(",", "."))


def enrich_trade_fields(ev: CashEvent) -> CashEvent:
    m = _TRADE_RE.match(ev.description)
    if not m:
        return ev

    side_nl = m.group(1).lower()
    qty = _parse_decimal_eu_str(m.group(2))
    price = _parse_decimal_eu_str(m.group(3))
    tcur = m.group(4)

    side = "BUY" if side_nl.startswith("koop") else "SELL"
    return replace(ev, side=side, quantity=qty, price=price, trade_currency=tcur)


def event_kind(ev: CashEvent) -> str:
    """
    Returns a normalized category key.
    Extend this as you discover more Omschrijving variants.
    """
    d = ev.description.lower()

    # Dividends
    if "dividend" in d and "tax" not in d and "belasting" not in d:
        return "DIVIDEND"

    # Dividend tax / withholding
    if "dividend" in d and ("tax" in d or "belasting" in d):
        return "DIVIDEND_TAX"

    # Interest
    if "interest" in d or d.startswith("rente"):
        return "INTEREST"

    # DEGIRO / exchange connectivity fees
    if "aansluitingskosten" in d:
        return "CONNECTIVITY_FEE"

    # Transaction costs
    if "transactiekosten" in d or "kosten van derden" in d:
        return "TRANSACTION_FEE"

    # External ADR/GDR costs
    if "adr/gdr" in d and "kosten" in d:
        return "ADR_GDR_FEE"

    # Cash sweep transfers between DEGIRO and flatex cash account
    if "cash sweep transfer" in d:
        return "CASH_SWEEP"

    # Bank transfers (wording varies)
    if d.startswith("overboeking van"):
        return "TRANSFER_IN"
    if d.startswith("overboeking naar"):
        return "TRANSFER_OUT"

    # iDEAL reservations (often used for deposits/withdrawals staging)
    if "reservation ideal" in d:
        return "IDEAL_RESERVATION"

    # Trades
    if d.startswith("koop "):
        return "TRADE_BUY"
    if d.startswith("verkoop "):
        return "TRADE_SELL"

    # Corporate actions (keep them visible, you can split later)
    if "stock split" in d:
        return "CORP_ACTION_STOCK_SPLIT"
    if "spin-off" in d:
        return "CORP_ACTION_SPINOFF"
    if "fusie" in d:
        return "CORP_ACTION_MERGER"
    if "delisting" in d:
        return "CORP_ACTION_DELISTING"
    if "wijziging isin" in d:
        return "CORP_ACTION_ISIN_CHANGE"

    # Capital distributions (you already saw "Kapitaalsuitkering")
    if "kapitaalsuitkering" in d:
        return "CAPITAL_DISTRIBUTION"

    return "OTHER"
