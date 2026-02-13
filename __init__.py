from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class CashEvent:
    date: str
    product: str                  # normalized: "<CASH>" for empty product
    isin: str
    description: str
    currency: str
    amount: Decimal               # signed cash amount
    order_id: str

    # Optional trade fields (only set when we can parse them)
    side: Optional[str] = None    # "BUY" | "SELL"
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    trade_currency: Optional[str] = None
