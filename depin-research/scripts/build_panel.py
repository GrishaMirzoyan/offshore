#!/usr/bin/env python3
"""Assemble the analysis panel: date x platform x GPU class x price (USD/GPU-hr).

Current inputs (present in repo):
  data/processed/aws_gpu_benchmark_monthly.csv   AWS on-demand, monthly steps
  data/processed/akt_market_daily.csv            AKT market cap/volume (Coin Metrics)
Inputs that land after user-machine pulls:
  data/raw/coingecko/akt_usd_daily.csv           full AKT/USD daily (pull_akt_usd.py)
  data/snapshots/YYYY-MM-DD/gpu_prices.json      Akash model-level prices (campaign)
  <executed-lease extract>                       from Numia/indexer (see step0_findings.md)

Output: data/processed/panel_daily.csv with columns
  date, platform, gpu_class, price_usd_per_gpu_hr, price_kind, akt_price_usd, akt_mcap_usd

Prep rules honored (master doc): UTC dates; missing days logged to
data/processed/panel_missing_days.txt, never filled; AWS monthly prices are
step-functions carried forward WITHIN their effective month only (that is the
publisher's own effective range, not imputation).
"""

import csv
import glob
import json
import os
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "processed", "panel_daily.csv")
MISSING_LOG = os.path.join(DATA, "processed", "panel_missing_days.txt")

GPU_CLASS = {"p5.48xlarge": "H100-80GB", "p4d.24xlarge": "A100-40GB", "p4de.24xlarge": "A100-80GB",
             "p5e.48xlarge": "H200", "p5en.48xlarge": "H200", "p6-b200.48xlarge": "B200"}
# Akash console model names -> comparable class (extend as snapshots accumulate)
AKASH_CLASS = {"h100": "H100-80GB", "a100": "A100-80GB", "h200": "H200", "b200": "B200"}


def month_days(month):
    y, m = int(month[:4]), int(month[5:7])
    d = date(y, m, 1)
    while d.month == m:
        yield d.isoformat()
        d += timedelta(days=1)


def load_akt():
    akt = {}
    cg = os.path.join(DATA, "raw", "coingecko", "akt_usd_daily.csv")
    if os.path.exists(cg):
        for r in csv.DictReader(open(cg)):
            akt[r["date"]] = (r["price_usd"], r["market_cap_usd"])
    else:
        for r in csv.DictReader(open(os.path.join(DATA, "processed", "akt_market_daily.csv"))):
            akt[r["date"]] = (r["price_usd"], r["market_cap_usd"])
    return akt


def main():
    akt = load_akt()
    rows, missing = [], []

    # AWS: expand monthly effective prices to days (publisher-defined step function)
    for r in csv.DictReader(open(os.path.join(DATA, "processed", "aws_gpu_benchmark_monthly.csv"))):
        for d in month_days(r["month"]):
            rows.append({"date": d, "platform": "aws-ondemand", "gpu_class": r["gpu_model"],
                         "price_usd_per_gpu_hr": r["price_usd_per_gpu_hr"], "price_kind": "posted-ondemand"})

    # Akash: snapshot campaign files (weighted average of open bids per model)
    for path in sorted(glob.glob(os.path.join(DATA, "snapshots", "*", "gpu_prices.json"))):
        day = os.path.basename(os.path.dirname(path))
        payload = json.load(open(path))
        for m in payload.get("data", {}).get("models", []):
            price = m.get("price") or {}
            cls = AKASH_CLASS.get((m.get("model") or "").lower())
            if cls and price.get("weightedAverage") is not None:
                rows.append({"date": day, "platform": "akash", "gpu_class": cls,
                             "price_usd_per_gpu_hr": price["weightedAverage"],
                             "price_kind": "posted-ask-weightedavg"})
        if not payload.get("data", {}).get("models"):
            missing.append(f"{day} akash gpu_prices: empty payload")

    for r in rows:
        p, c = akt.get(r["date"], ("", ""))
        r["akt_price_usd"], r["akt_mcap_usd"] = p, c

    rows.sort(key=lambda r: (r["date"], r["platform"], r["gpu_class"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "platform", "gpu_class", "price_usd_per_gpu_hr",
                                          "price_kind", "akt_price_usd", "akt_mcap_usd"])
        w.writeheader()
        w.writerows(rows)
    with open(MISSING_LOG, "w") as f:
        f.write("\n".join(missing) + ("\n" if missing else ""))
    print(f"wrote {OUT}: {len(rows)} rows; {len(missing)} gaps logged to {MISSING_LOG}")


if __name__ == "__main__":
    main()
