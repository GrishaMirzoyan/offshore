#!/usr/bin/env python3
"""Raw -> processed: monthly AWS on-demand GPU benchmark for us-east-1.

Input : data/raw/aws/ec2_gpu_ondemand_history.csv (all variants kept raw)
Filter: operating_system=Linux, pre_installed_sw=NA, tenancy=Shared,
        capacity_status=Used, market_option=OnDemand  (the honest on-demand
        Linux rate; everything else is reservations/unused-capacity variants)
Output: data/processed/aws_gpu_benchmark_monthly.csv
        + prints every month-over-month price change (structural-break candidates)
"""

import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw", "aws", "ec2_gpu_ondemand_history.csv")
OUT = os.path.join(HERE, "..", "data", "processed", "aws_gpu_benchmark_monthly.csv")


def main():
    rows = [r for r in csv.DictReader(open(RAW))
            if r["operating_system"] == "Linux" and r["pre_installed_sw"] == "NA"
            and r["tenancy"] == "Shared" and r["capacity_status"] == "Used"
            and r["market_option"] == "OnDemand" and r["unit"] == "Hrs"
            and float(r["price_usd_per_instance_hr"] or 0) > 0]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "instance_type", "gpu_model", "gpu_count",
                    "price_usd_per_instance_hr", "price_usd_per_gpu_hr", "offer_version"])
        series = defaultdict(list)
        for r in sorted(rows, key=lambda r: (r["instance_type"], r["offer_version"])):
            month = r["version_effective_begin"][:7]
            w.writerow([month, r["instance_type"], r["gpu_model"], r["gpu_count"],
                        r["price_usd_per_instance_hr"], r["price_usd_per_gpu_hr"], r["offer_version"]])
            series[r["instance_type"]].append((month, float(r["price_usd_per_instance_hr"])))

    print(f"wrote {OUT} ({sum(len(v) for v in series.values())} rows)\n")
    print("Price changes (month, instance, old -> new, %):")
    for it, pts in sorted(series.items()):
        for (m0, p0), (m1, p1) in zip(pts, pts[1:]):
            if abs(p1 - p0) > 1e-9:
                print(f"  {m1}  {it:18s} {p0:10.4f} -> {p1:10.4f}  ({(p1/p0-1)*100:+.1f}%)")


if __name__ == "__main__":
    main()
