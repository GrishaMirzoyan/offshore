#!/usr/bin/env python3
"""Daily snapshot logger for Akash GPU prices — the YELLOW-path data campaign.

Appends one dated snapshot per day of:
  /v1/gpu-prices     model-level min/max/avg/weighted/median USD prices
  /v1/gpu-breakdown  model-level capacity + leased counts + utilization
  /v1/graph-data/*   network aggregates (spend, leases, active GPUs)

Layout: data/snapshots/YYYY-MM-DD/{gpu_prices,gpu_breakdown,graph_<name>}.json
Idempotent per UTC day — safe to run from cron/CI more than once.

Cron (user machine):    5 0 * * *  cd <repo> && python3 depin-research/scripts/snapshot_gpu_prices.py
GitHub Actions template: see docs/snapshot_workflow_template.yml

Aggregation note (master doc prep rule 3): gpu-prices is computed by the
Console API from currently OPEN bids/leases — treat it as the posted/ask side;
executed-lease medians come later from indexer/Numia. Both are logged so the
ask-vs-executed wedge itself becomes measurable once the executed series lands.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

CONSOLE = "https://console.akash.network/api"
GRAPHS = ["dailyUUsdSpent", "dailyUAktSpent", "dailyLeaseCount", "activeLeaseCount", "activeGPU"]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "snapshots")


def get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "depin-snapshot/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main():
    day = datetime.now(timezone.utc).date().isoformat()
    out = os.path.join(ROOT, day)
    os.makedirs(out, exist_ok=True)
    targets = {"gpu_prices": f"{CONSOLE}/v1/gpu-prices", "gpu_breakdown": f"{CONSOLE}/v1/gpu-breakdown"}
    targets.update({f"graph_{g}": f"{CONSOLE}/v1/graph-data/{g}" for g in GRAPHS})

    failures = 0
    for name, url in targets.items():
        path = os.path.join(out, f"{name}.json")
        if os.path.exists(path):
            print(f"skip {name} (already logged for {day})")
            continue
        try:
            payload = {"pulled_at_utc": datetime.now(timezone.utc).isoformat(), "url": url, "data": get_json(url)}
            with open(path, "w") as f:
                json.dump(payload, f)
            print(f"ok   {name}")
        except Exception as e:
            failures += 1
            print(f"FAIL {name}: {e}", file=sys.stderr)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
