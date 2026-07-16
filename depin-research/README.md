# DePIN GPU pricing paper — data research package

Working directory for the empirical layer of *"Can Decentralized Compute
Markets Undercut Hyperscale Cloud Pricing? Evidence from DePIN GPU
Marketplaces"* (master document of 2026-07; Grigory Yusufov). Assembled
2026-07-16 inside a network-restricted sandbox — everything reachable was
pulled and processed; everything blocked got a runnable script + documented
recovery path.

## Status at a glance

| Master-doc dataset | Status | Where |
|---|---|---|
| Hyperscaler benchmark (AWS p5/p4d, us-east-1) | ✅ **DONE — monthly series 2023-01→2026-07, primary source** | `data/processed/aws_gpu_benchmark_monthly.csv` |
| AKT/USD daily | 🟡 market cap + volume 2021→2026-05 in hand (Coin Metrics); full price series = one script run on your machine | `data/processed/akt_market_daily.csv`, `scripts/pull_akt_usd.py` |
| Emissions/incentives (H2) | 🟡 regime table hand-collected, 2 rows flagged VERIFY; realized-emissions series scripted | `data/raw/akash/emissions_incentives_table.csv`, `docs/emissions_incentives_notes.md` |
| Akash lease/bid prices (THE go/no-go) | 🟡 endpoints mapped from source code; live depth probe + snapshot campaign ready to run | `docs/step0_findings.md`, `scripts/probe_pipeline.py`, `scripts/snapshot_gpu_prices.py` |
| Quality flags (H3) | ⬜ rides on the executed-lease path (Numia/indexer) | `docs/step0_findings.md` |

**Step 0 provisional verdict: YELLOW** (see `docs/step0_findings.md`) — daily
network aggregates since genesis + AKT/USD + AWS benchmark are certain;
model-level *price* history has no public history endpoint, so: start the
snapshot campaign immediately, check Wayback coverage, and use Numia BigQuery
for executed-lease history (the potential GREEN-flip).

## Headline empirical facts already in hand

- **AWS kept GPU on-demand prices flat for 29 months, then cut once (June
  2025): p5/H100 −44.0% ($98.32→$55.04/instance-hr, i.e. $12.29→$6.88 per
  GPU-hr), p4d/A100 −33.0%, p5en/H200 −25.4%.** Flat again since. A clean
  structural-break candidate for Test 1 and a dating anchor for "capacity
  events" in the gap-persistence regression.
- Akash emission regimes moved sharply: bounds 5–15% (2023) → 13–20% (Jan
  2024) → 8–13% (Aug 2024) → 4–8% (Mar 2025) → usage-driven BURN from Mar 23,
  2026 (BME). Five exogenous-ish break dates for H2.

## Run order (your machine, ~30 min + one AWS-account task)

```bash
cd depin-research
python3 scripts/probe_pipeline.py          # Step 0 gate: prints GREEN/YELLOW/RED
python3 scripts/pull_akt_usd.py            # full AKT/USD daily
python3 scripts/snapshot_gpu_prices.py     # day 1 of the price snapshot campaign
# then enable docs/snapshot_workflow_template.yml as a GitHub Action (or cron)
python3 scripts/build_panel.py             # assembles data/processed/panel_daily.csv
```

Manual tasks (each documented in docs/):
1. Archive the Sunrun release as PDF (5 min — `docs/sunrun_release.md`).
2. Verify the two flagged governance rows on Mintscan/Polkachu (10 min).
3. AWS spot: `DescribeSpotPriceHistory` only serves ~90 days — start archiving
   it now from any AWS account, or the spot comparator becomes recent-window only.
4. (Unlocks executed-lease medians + H3 audited flags) free GCP project →
   Numia public Akash dataset → SQL over bid/lease events.

## Layout

```
scripts/    pull_aws_gpu_pricing.py  process_aws.py  process_akt.py
            probe_pipeline.py  snapshot_gpu_prices.py  pull_akt_usd.py  build_panel.py
data/raw/        aws/  coinmetrics/  akash/          (raw layer — untouched)
data/processed/  aws_gpu_benchmark_monthly.csv  akt_market_daily.csv
docs/       step0_findings.md  emissions_incentives_notes.md  sunrun_release.md
            provenance.md  snapshot_workflow_template.yml
CODEBOOK.md      variable / unit / source / transformation (prep rule 7)
```

Prep discipline per master doc: raw untouched + provenance (`docs/provenance.md`);
cleaning script-only and reproducible; UTC everywhere; missing days logged not
filled; aggregation rule = median of executed leases (posted asks are logged
separately and labeled as such in `price_kind`).
