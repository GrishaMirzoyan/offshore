#!/usr/bin/env python3
"""Step 0 probe — the GO/NO-GO gate for the DePIN pricing paper.

Checks, from an unrestricted network, every data source the paper depends on
and prints a GREEN / YELLOW / RED verdict per the master document:

  GREEN  = daily per-GPU-class pricing back to early 2024 exists
  YELLOW = recent history only -> start daily snapshot logging immediately,
           narrow the estimation window
  RED    = no usable history -> stop, rescope

What it checks
  1. Akash Console API network aggregates (daily since genesis):
       /v1/graph-data/{dailyUUsdSpent,dailyUAktSpent,activeGPU,activeLeaseCount,dailyLeaseCount}
  2. Akash Console per-model daily capacity/utilization:
       /v1/gpu-breakdown  (date x vendor x model: totalGpus, leasedGpus, utilization)
  3. Akash Console current GPU price snapshot:
       /v1/gpu-prices     (min/max/avg/weighted/median USD per model) — saved,
       becomes day 1 of the snapshot campaign
  4. CoinGecko AKT/USD daily (price + market cap -> implied supply/emissions)
  5. Wayback Machine coverage of historical /v1/gpu-prices responses
     (the recovery path for pre-campaign model-level price history)

Run:  python3 probe_pipeline.py [--out probe_out]
No credentials required. Writes probe_report.json plus raw responses.

NOTE (2026-07-16): could not be run from the Claude Code sandbox — its egress
allowlist blocks console.akash.network, coingecko.com and web.archive.org.
Run from a normal machine. Source-code review of the Console API (see
docs/step0_findings.md) already established which endpoints exist and their
shapes; this script measures the DEPTH actually returned.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

CONSOLE = "https://console.akash.network/api"
GRAPHS = ["dailyUUsdSpent", "dailyUAktSpent", "dailyLeaseCount", "activeLeaseCount", "activeGPU"]
COINGECKO = "https://api.coingecko.com/api/v3/coins/akash-network/market_chart?vs_currency=usd&days=max&interval=daily"
WAYBACK_CDX = "http://web.archive.org/cdx/search/cdx?url={target}&output=json&fl=timestamp,statuscode&filter=statuscode:200&collapse=timestamp:8"
WAYBACK_TARGETS = [
    "console.akash.network/api/v1/gpu-prices",
    "api.cloudmos.io/v1/gpu-prices",
    "gpus.akash.network*",
    "akash.network/pricing/gpus*",
]

EARLY_2024 = "2024-03-01"  # master doc: "daily pricing back to early 2024"


def get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "depin-step0-probe/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def save(out, name, obj):
    path = os.path.join(out, name)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=str)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="probe_out")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    report = {"run_at_utc": datetime.now(timezone.utc).isoformat(), "checks": {}}

    # 1. graph-data depth
    for g in GRAPHS:
        key = f"graph-data/{g}"
        try:
            d = get_json(f"{CONSOLE}/v1/graph-data/{g}")
            snaps = d.get("snapshots", [])
            first = snaps[0]["date"][:10] if snaps else None
            last = snaps[-1]["date"][:10] if snaps else None
            save(args.out, f"graph_{g}.json", d)
            report["checks"][key] = {"ok": bool(snaps), "days": len(snaps), "first": first, "last": last}
        except Exception as e:
            report["checks"][key] = {"ok": False, "error": str(e)}

    # 2. gpu-breakdown depth (per-model capacity/utilization)
    try:
        d = get_json(f"{CONSOLE}/v1/gpu-breakdown")
        dates = sorted({row["date"][:10] for row in d})
        models = sorted({f'{row["vendor"]}/{row["model"]}' for row in d})
        save(args.out, "gpu_breakdown.json", d)
        report["checks"]["gpu-breakdown"] = {
            "ok": bool(dates), "days": len(dates),
            "first": dates[0] if dates else None, "last": dates[-1] if dates else None,
            "n_models": len(models),
        }
    except Exception as e:
        report["checks"]["gpu-breakdown"] = {"ok": False, "error": str(e)}

    # 3. current gpu-prices snapshot — day 1 of the logging campaign
    try:
        d = get_json(f"{CONSOLE}/v1/gpu-prices")
        n_priced = sum(1 for m in d.get("models", []) if m.get("price"))
        save(args.out, f"gpu_prices_{datetime.now(timezone.utc):%Y%m%d}.json", d)
        report["checks"]["gpu-prices"] = {"ok": n_priced > 0, "models_priced": n_priced}
    except Exception as e:
        report["checks"]["gpu-prices"] = {"ok": False, "error": str(e)}

    # 4. CoinGecko AKT/USD
    try:
        d = get_json(COINGECKO)
        prices = d.get("prices", [])
        first = datetime.fromtimestamp(prices[0][0] / 1000, tz=timezone.utc).date().isoformat() if prices else None
        save(args.out, "coingecko_akt_market_chart.json", d)
        report["checks"]["akt-usd"] = {"ok": bool(prices), "days": len(prices), "first": first,
                                       "has_market_caps": bool(d.get("market_caps"))}
    except Exception as e:
        report["checks"]["akt-usd"] = {"ok": False, "error": str(e)}

    # 5. Wayback coverage of gpu-prices (historical model-level price recovery)
    wb = {}
    for target in WAYBACK_TARGETS:
        try:
            rows = get_json(WAYBACK_CDX.format(target=urllib.parse.quote(target, safe="*/")))
            ts = [r[0] for r in rows[1:]] if rows else []
            wb[target] = {"snapshots": len(ts), "first": ts[0][:8] if ts else None, "last": ts[-1][:8] if ts else None}
        except Exception as e:
            wb[target] = {"error": str(e)}
    save(args.out, "wayback_coverage.json", wb)
    report["checks"]["wayback"] = wb

    # ---- verdict ----
    c = report["checks"]
    agg_ok = all(c.get(f"graph-data/{g}", {}).get("ok") and (c[f"graph-data/{g}"].get("first") or "9999") <= EARLY_2024
                 for g in ("dailyUUsdSpent", "activeLeaseCount"))
    akt_ok = c.get("akt-usd", {}).get("ok", False)
    model_price_history = any(
        isinstance(v, dict) and v.get("snapshots", 0) >= 20 and (v.get("first") or "99999999") <= EARLY_2024.replace("-", "")
        for v in wb.values()
    )
    if agg_ok and akt_ok and model_price_history:
        verdict = "GREEN"
        note = "Daily aggregates + AKT/USD + archived model-level prices back to early 2024. Full design."
    elif agg_ok and akt_ok:
        verdict = "YELLOW"
        note = ("Daily network aggregates and AKT/USD reach early 2024, but model-level PRICE history is "
                "recent-only. Start daily snapshot logging NOW (scripts/snapshot_gpu_prices.py), use "
                "network-level price indices for the long window, model-level for the recent window.")
    else:
        verdict = "RED"
        note = "Core aggregates or AKT/USD unavailable. Stop and rescope."
    report["verdict"] = verdict
    report["note"] = note

    save(args.out, "probe_report.json", report)
    print(json.dumps(report, indent=2, default=str))
    print(f"\nSTEP 0 VERDICT: {verdict}\n{note}")


if __name__ == "__main__":
    main()
