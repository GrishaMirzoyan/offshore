#!/usr/bin/env python3
"""Pull historical AWS EC2 on-demand pricing for GPU instances (H100/A100 class).

Source: AWS Price List Bulk API (public, no credentials required)
  https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/index.json  (version index)
  https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/{version}/us-east-1/index.json

AWS publishes roughly one offer version per month; each version file carries a
versionEffectiveBeginDate, so iterating versions yields a monthly on-demand
price series from the primary source. Files are ~360 MB each and are streamed
(never written to disk); only products/terms for the target instance types are
kept.

Output: data/raw/aws/ec2_gpu_ondemand_history.csv (one row per version x SKU x rate)
        data/raw/aws/provenance_aws.json

Usage: python3 pull_aws_gpu_pricing.py [--since 20230101] [--out DIR]
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

import ijson
import urllib.request

BASE = "https://pricing.us-east-1.amazonaws.com"
INDEX = BASE + "/offers/v1.0/aws/AmazonEC2/index.json"
REGION = "us-east-1"

# Instance types for the hyperscaler benchmark (master doc: p5 = H100, p4d/p4de = A100).
# H200/B200 rows included for context on hardware-generation drift.
TARGETS = {
    "p4d.24xlarge": ("A100-40GB", 8),
    "p4de.24xlarge": ("A100-80GB", 8),
    "p5.48xlarge": ("H100-80GB", 8),
    "p5e.48xlarge": ("H200", 8),
    "p5en.48xlarge": ("H200", 8),
    "p6-b200.48xlarge": ("B200", 8),
}

FIELDS = [
    "offer_version", "version_effective_begin", "version_effective_end",
    "instance_type", "gpu_model", "gpu_count", "sku", "operating_system",
    "pre_installed_sw", "tenancy", "capacity_status", "market_option",
    "offer_term_code", "rate_code", "unit", "price_usd_per_instance_hr",
    "price_usd_per_gpu_hr", "description",
]


def http_get(url, timeout=300):
    req = urllib.request.Request(url, headers={"User-Agent": "depin-research/0.1"})
    return urllib.request.urlopen(req, timeout=timeout)


def extract_version(version, meta, writer):
    """Stream one offer version file, return number of rows written."""
    url = f"{BASE}/offers/v1.0/aws/AmazonEC2/{version}/{REGION}/index.json"
    rows = 0
    with http_get(url) as resp:
        # products precede terms in the file, so a single pass suffices
        skus = {}  # sku -> product attributes
        parser = ijson.parse(resp)
        # Walk events manually for speed: capture products.<sku> objects whose
        # attributes.instanceType is a target, then terms.OnDemand.<sku>.
        builder = None
        prefix_root = None
        for prefix, event, value in parser:
            if event == "start_map" and (
                (prefix.count(".") == 1 and prefix.startswith("products."))
                or (prefix.count(".") == 2 and prefix.startswith("terms.OnDemand."))
            ):
                # cheap gate: for terms, only build if sku captured
                if prefix.startswith("terms.OnDemand."):
                    sku = prefix.split(".")[2]
                    if sku not in skus:
                        builder = None
                        prefix_root = None
                        continue
                builder = ijson.ObjectBuilder()
                builder.event(event, value)
                prefix_root = prefix
            elif builder is not None:
                builder.event(event, value)
                if event == "end_map" and prefix == prefix_root:
                    obj = builder.value
                    if prefix_root.startswith("products."):
                        attrs = obj.get("attributes", {})
                        it = attrs.get("instanceType")
                        if it in TARGETS:
                            skus[obj.get("sku") or prefix_root.split(".")[1]] = attrs
                    else:
                        sku = prefix_root.split(".")[2]
                        attrs = skus[sku]
                        it = attrs["instanceType"]
                        gpu_model, gpu_count = TARGETS[it]
                        for term_key, term in obj.items():
                            for rate_code, dim in term.get("priceDimensions", {}).items():
                                usd = dim.get("pricePerUnit", {}).get("USD")
                                price = float(usd) if usd else None
                                writer.writerow({
                                    "offer_version": version,
                                    "version_effective_begin": meta.get("versionEffectiveBeginDate", ""),
                                    "version_effective_end": meta.get("versionEffectiveEndDate", ""),
                                    "instance_type": it,
                                    "gpu_model": gpu_model,
                                    "gpu_count": gpu_count,
                                    "sku": sku,
                                    "operating_system": attrs.get("operatingSystem", ""),
                                    "pre_installed_sw": attrs.get("preInstalledSw", ""),
                                    "tenancy": attrs.get("tenancy", ""),
                                    "capacity_status": attrs.get("capacitystatus", ""),
                                    "market_option": attrs.get("marketoption", ""),
                                    "offer_term_code": term_key.split(".")[-1],
                                    "rate_code": rate_code,
                                    "unit": dim.get("unit", ""),
                                    "price_usd_per_instance_hr": usd,
                                    "price_usd_per_gpu_hr": (round(price / gpu_count, 6) if price else None),
                                    "description": dim.get("description", ""),
                                })
                                rows += 1
                    builder = None
                    prefix_root = None
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="20230101")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "raw", "aws"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    with http_get(INDEX) as r:
        index = json.load(r)
    versions = {k: v for k, v in sorted(index["versions"].items()) if k >= args.since}
    print(f"{len(versions)} offer versions since {args.since}", flush=True)

    out_csv = os.path.join(args.out, "ec2_gpu_ondemand_history.csv")
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for i, (version, meta) in enumerate(versions.items(), 1):
            t0 = time.time()
            n = extract_version(version, meta, writer)
            f.flush()
            print(f"[{i}/{len(versions)}] {version} ({meta.get('versionEffectiveBeginDate','')[:10]}): "
                  f"{n} rows in {time.time()-t0:.0f}s", flush=True)

    prov = {
        "dataset": "AWS EC2 on-demand GPU pricing, us-east-1, monthly offer versions",
        "source": "AWS Price List Bulk API",
        "endpoint": f"{BASE}/offers/v1.0/aws/AmazonEC2/{{version}}/{REGION}/index.json",
        "version_index": INDEX,
        "pull_date_utc": datetime.now(timezone.utc).isoformat(),
        "instance_types": sorted(TARGETS),
        "notes": [
            "Per-GPU-hour price = instance price / GPU count; bundled CPU/RAM/NVMe biases the DePIN gap upward (documented in master doc).",
            "On-demand only. Spot price history requires an authenticated AWS account (DescribeSpotPriceHistory, 90-day window) and is collected separately.",
            "All capacity_status/tenancy/OS variants kept in raw layer; filter to Linux/Shared/Used/NA in processed layer.",
        ],
    }
    with open(os.path.join(args.out, "provenance_aws.json"), "w") as f:
        json.dump(prov, f, indent=2)
    print("done:", out_csv, flush=True)


if __name__ == "__main__":
    main()
