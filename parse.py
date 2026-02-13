from __future__ import annotations

import argparse
import json
from decimal import Decimal
from typing import Any

from .aggregate import build_aggregation
from .parse import load_degiro_csv, row_to_event
from .classify import event_kind, enrich_trade_fields
from collections import Counter



class DecimalEncoder(json.JSONEncoder):
    def default(self, o: Any):
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="Path to DEGIRO Account.csv export")
    ap.add_argument("--out", default="aggregation.json", help="Output JSON filename")
    args = ap.parse_args()

    df = load_degiro_csv(args.csv)
    c = Counter()
    for _, row in df.iterrows():
        ev = enrich_trade_fields(row_to_event(row))
        k = event_kind(ev)
        if k == "OTHER":
            c[ev.description] += 1

    for desc, n in c.most_common(30):
        print(n, desc)

    
    agg = build_aggregation(df)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2, cls=DecimalEncoder)

    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
