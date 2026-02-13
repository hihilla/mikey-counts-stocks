from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal
from typing import Any, DefaultDict, Dict

import pandas as pd

from .classify import enrich_trade_fields, event_kind
from .models import CashEvent
from .parse import row_to_event


def _new_entry() -> dict[str, Any]:
    # You can add more bucket dicts here without touching the loop.
    return {
        "isin": "",
        "by_kind": defaultdict(lambda: defaultdict(lambda: Decimal("0"))),  # kind -> currency -> total
        "trades": {
            "BUY": {"quantity": Decimal("0"), "gross": defaultdict(lambda: Decimal("0"))},
            "SELL": {"quantity": Decimal("0"), "gross": defaultdict(lambda: Decimal("0"))},
        },
        "events_count": 0,
    }


def _ensure_isin(entry: dict[str, Any], isin: str) -> None:
    if isin and not entry["isin"]:
        entry["isin"] = isin


def _add_cash(entry: dict[str, Any], kind: str, currency: str, amount: Decimal) -> None:
    entry["by_kind"][kind][currency] += amount


def _add_trade(entry: dict[str, Any], ev: CashEvent) -> None:
    # Trade “gross” is the cash amount on that row (already signed in the CSV)
    # For buys: amount is typically negative; for sells: positive.
    if not ev.side or ev.quantity is None:
        return
    side = ev.side
    entry["trades"][side]["quantity"] += ev.quantity
    entry["trades"][side]["gross"][ev.currency] += ev.amount


def _finalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    by_kind = {k: dict(v) for k, v in entry["by_kind"].items()}

    dividends = by_kind.get("DIVIDEND", {})
    dividend_tax = by_kind.get("DIVIDEND_TAX", {})

    currencies = set(dividends) | set(dividend_tax)
    net_dividends: dict[str, Decimal] = {
        cur: dividends.get(cur, Decimal("0")) + dividend_tax.get(cur, Decimal("0"))
        for cur in currencies
    }

    trades = entry["trades"]
    trades_out = {
        side: {
            "quantity": trades[side]["quantity"],
            "gross": dict(trades[side]["gross"]),
        }
        for side in ("BUY", "SELL")
    }

    return {
        "isin": entry["isin"],
        "events_count": entry["events_count"],
        "by_kind": by_kind,
        "dividends": dividends,
        "dividend_tax": dividend_tax,
        "net_dividends": net_dividends,
        "trades": trades_out,
    }


def build_aggregation(df: pd.DataFrame) -> dict[str, Any]:
    agg: DefaultDict[str, dict[str, Any]] = defaultdict(_new_entry)

    for _, row in df.iterrows():
        ev = enrich_trade_fields(row_to_event(row))
        kind = event_kind(ev)

        entry = agg[ev.product]
        entry["events_count"] += 1
        _ensure_isin(entry, ev.isin)

        _add_cash(entry, kind, ev.currency, ev.amount)
        _add_trade(entry, ev)

    return {product: _finalize_entry(entry) for product, entry in agg.items()}
