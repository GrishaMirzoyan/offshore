#!/usr/bin/env python3
"""Pull full daily AKT/USD history from CoinGecko (price, market cap, volume).

Also derives:
  implied_supply     = market_cap / price          (circulating, CoinGecko basis)
  net_issuance_akt   = day-over-day change in implied_supply
                       (the realized-emissions series for the H2 test; after
                        2026-03-23 it is net of BME burns by construction)

Output: data/raw/coingecko/akt_usd_daily.csv + provenance JSON.

Run from an unrestricted machine (the Claude sandbox egress blocks CoinGecko):
  python3 pull_akt_usd.py [--api-key CG-...]   # demo/pro key optional

Fallback already in the repo: data/raw/coinmetrics/akt.csv (Coin Metrics
community archive; full daily market cap + volume 2021-03-12..2026-05-24, but
ReferenceRateUSD only for the trailing week — hence CoinGecko is preferred).
"""

import argparse
import csv
import json
import os
import urllib.request
from datetime import datetime, timezone

URL = "https://api.coingecko.com/api/v3/coins/akash-network/market_chart?vs_currency=usd&days=max&interval=daily"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("COINGECKO_API_KEY", ""))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "coingecko"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    headers = {"User-Agent": "depin-research/0.1"}
    if args.api_key:
        headers["x-cg-demo-api-key"] = args.api_key
    req = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)

    def by_day(series):
        out = {}
        for ts, v in series:
            day = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
            out[day] = v  # last observation of the day wins
        return out

    prices, caps, vols = by_day(d["prices"]), by_day(d["market_caps"]), by_day(d["total_volumes"])
    days = sorted(prices)
    path = os.path.join(args.out, "akt_usd_daily.csv")
    prev_supply = None
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "price_usd", "market_cap_usd", "volume_usd", "implied_supply_akt", "net_issuance_akt"])
        for day in days:
            p, c, v = prices.get(day), caps.get(day), vols.get(day)
            supply = (c / p) if (p and c) else None
            issuance = (supply - prev_supply) if (supply is not None and prev_supply is not None) else None
            w.writerow([day, p, c, v,
                        round(supply, 2) if supply is not None else "",
                        round(issuance, 2) if issuance is not None else ""])
            if supply is not None:
                prev_supply = supply

    with open(os.path.join(args.out, "provenance_coingecko.json"), "w") as f:
        json.dump({
            "dataset": "AKT/USD daily price, market cap, volume; derived supply and net issuance",
            "source": "CoinGecko API v3, coin id akash-network",
            "endpoint": URL,
            "pull_date_utc": datetime.now(timezone.utc).isoformat(),
            "rows": len(days), "first": days[0], "last": days[-1],
            "notes": [
                "UTC daily; last observation of day.",
                "implied_supply = market_cap/price (CoinGecko circulating basis) — validate a week against chain supply before using net_issuance in regressions.",
                "net_issuance is NET of BME burns after 2026-03-23; gross emissions need the mint-module series (see emissions table).",
            ],
        }, f, indent=2)
    print(f"wrote {path}: {len(days)} days ({days[0]}..{days[-1]})")


if __name__ == "__main__":
    main()
