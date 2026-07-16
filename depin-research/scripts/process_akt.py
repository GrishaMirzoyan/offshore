#!/usr/bin/env python3
"""Raw -> processed: AKT daily market series from the Coin Metrics community archive.

Input : data/raw/coinmetrics/akt.csv
Output: data/processed/akt_market_daily.csv
        (date, market_cap_usd, volume_usd, price_usd [trailing week only])

The Coin Metrics community file carries full daily market cap + reported spot
volume from 2021-03-12, but ReferenceRateUSD only for the trailing week.
The full daily PRICE series therefore comes from scripts/pull_akt_usd.py
(CoinGecko, run from an unrestricted machine); this file is the cross-check
and the market-cap series of record.
"""

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw", "coinmetrics", "akt.csv")
OUT = os.path.join(HERE, "..", "data", "processed", "akt_market_daily.csv")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "market_cap_usd", "volume_usd", "price_usd"])
        n = 0
        for r in csv.DictReader(open(RAW)):
            if not (r["CapMrktEstUSD"] or r["ReferenceRateUSD"]):
                continue
            w.writerow([r["time"], r["CapMrktEstUSD"] or "",
                        r["volume_reported_spot_usd_1d"] or "", r["ReferenceRateUSD"] or ""])
            n += 1
    print(f"wrote {OUT} ({n} rows)")


if __name__ == "__main__":
    main()
